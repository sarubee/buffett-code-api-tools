#!/usr/bin/env python

#   Copyright 2019 Sarubee
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
bc_api.py
"""

import pandas as pd
import requests
import time  
import math
from urllib.parse import urljoin
from pathlib import Path
import traceback 
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)

class BCFetchStopped(Exception):
    pass
class BCFetchError(RuntimeError):
    pass
class BCExceededFetchError(BCFetchError):
    pass

class BCAPI:
    # 取得元
    URL_API = "https://api.buffett-code.com/api/v2/"

    # 取得制限銘柄数・期間
    MAX_NUM_COMPANY = 3
    MAX_NUM_YEAR = 3

    def __init__(self, api_key):
        self.api_key = api_key
        self.stop_fetch = False # fetch を途中でやめるためのフラグ

    @staticmethod
    def __get(url, params, headers):
        """API データ取得用の基本関数

        Parameters
        ----------
        url : str 
            データ取得先 URL
        params : dict 
            取得用パラメータ
        headers : dict 
            取得用ヘッダ

        Returns
        -------
        dict 
            取得したデータ
        """

        # データ取得
        # 終わったら負荷をかけないように 1 秒休む
        d = requests.get(url, params=params, headers=headers).json()
        time.sleep(1)
        # エラー時にはメッセージが "message" キーに格納されている
        if "message" in d:
            if d["message"] == "Limit Exceeded":
                raise BCExceededFetchError(f"Fetching Error: {d['message']}")
            else:
                raise BCFetchError(f"Fetching Error: {d['message']}")
        return d

    def get_quarter_directly(self, tickers, start, end):
        """引数をそのまま渡す四半期データ取得用関数

        Parameters
        ----------
        tickers : list 
            取得する銘柄コード
        start : str
            開始四半期 (ex. "2012Q1")
        end : str
            終了四半期 (ex. "2015Q4")

        Returns
        -------
        dict 
            取得したデータ
        """

        url =  urljoin(self.URL_API, "quarter")
        ticker_str = ",".join(map(str, tickers))
        params =  {"tickers" : ticker_str, "from" : start, "to" : end}
        headers = {"x-api-key" : self.api_key}

        logger.info(f"getting quarter data (tickers: {tickers}, start: {start}, end: {end}) ...")
        return BCAPI.__get(url, params, headers)

    def get_indicator_directly(self, tickers):
        """引数をそのまま渡す指標データ取得用関数

        Parameters
        ----------
        tickers : list 
            取得する銘柄コード

        Returns
        -------
        dict 
            取得したデータ
        """

        url =  urljoin(self.URL_API, "indicator")
        ticker_str = ",".join(map(str, tickers))
        params =  {"tickers" : ticker_str}
        headers = {"x-api-key" : self.api_key}

        logger.info(f"getting indicator data (tickers: {tickers}) ...")
        return BCAPI.__get(url, params, headers)

    def get_company_directly(self):
        """会社データ取得用関数

        Returns
        -------
        dict 
            取得したデータ
        """

        url =  urljoin(self.URL_API, "company")
        params =  {}
        headers = {"x-api-key" : self.api_key}

        logger.info(f"getting company data ...")
        return BCAPI.__get(url, params, headers)

    def __fetch_safe(self, retry, func, *args, **kwargs):
        """retry を行いつつ指定関数を実行しデータを取得

        Parameters
        ----------
        retry : int 
            エラーが起きた場合のリトライ間隔 [minites]
            負数ならリトライしない。
            NOTE: 取得制限に引っかかった場合はこの値とは関係な 24h 待つ。
        func : function 
            実行関数

        Returns
        -------
        dict 
            取得したデータ
        """
        retry_time = datetime(1,1,1,0,0,0,000000) # 適当に小さい値に初期化 
        d = None

        while not self.stop_fetch:
            if datetime.now() < retry_time:
                sleep(1)
                continue
            try:
                d = func(*args, **kwargs)
            except BCExceededFetchError as e:
                # 24時間休んで retry
                logger.warn(e.args)
                logger.warn(f"Wait for 1 day...")
                retry_time = datetime.now() + timedelta(days=1)  
                continue
            except:
                if retry < 0:
                    raise
                else:
                    logger.error(traceback.print_exc())
                    logger.error(f"Wait for {retry} minutes...")
                    retry_time = datetime.now() + timedelta(seconds=retry*60)  
                    continue
            break
        else:
            # stop フラグが設定された
            raise BCFetchStopped()
        return d

    @staticmethod
    def __sliced_tickers_generator(tickers):
        """ 一度の fetch で指定できる企業数(3つ) に制限があるので小分け

        Parameters
        ----------
        tickers : list 
            銘柄コード

        Yields 
        -------
        list 
            小分けされた銘柄コード
        """

        for i in range(math.ceil(len(tickers) / BCAPI.MAX_NUM_COMPANY)):
            j = i * BCAPI.MAX_NUM_COMPANY
            ts = tickers[j:j+BCAPI.MAX_NUM_COMPANY]
            yield ts

    @staticmethod
    def __sliced_quarters_generator(start, end):
        """ 一度の fetch で指定できる期間（3年）に制限があるので小分け
        Parameters
        ----------
        start : str
            開始四半期 (ex. "2012Q1")
        end : str
            終了四半期 (ex. "2015Q4")

        Yields 
        -------
        list 
            小分けされた四半期期間 (ex. ["2012Q1", "2014Q4"])
        """

        # 次/前の四半期を求める内部関数
        def __next_q(year, quarter):
            if quarter > 3:
                y = year + 1
                q = 1
            else:
                y = year
                q = quarter + 1
            return [y, q]
        def __prev_q(year, quarter):
            if quarter < 2:
                y = year - 1
                q = 4 
            else:
                y = year
                q = quarter - 1
            return [y, q]

        # self.MAX_NUM_YEAR ごとに小分け
        sy, sq = [int(s) for s in start.split("Q")]
        ey, eq = orig_ey, orig_eq= [int(s) for s in end.split("Q")]
        while True:
            dy = ey - sy
            dq = eq - sq
            if dy > BCAPI.MAX_NUM_YEAR or (dy == BCAPI.MAX_NUM_YEAR and dq >= 0): 
                ey_tmp, eq_tmp = __prev_q(sy + BCAPI.MAX_NUM_YEAR, sq)
                yield [f"{sy}Q{sq}", f"{ey_tmp}Q{eq_tmp}"]
                sy, sq = __next_q(ey_tmp, eq_tmp) 
            else:
                yield [f"{sy}Q{sq}", f"{ey}Q{eq}"]
                break

    def get_quarter(self, tickers, start, end, func=None, retry=-1):
        """諸々の調整をしつつ四半期財務データを取得

        年は年度(始まるときの年)、Qは企業別に第何四半期か、のようだ。

        Parameters
        ----------
        tickers : list 
            取得する銘柄コード
        start : str
            開始四半期 (ex. "2012Q1")
        end : str
            終了四半期 (ex. "2015Q4")
        func : function 
            取得データに対して逐次実行する後処理
            多数取得する場合は何らかの要因で中断しがちなので func で逐次処理できるようにしてある。
        retry :  int 
            エラーが起きた場合のリトライ間隔 [minites]
            負数ならリトライしない。
            NOTE: 取得制限に引っかかった場合はこの値とは関係なく 24h 待つ。

        Returns
        -------
        list 
            取得した四半期データ(要素は pandas.DataFrame)
        """

        # ticker を小分けしつつ実行
        results = [] 
        col_dict = None
        try:
            for ts in BCAPI.__sliced_tickers_generator(tickers): 
                # 期間を小分けしつつ実行
                results_ts = [] 
                for i, p in enumerate(BCAPI.__sliced_quarters_generator(start, end)): 
                    # 取得
                    d = self.__fetch_safe(retry, self.get_quarter_directly, ts, p[0], p[1])

                    # 列定義
                    if col_dict is None:
                        col_dict = d["column_description"]
                    elif col_dict != d["column_description"]:
                        # ありえる？一応エラーにしておく
                        raise RuntimeError(f"column definition is not unique!!")
                    # dataframe 化 
                    dfs = []
                    for t in ts:
                        l = d[str(t)]
                        if l is None or len(l) < 1: 
                            dfs.append(None)
                            continue
                        df = pd.DataFrame(l)
                        df["ticker"] = t
                        df.set_index(["ticker", "fiscal_year", "fiscal_quarter"], inplace=True)
                        df.sort_index(inplace=True)
                        # NOTE: 四半期データで重複している場合があった。どれが正しいかは不明・・・だがとりあえず重複を削除する
                        df = df[~df.index.duplicated(keep="last")]
                        df.reset_index(inplace=True)

                        dfs.append(df)

                    # 各期間の結果を結合 
                    if i < 1:
                        results_ts = dfs
                        continue
                    for j, df in enumerate(dfs):
                        if results_ts[j] is None:
                            results_ts[j] = df
                        elif df is not None:
                            results_ts[j] = pd.concat([results_ts[j], df])

                # func が指定されていればここで各 df に対して実行。
                if func is not None:
                    for j, df in enumerate(results_ts):
                        func(ts[j], df, col_dict)
                results += results_ts 
        except BCFetchStopped:
            pass

        return results, col_dict

    def get_indicator(self, tickers, func=None, retry=-1):
        """諸々の調整をしつつ指標データを取得

        Parameters
        ----------
        tickers : list 
            取得する銘柄コード
        func : function 
            取得データに対して逐次実行する後処理
            多数取得する場合は何らかの要因で中断しがちなので func で逐次処理できるようにしてある。
        retry :  int 
            エラーが起きた場合のリトライ間隔 [minites]
            負数ならリトライしない。
            NOTE: 取得制限に引っかかった場合はこの値とは関係なく 24h 待つ。

        Returns
        -------
        list 
            取得した四半期データ(要素は pandas.DataFrame)
        """
        # ticker を小分けしつつ実行
        results = [] 
        col_dict = None
        try:
            for ts in BCAPI.__sliced_tickers_generator(tickers):
                # 取得
                d = self.__fetch_safe(retry, self.get_indicator_directly, ts)
                # 列定義
                if col_dict is None:
                    col_dict = d["column_description"]
                elif col_dict != d["column_description"]:
                    # ありえる？一応エラーにしておく
                    raise RuntimeError(f"column definition is not uniq!!")
                # dataframe 化 
                dfs = []
                for t in ts:
                    l = d[str(t)]
                    if l is None or len(l) < 1: 
                        dfs.append(None)
                        continue
                    df = pd.DataFrame({"ticker" : t, **l[0]}, index=[0])
                    dfs.append(df)
                # func が指定されていればここで各 df に対して実行。
                if func is not None:
                    for i, df in enumerate(dfs):
                        func(ts[i], df, col_dict)
                results.extend(dfs)
        except BCFetchStopped:
            pass

        return results, col_dict

    def get_company(self, retry=-1):
        """会社データを取得

        Parameters
        ----------
        retry :  int 
            エラーが起きた場合のリトライ間隔 [minites]
            負数ならリトライしない。
            NOTE: 取得制限に引っかかった場合はこの値とは関係なく 24h 待つ。

        Returns
        -------
        list 
            取得した会社データ(要素は pandas.DataFrame)
        """

        try:
            # 取得
            d = self.__fetch_safe(retry, self.get_company_directly)
        except BCFetchStopped:
            return None, {}
        # 列定義
        col_dict = d.pop("column_description")

        dfs = []
        for k, v in d.items():
            df = pd.Series({"ticker" : k, **v[0]})
            # NOTE: 英語会社名にダブルクォーテーションがついたりつかなかったりする場合があるので削っておく
            df["company_name_en"] = str(df["company_name_en"]).replace('"', '')
            dfs.append(df)
        result = pd.DataFrame(dfs)

        return result, col_dict

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
bc_data.py
"""

from pathlib import Path
import pickle 
import numpy as np 
import matplotlib.pyplot as plt 
from matplotlib.backend_bases import MouseButton
import webbrowser 
import json
import re 
from abc import ABCMeta, abstractmethod
import time
import logging
logger = logging.getLogger(__name__)

from bc_api import *

class BCDataCompany():
    """
    会社情報データクラス

    Attributes
    ----------
    data : pd.DataFrame
        データ
    dic : dic 
        列名定義辞書

    """
    def __init__(self, data, dic):
        self.data = data
        self.dic = dic

    def tickers(self): 
        return list(self.data["ticker"])

class BCDataAbs(metaclass=ABCMeta):
    """
    データ要素 (indicator, quarter) の抽象基底クラス

    Attributes
    ----------
    data : pd.DataFrame
        データ
    dic : dic 
        列名定義辞書
    """

    @abstractmethod
    def __init__(self, data, dic):
        self.data = data
        self.dic = dic

    @abstractmethod
    def get_values(self, query): 
        # 派生クラスに移譲
        pass

    @staticmethod
    def replace_value_str(str_list, columns, df_name):
        """
        str_list に含まれる列名 (columns で定義) を eval で使う文字列に置換。 ex) "pbr" -> f"{df_name}['pbr']" 
        NOTE: 列名が他の列名の一部になっているケースがある。
              長いものから置き換えていき、さらに再置換しないよう(ダブル)クォーテーションに囲まれたものは置換しないようにする
        """
        for c in sorted(columns, key=lambda s: len(s), reverse=True):
            def __replace_val(m):
                s = m.group()
                b =  s if s.startswith(("'", "\"")) else s.replace(c, f"{df_name}['{c}']")
                return b
            str_list = [re.sub(r"'[^'\"]*'|\"[^'\"]*\"|[^'\"]*", __replace_val, s) for s in str_list]
        return str_list 

class BCDataQuarter(BCDataAbs): 
    """
    四半期財務データクラス
    """

    def __init__(self, data, dic):
        super().__init__(data, dic)

    def get_values(self, query): 
        """
        指定値の取得
        NOTE: 最終年の Q4 データから取得する。ただし、cagr(), mean() は各年 Q4 データを使って算出。
        """
        str_list = query.values()
        df = self.data

        # 使う列だけ抜き出しておく
        columns = [c for c in df.columns if any([c in s for s in str_list])]
        if len(columns) < 1:
            return None
        columns += ["ticker", "fiscal_year", "fiscal_quarter"]
        # Q4 データが対象
        y = df.loc[df["fiscal_quarter"] == 4, columns]
        if any(["cagr" in s for s in str_list]):
            # 成長率を求める場合は fiscal_year を index に指定しておく。
            # NOTE: set_index するとちょっと遅くなる。
            y.set_index("fiscal_year", inplace=True)

        def cagr(series, n=None, all_plus=False):
            """
            年間成長率を算出
            Parameters
            ----------
            series : pandas.Series 
                対象 Q4 データ
            n : int 
                何年分のデータを使って計算するか
            all_plus : bool 
                True ならすべて年次プラス成長の場合だけ値を返す
            """
            if series.isnull().all() or len(series) < 2:
                return np.nan
            years = list(series.index.get_level_values("fiscal_year").values)

            ey = years[-1]
            e = float(series.iloc[-1])
            sy = years[0] if n is None else ey - n
            try:
                i = years.index(sy)
            except:
                return np.nan
            s = float(series.iloc[i])
            if not (s > 0 and e > 0): 
                return np.nan  
            val = ((e / s) ** (1 / (ey - sy)) - 1) * 100.0 

            if all_plus:
                c = series[i:].pct_change().dropna()
                if (c < 0).any():
                    return np.nan
            return val
        def mean(v):
            """
            平均値を算出
            TODO: n 指定?
            """
            if v.isnull().all():
                return np.nan
            return(np.nanmean(v))
    
        # 取得文字列置換
        str_list = BCDataAbs.replace_value_str(str_list, y.columns, "d")

        exec_locals = locals()
        def _get_values(d):
            exec_locals.update(locals())
            result = []
            for op in str_list: 
                try:
                    v = eval(op, {}, exec_locals)
                    if isinstance(v, pd.Series):
                        # 最終年のデータを使用
                        v = v.iloc[-1]
                    if v is None:
                        v = np.nan
                except:
                    v = np.nan
                result.append(v)
            return pd.Series(result)

        result = y.groupby("ticker").apply(_get_values)

        result.columns = query.keys()
        return result

class BCDataIndicator(BCDataAbs):
    """
    株価指標データクラス
    """

    def __init__(self, data, dic):
        super().__init__(data, dic)

    def get_values(self, query): 
        """
        指定値の取得
        """
        str_list = query.values()
        df = self.data

        # 使う列だけ抜き出しておく
        columns = [c for c in df.columns if any([c in s for s in str_list])]
        if len(columns) < 1:
            return None
        columns += ["ticker", "day"]
        df = df.loc[:, columns]

        # 取得文字列置換
        str_list = BCDataAbs.replace_value_str(str_list, df.columns, "d")

        exec_locals = locals()
        def _get_values(d):
            exec_locals.update(locals())
            result = []
            for op in str_list: 
                try:
                    v = eval(op, {}, exec_locals)[0]
                    if v is None:
                        v = np.nan 
                except:
                    v = np.nan
                result.append(v)
            return pd.Series(result)
        result = df.groupby("ticker").apply(_get_values)
        result.columns = query.keys()
        return result

def _read_csv(p):
    return pd.read_csv(p)
def _read_pickle(p):
    with open(p, mode = "rb") as f:
        return pickle.load(f)
def _read_json(p):
    with open(p, mode = "r") as f:
            return json.load(f)

class BCData:
    """
    バフェットコード API データを扱う

    Attributes
    ----------
    root_dir : Path
        ルートディレクトリ
    company : BCDataCompany
        会社データ
    quarter : BCDataQuarter
        四半期財務データ
    indicator : BCDataIndicator 
        株価指標データ
    plot_caches : pd.DataFrame
        プロット用データのキャッシュ 
    """

    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)

        self.company = None
        self.quarter = None
        self.indicator = None

        # ディレクトリ指定があれば読みこみ
        self.load_company()
        self.load_quarter()
        self.load_indicator()

        self.plot_caches = pd.DataFrame() 

    def load_company(self):
        d = self.root_dir / "company"
        csv = d / "company.csv"
        json = d / "columns.json"
        if not (d.exists() and csv.exists() and json.exists()):
            logger.warn(f"could not load company data")
            self.company = None
        else:
            self.company = BCDataCompany(_read_csv(csv), _read_json(json))
    def load_quarter(self):
        d = self.root_dir / "quarter"
        pkl = d / "all.pickle"
        json = d / "columns.json"
        if not (d.exists() and pkl.exists() and json.exists()):
            logger.warn(f"could not load quarter data")
            self.quarter = None
        else:
            self.quarter = BCDataQuarter(_read_pickle(pkl), _read_json(json))
    def load_indicator(self):
        d = self.root_dir / "indicator"
        pkl = d / "all.pickle"
        json = d / "columns.json"
        if not (d.exists() and pkl.exists() and json.exists()):
            logger.warn(f"could not load indicator data")
            self.indicator = None
        else:
            self.indicator = BCDataIndicator(_read_pickle(pkl), _read_json(json))

    def fetch_company(self, api, retry=-1, overwrite=False):
        """API 指標データ取得関数

        API でデータを取得し、self.rootdir/company/ 以下に
         * company.csv
         * columns.json     # 列名定義 
         を出力する。

        Parameters
        ----------
        api : BCAPI インスタンス 
        retry : int 
            エラーが起きた場合のリトライ間隔 [minites]
            負数ならリトライしない。
            NOTE: 取得制限に引っかかった場合はこの値とは関係な 24h 待つ。
        overwrite: bool
            既存のCSVを上書きするか
        """

        d = self.root_dir / "company"
        d.mkdir(parents=True, exist_ok=True)
        outpath_csv = d / "company.csv"
        outpath_json = d / "columns.json" 

        if outpath_csv.exists() and not overwrite:
            logger.warn(f"'company.csv' already exists! Skipped fetching.")
            return

        # API からデータ取得
        df, dic = api.get_company(retry)
        logger.info(f"making '{outpath_csv}' ...")
        df.to_csv(outpath_csv, index=False, encoding="utf_8_sig")
        with open(outpath_json, "w") as f:
            json.dump(dic, f, ensure_ascii=False, indent=4)

        self.load_company()

    def __fetch_elem(self, mode, api, retry=-1, overwrite=False, config=None):
        """API データ(quarter, indicator) 取得内部関数

        Parameters
        ----------
        mode : str
            取得対象 ("quarter" or "indicator")
        api : BCAPI インスタンス 
        retry : int 
        overwrite: bool
        config: dict
            mode 固有の追加情報
                * quarter の場合
                    start : str
                        開始年 (ex. "2012")
                    end : str
                        終了年 (ex. "2015")
        """

        def __make_all_pickle(outdir):
            """
            指定ディレクトリ以下の CSV ファイルをまとめた pickle ファイルを出力する。
            """
            outpath = f"{outdir}/all.pickle"
            logger.info(f"converting '{outdir}/*.csv' to '{outpath}' ...")
            dfs = []
            for p in sorted(list(Path(outdir).glob("*.csv"))):
                dfs.append(pd.read_csv(p))
            all_df = pd.concat(dfs, sort=False)
            all_df.to_pickle(outpath)

        if self.company is None:
            raise RuntimeError(f"company is not loaded!")
        tickers = self.company.tickers()

        if mode == "quarter":
            outdir = self.root_dir / "quarter"
        elif mode == "indicator":
            outdir = self.root_dir / "indicator"
        else:
            raise RuntimeError(f"invalid mode {mode}")

        outdir.mkdir(parents=True, exist_ok=True)

        exist_tickers = [int(p.stem) for p in list(Path(outdir).glob("*.csv"))]
        undefined_tickers = list(set(exist_tickers) - set(tickers))
        if len(undefined_tickers) > 0:
            # 指定外の銘柄の CSV が存在。ファイル削除する？
            logger.warn(f"CSVs with invalid tickers exist ({undefined_tickers})!!")
        # overwrite==False なら既に取得済みのものは飛ばす
        if not overwrite:
            targets = list(set(tickers) - set(exist_tickers))
        else:
            targets = tickers
        targets.sort()

        if len(targets) < 1:
            logger.warn(f"Target tickers are empty!!")
        else:
            columns_outpath = outdir / "columns.json" 
            need_output_columns = overwrite or not columns_outpath.exists()

            def _write_csv(ticker, df, col_dict):
                nonlocal need_output_columns
                if df is not None:
                    outpath = f"{outdir}/{ticker}.csv"
                    logger.info(f"making '{outpath}' ...")
                    df.to_csv(outpath, index=False, encoding="utf_8_sig")
                if need_output_columns:
                    # 最初の一回だけ出力
                    with open(columns_outpath, "w") as f:
                        json.dump(col_dict, f, ensure_ascii=False, indent=4)
                    need_output_columns = False 

            # API からデータ取得
            if mode == "quarter":
                # 開始は Q1, 終了は Q4 で固定
                start_q = f"{config['start']}Q1"
                end_q = f"{config['end']}Q4"
                api.get_quarter(targets, start_q, end_q, _write_csv, retry)
            elif mode == "indicator":
                api.get_indicator(targets, _write_csv, retry)
        # 終わったら全部をまとめた pickle ファイルを作っておく
        __make_all_pickle(outdir) 
        if mode == "quarter":
            self.load_quarter()
        if mode == "indicator":
            self.load_indicator()

    def fetch_quarter(self, api, start, end, retry=-1, overwrite=False):
        """API 四半期データ取得関数

        API でデータを取得し、指定ディレクトリ以下に
         * {銘柄コード}.csv
         * columns.json     # 列名定義 
         * all.pickle       # 全銘柄分を連結した dataframe
         を出力する。

        Parameters
        ----------
        api : BCAPI インスタンス 
        start : str
            開始年 (ex. "2012")
        end : str
            終了年 (ex. "2015")
        retry : int 
            エラーが起きた場合のリトライ間隔 [minites]
            負数ならリトライしない。
            NOTE: 取得制限に引っかかった場合はこの値とは関係な 24h 待つ。
        overwrite: bool
            既存の CSV を上書きするか
        """
        self.__fetch_elem("quarter", api, retry, overwrite, config={"start":start, "end":end})

    def fetch_indicator(self, api, retry=-1, overwrite=False):
        """API 指標データ取得関数

        API でデータを取得し、指定ディレクトリ以下に
         * {銘柄コード}.csv
         * columns.json     # 列名定義 
         * all.pickle       # 全銘柄分を連結した dataframe
         を出力する。

        Parameters
        ----------
        api : BCAPI インスタンス 
        retry : int 
            エラーが起きた場合のリトライ間隔 [minites]
            負数ならリトライしない。
            NOTE: 取得制限に引っかかった場合はこの値とは関係な 24h 待つ。
        overwrite: bool
            既存の各 CSV データを上書きするか
        """
        self.__fetch_elem("indicator", api, retry, overwrite, config={})

    def get_plot_values(self, val_dict):
        """
        プロットに使う値を取得
        """

        result = pd.DataFrame() 
        query = {} 
        for k, v in val_dict.items():
            # TODO: 空白詰める
            if v in self.plot_caches.columns:
                # キャッシュあったらそれを使う
                logger.debug(f"cache hit! {v}")
                result[k] = self.plot_caches[v]
            else:
                query[k] =  v
                
        if len(query) > 0:
            vals = pd.DataFrame()
            start = time.time()
            i_vals = self.indicator.get_values(query) if self.indicator is not None else None
            logger.debug(f"self.indicator.get_values() TIME: {time.time() - start}")
            #  すべて nan の列があったら quarter のほうも見る
            if i_vals is None or np.isnan(i_vals.astype(float)).all().any() and self.quarter is not None:
                start = time.time()
                q_vals = self.quarter.get_values(query)
                logger.debug(f"self.quarter.get_values() TIME: {time.time() - start}")
                if i_vals is None: 
                    vals = q_vals
                else:
                    for col, item in i_vals.iteritems():
                        if not np.isnan(item.astype(float)).all():
                            vals[col] = item
                        else:
                            vals[col] = q_vals[col] 
            else:
                vals = i_vals
            # 結果格納
            if vals is not None:
                result = pd.concat([result, vals], axis=1, sort=True)
                result.index.name = "ticker" # 何故か concat すると名前が落ちる場合がある
            
            # 列を中身に直して重複を除いた上で cache にも追加
            vals.columns = [query[c] for c in vals.columns] 
            vals = vals.loc[:,~vals.columns.duplicated()]
            self.plot_caches = pd.concat([self.plot_caches, vals], axis=1, sort=True)
            self.plot_caches.index.name = "ticker" # 何故か concat すると名前が落ちる場合がある
 
        return result 

    def plot_scatter_clickable(self, fig, ax,
                               x_str, y_str, filter_str=None,
                               size_str=None, size_scale=0.5,
                               category=None,
                               xyline=False,
                               xlim=None, ylim=None,
                               xlabel=None, ylabel=None, slabel=None,
                               click_open_company=False, click_open_arb=[],
                               annotate="mouseover"):
        """
        quarter, indicator データを各銘柄について散布図としてプロットする。
        """
        # TODO: スペース詰めとか他のもまとめてやるべき
        if filter_str is not None and len(filter_str) < 1:
            filter_str = None
        if size_str is not None and len(size_str) < 1:
            size_str = None

        target_dict = {"x" : x_str, "y" : y_str}
        if filter_str is not None:
            target_dict["filter"] = filter_str 
        if size_str is not None:
            target_dict["size"] = size_str 
        df = self.get_plot_values(target_dict)
        # x, y は必須。ないものは除外。
        df = df[~(np.isnan(df["x"]) | np.isnan(df["y"]))]
        
        # 会社情報とマージ。両方に存在しない ticker は除外。
        df.reset_index(drop=False, inplace=True)
        df["ticker"] = df["ticker"].astype(int)
        df = pd.merge(self.company.data, df, on="ticker")

        size_scale = max(size_scale, 0.05)
        size_scale_sq = size_scale ** 2
        if size_str is not None:
            # 適当にサイズは調整 
            max_ = np.nanmax(df["size"])
            df["ssize"] = np.array([s / max_ if s > 0 else np.nan for s in df["size"]]) * size_scale_sq * 10000 
        else:
            df["ssize"] = size_scale_sq * 200 
        # size 指定時に列がないものも除外
        df = df[~(np.isnan(df["ssize"]))]

        if category is not None:
            df = df[df["tosyo_33category"] == category]

        if filter_str is not None:
            len_orig = len(df) 
            df = df[df["filter"]]
            len_filtered = len(df) 
            logger.info(f"filtered: {len_orig} => {len_filtered}")

        # index を振り直す
        df.reset_index(inplace=True) 

        # 各種プロット設定
        default_colors = ["blue"] * len(df)
        coll = ax.scatter(df["x"], df["y"], color=default_colors, s=df["ssize"], alpha=0.3, picker=True)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        xlabel = xlabel if xlabel is not None else x_str
        ylabel = ylabel if ylabel is not None else y_str
        slabel = slabel if slabel is not None else size_str
        ax.set_xlabel(xlabel, fontsize=14)
        ax.set_ylabel(ylabel, fontsize=14)
        ax.grid(True, 'major', 'both', alpha=0.7, linestyle='--')
        if xyline:
            min_ = np.min([ax.get_xlim()[0], ax.get_ylim()[0]]) 
            max_ = np.max([ax.get_xlim()[1], ax.get_ylim()[1]]) 
            lim = [min_, max_]
            ax.plot(lim, lim, color="black", alpha=0.5)
        if annotate == "mouseover":
            an = ax.annotate("", (0, 0), (1, 1), textcoords="offset points")
            an.set_visible(False)
        else: # "all"
            for i, row in df.iterrows():
                ax.annotate(f"{df['ticker'][i]}\n{df['company_name_en'][i]}",
                            xy=(row["x"], row["y"]))

        # interactive 定義
        def _change_color(i):
            colors = list(default_colors)
            if i is not None:
                colors[i] = "red" 
            coll.set_facecolors(colors)
            coll.set_edgecolors(colors)

        def on_motion(event):
            on_plots, items = coll.contains(event)
            if on_plots:
                i = items["ind"][0] 
                _change_color(i)
                if annotate == "mouseover":
                    an.xy = coll.get_offsets()[i]
                    a_text = f"{df['ticker'][i]} {df['company_name_en'][i]}\n" +\
                             f"===============\n" +\
                             f"{xlabel}\n" +\
                             f"{df['x'].iloc[i]}\n" +\
                             f"{ylabel}\n" +\
                             f"{df['y'].iloc[i]}\n"
                    if size_str is not None:
                        a_text += f"{slabel}\n" +\
                                  f"{df['size'].iloc[i]}\n"
                    an.set_text(a_text)
                    an.set_visible(True) 
            else:
                _change_color(None)
                if annotate == "mouseover":
                    an.set_visible(False)
            fig.canvas.draw()
        def on_pick(event):
            if event.mouseevent.button != MouseButton.LEFT:
                return
            i = event.ind[0]
            fig.canvas.draw()
            for url in click_open_arb:
                url = url.replace("TICKER", str(df['ticker'][i]))
                logger.info(f"open {url}")
                webbrowser.open(url)
            if click_open_company:
                url = df["url"][i]
                logger.info(f"open {url}")
                webbrowser.open(url)

        cids = []
        cids.append(fig.canvas.mpl_connect('motion_notify_event', on_motion))
        if click_open_company or len(click_open_arb) > 0:
            cids.append(fig.canvas.mpl_connect('pick_event', on_pick))

        return cids

#!/usr/bin/env python

#   Copyright 2020 Sarubee
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
bc_plot.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseButton
import webbrowser
from abc import ABCMeta, abstractmethod
import logging
logger = logging.getLogger(__name__)

class BCPlotXY(metaclass=ABCMeta):
    """
    scatter, line プロットの抽象基底クラス
    """
    @abstractmethod
    def __init__(self, fig, ax,
                 x, y,
                 xlabel=None, ylabel=None,
                 xlim=None, ylim=None,
                 normalize_idx=None):

        self.fig = fig
        self.ax = ax

        # self.n は [n1, n2, ..., nN]
        # ここで、N は y の系列数、n1 は系列 1 の要素数。
        # self.y/x 等は [[y1_1, ..., y1_n1], [y2_1, ...y2_n2], ..., [yN_1, ..., yN_nN]]
        self.y = y if isinstance(y[0], list) else [y]
        self.n = [len(l) for l in self.y]
        # x。各 y 系列で x が共通の場合は展開
        self.x = x if isinstance(x[0], list) else [x] * len(self.n)
        self.check_length(self.x)

        self.xlabel = xlabel
        self.ylabel = ylabel
        self.xlim = xlim
        self.ylim = ylim

        self.cids = []

    def check_length(self, t, legend_only=False):
        if not (len(t) == len(self.n) and
                (legend_only or all(len(t[i]) == self.n[i] for i in range(len(self.n))))):
            raise RuntimeError("Lengths of plot data are not same!")

    def set_xy_common(self):
        self.ax.set_xlim(self.xlim)
        self.ax.set_ylim(self.ylim)
        self.ax.set_xlabel(self.xlabel, fontsize=14)
        self.ax.set_ylabel(self.ylabel, fontsize=14)
        self.ax.grid(True, 'major', 'both', alpha=0.7, linestyle='--')

    def clear(self):
        self.ax.cla()
        for cid in self.cids:
            self.fig.canvas.mpl_disconnect(cid)
        self.cids = []

class BCPlotLine(BCPlotXY):
    """
    scatter plot クラス
    """
    def __init__(self, fig, ax,
                 x, y, label=None,
                 xlabel=None, ylabel=None,
                 xlim=None, ylim=None,
                 color=None):

        super().__init__(fig, ax, x=x, y=y,
                         xlabel=xlabel, ylabel=ylabel,
                         xlim=xlim, ylim=ylim)

        if label is not None:
            self.check_length(label, True)
        self.label = label
        # color は y の系列で決定
        if color is None:
            # 系列ごとの rainbow カラー分けがデフォルト
            color = plt.cm.rainbow(np.linspace(0, 1, len(self.n)))
        elif not isinstance(color, list):
            # 一つだけ指定されている場合を展開
            color = [color] * len(self.n)
        self.check_length(color, True)
        self.color = color

    def plot(self):
        for i in range(len(self.n)):
            # 各種プロット設定
            self.ax.plot(self.x[i], self.y[i],
                         color=self.color[i],
                         label=self.label[i] if self.label is not None else None)
        self.set_xy_common()
        if self.label is not None:
            self.ax.legend()

    # そのままプロットする版
    @staticmethod
    def exec_plot(fig_size=(10, 10), **kwargs):
        fig = plt.figure(figsize=fig_size)
        ax = fig.add_subplot(1, 1, 1)
        BCPlotLine(fig, ax, **kwargs).plot()
        plt.show()

class BCPlotScatter(BCPlotXY):
    """
    scatter plot クラス
    """
    def __init__(self, fig, ax,
                 x, y, size=20,
                 xlabel=None, ylabel=None, slabel=None,
                 xyline=False,
                 xlim=None, ylim=None,
                 color="blue",
                 click_color="red",
                 click_open_urls=None,
                 annotate="none", annotate_strs=None):

        super().__init__(fig, ax, x=x, y=y,
                         xlabel=xlabel, ylabel=ylabel,
                         xlim=xlim, ylim=ylim)

        def _expand_plot_list(target):
            if not isinstance(target, list):
                # 一つだけ指定されている場合を展開
                result = [[target] * n for n in self.n]
            elif not isinstance(target[0], list):
                # ただのリストなら一つの要素とみなす
                result = [target]
            else:
                # リストのリスト
                # TODO: 各系列が一要素なら展開する？
                result = target
            self.check_length(result)
            return result

        self.size = _expand_plot_list(size)
        self.color = _expand_plot_list(color)
        if click_open_urls is not None:
            click_open_urls = _expand_plot_list(click_open_urls)
        if annotate_strs is not None:
            annotate_strs = _expand_plot_list(annotate_strs)

        self.click_color = click_color
        self.slabel = slabel
        self.xyline = xyline
        self.annotate = annotate

        # TODO: 以下は複数系列対応するまでの暫定措置
        self.x = self.x[0]
        self.y = self.y[0]
        self.size = self.size[0]
        self.color = self.color[0]
        self.click_open_urls = None if click_open_urls is None else click_open_urls[0]
        self.annotate_strs = None if annotate_strs is None else annotate_strs[0]

    def plot(self):
        # 各種プロット設定
        coll = self.ax.scatter(self.x, self.y, color=self.color, s=self.size, alpha=0.3, picker=True)
        self.set_xy_common()
        if self.xyline:
            min_ = np.min([self.ax.get_xlim()[0], self.ax.get_ylim()[0]])
            max_ = np.max([self.ax.get_xlim()[1], self.ax.get_ylim()[1]])
            lim = [min_, max_]
            self.ax.plot(lim, lim, color="black", alpha=0.5)
        annotate_on = False
        if self.annotate == "mouseover":
            an = self.ax.annotate("", (0, 0), (1, 1), textcoords="offset points")
            an.set_visible(False)
            annotate_on = True
        else: # "all"
            for i, (xx, yy) in enumerate(zip(self.x, self.y)):
                self.ax.annotate(self.annotate_strs[i] if self.annotate_strs is not None else None, xy=(xx, yy))

        # interactive 定義
        def _change_color(i):
            color = list(self.color)
            if i is not None:
                color[i] = self.click_color
            coll.set_facecolors(color)
            coll.set_edgecolors(color)

        def on_motion(event):
            on_plots, items = coll.contains(event)
            if on_plots:
                i = items["ind"][0]
                _change_color(i)
                if annotate_on:
                    an.xy = coll.get_offsets()[i]
                    a_text = ""
                    if self.annotate_strs is not None:
                        a_text += f"{self.annotate_strs[i]}\n===============\n"
                    if self.xlabel is not None:
                        a_text += self.xlabel + "\n"
                    a_text += f"{self.x[i]}\n"
                    if self.ylabel is not None:
                        a_text += self.ylabel + "\n"
                    a_text += f"{self.y[i]}\n"
                    if self.size is not None and self.slabel is not None:
                        a_text += self.slabel + "\n"
                        a_text += f"{self.size[i]}\n"
                    an.set_text(a_text)
                    an.set_visible(True)
            else:
                _change_color(None)
                if annotate_on:
                    an.set_visible(False)
            self.fig.canvas.draw()
        def on_pick(event):
            if event.mouseevent.button != MouseButton.LEFT:
                return
            i = event.ind[0]
            self.fig.canvas.draw()
            if self.click_open_urls is not None:
                urls = self.click_open_urls[i]
                if not isinstance(urls, list):
                    urls = [urls]
                for u in urls:
                    logger.info(f"open {u}")
                    webbrowser.open(u)

        if self.click_open_urls is not None or annotate_on:
            self.cids.append(self.fig.canvas.mpl_connect('motion_notify_event', on_motion))
        if self.click_open_urls is not None:
            self.cids.append(self.fig.canvas.mpl_connect('pick_event', on_pick))

    # そのままプロットする版
    @staticmethod
    def exec_plot(fig_size=(10, 10), **kwargs):
        fig = plt.figure(figsize=fig_size)
        ax = fig.add_subplot(1, 1, 1)
        BCPlotScatter(fig, ax, **kwargs).plot()
        plt.show()

# テストコード
if __name__ == "__main__":
    logging.basicConfig(
        level = logging.INFO,
        format = "[%(asctime)s][%(levelname)s] %(message)s",
    )

    import pandas as pd
    # warning 対策。メイン部分に追加したほうがいいかも
    from pandas.plotting import register_matplotlib_converters
    register_matplotlib_converters()
    from bc_data import *

    bc = BCData("bc_data", load_indicator=True)
    df = bc.indicator.get_values({"x":"pbr", "y":"per_forecast"})
    BCPlotScatter.exec_plot(fig_size=(10,5),
                            x=list(df["x"]), y=list(df["y"]),
                            xlim=[0, 2], ylim=[0, 30],
                            xlabel="pbr", ylabel="per_forecast",
                            annotate="mouseover")

    #bc = BCData("bc_data", load_daily=True)
    #target_tickers = [2780, 6620, 8841, 9305]
    #selected = bc.daily.select_data(target_tickers)
    #x = []
    #y = []
    #label = []
    #for k, v in selected.items():
    #    x.append(list(pd.to_datetime(v["day"])))
    #    y.append(list(v["market_capital"] / v["market_capital"][0]))
    #    label.append(bc.company.ticker2name(k))
    #BCPlotLine.exec_plot(fig_size=(10,5),
    #                     x=x, y=y, label=label,
    #                     xlabel="day", ylabel="normalized market_capital")

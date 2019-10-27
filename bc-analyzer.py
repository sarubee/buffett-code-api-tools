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
 bc_analyzer.py
 - GUI program to get and analyze Buffett Code API data
"""

import argparse 
import sys 
import tkinter as tk 
import tkinter.scrolledtext as scrolledtext
from tkinter import ttk 
from tkinter import filedialog 
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import logging 
import threading 

from bc_data import *
from bc_api import *

### widget 定義 ###

class LoggingFrame(ttk.LabelFrame):
    """
    ログ出力 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.scrolled_text = scrolledtext.ScrolledText(self, height=5, state="disabled")
        self.scrolled_text.pack(expand=1, fill="x")

class ValEntryFrame(ttk.Frame):
    """
    列名入力 Frame (共通で使う)
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.entry = ttk.Entry(self)
        self.entry.grid(row=0, column=0, sticky=tk.E+tk.W)
        self.add_button = ttk.Button(self, text="+", width=2)
        self.add_button.grid(row=0, column=1)

class PlotAxisFrame(ttk.LabelFrame):
    """
    x, y 軸指定 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="value").grid(row=0, column=0)
        self.value_entry = ValEntryFrame(self)
        self.value_entry.grid(row=0, column=1, sticky=tk.E+tk.W)
        ttk.Label(self, text="min").grid(row=1, column=0)
        self.min_entry = ttk.Entry(self)
        self.min_entry.grid(row=1, column=1, sticky=tk.W)
        ttk.Label(self, text="max").grid(row=2, column=0)
        self.max_entry = ttk.Entry(self)
        self.max_entry.grid(row=2, column=1, sticky=tk.W)

class PlotSizeFrame(ttk.LabelFrame):
    """
    plot size 指定 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="value").grid(row=0, column=0)
        self.value_entry = ValEntryFrame(self)
        self.value_entry.grid(row=0, column=1, sticky=tk.E+tk.W)
        ttk.Label(self, text="scale").grid(row=1, column=0)
        self.scale = ttk.Scale(self, from_=0, to=1)
        self.scale.grid(row=1, column=1, sticky=tk.E+tk.W)

class PlotFilterFrame(ttk.LabelFrame):
    """
    filter 指定 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)

        self.value_entry = ValEntryFrame(self)
        self.value_entry.grid(row=0, column=0, sticky=tk.E+tk.W)

class PlotCategoryFrame(ttk.LabelFrame):
    """
    category 選択 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)

        self.category_combo = ttk.Combobox(self, state="readonly")
        self.category_combo.grid(row=0, column=0, sticky=tk.E+tk.W)

class PlotClickActionFrame(ttk.LabelFrame):
    """
    click action 選択 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.open_arb_check = ttk.Checkbutton(self, text="Open URLs below")
        self.open_arb_check.pack(expand=1, fill="both")
        self.open_arb_entry = ttk.Entry(self)
        self.open_arb_entry.pack(expand=1, fill="both")
        self.open_company_check = ttk.Checkbutton(self, text="Open company URL")
        self.open_company_check.pack(expand=1, fill="both")

class PlotAnnotationFrame(ttk.LabelFrame):
    """
    annotation 選択 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)

        self.combo = ttk.Combobox(self, state="readonly")
        self.combo.grid(row=0, column=0, sticky=tk.E+tk.W)
        self.combo["values"] = ["mouseover", "all"]  

class PlotConfigFrame(ttk.Frame):
    """
    プロット設定の Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.x_frame = PlotAxisFrame(self, text="X-axis")
        self.x_frame.grid(row=0, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
        self.y_frame = PlotAxisFrame(self, text="Y-axis")
        self.y_frame.grid(row=1, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
        self.yx_check = ttk.Checkbutton(self, text="Show y=x")
        self.yx_check.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        self.size_frame = PlotSizeFrame(self, text="Size")
        self.size_frame.grid(row=3, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
        self.filter_frame = PlotFilterFrame(self, text="Filter")
        self.filter_frame.grid(row=4, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
        self.category_frame = PlotCategoryFrame(self, text="Category")
        self.category_frame.grid(row=5, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
        self.click_action_frame = PlotClickActionFrame(self, text="Click Action")
        self.click_action_frame.grid(row=6, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
        self.annotation_frame = PlotAnnotationFrame(self, text="Annotation")
        self.annotation_frame.grid(row=7, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
        self.plot_btn = ttk.Button(self, text="Plot")
        self.plot_btn.grid(row=8, column=0, padx=5, pady=5)

class CanvasFrame(ttk.Frame):
    """
    プロットキャンバスの Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(fill="both", expand=1)

class PlotFrame(ttk.Frame):
    """
    プロットメイン Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas_frame = CanvasFrame(self)
        self.canvas_frame.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self.config_frame = PlotConfigFrame(self)
        self.config_frame.grid(row=0, column=1, sticky=tk.N+tk.S+tk.E+tk.W)
        self.value_tree = ttk.Treeview(self)

class DataRootDirFrame(ttk.LabelFrame):
    """
    データルートディレクトリ指定 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.entry = ttk.Entry(self, width=50, state="disabled")
        self.entry.grid(row=0, column=0, sticky=tk.W+tk.E)
        self.select_btn = ttk.Button(self, text="Select")
        self.select_btn.grid(row=0, column=1)

class DataFetchFrame(ttk.LabelFrame):
    """
    データ取得 Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(1, weight=1)

        self.overwrite_check = ttk.Checkbutton(self, text="Overwrite CSVs")
        self.overwrite_check.grid(row=0, column=0, columnspan=2, sticky=tk.W)
 
        self.api_key_label = ttk.Label(self, text="API KEY ")
        self.api_key_label.grid(row=1, column=0, sticky=tk.W)
        self.api_key_entry = ttk.Entry(self, show="*", width=30)
        self.api_key_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W+tk.E)

        self.grid_rowconfigure(3, minsize=5)

        self.separator = ttk.Separator(self)
        self.separator.grid(row=4, column=0, columnspan=3, sticky=tk.W+tk.E)

        self.company_check = ttk.Checkbutton(self, text="Company")
        self.company_check.grid(row=5, column=0, columnspan=2, sticky=tk.W)
        self.quarter_check = ttk.Checkbutton(self, text="Quarter")
        self.quarter_check.grid(row=6, column=0, columnspan=2, sticky=tk.W)
        self.start_y_label = ttk.Label(self, text="Start Year ")
        self.start_y_label.grid(row=7, column=0)
        self.start_y_entry = ttk.Entry(self)
        self.start_y_entry.grid(row=7, column=1, sticky=tk.W)
        self.end_y_label = ttk.Label(self, text="End Year ")
        self.end_y_label.grid(row=8, column=0)
        self.end_y_entry = ttk.Entry(self)
        self.end_y_entry.grid(row=8, column=1, sticky=tk.W)
 
        self.indicator_check = ttk.Checkbutton(self, text="Indicator")
        self.indicator_check.grid(row=9, column=0, columnspan=2, sticky=tk.W)

        self.fetch_btn = ttk.Button(self, text="Fetch")
        self.fetch_btn.grid(row=10, column=0)
        self.stop_btn = ttk.Button(self, text="Stop", state="disabled")
        self.stop_btn.grid(row=10, column=1, sticky=tk.W, padx=5)

class DataFrame(ttk.Frame):
    """
    データ関連のメイン Frame
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.dir_frame = DataRootDirFrame(self, text="Root Directory")
        self.dir_frame.grid(row=0, column=0, sticky=tk.W+tk.E, padx=5, pady=15)
        self.fetch_frame = DataFetchFrame(self, text="Fetch")
        self.fetch_frame.grid(row=1, column=0, sticky=tk.W+tk.E, padx=5, pady=15)

### variables ###

class DataVariables():
    """
    データ関連の variables
    """
    def __init__(self, data_frame):
        self.root_dir = tk.StringVar()
        self.fetch_overwrite = tk.BooleanVar()
        self.fetch_company = tk.BooleanVar()
        self.fetch_quarter = tk.BooleanVar()
        self.fetch_indicator = tk.BooleanVar()
        self.fetch_api_key = tk.StringVar()
        self.fetch_start_y = tk.StringVar()
        self.fetch_end_y = tk.StringVar()

        data_frame.dir_frame.entry["textvariable"] = self.root_dir
        data_frame.fetch_frame.overwrite_check["variable"] = self.fetch_overwrite
        data_frame.fetch_frame.api_key_entry["textvariable"] = self.fetch_api_key
        data_frame.fetch_frame.company_check["variable"] = self.fetch_company
        data_frame.fetch_frame.quarter_check["variable"] = self.fetch_quarter
        data_frame.fetch_frame.start_y_entry["textvariable"] = self.fetch_start_y
        data_frame.fetch_frame.end_y_entry["textvariable"] = self.fetch_end_y
        data_frame.fetch_frame.indicator_check["variable"] = self.fetch_indicator

class PlotAxisVariables():
    """
    プロット軸 variables (x, y 共通)
    """
    def __init__(self, axis_frame):
        self.value = tk.StringVar()
        self.min = tk.StringVar()
        self.max = tk.StringVar()

        axis_frame.value_entry.entry["textvariable"] = self.value
        axis_frame.min_entry["textvariable"] = self.min
        axis_frame.max_entry["textvariable"] = self.max

class PlotSizeVariables():
    """
    プロットサイズ variables
    """
    def __init__(self, size_frame):
        self.value = tk.StringVar()
        self.scale = tk.DoubleVar()

        size_frame.value_entry.entry["textvariable"] = self.value
        size_frame.scale["variable"] = self.scale

class PlotVariables():
    """
    プロット関連の variables
    """
    def __init__(self, plot_frame):
        self.x = PlotAxisVariables(plot_frame.config_frame.x_frame) 
        self.y = PlotAxisVariables(plot_frame.config_frame.y_frame)
        self.size = PlotSizeVariables(plot_frame.config_frame.size_frame) 

        self.show_yx = tk.BooleanVar()
        self.filter = tk.StringVar()
        self.category = tk.StringVar()
        self.do_open_company = tk.BooleanVar()
        self.do_open_arb = tk.BooleanVar()
        self.arb_url = tk.StringVar()
        self.annotation = tk.StringVar()
        plot_frame.config_frame.yx_check["variable"] = self.show_yx
        plot_frame.config_frame.filter_frame.value_entry.entry["textvariable"] = self.filter
        plot_frame.config_frame.category_frame.category_combo["textvariable"] = self.category 
        plot_frame.config_frame.click_action_frame.open_company_check["variable"] = self.do_open_company
        plot_frame.config_frame.click_action_frame.open_arb_check["variable"] = self.do_open_arb
        plot_frame.config_frame.click_action_frame.open_arb_entry["textvariable"] = self.arb_url
        plot_frame.config_frame.annotation_frame.combo["textvariable"] = self.annotation

### その他 ###

class LoggingHandler(logging.Handler):
    """
    ログハンドラ 
    """
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget 
    def emit(self, record):
        self.text_widget.configure(state="normal")
        if len(self.text_widget.get("1.0", "end-1c")) > 0:
            self.text_widget.insert("end", "\n")
        self.text_widget.insert("end", self.format(record))
        self.text_widget.configure(state="disabled")
        self.text_widget.yview(tk.END)
        update_idletasks() # これがないと反映が他の時間がかかる処理後になる場合があった

class FetchThread(threading.Thread):
    """
    データ取得時のスレッド
    """
    def __init__(self, api_key, target):
        self.bcapi = BCAPI(api_key)
        super().__init__(target=target, args=(self.bcapi,))

    def stop(self):
        self.bcapi.stop_fetch = True

class Application(ttk.Frame):
    """
    アプリ本体
    """
    def __init__(self, master, root_dir, debug, **kwargs):
        super().__init__(master, **kwargs)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabelframe.Label", font=("", 12))
        style.configure("TNotebook.Tab", font=("", 12))

        master.protocol('WM_DELETE_WINDOW', self.on_window_exit) 
        master.title("bc-analyzer")
        master.geometry("1800x1000")
        self.master = master
        self.pack(expand=1, fill="both")

        self.create_widgets()
        self.set_logger(debug)
        self.set_variables(root_dir)
        self.set_events()

        self.plot_cids = []

        # データ取得関連
        self.fetch_thread = None
        self.bcapi = None

        self.bcdata = None 

        # root dir 指定があればデータは読み込んでおく
        if root_dir is not None:
            self.exec_load()

    def on_window_exit(self):
        self.master.quit()
        self.master.destroy()
    
    def create_widgets(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(expand=1, fill="both")
        self.data_frame = DataFrame(self)
        self.plot_frame = PlotFrame(self)
        self.nb.add(self.data_frame, text="Data")
        self.nb.add(self.plot_frame, text="Scatter Plot")

        # log 出力用
        self.logging_frame = LoggingFrame(self, text="Log")
        self.logging_frame.pack(fill="x")

    def set_logger(self, debug):
        logging.basicConfig(
            level = logging.INFO,
            format = "[%(asctime)s][%(levelname)s] %(message)s",
            handlers=[LoggingHandler(self.logging_frame.scrolled_text)]
        )
        self.logger = logging.getLogger()
        if debug:
            # デバッグ指定があれば、自作スクリプトは DEBUG まで出す
            logging.getLogger("__name__").setLevel(logging.DEBUG)
            logging.getLogger("bc_data").setLevel(logging.DEBUG)
            logging.getLogger("bc_api").setLevel(logging.DEBUG)

    def set_variables(self, root_dir=None):
        self.data_vars = DataVariables(self.data_frame)
        self.plot_vars = PlotVariables(self.plot_frame)

        # default 値を設定
        # TODO: 前回終了状態のロードをしたい！
        if root_dir is not None:
            self.data_vars.root_dir.set(root_dir)
        self.data_vars.fetch_overwrite.set(False)
        self.data_vars.fetch_company.set(True)
        self.data_vars.fetch_quarter.set(True)
        self.data_vars.fetch_start_y.set("2011")
        self.data_vars.fetch_end_y.set("2019")
        self.data_vars.fetch_indicator.set(True)

        self.plot_vars.x.value.set("pbr")
        self.plot_vars.x.min.set("0")
        self.plot_vars.x.max.set("10")
        self.plot_vars.y.value.set("per_forecast")
        self.plot_vars.y.min.set("0")
        self.plot_vars.y.max.set("30")
        self.plot_vars.show_yx.set(False)
        self.plot_vars.size.value.set("market_capital")
        self.plot_vars.size.scale.set(0.5)
        self.plot_vars.category.set("(all)")
        self.plot_vars.do_open_company.set(False)
        self.plot_vars.do_open_arb.set(True)
        self.plot_vars.arb_url.set("https://www.buffett-code.com/company/TICKER")
        self.plot_vars.annotation.set("mouseover")

    def set_events(self):
        self.data_frame.dir_frame.select_btn["command"] = self.select_root_directory 
        self.data_frame.fetch_frame.fetch_btn["command"] = self.exec_fetch
        self.data_frame.fetch_frame.stop_btn["command"] = self.stop_fetch
        self.plot_frame.config_frame.plot_btn["command"] = self.exec_plot
        self.plot_frame.config_frame.x_frame.value_entry.add_button["command"] = lambda : self.exec_value_tree(self.plot_frame.config_frame.x_frame.value_entry.entry) 
        self.plot_frame.config_frame.y_frame.value_entry.add_button["command"] = lambda : self.exec_value_tree(self.plot_frame.config_frame.y_frame.value_entry.entry) 
        self.plot_frame.config_frame.size_frame.value_entry.add_button["command"] = lambda : self.exec_value_tree(self.plot_frame.config_frame.size_frame.value_entry.entry) 
        self.plot_frame.config_frame.filter_frame.value_entry.add_button["command"] = lambda : self.exec_value_tree(self.plot_frame.config_frame.filter_frame.value_entry.entry) 

    def select_root_directory(self):
        path = tk.filedialog.askdirectory()
        self.data_vars.root_dir.set(path) 
        # 選択したら root_dir を load する
        self.exec_load()

    def exec_fetch(self):
        def _enable_widgets(is_start):
            # fetch スタート時には stop ボタンは有効化、それ以外は終わるまで無効化
            # fetch 終了時には逆
            state_stop = "enabled" if is_start else "disabled"  
            state_others = "disabled" if is_start else "enabled"  
            dir_frame = self.data_frame.dir_frame
            dir_frame.select_btn["state"] = state_others 
            fetch_frame = self.data_frame.fetch_frame
            fetch_frame.overwrite_check["state"] = state_others
            fetch_frame.api_key_label["state"] = state_others
            fetch_frame.api_key_entry["state"] = state_others
            fetch_frame.company_check["state"] = state_others
            fetch_frame.quarter_check["state"] = state_others
            fetch_frame.indicator_check["state"] = state_others
            fetch_frame.start_y_label["state"] = state_others
            fetch_frame.start_y_entry["state"] = state_others
            fetch_frame.end_y_label["state"] = state_others
            fetch_frame.end_y_entry["state"] = state_others
            fetch_frame.fetch_btn["state"] = state_others
            fetch_frame.stop_btn["state"] = state_stop

        self.logger.info("START fetch")
        _enable_widgets(True)

        overwrite = self.data_vars.fetch_overwrite.get()
        do_fetch_c = self.data_vars.fetch_company.get()
        do_fetch_q = self.data_vars.fetch_quarter.get()
        do_fetch_i = self.data_vars.fetch_indicator.get()
        api_key = self.data_vars.fetch_api_key.get()
        start = self.data_vars.fetch_start_y.get()
        end = self.data_vars.fetch_end_y.get()

        def _exec_fetch_inner(bcapi):
            # NOTE: tkinter を multithread で使っていいのか？現状問題は起きていないが・・。
            #       必要なら対策を検討。
            try:
                if do_fetch_c and not bcapi.stop_fetch:
                    self.bcdata.fetch_company(bcapi, overwrite=overwrite)
                if do_fetch_q and not bcapi.stop_fetch:
                    self.bcdata.fetch_quarter(bcapi, start, end, overwrite=overwrite)
                if do_fetch_i and not bcapi.stop_fetch:
                    self.bcdata.fetch_indicator(bcapi, overwrite=overwrite)
            except Exception as e:
                self.logger.exception(e)

            # NOTE: main thread で join() しようとすると、fetch thread 側の log 出力で固まるので thread の終了に伴う処理はここでやる
            self.fetch_thread = None 
            _enable_widgets(False)
            self.logger.info("END fetch!")
        # 別スレッドで実行する
        self.fetch_thread = FetchThread(api_key, _exec_fetch_inner) 
        self.fetch_thread.start()

    def stop_fetch(self):
        self.data_frame.fetch_frame.stop_btn["state"] = "disabled" 
        if self.fetch_thread is None:
            return
        self.logger.info("stopping fetching thread ...")
        self.fetch_thread.stop()

    def exec_value_tree(self, entry):
        def _is_valid(elem):
            return elem is not None and elem.data is not None and elem.dic is not None

        tree_dialog = tk.Toplevel(entry)
        tree_dialog.title("Choose value")

        tree_dialog.rowconfigure(0, weight=1)
        tree_dialog.columnconfigure(0, weight=1)

        tree = ttk.Treeview(tree_dialog, columns=("name_jp", "unit"), height=40)
        sb = ttk.Scrollbar(tree_dialog, orient=tk.VERTICAL, command=tree.yview)
        tree["yscroll"] = sb.set

        tree.heading("#0", text="name")
        tree.column("#0", width=500)
        tree.heading("name_jp", text="name_jp")
        tree.column("name_jp", width=500)
        tree.heading("unit", text="unit")
        tree.column("unit", width=100)
        if _is_valid(self.bcdata.quarter):
            qid = tree.insert("", "end", text="quarter", open=True)
            fid = tree.insert(qid, "end", text="function", open=True) 
            # 定義済み関数を最初に追加
            tree.insert(fid, "end", text="cagr()", value=("年成長率 ex.) cagr(operating_income, 5, all_true=True)", "%")) 
            tree.insert(fid, "end", text="mean()", value=("年平均値 ex.) mean(operating_income)", "")) 
            for k, v in sorted(self.bcdata.quarter.dic.items(), key=lambda x: x[0]):
                # 辞書にある列を順次追加
                tree.insert(qid, "end", text=k, values=(v["name_jp"], v["unit"]))
        if _is_valid(self.bcdata.indicator):
            iid = tree.insert("", "end", text="indicator", open=True)
            for k, v in sorted(self.bcdata.indicator.dic.items(), key=lambda x: x[0]):
                # 辞書にある列を順次追加
                tree.insert(iid, "end", text = k, values=(v["name_jp"], v["unit"]))

        # double click で選択
        # TODO: insert ボタンもあったほうがわかりやすい？
        def on_double_click(self):
            i = tree.selection()[0]
            s = tree.item(i, "text")
            if s in ["quarter", "function", "indicator"]:
                return
            try:
                entry.delete("sel.first", "sel.last")
            except:
                pass
            entry.insert(entry.index(tk.INSERT), s)
            tree_dialog.destroy()
        tree.bind("<Double-1>", on_double_click)

        tree_dialog.grab_set()
        tree.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        sb.grid(row=0, column=1, sticky=tk.N+tk.S+tk.E+tk.W)

    def exec_load(self):
        self.logger.info("START load")
        root_dir = self.data_vars.root_dir.get()
        self.logger.info(f"loading {root_dir} ...")
        self.bcdata = BCData(root_dir)

        # category 一覧を設定
        combo = self.plot_frame.config_frame.category_frame.category_combo
        if self.bcdata.company is not None and self.bcdata.company.data is not None:
            combo["values"] = ["(all)"] + list(set(self.bcdata.company.data["tosyo_33category"]))
        else:
            combo["values"] = ["(all)"]
        combo.current(0)

        self.logger.info("END load!")

    def clear_plot(self):
        cf = self.plot_frame.canvas_frame
        cf.ax.cla()
        for cid in self.plot_cids:
            cf.fig.canvas.mpl_disconnect(cid)
        self.plot_cids = []

    def exec_plot(self):
        # データがロードされているか確認
        if self.bcdata is None:
            self.logger.error("No data is loaded.")
            return
        elif self.bcdata.company is None:
            self.logger.error("Company data is not loaded.")
            return
        elif self.bcdata.quarter is None and self.bcdata.indicator is None:
            self.logger.error("Both quarter and indicator data are not loaded.")
            return

        self.logger.info("START plot")
        def _get_float(var):
            v = var.get()
            if len(v) < 1:
                return None 
            else:
                return float(v)
        try:
            x = self.plot_vars.x.value.get()
            y = self.plot_vars.y.value.get()
            size = self.plot_vars.size.value.get()
            show_yx = self.plot_vars.show_yx.get()
            filter_str = self.plot_vars.filter.get()
            category = self.plot_vars.category.get()
            annotate = self.plot_vars.annotation.get()
            if category == "(all)":
                category = None
            if len(x) < 1 or len(y) < 1:
                self.logger.error("Please specify x and y value")
                return
            xlim = [_get_float(self.plot_vars.x.min), _get_float(self.plot_vars.x.max)]
            ylim = [_get_float(self.plot_vars.y.min), _get_float(self.plot_vars.y.max)]
            size_scale = self.plot_vars.size.scale.get()
            # URL はセミコロン区切りで複数指定可
            arb_urls = []
            if self.plot_vars.do_open_arb.get():
                arb_urls = [u.strip() for u in self.plot_vars.arb_url.get().split(";") if not u.strip() == ""]
            do_open_company = self.plot_vars.do_open_company.get()

            self.clear_plot()
            cf = self.plot_frame.canvas_frame

            cids = self.bcdata.plot_scatter_clickable(cf.fig, cf.ax,
                                                      x, y, xlim=xlim, ylim=ylim,
                                                      filter_str=filter_str, size_str=size, size_scale=size_scale,
                                                      category=category,
                                                      xyline=show_yx,
                                                      click_open_company=do_open_company,  click_open_arb=arb_urls,
                                                      annotate=annotate)
            self.plot_cids += cids
            cf.canvas.draw()
        except Exception as e:
            self.logger.exception(e)

        self.logger.info("END plot!")

if __name__ == "__main__":
    # 引数パース
    parser = argparse.ArgumentParser()
    parser.add_argument("root_dir", help="root directory", nargs="?")
    parser.add_argument("--debug", help="execute this program in debug mode", action="store_true")
    args = parser.parse_args()
    root_dir = Path(args.root_dir).resolve() if args.root_dir is not None else None
    
    root = tk.Tk()
    def update_idletasks():
        root.update_idletasks()
    app = Application(master=root, root_dir=root_dir, debug=args.debug)
    app.mainloop()

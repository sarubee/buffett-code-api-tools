# buffett-code-api-tools  
バフェット・コードの web API 活用のための Python ツールのレポジトリです（非公式）。  
データの取得には web API の key が必要です。

* [バフェット・コード公式](https://www.buffett-code.com/ "バフェット・コード公式")  
* [web API 仕様](https://docs.buffett-code.com/ "web API 仕様")  

---
## Requirement
* Python (3.7.5)  

Python の標準ライブラリに含まれない以下のライブラリ（およびそれらの依存ライブラリ）に依存しています。  
* pandas (0.25.3)
* numpy (1.18.0)
* matplotlib (3.1.2)
* requests (2.18.4)
* python-dateutil (2.8.1)
---
## Author
[github](https://github.com/sarubee "github"), [twitter](https://twitter.com/fire50net "twitter"), [blog](https://fire50.net/ "blog")

---
## License
Apache License 2.0

---
## Description
### bc-analyzer
GUI ツールです。
バフェット・コード web API からデータを取得・保存し、散布図プロットを作って分析を行うことができます。

#### 起動方法
```bash
$ python bc-analyzer.py [root_directory]
```
root_directory はデータの保存先（ロード元）ディレクトリを指定。 GUI 画面でも選択できるので省略可。

#### データ取得画面
![bc-analyzer_data](https://github.com/sarubee/buffett-code-api-tools/blob/images/image_bc-analyzer_data.png)
- Root Directory: データの保存先（ロード元）ディレクトリ (**必須**)
- Fetch: データ取得に関する設定
  - Overwrite CSVs: 保存済み CSV を上書きするかどうか
  - API Key: バフェット・コード web API のキー (データ取得時には**必須**)
  - Company: 会社情報データを取得するかどうか
  - Quarter: 財務データを取得するかどうか
    - Start : 財務データの取得開始年
    - End : 財務データ取得終了年
  - Indicator : 株価指標データを取得するかどうか
  - Daily: デイリーデータを取得するかどうか
    - Start : デイリーデータの取得開始年
    - End : デイリーデータ取得終了年
  - Fetch ボタン: 上記の設定に従い、データの取得を開始します
  - Stop ボタン: データの取得を停止します
- Log: プログラムの実行状況を出力します

※ Quarter、Indicator、Daily データ取得は取得済みの Company データの各銘柄について行うので Company データが先に取得されている必要があります（同時指定も OK）。

##### 保存ファイルツリー
```
{Root Directory}/
  ├- company/
  |    ├- columns.json   # company データ列名定義
  |    └- company.csv    # 全社 company データ
  ├- quarter/
  |    ├- columns.json   # quarter データ列名定義
  |    ├- {ticker}.csv   # 各社 quarter データ
  |    └- all.pickle     # 全社 quarter データを一つにまとめたもの (pandas.DataFrame)
  └- indicator/
  |    ├- columns.json   # indicator データ列名定義
  |    ├- {ticker}.csv   # 各社 indicator データ
  |    └- all.pickle     # 全社 indicator データを一つにまとめたもの (pandas.DataFrame)
  └- daily/
       ├- columns.json   # daily データ列名定義
       ├- {ticker}.csv   # 各社 daily データ
       └- all.pickle     # 全社 daily データを一つにまとめたもの (pandas.DataFrame)
```
※ all.pickle は Fetch 終了時または Stop 時に、{ticker}.csv を基に作成されます。

#### 散布図プロット画面
quarter データおよび indicator データを使って散布図プロットを作ります。

![bc-analyzer_data](https://github.com/sarubee/buffett-code-api-tools/blob/images/image_bc-analyzer_scatter_plot.png)

- X-axis（**value 指定必須**）
- Y-axis (**value 指定必須**)
- Size
  - x軸、y軸、プロットサイズに何を使うかを value に指定します。
  - 横の "+" ボタンをクリックすると、列名（と追加定義関数）のリストを参照できます。リストからダブルクリックでエントリに挿入します。
  - quarter データの項目を選んだ場合は、Q4 (年間)値の最新のデータが使用されます。
  - quarter データに対しては、年平均成長率 cagr(), 平均 mean() も使用可能です。その場合、各年の Q4 の値を使って算出されます。
  - データ同士の演算も可能 (例: ex_operating_income / operating_income) ですが、quarter データと indicator データにまたがった演算はできません。
- Filter: プロット銘柄をフィルタリングします
  - 例1) 予想配当利回り5%以上の銘柄のみプロットする: `dividend_yield_forecast > 5`
  - 例2) 配当性向50%以下、かつ予想配当利回り5%以上の銘柄のみプロットする: `(dividend_payout_ratio < 50) & (dividend_yield_forecast > 5)`
- Category: 東証33業種のうちプロットする業種を選択
- ClickAction: プロット点をクリックした際の挙動
  - Open URLs below: 設定した任意の URL (TICKER と書いた部分はクリックした銘柄の証券コードに置き換えます)をブラウザで開きます。複数のURLを指定する場合はセミコロン(;)で区切ります。
  - Open company URL: クリックした銘柄の会社のURLをブラウザで開きます
- Annnotation: 銘柄情報のアノテーションの出し方
  - mouseover: プロット点をマウスオーバーした場合に出します
  - all: すべてのプロット点に出します（プロット銘柄数が少ない場合に活用してください）
- Plot ボタン:上記設定に基づきプロットを実行します
- Log: プログラムの実行状況を出力します

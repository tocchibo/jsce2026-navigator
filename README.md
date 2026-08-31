# JSCE 2026 大会ナビ

令和8年度土木学会全国大会の9月2日〜4日を対象にした、スマートフォン向け静的タイムテーブルです。

## 確認方法

依存パッケージはありません。リポジトリ直下で次を実行します。

```powershell
uv run python -m http.server 8000
```

ブラウザで `http://localhost:8000/` を開いてください。`index.html` をGitHub Pagesでそのまま公開することもできます。

## 主な機能

- 「今から1時間」に重なるセッションの表示
- 「今から1時間」「9/2」「9/3」「9/4」の4タブ切り替え
- 日別プログラムの開始時刻グループ表示
- 開催中の講演と次の講演の強調表示
- セッションカードから開く全画面の講演一覧
- 講演番号から生成したConfit公式ページへのリンク
- Confit本家ブックマークへのリンク
- 「今から1時間」タブでの表示基準日時の変更（初期値は現在日時）
- テーマ・部門・キャンパスの複数選択と、題名・著者全員・所属・講演番号による絞り込み
- 19個の横断テーマによる絞り込みと、セッション・講演のカテゴリ表示
- スマートフォン／PC向けレスポンシブ表示

プログラムPDFから抽出した748セッション、5,636講演を収録しています。

## 独自カテゴリ設計

講演内容を横断的に探すための分類体系は、[カテゴリ事前設計](docs/category-taxonomy-design.md)にまとめています。機械可読な定義は `data/category_taxonomy.json`、全5,636講演の公開用タグは `data/categories.json` です。分類結果の分布と要確認件数は[全講演一次分類レポート](docs/category-all-report.md)、120講演での事前検証は[層化試行レポート](docs/category-pilot-v02-report.md)に記録しています。

```powershell
uv run --no-project python scripts\validate_category_taxonomy.py
```

梗概の著者キーワード・短い内容要約は、PDFからローカル専用ファイルへ抽出します。抽出物はGitの管理対象外です。

```powershell
uv run --no-project python scripts\extract_category_sample.py
uv run --no-project python scripts\build_category_pilot_v02.py
uv run --no-project python scripts\analyze_category_pilot_v02.py
```

全件処理はPDFを1回走査してローカル解析データを作り、公開用タグだけを書き出します。PDF由来の内容要約・著者キーワード・分類スコア・確認キューはGit管理対象外です。

```powershell
uv run --no-project python scripts\extract_all_abstract_summaries.py
uv run --no-project python scripts\build_category_all.py
uv run --no-project python scripts\analyze_category_all.py
uv run --no-project python scripts\validate_category_taxonomy.py
```

## プログラムデータの再生成

```powershell
uv run --no-project python scripts\extract_program.py
```

PDFのプログラム部から `data\sessions.json` を再生成し、想定件数、講演番号の重複、対象日を検証します。

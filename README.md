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
- セッションを展開した講演一覧
- 講演番号から生成したConfit公式ページへのリンク
- Confit本家ブックマークへのリンク
- 「今から1時間」タブでの表示基準日時の変更（初期値は現在日時）
- 部門・キャンパス・題名・著者全員・所属・講演番号による絞り込み
- スマートフォン／PC向けレスポンシブ表示

プログラムPDFから抽出した748セッション、5,636講演を収録しています。

## 独自カテゴリ設計

講演内容を横断的に探すための分類体系案は、[カテゴリ事前設計](docs/category-taxonomy-design.md)にまとめています。機械可読な定義は `data/category_taxonomy.json`、120講演の層化試行結果は `data/category_pilot_v02.json`、評価結果は[層化試行レポート](docs/category-pilot-v02-report.md)です。

```powershell
uv run --no-project python scripts\validate_category_taxonomy.py
```

梗概の著者キーワード・短い内容要約は、PDFからローカル専用ファイルへ抽出します。抽出物はGitの管理対象外です。

```powershell
uv run --no-project python scripts\extract_category_sample.py
uv run --no-project python scripts\build_category_pilot_v02.py
uv run --no-project python scripts\analyze_category_pilot_v02.py
```

## プログラムデータの再生成

```powershell
uv run --no-project python scripts\extract_program.py
```

PDFのプログラム部から `data\sessions.json` を再生成し、想定件数、講演番号の重複、対象日を検証します。

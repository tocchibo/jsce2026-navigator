# JSCE / JSME 2026 大会ナビ

土木学会と日本機械学会の2026年全国大会プログラムを、同じ画面で閲覧するための静的Webアプリです。

- リポジトリ直下の `index.html`: JSCE 2026
- `jsme2026/index.html`: JSME 2026
- `assets/`: 両大会で共有する画面・スタイル
- `events/<event-id>/`: 大会ごとの設定・公開データ・個人プラン
- `scripts/extract/`: PDF書式ごとの専用抽出器
- `sources/`: Git管理外の原本PDF

GitHub Pagesでは次のURLになります。

- `https://tocchibo.github.io/jsce2026-navigator/`
- `https://tocchibo.github.io/jsce2026-navigator/jsme2026/`

## ローカル確認

```powershell
uv run python -m http.server 8000
```

ブラウザで以下を開きます。

- `http://localhost:8000/`
- `http://localhost:8000/jsme2026/`

## 共通機能

- 「今から1時間」と日別プログラムの切り替え
- 開催中のセッション、講演中・次の講演の強調
- 分野、部門・企画種別、会場・棟による複数選択フィルター
- 題名、著者、所属、講演番号によるキーワード検索
- セッションカードから開く講演一覧
- Confit公式講演ページ、公式ブックマークへのリンク
- URLの `plan` パラメータによる個人用スケジュール
- スマートフォン／PC向けレスポンシブ表示

大会名、日程、テーマ色、データURL、フィルター名などは、各大会の `event.json` で切り替えます。PDF抽出処理は大会ごとの書式に決定的に従うため、共通化せず別モジュールにしています。

## 収録データ

### JSCE 2026

9月2日〜4日の748セッション、5,636講演を収録しています。

JSCE独自の19個の横断テーマは、[カテゴリ事前設計](docs/category-taxonomy-design.md)にまとめています。機械可読な定義は `events/jsce2026/category_taxonomy.json`、公開用タグは `events/jsce2026/categories.json` です。分類結果は[全講演一次分類レポート](docs/category-all-report.md)、120講演での事前検証は[層化試行レポート](docs/category-pilot-v02-report.md)に記録しています。

### JSME 2026

`jsme2026_program_all.pdf` のプログラム欄（先頭117ページ）を対象とし、9月6日〜9日の全分野250開催枠を収録しています。PDFに個別番号がある1,063講演・行事と、個別番号のない33行事を合わせ、画面上では1,096項目を表示します。通常講演に加え、基調講演、フォーラム、ワークショップ、一般公開イベント、関係者向け行事を含みます。

セッション一覧PDFに掲載されたS・Jセッション61件がすべて含まれることを番号で突合しています。個別時刻がPDFに記載されていない講演は推定せず、「時刻記載なし」として扱います。`S171-07` と `S052p-04` はPDFの記載どおり「欠番」として保持しています。

## データ再生成

原本PDFは公開データへ含めず、次の場所に置きます。

```text
sources/jsce2026/program.pdf
sources/jsme2026/jsme2026_program_all.pdf
sources/jsme2026/nenji2026sessions_ja_20260511131150123.pdf
```

JSMEデータの再生成:

```powershell
uv run python -m scripts.extract.jsme2026
```

JSCEデータの再生成:

```powershell
uv run python -m scripts.extract.jsce2026
```

## 検証

イベント設定、日程、想定件数、セッションID、講演番号、カテゴリ参照をまとめて検証します。

```powershell
uv run python -m scripts.validate_events
uv run python scripts\validate_category_taxonomy.py
```

ローカルサーバーを起動した状態で、ChromeまたはEdgeを使った両大会のスモークテストを実行できます。

```powershell
uv run python scripts\browser_smoke_test.py
```

梗概由来の要約、著者キーワード、分類スコア、確認キューは `*.local.json` としてGit管理外に置きます。

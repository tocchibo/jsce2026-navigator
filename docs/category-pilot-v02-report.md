# 独自カテゴリ v0.2 層化試行レポート

## 結果概要

公式8分類から各15講演、計120講演を等間隔で抽出し、PDFの著者キーワードと短い内容要約を用いて5軸分類を試行した。

- 分類体系: `0.2.0`
- 抽出成功: 120/120講演
- 要確認: 20講演（16.7%）
- low判定: 8講演（6.7%）
- medium判定: 18講演（15.0%）
- high判定: 94講演（78.3%）

`high`は明示規則上の根拠強度であり、人手による正解保証ではない。今回の試行分類は全件分類前の分類体系・抽出方式・境界規則の検証用である。

## PDF抽出の検証

各講演の推定ページ周辺から、講演番号と著者キーワードの両方が一致するページだけを採用した。推定との差は次のとおりだった。

| 推定との差 | 講演数 |
|---:|---:|
| -3ページ | 29 |
| -2ページ | 21 |
| -1ページ | 51 |
| +0ページ | 19 |

全120講演で番号・キーワード・要約を取得できた。長いキーワードの折り返しも空行まで連結し、要約への混入を防止した。梗概本文と要約はローカルファイルだけに保存し、Git管理対象には含めない。

## v0.1から追加した分類

試行標本で既存タグへ無理に割り当てるケースが生じたため、次を追加した。

- 対象・分野: `construction_materials`（建設材料）
- 対象・分野: `atmosphere_climate`（気象・気候）
- 目的・工程: `performance_evaluation`（性能評価・現象解明）
- 目的・工程: `technology_development`（技術・システム開発）
- 課題: `knowledge_transfer`（技術継承・人材確保）
- 材料: `polymer_resin`の表示を「樹脂・ゴム・高分子材料」へ拡張

## 軸別タグ分布

### 対象・分野

| タグ | 講演数 |
|---|---:|
| 建設材料 (`construction_materials`) | 21 |
| 地盤・基礎・斜面 (`ground_foundation_slope`) | 19 |
| 構造一般 (`structural_system`) | 18 |
| 橋梁・高架橋 (`bridge`) | 17 |
| 道路・舗装 (`road_pavement`) | 14 |
| 河川・流域 (`river_watershed`) | 13 |
| トンネル・地下空間 (`tunnel_underground`) | 12 |
| 海岸・港湾・海洋 (`coast_port_ocean`) | 9 |
| 都市・地域・交通 (`urban_transport`) | 9 |
| 建設現場・生産 (`construction_site`) | 7 |
| 鉄道・軌道 (`railway`) | 7 |
| 環境・生態系 (`environment_ecosystem`) | 6 |
| 廃棄物・汚染・処分 (`waste_contamination`) | 6 |
| 上下水道・水処理 (`water_sewerage`) | 6 |
| 気象・気候 (`atmosphere_climate`) | 5 |
| 社会基盤一般 (`civil_systems`) | 5 |
| 教育・人材・社会 (`education_society`) | 5 |
| エネルギー・産業施設 (`energy_industrial`) | 5 |
| ダム・貯水池 (`dam_reservoir`) | 2 |

### 目的・工程

| タグ | 講演数 |
|---|---:|
| 性能評価・現象解明 (`performance_evaluation`) | 71 |
| 設計・照査・解析 (`design_analysis`) | 27 |
| 調査・計測 (`survey_measurement`) | 19 |
| 施工・製造 (`construction`) | 15 |
| 維持管理・補修補強 (`maintenance_repair`) | 13 |
| 環境評価・保全・浄化 (`environmental_action`) | 9 |
| 技術・システム開発 (`technology_development`) | 7 |
| 材料・工法開発 (`material_development`) | 7 |
| 政策・計画 (`policy_planning`) | 7 |
| 点検・診断 (`inspection_diagnosis`) | 6 |
| 防災・避難・災害対応 (`disaster_action`) | 5 |
| 教育・人材・合意形成 (`education_consensus`) | 5 |
| 更新・解体・再利用 (`renewal_demolition`) | 5 |
| 品質管理・検査 (`quality_control`) | 3 |
| 運用・マネジメント (`operation_management`) | 3 |

### 技術・手法

| タグ | 講演数 |
|---|---:|
| 数値解析・シミュレーション (`numerical_simulation`) | 12 |
| 室内実験・模型実験 (`laboratory_experiment`) | 11 |
| 現地試験・モニタリング (`field_test_monitoring`) | 10 |
| 統計・確率・最適化 (`statistics_optimization`) | 9 |
| AI・機械学習 (`ai_ml`) | 8 |
| センサ・IoT (`sensing_iot`) | 4 |
| 3次元計測・点群・リモートセンシング (`three_d_remote`) | 3 |
| 画像解析・コンピュータビジョン (`image_processing`) | 3 |
| 非破壊検査 (`nondestructive_testing`) | 2 |
| BIM/CIM・デジタルツイン (`bim_digital_twin`) | 2 |
| GIS・地理空間情報 (`gis_spatial`) | 2 |
| ドローン・無人機 (`drone_uncrewed`) | 2 |
| データ基盤・ソフトウェア (`data_platform`) | 1 |

### 材料

| タグ | 講演数 |
|---|---:|
| コンクリート・セメント (`concrete_cement`) | 15 |
| 土・岩・ベントナイト (`soil_rock`) | 15 |
| 鋼・金属 (`steel_metal`) | 13 |
| 副産物・再生材料 (`waste_recycled`) | 6 |
| FRP・複合材料 (`frp_composite`) | 3 |
| 樹脂・ゴム・高分子材料 (`polymer_resin`) | 3 |
| アスファルト (`asphalt`) | 2 |
| 木材・バイオマス (`wood_biomass`) | 2 |
| 水・底質・流砂 (`water_sediment`) | 2 |
| CO2・炭素材料 (`co2_carbon`) | 2 |
| ジオシンセティックス (`geosynthetics`) | 1 |

### 課題・横断テーマ

| タグ | 講演数 |
|---|---:|
| 地震・断層・液状化 (`seismic_liquefaction`) | 8 |
| 安全・リスク (`safety_risk`) | 8 |
| 老朽化・長寿命化 (`aging_lifecycle`) | 7 |
| 洪水・津波・高潮 (`flood_tsunami_storm`) | 6 |
| 劣化・腐食・耐久性 (`deterioration_corrosion`) | 6 |
| 疲労・破壊・耐荷力 (`fatigue_fracture`) | 6 |
| 風・雪・寒冷地 (`wind_snow_cold`) | 6 |
| 土砂災害・洗掘・侵食 (`landslide_erosion`) | 6 |
| 生物多様性・水質 (`biodiversity_water_quality`) | 5 |
| 技術継承・人材確保 (`knowledge_transfer`) | 4 |
| 気候変動・脱炭素 (`climate_decarbonization`) | 4 |
| 生産性・省人化 (`productivity_labor`) | 4 |
| 資源循環・リサイクル (`circular_resources`) | 4 |
| 汚染・浄化 (`pollution_remediation`) | 3 |
| 移動・アクセシビリティ (`mobility_accessibility`) | 3 |
| 制度・調達・事業管理 (`governance_procurement`) | 3 |
| レジリエンス・緊急対応 (`resilience_emergency`) | 1 |

## 要確認理由

| 理由 | 件数 |
|---|---:|
| `phase:tag_limit` | 9 |
| `phase:fallback` | 5 |
| `domain:fallback` | 3 |
| `domain:tag_limit` | 3 |

`fallback`は内容から必須軸を確定できず公式部門等から補ったもの、`tag_limit`は候補が軸の上限を超えたものを表す。どちらも自動確定せず確認対象とする。

## 要確認講演

| 講演番号 | 題名 | 理由 |
|---|---|---|
| I-01 | AI打音解析によるFRP製アンダーデッキパネル工法の間詰部評価 | `phase:tag_limit` |
| IV-37 | 石垣修復工事における３次元シミュレーションを活用した築石配置計画と施工管理 | `phase:tag_limit` |
| V-140 | 亜硝酸塩系防錆剤による腐食抑制効果に関する検討 | `domain:fallback` |
| VII-21 | 嫌気性処理汚泥に優占する未培養系統分類群Synergistota門に属する細菌の分離 | `phase:fallback` |
| CS10-16 | 令和6年能登半島地震と令和6年9月20日からの大雨における道路橋の被害事例の整理 | `phase:fallback` |
| II-165 | ゲート直下に形成される跳水の乱れ強さの特性に対するフルード数の影響 | `domain:fallback` |
| IV-55 | 交差点間の道路空間における横断可能性の検討 | `phase:fallback` |
| IV-93 | 首都高速道路上での高視認性 LED プロジェクターを用いた誘導効果の検証 | `phase:tag_limit` |
| IV-147 | 落石防護網施工におけるUAV(無人航空機)を活用した出来形管理 | `phase:tag_limit` |
| V-210 | フライアッシュおよび高炉スラグ微粉末を同時に用いた3成分高流動コンクリートの基礎物性 | `domain:tag_limit` |
| VI-634 | 魚群探知機を用いた簡易な橋梁洗掘調査手法の開発と実橋梁による計測精度の検証 | `phase:tag_limit` |
| VII-99 | 微生物由来の蓄電性鉱物を用いる塩素化エチレン類の脱塩素速度の向上に関する基礎的検討 | `phase:fallback` |
| CS6-22 | FRP部材を用いて補強された道路橋床版の輪荷重走行試験再現解析と損傷評価 | `phase:tag_limit` |
| CS11-28 | 地方インフラメンテナンスにおける生成AIを活用した技術継承モデルの提案 | `phase:tag_limit` |
| I-419 | TLP 型ハイブリッド浮体接合部の模型載荷実験の再現解析 | `domain:tag_limit` |
| IV-165 | 防災・避難ガイドライン策定のための避難意識についての分析 | `domain:fallback` |
| IV-259 | 線路沿線の用地外大規模岩盤斜面に対する3種類のソフト対策導入について | `phase:fallback` |
| V-628 | 締固めを必要とする高流動コンクリートの硬化後物性に及ぼす材料分離の影響とその解析的評価 | `phase:tag_limit` |
| VII-109 | 大規模商業施設で運用中のグリーンインフラ「バイオスウェル」の計測・モニタリング その2 | `domain:tag_limit` |
| CS14-70 | トンネル越流予測のための機械学習モデルの比較 | `phase:tag_limit` |

## 判定規則の修正例

全120件の題名・タグを確認し、次の部分一致誤判定を修正した。

- 「移動床」の「移動」を交通・アクセシビリティとして扱わない
- `SAR`内の`AR`を拡張現実として扱わない
- 「避難坑」を避難行動として扱わない
- 3Dプリンティングを3次元計測として扱わない
- 環境保全を構造物の維持保全として扱わない
- カーボンニュートラルという語だけでCO2を材料タグにしない

## 判定

low判定は6.7%で、事前に定めた15%以下の目標を満たした。全軸で複数タグが使用され、特定の公式部門だけに依存しない横断分類も確認できた。v0.2の5軸構造は全件分類へ進める水準と判断する。

ただし、要確認講演は人手で確定し、全件分類後もカテゴリ別標本による適合率評価を別途行う。

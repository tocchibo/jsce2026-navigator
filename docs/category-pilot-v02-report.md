# 独自カテゴリ v0.2 層化試行レポート（v0.3規則再評価）

## 結果概要

公式8分類から各15講演、計120講演を等間隔で抽出し、PDFの著者キーワードと短い内容要約を用いて5軸分類を試行した。

- 分類体系: `0.2.0`
- 抽出成功: 120/120講演
- 要確認: 19講演（15.8%）
- low判定: 4講演（3.3%）
- medium判定: 19講演（15.8%）
- high判定: 97講演（80.8%）

`high`は明示規則上の根拠強度であり、人手による正解保証ではない。v0.2分類体系を、全件分布から調整した軸別重みのv0.3規則で再評価した。

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
| 地盤・基礎・斜面 (`ground_foundation_slope`) | 31 |
| 橋梁・高架橋 (`bridge`) | 27 |
| 建設材料 (`construction_materials`) | 25 |
| 構造一般 (`structural_system`) | 25 |
| 道路・舗装 (`road_pavement`) | 21 |
| 河川・流域 (`river_watershed`) | 14 |
| トンネル・地下空間 (`tunnel_underground`) | 13 |
| 海岸・港湾・海洋 (`coast_port_ocean`) | 12 |
| 社会基盤一般 (`civil_systems`) | 11 |
| 都市・地域・交通 (`urban_transport`) | 11 |
| 建設現場・生産 (`construction_site`) | 9 |
| エネルギー・産業施設 (`energy_industrial`) | 9 |
| 環境・生態系 (`environment_ecosystem`) | 8 |
| 気象・気候 (`atmosphere_climate`) | 8 |
| 上下水道・水処理 (`water_sewerage`) | 8 |
| 鉄道・軌道 (`railway`) | 8 |
| 廃棄物・汚染・処分 (`waste_contamination`) | 6 |
| 教育・人材・社会 (`education_society`) | 6 |
| ダム・貯水池 (`dam_reservoir`) | 3 |
| 宇宙・月面インフラ (`space_lunar`) | 1 |

### 目的・工程

| タグ | 講演数 |
|---|---:|
| 性能評価・現象解明 (`performance_evaluation`) | 69 |
| 設計・照査・解析 (`design_analysis`) | 28 |
| 調査・計測 (`survey_measurement`) | 20 |
| 施工・製造 (`construction`) | 18 |
| 維持管理・補修補強 (`maintenance_repair`) | 14 |
| 政策・計画 (`policy_planning`) | 11 |
| 技術・システム開発 (`technology_development`) | 10 |
| 環境評価・保全・浄化 (`environmental_action`) | 9 |
| 防災・避難・災害対応 (`disaster_action`) | 7 |
| 材料・工法開発 (`material_development`) | 7 |
| 点検・診断 (`inspection_diagnosis`) | 6 |
| 教育・人材・合意形成 (`education_consensus`) | 5 |
| 更新・解体・再利用 (`renewal_demolition`) | 5 |
| 品質管理・検査 (`quality_control`) | 4 |
| 運用・マネジメント (`operation_management`) | 3 |

### 技術・手法

| タグ | 講演数 |
|---|---:|
| 数値解析・シミュレーション (`numerical_simulation`) | 13 |
| 現地試験・モニタリング (`field_test_monitoring`) | 12 |
| 室内実験・模型実験 (`laboratory_experiment`) | 11 |
| 統計・確率・最適化 (`statistics_optimization`) | 9 |
| AI・機械学習 (`ai_ml`) | 8 |
| センサ・IoT (`sensing_iot`) | 4 |
| BIM/CIM・デジタルツイン (`bim_digital_twin`) | 3 |
| 3次元計測・点群・リモートセンシング (`three_d_remote`) | 3 |
| 画像解析・コンピュータビジョン (`image_processing`) | 3 |
| 非破壊検査 (`nondestructive_testing`) | 2 |
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
| 老朽化・長寿命化 (`aging_lifecycle`) | 11 |
| 地震・断層・液状化 (`seismic_liquefaction`) | 8 |
| 安全・リスク (`safety_risk`) | 8 |
| 風・雪・寒冷地 (`wind_snow_cold`) | 7 |
| 生物多様性・水質 (`biodiversity_water_quality`) | 6 |
| 洪水・津波・高潮 (`flood_tsunami_storm`) | 6 |
| 劣化・腐食・耐久性 (`deterioration_corrosion`) | 6 |
| 疲労・破壊・耐荷力 (`fatigue_fracture`) | 6 |
| 土砂災害・洗掘・侵食 (`landslide_erosion`) | 6 |
| 制度・調達・事業管理 (`governance_procurement`) | 5 |
| 技術継承・人材確保 (`knowledge_transfer`) | 4 |
| 気候変動・脱炭素 (`climate_decarbonization`) | 4 |
| 生産性・省人化 (`productivity_labor`) | 4 |
| 資源循環・リサイクル (`circular_resources`) | 4 |
| 汚染・浄化 (`pollution_remediation`) | 3 |
| 移動・アクセシビリティ (`mobility_accessibility`) | 3 |
| レジリエンス・緊急対応 (`resilience_emergency`) | 1 |
| 騒音・振動 (`noise_vibration`) | 1 |

## 要確認理由

| 理由 | 件数 |
|---|---:|
| `domain:tag_limit_tie` | 10 |
| `phase:tag_limit_tie` | 6 |
| `phase:fallback` | 3 |
| `domain:fallback` | 1 |

`fallback`は内容から必須軸を確定できず公式部門等から補ったもの、`tag_limit_tie`は軸の上限境界で候補が同点になったものを表す。どちらも自動確定せず確認対象とする。

## 要確認講演

| 講演番号 | 題名 | 理由 |
|---|---|---|
| I-01 | AI打音解析によるFRP製アンダーデッキパネル工法の間詰部評価 | `domain:tag_limit_tie`, `phase:tag_limit_tie` |
| IV-37 | 石垣修復工事における３次元シミュレーションを活用した築石配置計画と施工管理 | `phase:tag_limit_tie` |
| V-71 | アジテータ車挿入型棒状 RI 水分計を用いたコンクリート単位水量の全量管理 | `domain:tag_limit_tie` |
| CS10-16 | 令和6年能登半島地震と令和6年9月20日からの大雨における道路橋の被害事例の整理 | `phase:fallback` |
| IV-55 | 交差点間の道路空間における横断可能性の検討 | `phase:fallback` |
| IV-93 | 首都高速道路上での高視認性 LED プロジェクターを用いた誘導効果の検証 | `phase:tag_limit_tie` |
| V-210 | フライアッシュおよび高炉スラグ微粉末を同時に用いた3成分高流動コンクリートの基礎物性 | `domain:tag_limit_tie` |
| V-349 | 浄水場施設におけるフロック形成池の迂流壁プレキャスト化に関する検討 | `domain:tag_limit_tie` |
| VI-887 | 泥水式シールド工法を対象とした凝集抑制型安定液の開発 その2 | `domain:tag_limit_tie` |
| VII-40 | 植物由来医薬品工場から排出される植物残渣のメタン発酵処理効率向上のための前処理検討 | `domain:tag_limit_tie` |
| VII-99 | 微生物由来の蓄電性鉱物を用いる塩素化エチレン類の脱塩素速度の向上に関する基礎的検討 | `phase:fallback` |
| CS6-22 | FRP部材を用いて補強された道路橋床版の輪荷重走行試験再現解析と損傷評価 | `phase:tag_limit_tie` |
| I-419 | TLP 型ハイブリッド浮体接合部の模型載荷実験の再現解析 | `domain:tag_limit_tie` |
| III-444 | 地盤特性の不均質性を踏まえたボックスカルバートの沈下問題に関する基礎的研究 | `domain:tag_limit_tie` |
| IV-165 | 防災・避難ガイドライン策定のための避難意識についての分析 | `domain:fallback` |
| V-628 | 締固めを必要とする高流動コンクリートの硬化後物性に及ぼす材料分離の影響とその解析的評価 | `phase:tag_limit_tie` |
| VI-1647 | FFUセグメントにおける内面補強鋼殻の試作・組立試験 | `domain:tag_limit_tie` |
| CS9-51 | RFIDひずみ計測システムを用いた鉄道PC橋りょうの有効プレストレスの推定 | `domain:tag_limit_tie` |
| CS14-70 | トンネル越流予測のための機械学習モデルの比較 | `phase:tag_limit_tie` |

## 判定規則の修正例

全120件の題名・タグを確認し、次の部分一致誤判定を修正した。

- 「移動床」の「移動」を交通・アクセシビリティとして扱わない
- `SAR`内の`AR`を拡張現実として扱わない
- 「避難坑」を避難行動として扱わない
- 3Dプリンティングを3次元計測として扱わない
- 環境保全を構造物の維持保全として扱わない
- カーボンニュートラルという語だけでCO2を材料タグにしない

## 判定

low判定は3.3%で、事前に定めた15%以下の目標を満たした。全軸で複数タグが使用され、特定の公式部門だけに依存しない横断分類も確認できた。

全5,636講演の一次分類結果と残る要確認件数は `docs/category-all-report.md` に記録する。

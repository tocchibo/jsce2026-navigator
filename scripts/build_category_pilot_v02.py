"""梗概要約の層化標本を、明示した重み付き規則でv0.2試行分類する。"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "category_sample_source.local.json"
TAXONOMY_PATH = ROOT / "data" / "category_taxonomy.json"
OUTPUT_PATH = ROOT / "data" / "category_pilot_v02.json"

AXIS_FIELD_WEIGHTS = {
    "domain": {"title": 6, "keywords": 7, "session": 4, "summary": 5},
    "phase": {"title": 6, "keywords": 7, "session": 5, "summary": 3},
    "method": {"title": 6, "keywords": 7, "session": 5, "summary": 4},
    "material": {"title": 6, "keywords": 7, "session": 3, "summary": 4},
    "issue": {"title": 6, "keywords": 7, "session": 5, "summary": 4},
}
THRESHOLDS = {"domain": 5, "phase": 5, "method": 5, "material": 5, "issue": 5}

RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "domain": {
        "bridge": (r"橋梁|橋|橋りょう|床版|橋脚|橋台|支承|PC桁|鋼桁|合成桁|鈑桁|主桁|\bbridge(?:s)?\b",),
        "road_pavement": (r"道路|高速道路|舗装|路盤|路床|交差点|交通流|通行止め|ETC|BPR関数|\broad(?:s)?\b|\bpavement\b|\btraffic\b",),
        "railway": (r"鉄道|軌道|新幹線|線路|列車|レール|ホーム柵|走行安全性|\brailway\b|\brail\b|\btrack\b",),
        "tunnel_underground": (r"トンネル|シールド|NATM|セグメント|坑門|覆工|地下空間|\btunnel(?:s)?\b|\bunderground\b",),
        "ground_foundation_slope": (r"地盤|地山|斜面|盛土|土質|土層|砂質土|粘性土|細粒分|地質|地層|間隙(?:径|比|水|圧)|液状化|杭|基礎(?!的|物性|研究|実験)|圧密|ベントナイト|土留め|地中連続壁|カルバート|ケーソン|\bsoil\b|\bground\b|\bfoundation\b|\bslope\b|\bgeotechnical\b|\bgeological\b",),
        "river_watershed": (r"河川|河道|流域|洪水|氾濫|流出|砂防|治山ダム|高水敷|流域治水|掃流|河床|\briver\b|\bwatershed\b|\bflood(?:ing)?\b",),
        "coast_port_ocean": (r"海岸|港湾|岸壁|漁港|海洋|海底|沿岸|アマモ|海水|洋上|波浪|干潟|感潮|潮汐|海面|水面波|\bcoast(?:al)?\b|\bport\b|\bocean\b|\bmarine\b|\bwave(?:s)?\b",),
        "dam_reservoir": (r"ダム湖|貯水池|ダム運用|水力発電ダム|アーチダム|重力式ダム|フィルダム|ダム(?:本体|堤体|基礎|管理|再生|事業|貯水|放流|耐震|施工|建設)|\bdam\b|\breservoir\b",),
        "water_sewerage": (r"上水|下水|浄水|用排水|水処理|汚泥|フロック形成池|メタン発酵|管路|不断水",),
        "atmosphere_climate": (r"降雨|降雪|積雪|気温|気候|降水|線状降水帯|熱環境|\bclimate\b|\brainfall\b|\bsnow\b",),
        "urban_transport": (r"都市|地域計画|公共交通|人流|交通結節|交通行動|居住|歩行者|避難支援|交通規制|土木計画|景観|街路|駅空間",),
        "structural_system": (r"テンセグリティ|構造物|ボックスカルバート|送電鉄塔|浮体|接合部|継手|ボルト|溶接|耐荷力|防護柵|石垣|\bstructur(?:e|al)\b",),
        "construction_materials": (r"コンクリート|セメント|モルタル|アスファルト|鋼材|鋼素地|FRP|ジオポリマー|スラグ|固化材|新材料|建設材料|材料(?:特性|開発|設計|評価|試験|物性|分離|組成|製造)|複合材料|\bconcrete\b|\bcement(?:itious)?\b|\bsteel\b|\bmaterials?\b|\bcomposite(?:s)?\b",),
        "construction_site": (r"建設現場|建設業|作業所|施工管理|出来形管理|工事安全|施工現場|現場における",),
        "environment_ecosystem": (r"生態|生息|魚類|微生物|細菌|生物多様性|環境DNA|自然共生|グリーンインフラ|植被|アマモ場|都市熱環境|環境保全",),
        "waste_contamination": (r"廃棄物|汚染|焼却施設|放射性|マイクロプラスチック|塩素化エチレン",),
        "energy_industrial": (r"発電|風力|送電|エネルギー|CCUS|DAC技術|CO2(?:回収|貯留|圧入|地中)|二酸化炭素(?:回収|貯留|圧入|地中)",),
        "space_lunar": (r"宇宙|月面|レゴリス",),
        "civil_systems": (r"社会基盤|インフラ|建設DX|組織的運用|マネジメント|データサイエンス|計算力学|V&V|UQ|土木分野|\bDX\b|\binfrastructure\b",),
        "education_society": (r"教育|人材|人財|リスキリング|リテラシー|技術継承|DEI|合意形成",),
    },
    "phase": {
        "policy_planning": (r"計画|政策|構想|ガイドライン|候補案|立地特性|意思決定|\bplanning\b|\bpolicy\b",),
        "survey_measurement": (r"調査|計測|測定|観測|モニタリング|検層|サウンディング|推定|\bsurvey\b|\bmeasurement\b|\bmonitoring\b|\bestimation\b",),
        "design_analysis": (r"設計|照査|解析|シミュレーション|予測|推計|算定|試算|モデル|FEM|有限要素|\bdesign\b|\banalysis\b|\bsimulation\b|\bmodel(?:ing|ling)?\b",),
        "performance_evaluation": (r"性能|評価|特性|挙動|強度|耐荷|実験|試験|影響|機構|再現|検証|物性|安定性|効率|変化|基礎研究|実験的検討|原因.*究明|比較|分析|\bevaluation\b|\bperformance\b|\bbehavio(?:u)?r\b|\bcharacteristics?\b|\bdurability\b|\bstrength\b|\bexperiment\b|\bstudy\b|\binvestigation\b",),
        "technology_development": (r"システム|アプリケーション|手法の開発|技術.*開発|モデルの提案|高度化|\bdevelopment\b",),
        "material_development": (r"材料.*開発|工法.*開発|固化材|配合|混和|ジオポリマー|相溶性|プレキャスト化",),
        "construction": (r"施工|工事|掘削|築造|製造|打設|解体|\bconstruction\b",),
        "quality_control": (r"品質管理|検査|出来形|単位水量|施工管理|品質確認",),
        "inspection_diagnosis": (r"点検|診断|異常検知|健全性|損傷評価|変状|打音",),
        "maintenance_repair": (r"維持管理|補修|耐震補強|補強工|既設.*補強|床版補強|インフラ保全|維持保全|修復|取替|長期保全|機能の回復|\bmaintenance\b|\brepair\b",),
        "renewal_demolition": (r"更新|解体|再利用|リサイクル|床版取替",),
        "operation_management": (r"運用|交通制御|交通規制|工程管理|事業管理|ダム運用",),
        "disaster_action": (r"防災|避難(?:行動|計画|支援|誘導|ガイドライン|経路|所)|災害対応|緊急復旧|事故対策|安全対策",),
        "environmental_action": (r"環境評価|環境保全|浄化|資源回収|有用物質.*回収|海水.*回収|生態系造成|生物多様性|自然共生|環境DNA|植被|カーボンニュートラル",),
        "education_consensus": (r"教育|人材育成|人財育成|リスキリング|リテラシー|技術継承|合意形成|ダイバーシティ|エクイティ|インクルージョン|\bDEI\b|\beducation\b",),
    },
    "method": {
        "ai_ml": (r"AI|人工知能|機械学習|深層学習|生成AI|局所外れ値因子",),
        "image_processing": (r"画像|カメラ|写真測量|顕微鏡|サーモグラフィ|オルソ|ExG|画像検索",),
        "sensing_iot": (r"IoT|センサ|RFID|光ファイバ|計測システム|検知装置",),
        "three_d_remote": (r"3D(?:計測|モデル|レーザ|点群)|３D(?:計測|モデル|レーザ|点群)|三次元計測|3次元計測|点群|SAR衛星|Sentinel|リモートセンシング|レーザ",),
        "gis_spatial": (r"\bGIS\b|地理空間|デジタル道路地図|空間分析",),
        "bim_digital_twin": (r"BIM|CIM|デジタルツイン|PLATEAU",),
        "data_platform": (r"データ基盤|データ連携|アプリケーション|ソフトウェア|データベース|情報システム",),
        "numerical_simulation": (r"FEM|有限要素|数値解析|数値実験|シミュレーション|CFD|FLIP|非線形解析|RFEM",),
        "statistics_optimization": (r"統計|確率|最適化|回帰分析|因果効果|アンサンブル|時系列分析|信頼性評価|べき乗則",),
        "laboratory_experiment": (r"室内実験|模型実験|載荷試験|振動台実験|風洞試験|供試体|実験的|基礎実験",),
        "field_test_monitoring": (r"現地|実橋|長期観測|実証試験|モニタリング|供用後|施工実績|現場",),
        "nondestructive_testing": (r"非破壊|打音|サーモグラフィ|超音波|レーダ|電気検層",),
        "robotics_automation": (r"ロボット|自動化|自律施工|無人施工",),
        "drone_uncrewed": (r"UAV|ドローン|無人航空|水中ロボット|ROV",),
        "vr_ar_metaverse": (r"(?<![A-Z])(?:VR|AR)(?![A-Z])|メタバース|仮想現実|拡張現実",),
        "economic_lca": (r"LCA|費用.*便益|経済評価|ライフサイクル評価",),
    },
    "material": {
        "concrete_cement": (r"コンクリート|セメント|モルタル|RC床版|PC床版|PC桁|UFC",),
        "steel_metal": (r"鋼|鉄筋|ボルト|ステンレス|SUS|アルミ",),
        "asphalt": (r"アスファルト|舗装材",),
        "soil_rock": (r"地盤|地山|土質|土壌|岩盤|粘土|ベントナイト|盛土|路盤",),
        "frp_composite": (r"FRP|CFRP|GFRP|連続繊維",),
        "wood_biomass": (r"木材|木質|バイオマス|植物残渣",),
        "polymer_resin": (r"樹脂|ゴム|高分子|プラスチック",),
        "geosynthetics": (r"ジオシンセティックス|ジオテキスタイル|補強土",),
        "water_sediment": (r"底質|底泥|流砂|掃流砂|河床材料",),
        "waste_recycled": (r"副産物|再生材料|リサイクル|廃プラスチック|スラグ|スラッジ|焼却灰",),
        "co2_carbon": (r"CO2(?:固定|吸収|回収|貯留|注入)|二酸化炭素(?:固定|吸収|回収|貯留|注入)|炭酸化|炭酸カルシウム|バイオ炭",),
        "radioactive": (r"放射性|核種",),
    },
    "issue": {
        "aging_lifecycle": (r"老朽|長寿命|維持管理|長期保全|予防保全|耐久性",),
        "seismic_liquefaction": (r"地震|耐震|液状化|断層|振動台",),
        "flood_tsunami_storm": (r"洪水|氾濫|津波|高潮|水害|線状降水帯|大雨",),
        "landslide_erosion": (r"土砂災害|落石|洗掘|侵食|浸食|斜面崩壊",),
        "wind_snow_cold": (r"耐風|風洞|積雪|雪|寒冷地|凍結|凍害",),
        "fatigue_fracture": (r"疲労|破断|破壊|耐荷力|き裂|クラック",),
        "deterioration_corrosion": (r"劣化|腐食|塩害|耐久性|剥落",),
        "climate_decarbonization": (r"気候変動|脱炭素|カーボンニュートラル|CO2|温暖化|CDR",),
        "circular_resources": (r"資源循環|リサイクル|再生材料|副産物|廃プラスチック|有用物質.*回収",),
        "biodiversity_water_quality": (r"生物多様性|生態系|水質|環境DNA|アマモ|栄養塩|OECM",),
        "pollution_remediation": (r"汚染|浄化|マイクロプラスチック|PFAS|PFOA|塩素化エチレン",),
        "noise_vibration": (r"騒音|音響|環境振動|交通振動|振動公害",),
        "safety_risk": (r"安全|リスク|事故|危険|防護",),
        "productivity_labor": (r"生産性|省人|省力|効率化|合理化|業務効率",),
        "knowledge_transfer": (r"技術継承|人材育成|人財育成|リスキリング|暗黙知|若手教育",),
        "resilience_emergency": (r"レジリエンス|緊急|復旧|マルチハザード|事業継続",),
        "mobility_accessibility": (r"移動(?:手段|支援|行動)|公共交通|歩行者|乗り継ぎ|交通不便|要支援者",),
        "governance_procurement": (r"制度|調達|契約|組織|マネジメント|ガイドライン",),
    },
}

DIVISION_FALLBACK = {
    "第I部門": "structural_system",
    "第II部門": "river_watershed",
    "第III部門": "ground_foundation_slope",
    "第IV部門": "urban_transport",
    "第V部門": "construction_materials",
    "第VI部門": "construction_site",
    "第VII部門": "environment_ecosystem",
    "共通セッション": "civil_systems",
}


def field_matches(
    item: dict[str, object], axis_id: str, label_id: str
) -> set[str]:
    fields = {
        "title": str(item["title"]),
        "keywords": " ".join(str(value) for value in item["keywords"]),
        "session": str(item["session"]),
        "summary": str(item["summary"]),
    }
    return {
        field_name
        for field_name, text in fields.items()
        if any(
            re.search(pattern, text, flags=re.IGNORECASE)
            for pattern in RULES[axis_id][label_id]
        )
    }


def score_labels(item: dict[str, object], axis_id: str) -> list[tuple[str, int]]:
    weights = AXIS_FIELD_WEIGHTS[axis_id]
    scores: Counter[str] = Counter()
    for label_id in RULES[axis_id]:
        for field_name in field_matches(item, axis_id, label_id):
            scores[label_id] += weights[field_name]
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


def classify(item: dict[str, object], axis_by_id: dict[str, dict[str, object]]) -> dict[str, object]:
    labels: dict[str, list[str]] = {}
    score_evidence: dict[str, dict[str, int]] = {}
    field_evidence: dict[str, dict[str, list[str]]] = {}
    review_reasons: list[str] = []

    for axis_id, axis in axis_by_id.items():
        ranked = score_labels(item, axis_id)
        threshold = THRESHOLDS[axis_id]
        candidates = [(label, score) for label, score in ranked if score >= threshold]
        max_items = int(axis["max_items"])
        if (
            len(candidates) > max_items
            and candidates[max_items - 1][1] == candidates[max_items][1]
        ):
            review_reasons.append(f"{axis_id}:tag_limit_tie")
        selected = candidates[:max_items]

        if not selected and bool(axis["required"]):
            fallback = (
                DIVISION_FALLBACK[str(item["division"])]
                if axis_id == "domain"
                else "performance_evaluation"
            )
            selected = [(fallback, 0)]
            review_reasons.append(f"{axis_id}:fallback")

        labels[axis_id] = [label for label, _ in selected]
        score_evidence[axis_id] = {label: score for label, score in selected}
        field_evidence[axis_id] = {
            label: sorted(field_matches(item, axis_id, label)) if score else ["fallback"]
            for label, score in selected
        }

    if any(reason.endswith("fallback") for reason in review_reasons):
        confidence = "low"
    elif review_reasons:
        confidence = "medium"
    elif all(
        {"summary", "keywords"}
        & set(field_evidence[axis_id][labels[axis_id][0]])
        for axis_id, axis in axis_by_id.items()
        if bool(axis["required"])
    ):
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "code": item["code"],
        "labels": labels,
        "confidence": confidence,
        "review_required": bool(review_reasons),
        "review_reasons": review_reasons,
        "scores": score_evidence,
        "evidence_fields": field_evidence,
    }


def main() -> int:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    axis_by_id = {axis["id"]: axis for axis in taxonomy["axes"]}
    presentations = []
    for item in source["presentations"]:
        classified = classify(item, axis_by_id)
        classified.pop("evidence_fields")
        presentations.append(classified)
    output = {
        "taxonomy_version": taxonomy["schema_version"],
        "status": "stratified_pilot",
        "sample_method": "15 evenly spaced presentations per official division",
        "classification_method": "axis-sensitive explicit evidence rules v0.3",
        "presentations": presentations,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    confidence = Counter(item["confidence"] for item in presentations)
    reviews = sum(bool(item["review_required"]) for item in presentations)
    print(f"分類完了: {len(presentations)}講演 / 要確認 {reviews}件 / {dict(confidence)}")
    print(f"出力: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

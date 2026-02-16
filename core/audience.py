"""
觀眾輪廓預測模組

基於類型、預算、卡司等資訊，使用規則式引擎推估目標觀眾。
不需外部 API，所有推估皆為內建規則。
"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class AudienceSegment:
    """觀眾分群"""
    label: str
    age_range: str
    gender_ratio: Dict[str, float]  # {'male': 0.6, 'female': 0.4}
    share: float  # 佔比 (0-1)


@dataclass
class AudienceProfile:
    """觀眾輪廓預測結果"""
    primary_segment: AudienceSegment
    segments: List[AudienceSegment]
    total_audience_index: float  # 預估觀影人數指數 (1.0 = 平均)
    family_friendly: bool
    repeat_watch_factor: float  # 重看率指數 (1.0 = 普通)


# NOTE: 規則矩陣——各類型的基礎觀眾分佈
GENRE_AUDIENCE_RULES = {
    '動作': {
        'segments': [
            AudienceSegment('男性青年', '18-30', {'male': 0.70, 'female': 0.30}, 0.45),
            AudienceSegment('男性壯年', '30-45', {'male': 0.60, 'female': 0.40}, 0.30),
            AudienceSegment('青少年', '15-20', {'male': 0.55, 'female': 0.45}, 0.15),
            AudienceSegment('一般觀眾', '20-50', {'male': 0.50, 'female': 0.50}, 0.10),
        ],
        'base_index': 1.2,
        'family_friendly': False,
        'repeat_factor': 1.1,
    },
    '愛情': {
        'segments': [
            AudienceSegment('女性青年', '18-30', {'male': 0.30, 'female': 0.70}, 0.40),
            AudienceSegment('女性壯年', '25-40', {'male': 0.35, 'female': 0.65}, 0.25),
            AudienceSegment('情侶觀眾', '20-35', {'male': 0.48, 'female': 0.52}, 0.25),
            AudienceSegment('一般觀眾', '20-50', {'male': 0.45, 'female': 0.55}, 0.10),
        ],
        'base_index': 0.9,
        'family_friendly': False,
        'repeat_factor': 0.8,
    },
    '恐怖': {
        'segments': [
            AudienceSegment('男性青年', '18-28', {'male': 0.55, 'female': 0.45}, 0.45),
            AudienceSegment('女性青年', '18-28', {'male': 0.40, 'female': 0.60}, 0.25),
            AudienceSegment('大學生族群', '18-24', {'male': 0.50, 'female': 0.50}, 0.20),
            AudienceSegment('恐怖片愛好者', '20-40', {'male': 0.55, 'female': 0.45}, 0.10),
        ],
        'base_index': 1.0,
        'family_friendly': False,
        'repeat_factor': 0.9,
    },
    '喜劇': {
        'segments': [
            AudienceSegment('家庭觀眾', '25-50', {'male': 0.48, 'female': 0.52}, 0.35),
            AudienceSegment('青年族群', '18-30', {'male': 0.50, 'female': 0.50}, 0.30),
            AudienceSegment('銀髮族', '50-65', {'male': 0.45, 'female': 0.55}, 0.15),
            AudienceSegment('青少年', '13-18', {'male': 0.50, 'female': 0.50}, 0.20),
        ],
        'base_index': 1.3,
        'family_friendly': True,
        'repeat_factor': 1.0,
    },
    '職人劇': {
        'segments': [
            AudienceSegment('職場工作者', '25-45', {'male': 0.48, 'female': 0.52}, 0.40),
            AudienceSegment('青年白領', '22-35', {'male': 0.45, 'female': 0.55}, 0.30),
            AudienceSegment('壯年觀眾', '35-55', {'male': 0.50, 'female': 0.50}, 0.20),
            AudienceSegment('一般觀眾', '20-50', {'male': 0.50, 'female': 0.50}, 0.10),
        ],
        'base_index': 0.8,
        'family_friendly': False,
        'repeat_factor': 0.7,
    },
}


# NOTE: 題材關鍵字與熱度貢獻值
TOPIC_KEYWORDS = {
    # 高熱度題材
    '台灣': 1.2, '本土': 1.1, '社會': 1.0, '犯罪': 1.3, '追兇': 1.2,
    '復仇': 1.1, '鬼怪': 1.2, '都市': 0.9, '校園': 1.0, '青春': 1.1,
    '搞笑': 1.0, '感人': 0.9, '家庭': 1.0, '親情': 1.0,
    # 中熱度
    '歷史': 0.8, '戰爭': 0.9, '科幻': 0.7, '奇幻': 0.8, '懸疑': 1.1,
    '推理': 1.0, '美食': 1.0, '旅行': 0.8, '運動': 0.9, '音樂': 0.8,
    # 特殊加分
    '真人真事': 1.3, '改編': 1.1, 'IP': 1.2, '續集': 1.3,
    '金馬': 0.7, '藝術': 0.5, '實驗': 0.4,
}


def predict_audience_profile(
    genre: str,
    budget: float,
    cast_level: int,
    is_sequel: bool = False,
) -> AudienceProfile:
    """
    預測目標觀眾輪廓。

    NOTE: 高預算和明星卡司會提高觀影人數指數；
          續集會提高重看率。

    Args:
        genre: 電影類型
        budget: 預算（百萬 TWD）
        cast_level: 卡司等級 (1-5)
        is_sequel: 是否為續集

    Returns:
        AudienceProfile 物件
    """
    rules = GENRE_AUDIENCE_RULES.get(genre, GENRE_AUDIENCE_RULES['動作'])

    # 觀影人數指數調整
    index = rules['base_index']

    # 高預算 → 高曝光
    if budget > 80:
        index *= 1.2
    elif budget > 50:
        index *= 1.1

    # 明星效應
    if cast_level >= 4:
        index *= 1.15
    elif cast_level <= 2:
        index *= 0.85

    # 重看率
    repeat_factor = rules['repeat_factor']
    if is_sequel:
        repeat_factor *= 1.3

    return AudienceProfile(
        primary_segment=rules['segments'][0],
        segments=rules['segments'],
        total_audience_index=round(index, 2),
        family_friendly=rules['family_friendly'],
        repeat_watch_factor=round(repeat_factor, 2),
    )


def estimate_topic_heat(keywords: List[str]) -> Dict:
    """
    分析劇本關鍵字的題材熱度。

    NOTE: 從 TOPIC_KEYWORDS 查表計算各維度熱度，
          並給出綜合評分。

    Args:
        keywords: 劇本摘要提取的關鍵字列表

    Returns:
        Dict 包含 overall_score, matched_keywords, analysis
    """
    if not keywords:
        return {
            'overall_score': 50.0,
            'matched_keywords': [],
            'analysis': '未提供關鍵字，無法分析。',
        }

    matched = []
    scores = []
    for kw in keywords:
        kw = kw.strip()
        if kw in TOPIC_KEYWORDS:
            matched.append({'keyword': kw, 'heat': TOPIC_KEYWORDS[kw]})
            scores.append(TOPIC_KEYWORDS[kw])

    if not scores:
        overall = 50.0
        analysis = '提供的關鍵字未匹配到已知題材，建議補充更多描述。'
    else:
        avg_heat = sum(scores) / len(scores)
        overall = min(100.0, avg_heat * 60)

        # 根據熱度等級給出分析
        if overall >= 75:
            analysis = '🔥 題材熱度高！涵蓋市場關注的熱門元素，具備話題性。'
        elif overall >= 55:
            analysis = '📊 題材熱度中等。具備一定吸引力，建議搭配行銷策略強化話題。'
        else:
            analysis = '⚡ 題材較為小眾或藝術取向。需精準定位目標觀眾。'

    return {
        'overall_score': round(overall, 1),
        'matched_keywords': matched,
        'unmatched_keywords': [kw for kw in keywords if kw.strip() not in TOPIC_KEYWORDS],
        'analysis': analysis,
    }


def get_audience_radar_data(profile: AudienceProfile) -> Dict:
    """
    將觀眾輪廓轉換為雷達圖資料格式。

    NOTE: 各維度分數以 0-100 表示，用於 Plotly 雷達圖。

    Returns:
        Dict 包含 categories 和 values
    """
    # 從 segments 計算各年齡層佔比
    youth_share = sum(s.share for s in profile.segments if '18' in s.age_range or '15' in s.age_range or '13' in s.age_range)
    adult_share = sum(s.share for s in profile.segments if '30' in s.age_range or '25' in s.age_range)
    senior_share = sum(s.share for s in profile.segments if '50' in s.age_range or '45' in s.age_range)

    # 男女比
    avg_male = sum(s.gender_ratio['male'] * s.share for s in profile.segments)

    return {
        'categories': ['青年吸引力', '家庭觀影', '重看意願', '觀影人數', '男性偏好', '話題性'],
        'values': [
            min(100, youth_share * 150),
            100 if profile.family_friendly else 30,
            min(100, profile.repeat_watch_factor * 70),
            min(100, profile.total_audience_index * 65),
            min(100, avg_male * 130),
            min(100, profile.total_audience_index * 55 + profile.repeat_watch_factor * 20),
        ],
    }

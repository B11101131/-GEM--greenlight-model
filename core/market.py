"""
市場分析模組

提供歷史票房查詢、競爭片分析、檔期選擇建議等功能。
資料來源為 data/ 目錄下的 CSV 檔案。
"""
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# NOTE: 資料檔路徑，相對於專案根目錄
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HISTORICAL_CSV = os.path.join(DATA_DIR, "historical_box_office.csv")
CALENDAR_CSV = os.path.join(DATA_DIR, "release_calendar.csv")


@dataclass
class GenreStats:
    """類型票房統計結果"""
    genre: str
    count: int
    mean_box_office: float
    median_box_office: float
    p25_box_office: float
    p75_box_office: float
    mean_budget: float
    mean_roi: float


@dataclass
class CompetitionResult:
    """競爭分析結果"""
    month: int
    month_label: str
    competition_level: int
    holiday_factor: float
    avg_box_office_index: float
    genre_fit: bool
    risk_assessment: str  # 低/中/高


@dataclass
class MonthRecommendation:
    """檔期推薦結果"""
    month: int
    month_label: str
    score: float  # 綜合評分 (0-100)
    reasons: List[str]


def load_historical_data() -> pd.DataFrame:
    """
    載入歷史票房資料。

    Returns:
        歷史票房 DataFrame
    """
    if not os.path.exists(HISTORICAL_CSV):
        return pd.DataFrame()

    df = pd.read_csv(HISTORICAL_CSV)
    # NOTE: 計算 ROI 欄位供後續分析使用
    df['total_cost'] = df['budget'] + df['marketing']
    df['total_revenue'] = df['box_office'] * 0.5 + df['streaming_revenue']
    df['net_profit'] = df['total_revenue'] - df['total_cost']
    df['roi'] = (df['net_profit'] / df['total_cost'] * 100).round(1)
    return df


def filter_comparables(
    genre: Optional[str] = None,
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> pd.DataFrame:
    """
    篩選同類型可比專案。

    Args:
        genre: 篩選類型（None 表示不限）
        budget_min: 最低預算（百萬 TWD）
        budget_max: 最高預算（百萬 TWD）
        year_min: 最早年份
        year_max: 最晚年份

    Returns:
        篩選後的 DataFrame
    """
    df = load_historical_data()
    if df.empty:
        return df

    if genre:
        df = df[df['genre'] == genre]
    if budget_min is not None:
        df = df[df['budget'] >= budget_min]
    if budget_max is not None:
        df = df[df['budget'] <= budget_max]
    if year_min is not None:
        df = df[df['year'] >= year_min]
    if year_max is not None:
        df = df[df['year'] <= year_max]

    return df.reset_index(drop=True)


def get_genre_statistics(genre: str) -> Optional[GenreStats]:
    """
    計算指定類型的票房統計。

    Args:
        genre: 電影類型

    Returns:
        GenreStats 物件，若無資料則回傳 None
    """
    df = load_historical_data()
    genre_df = df[df['genre'] == genre]

    if genre_df.empty:
        return None

    return GenreStats(
        genre=genre,
        count=len(genre_df),
        mean_box_office=float(genre_df['box_office'].mean()),
        median_box_office=float(genre_df['box_office'].median()),
        p25_box_office=float(genre_df['box_office'].quantile(0.25)),
        p75_box_office=float(genre_df['box_office'].quantile(0.75)),
        mean_budget=float(genre_df['budget'].mean()),
        mean_roi=float(genre_df['roi'].mean()),
    )


def get_all_genre_statistics() -> Dict[str, GenreStats]:
    """
    計算所有類型的票房統計。

    Returns:
        Dict，key 為類型名稱，value 為 GenreStats
    """
    df = load_historical_data()
    if df.empty:
        return {}

    result = {}
    for genre in df['genre'].unique():
        stats = get_genre_statistics(genre)
        if stats:
            result[genre] = stats
    return result


def load_release_calendar() -> pd.DataFrame:
    """
    載入檔期參考資料。

    Returns:
        檔期資料 DataFrame
    """
    if not os.path.exists(CALENDAR_CSV):
        return pd.DataFrame()
    return pd.read_csv(CALENDAR_CSV)


def analyze_competition(release_month: int, genre: str) -> CompetitionResult:
    """
    分析指定月份的競爭強度。

    NOTE: 競爭風險由 competition_level 和類型匹配度共同決定。
          若該月份不適合此類型且競爭激烈，風險評為「高」。

    Args:
        release_month: 預計上映月份 (1-12)
        genre: 電影類型

    Returns:
        CompetitionResult 物件
    """
    calendar_df = load_release_calendar()
    month_data = calendar_df[calendar_df['month'] == release_month]

    if month_data.empty:
        return CompetitionResult(
            month=release_month,
            month_label=f"{release_month} 月",
            competition_level=3,
            holiday_factor=1.0,
            avg_box_office_index=1.0,
            genre_fit=False,
            risk_assessment="中",
        )

    row = month_data.iloc[0]
    best_genres = str(row['best_genres']).split(';')
    genre_fit = genre in best_genres
    competition_level = int(row['competition_level'])

    # NOTE: 風險評級邏輯 — 高競爭 + 類型不符 = 高風險
    if competition_level >= 4 and not genre_fit:
        risk = "高"
    elif competition_level >= 4 or not genre_fit:
        risk = "中"
    else:
        risk = "低"

    return CompetitionResult(
        month=release_month,
        month_label=str(row['label']),
        competition_level=competition_level,
        holiday_factor=float(row['holiday_factor']),
        avg_box_office_index=float(row['avg_box_office_index']),
        genre_fit=genre_fit,
        risk_assessment=risk,
    )


def recommend_release_months(genre: str) -> List[MonthRecommendation]:
    """
    推薦上映月份，依綜合評分排序。

    NOTE: 評分公式 = 票房指數 × 30 + 假期因子 × 20 + 類型匹配 × 30 - 競爭壓力 × 20
          分數範圍約 0-100，越高越推薦。

    Args:
        genre: 電影類型

    Returns:
        按評分降序排列的 MonthRecommendation 列表
    """
    calendar_df = load_release_calendar()
    if calendar_df.empty:
        return []

    recommendations = []

    for _, row in calendar_df.iterrows():
        month = int(row['month'])
        best_genres = str(row['best_genres']).split(';')
        genre_fit = genre in best_genres

        # 綜合評分
        box_office_score = float(row['avg_box_office_index']) * 30
        holiday_score = float(row['holiday_factor']) * 20
        genre_score = 30.0 if genre_fit else 0.0
        competition_penalty = int(row['competition_level']) * 4

        score = box_office_score + holiday_score + genre_score - competition_penalty
        score = max(0.0, min(100.0, score))

        # 產生推薦理由
        reasons = []
        if genre_fit:
            reasons.append(f"✅ 此月份適合「{genre}」類型")
        else:
            reasons.append(f"⚠️ 此月份非「{genre}」類型旺季")

        if float(row['avg_box_office_index']) >= 1.2:
            reasons.append("📈 票房表現高於平均")
        elif float(row['avg_box_office_index']) <= 0.7:
            reasons.append("📉 票房表現低於平均")

        if float(row['holiday_factor']) >= 1.3:
            reasons.append("🎉 假期效應強（連假/寒暑假）")

        if int(row['competition_level']) >= 4:
            reasons.append("🔥 競爭激烈（同期大片多）")
        elif int(row['competition_level']) <= 2:
            reasons.append("💎 競爭較少，有利排片")

        if row.get('notes'):
            reasons.append(f"📝 {row['notes']}")

        recommendations.append(MonthRecommendation(
            month=month,
            month_label=str(row['label']),
            score=round(score, 1),
            reasons=reasons,
        ))

    # 按評分排序
    recommendations.sort(key=lambda x: x.score, reverse=True)
    return recommendations


def get_monthly_genre_performance() -> pd.DataFrame:
    """
    計算各月份 × 各類型的票房表現矩陣，用於熱力圖。

    Returns:
        pivot DataFrame (月份 × 類型)，值為平均票房
    """
    df = load_historical_data()
    if df.empty:
        return pd.DataFrame()

    pivot = df.pivot_table(
        values='box_office',
        index='release_month',
        columns='genre',
        aggfunc='mean',
    ).round(1)

    # 確保 12 個月都有資料
    all_months = pd.Index(range(1, 13), name='release_month')
    pivot = pivot.reindex(all_months).fillna(0)

    return pivot

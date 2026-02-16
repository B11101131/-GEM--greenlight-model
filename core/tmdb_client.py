"""
TMDB 電影資料庫整合

透過 TMDB API 取得全球電影票房、評分、演員等真實市場數據。
內建快取機制避免重複呼叫。
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# NOTE: 簡易記憶體快取，避免同一 session 重複呼叫
_cache: Dict[str, dict] = {}
CACHE_TTL_SECONDS = 300  # 5 分鐘

BASE_URL = "https://api.themoviedb.org/3"

# 類型 ID 對照表（TMDB → GEM 系統）
GENRE_MAP = {
    28: "動作", 12: "動作", 16: "動作",
    35: "喜劇",
    10749: "愛情",
    27: "恐怖", 53: "恐怖",
    18: "職人劇", 10751: "職人劇",
    878: "動作", 14: "動作",
}


@dataclass
class TmdbMovie:
    """TMDB 電影資料"""
    tmdb_id: int = 0
    title: str = ""
    original_title: str = ""
    release_date: str = ""
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    overview: str = ""
    genres: List[str] = field(default_factory=list)
    revenue: float = 0.0  # 全球票房（USD）
    budget_usd: float = 0.0
    poster_url: str = ""


@dataclass
class TmdbSearchResult:
    """TMDB 搜尋結果"""
    movies: List[TmdbMovie] = field(default_factory=list)
    total_results: int = 0
    source: str = "tmdb"


def _get_cached(key: str) -> Optional[dict]:
    """取得快取資料（若未過期）"""
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            return entry["data"]
        else:
            del _cache[key]
    return None


def _set_cache(key: str, data: dict) -> None:
    """設定快取"""
    _cache[key] = {"data": data, "timestamp": time.time()}


def _api_request(
    endpoint: str,
    api_key: str,
    params: Optional[Dict] = None,
) -> Optional[Dict]:
    """
    發送 TMDB API 請求。

    NOTE: 自動加入 api_key 和 language 參數，
          含 timeout 和錯誤處理。
    """
    import requests

    if params is None:
        params = {}
    params["api_key"] = api_key
    params["language"] = "zh-TW"

    cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        resp = requests.get(
            f"{BASE_URL}{endpoint}",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _set_cache(cache_key, data)
        return data
    except Exception as e:
        logger.warning(f"TMDB API 請求失敗: {endpoint} → {e}")
        return None


def search_similar_movies(
    genre: str,
    api_key: str,
    year_from: int = 2020,
    year_to: int = 2025,
    page: int = 1,
) -> TmdbSearchResult:
    """
    搜尋指定類型的近期電影。

    NOTE: 搜尋結果以 popularity 排序，
          取得最受歡迎的同類型影片。
    """
    import json

    # 將 GEM 類型轉為 TMDB genre_id
    gem_to_tmdb = {
        "動作": "28",
        "喜劇": "35",
        "愛情": "10749",
        "恐怖": "27",
        "職人劇": "18",
    }
    genre_id = gem_to_tmdb.get(genre, "28")

    data = _api_request("/discover/movie", api_key, {
        "with_genres": genre_id,
        "primary_release_date.gte": f"{year_from}-01-01",
        "primary_release_date.lte": f"{year_to}-12-31",
        "sort_by": "popularity.desc",
        "page": page,
        "region": "TW",
    })

    if not data:
        return TmdbSearchResult()

    movies = []
    for item in data.get("results", [])[:10]:
        movies.append(TmdbMovie(
            tmdb_id=item.get("id", 0),
            title=item.get("title", ""),
            original_title=item.get("original_title", ""),
            release_date=item.get("release_date", ""),
            vote_average=item.get("vote_average", 0),
            vote_count=item.get("vote_count", 0),
            popularity=item.get("popularity", 0),
            overview=item.get("overview", "")[:100],
            genres=[GENRE_MAP.get(gid, "其他") for gid in item.get("genre_ids", [])],
            poster_url=f"https://image.tmdb.org/t/p/w200{item.get('poster_path', '')}" if item.get("poster_path") else "",
        ))

    return TmdbSearchResult(
        movies=movies,
        total_results=data.get("total_results", 0),
    )


def get_movie_details(tmdb_id: int, api_key: str) -> Optional[TmdbMovie]:
    """
    取得單一電影的詳細資料（含票房和預算）。

    NOTE: discover endpoint 不含 revenue/budget，
          需額外呼叫 movie details endpoint。
    """
    data = _api_request(f"/movie/{tmdb_id}", api_key)
    if not data:
        return None

    return TmdbMovie(
        tmdb_id=data.get("id", 0),
        title=data.get("title", ""),
        original_title=data.get("original_title", ""),
        release_date=data.get("release_date", ""),
        vote_average=data.get("vote_average", 0),
        vote_count=data.get("vote_count", 0),
        popularity=data.get("popularity", 0),
        overview=data.get("overview", "")[:200],
        genres=[g.get("name", "") for g in data.get("genres", [])],
        revenue=data.get("revenue", 0) / 1_000_000,  # 轉為百萬 USD
        budget_usd=data.get("budget", 0) / 1_000_000,
    )


def get_trending(api_key: str, time_window: str = "week") -> TmdbSearchResult:
    """
    取得熱門趨勢電影。

    Args:
        api_key: TMDB API 金鑰
        time_window: "day" 或 "week"
    """
    data = _api_request(f"/trending/movie/{time_window}", api_key)
    if not data:
        return TmdbSearchResult()

    movies = []
    for item in data.get("results", [])[:10]:
        movies.append(TmdbMovie(
            tmdb_id=item.get("id", 0),
            title=item.get("title", ""),
            original_title=item.get("original_title", ""),
            release_date=item.get("release_date", ""),
            vote_average=item.get("vote_average", 0),
            vote_count=item.get("vote_count", 0),
            popularity=item.get("popularity", 0),
            overview=item.get("overview", "")[:100],
            genres=[GENRE_MAP.get(gid, "其他") for gid in item.get("genre_ids", [])],
            poster_url=f"https://image.tmdb.org/t/p/w200{item.get('poster_path', '')}" if item.get("poster_path") else "",
        ))

    return TmdbSearchResult(
        movies=movies,
        total_results=data.get("total_results", len(movies)),
    )


# NOTE: 需要 import json 在模組層級
import json

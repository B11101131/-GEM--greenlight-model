"""
LLM 劇本分析引擎

使用外部 LLM API（OpenAI / Gemini）進行劇本深度分析。
若 API 不可用，自動 fallback 到 audience.py 的規則引擎。
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# NOTE: 統一 prompt 模板，確保不同 LLM 回傳格式一致
SCRIPT_ANALYSIS_PROMPT = """你是一位專業的台灣電影市場分析師。
請根據以下電影資訊，提供詳盡的市場分析報告。

## 電影資訊
- 類型：{genre}
- 預算：{budget} 百萬台幣
- 劇本大綱：{synopsis}
- 卡司等級：{cast_level}/5
- 是否為續集：{is_sequel}

## 請提供以下分析（以 JSON 格式回覆）：
{{
  "topic_heat": {{
    "score": <1-100 分>,
    "reasoning": "<題材熱度分析原因>"
  }},
  "target_audience": {{
    "primary": "<主要目標觀眾描述>",
    "age_range": "<目標年齡範圍>",
    "gender_skew": "<性別傾向：均衡/偏男/偏女>"
  }},
  "market_positioning": {{
    "comparable_films": ["<類似影片 1>", "<類似影片 2>"],
    "differentiation": "<市場差異化優勢>",
    "expected_box_office_range": "<預估票房範圍>"
  }},
  "risk_factors": [
    "<風險 1>",
    "<風險 2>"
  ],
  "marketing_suggestions": [
    "<行銷建議 1>",
    "<行銷建議 2>"
  ],
  "overall_assessment": "<一句話總結>"
}}

請確保回覆為合法的 JSON 格式。"""


@dataclass
class ScriptAnalysisResult:
    """劇本分析結果"""
    topic_heat_score: float = 0.0
    topic_heat_reasoning: str = ""
    target_audience_primary: str = ""
    target_audience_age: str = ""
    target_audience_gender: str = ""
    comparable_films: List[str] = field(default_factory=list)
    differentiation: str = ""
    expected_box_office: str = ""
    risk_factors: List[str] = field(default_factory=list)
    marketing_suggestions: List[str] = field(default_factory=list)
    overall_assessment: str = ""
    source: str = "llm"  # "llm" 或 "fallback"
    provider: str = ""
    raw_response: str = ""


def analyze_script(
    synopsis: str,
    genre: str,
    budget: float,
    cast_level: int = 3,
    is_sequel: bool = False,
) -> ScriptAnalysisResult:
    """
    使用 LLM 分析劇本大綱。

    NOTE: 自動偵測可用的 LLM provider，
          若都不可用則 fallback 到規則引擎。

    Args:
        synopsis: 劇本大綱或故事摘要
        genre: 電影類型
        budget: 預算（百萬 TWD）
        cast_level: 卡司等級 (1-5)
        is_sequel: 是否為續集

    Returns:
        ScriptAnalysisResult 分析結果
    """
    from core.api_config import get_llm_provider, get_api_key

    provider = get_llm_provider()

    if provider is None:
        logger.info("無可用 LLM API，使用 fallback 規則引擎")
        return _fallback_analysis(synopsis, genre, budget, cast_level, is_sequel)

    api_key = get_api_key(provider)
    prompt = SCRIPT_ANALYSIS_PROMPT.format(
        genre=genre,
        budget=budget,
        synopsis=synopsis,
        cast_level=cast_level,
        is_sequel="是" if is_sequel else "否",
    )

    try:
        if provider == "openai":
            raw = _call_openai(api_key, prompt)
        elif provider == "gemini":
            raw = _call_gemini(api_key, prompt)
        elif provider == "anthropic":
            raw = _call_anthropic(api_key, prompt)
        else:
            return _fallback_analysis(synopsis, genre, budget, cast_level, is_sequel)

        result = _parse_llm_response(raw)
        result.provider = provider
        result.raw_response = raw
        return result

    except Exception as e:
        logger.warning(f"LLM 分析失敗 ({provider}): {e}，使用 fallback")
        return _fallback_analysis(synopsis, genre, budget, cast_level, is_sequel)


def _call_openai(api_key: str, prompt: str) -> str:
    """呼叫 OpenAI API"""
    import requests

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "你是專業的台灣電影市場分析師，請以 JSON 格式回覆。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_gemini(api_key: str, prompt: str) -> str:
    """呼叫 Gemini API"""
    import requests

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000,
                "responseMimeType": "application/json",
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_anthropic(api_key: str, prompt: str) -> str:
    """呼叫 Anthropic Claude API"""
    import requests

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2000,
            "system": "你是專業的台灣電影市場分析師，請以 JSON 格式回覆。",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    # NOTE: Anthropic 回傳格式：content[0].text
    return data["content"][0]["text"]


def _parse_llm_response(raw: str) -> ScriptAnalysisResult:
    """
    解析 LLM 回傳的 JSON。

    NOTE: LLM 回傳格式可能不完全符合預期，
          每個欄位都做安全存取。
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # HACK: 嘗試從 markdown code block 中提取 JSON
        import re
        match = re.search(r'```json?\s*(.*?)\s*```', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
            logger.warning("LLM 回傳非 JSON 格式")
            return ScriptAnalysisResult(
                overall_assessment=raw[:500],
                source="llm",
            )

    # 安全取值
    topic = data.get("topic_heat", {})
    audience = data.get("target_audience", {})
    market = data.get("market_positioning", {})

    return ScriptAnalysisResult(
        topic_heat_score=float(topic.get("score", 50)),
        topic_heat_reasoning=str(topic.get("reasoning", "")),
        target_audience_primary=str(audience.get("primary", "")),
        target_audience_age=str(audience.get("age_range", "")),
        target_audience_gender=str(audience.get("gender_skew", "")),
        comparable_films=list(market.get("comparable_films", [])),
        differentiation=str(market.get("differentiation", "")),
        expected_box_office=str(market.get("expected_box_office_range", "")),
        risk_factors=list(data.get("risk_factors", [])),
        marketing_suggestions=list(data.get("marketing_suggestions", [])),
        overall_assessment=str(data.get("overall_assessment", "")),
        source="llm",
    )


def _fallback_analysis(
    synopsis: str,
    genre: str,
    budget: float,
    cast_level: int,
    is_sequel: bool,
) -> ScriptAnalysisResult:
    """
    Fallback：使用 audience.py 的規則引擎。

    NOTE: 當 LLM API 不可用時自動啟用，
          提供基本的關鍵字分析結果。
    """
    from core.audience import estimate_topic_heat, predict_audience_profile

    # 從大綱提取關鍵字
    keywords = _extract_keywords(synopsis)
    heat_result = estimate_topic_heat(keywords)

    profile = predict_audience_profile(
        genre=genre,
        budget=budget,
        cast_level=cast_level,
        is_sequel=is_sequel,
    )

    return ScriptAnalysisResult(
        topic_heat_score=heat_result.get("overall_score", 50),
        topic_heat_reasoning=heat_result.get("analysis", "規則引擎分析"),
        target_audience_primary=profile.primary_segment.label,
        target_audience_age=profile.primary_segment.age_range,
        target_audience_gender="均衡",
        comparable_films=[],
        differentiation="",
        expected_box_office="",
        risk_factors=[],
        marketing_suggestions=[],
        overall_assessment=f"基於規則引擎的初步分析（題材指數: {heat_result.get('overall_score', 5)}/10）",
        source="fallback",
    )


def _extract_keywords(synopsis: str) -> List[str]:
    """
    從劇本大綱提取關鍵字。

    NOTE: 簡單實作——以常見分類關鍵字做比對。
          不依賴外部 NLP 套件。
    """
    keyword_pool = [
        "愛情", "復仇", "家庭", "友情", "成長",
        "犯罪", "推理", "懸疑", "鬼怪", "靈異",
        "校園", "職場", "運動", "音樂", "美食",
        "歷史", "戰爭", "科幻", "奇幻", "冒險",
        "社會", "政治", "環保", "醫療", "法律",
        "AI", "機器人", "太空", "末日", "喪屍",
    ]
    return [kw for kw in keyword_pool if kw in synopsis]

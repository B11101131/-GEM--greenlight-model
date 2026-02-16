"""
外部 API 設定管理器

統一管理所有外部 API 連線設定，支援 OpenAI / Gemini / TMDB / 自訂 API。
金鑰以環境變數或 Streamlit secrets 方式讀取，確保安全性。
"""
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# NOTE: 設定檔路徑（本地磁碟，不應上傳 git）
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".api_config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "api_settings.json")

# 支援的 API provider 定義
SUPPORTED_PROVIDERS = {
    "openai": {
        "label": "OpenAI (GPT)",
        "description": "使用 GPT-4o-mini 進行劇本分析與題材評估",
        "env_key": "OPENAI_API_KEY",
        "required_fields": ["api_key"],
        "default_model": "gpt-4o-mini",
    },
    "gemini": {
        "label": "Google Gemini",
        "description": "使用 Gemini 2.0 Flash 進行劇本分析與題材評估",
        "env_key": "GEMINI_API_KEY",
        "required_fields": ["api_key"],
        "default_model": "gemini-2.0-flash",
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "description": "使用 Claude 3.5 Sonnet 進行劇本分析與題材評估",
        "env_key": "ANTHROPIC_API_KEY",
        "required_fields": ["api_key"],
        "default_model": "claude-3-5-sonnet-20241022",
    },
    "tmdb": {
        "label": "TMDB 電影資料庫",
        "description": "取得全球電影票房、評分、演員等真實市場數據",
        "env_key": "TMDB_API_KEY",
        "required_fields": ["api_key"],
        "base_url": "https://api.themoviedb.org/3",
    },
    "custom": {
        "label": "自訂 REST API",
        "description": "連接使用者自建的票房/市場資料端點",
        "required_fields": ["base_url"],
        "optional_fields": ["api_key", "headers"],
    },
}


@dataclass
class ApiStatus:
    """API 連線狀態"""
    provider: str
    is_configured: bool = False
    is_connected: bool = False
    latency_ms: float = 0.0
    message: str = ""
    model: str = ""


def _ensure_config_dir() -> None:
    """確保設定目錄存在"""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # NOTE: 自動建立 .gitignore 防止金鑰外洩
    gitignore_path = os.path.join(CONFIG_DIR, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("*\n")


def load_api_config() -> Dict[str, Dict]:
    """
    載入 API 設定。

    NOTE: 優先順序：
    1. 環境變數（適合 CI/CD）
    2. Streamlit secrets（適合部署）
    3. 本地設定檔（適合開發）
    """
    config: Dict[str, Dict] = {}

    # 讀取本地設定檔
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"API 設定檔讀取失敗: {e}")

    # 環境變數覆蓋
    for provider, info in SUPPORTED_PROVIDERS.items():
        env_key = info.get("env_key")
        if env_key:
            env_val = os.getenv(env_key)
            if env_val:
                if provider not in config:
                    config[provider] = {}
                config[provider]["api_key"] = env_val

    # Streamlit secrets 覆蓋
    try:
        import streamlit as st
        for provider, info in SUPPORTED_PROVIDERS.items():
            env_key = info.get("env_key", "")
            if env_key and hasattr(st, "secrets") and env_key in st.secrets:
                if provider not in config:
                    config[provider] = {}
                config[provider]["api_key"] = st.secrets[env_key]
    except Exception:
        pass

    return config


def save_api_config(config: Dict[str, Dict]) -> None:
    """
    儲存 API 設定到本地檔案。

    NOTE: 金鑰以明文存於本地磁碟，
          目錄已有 .gitignore 保護不會上傳。
    """
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info("API 設定已儲存")


def is_provider_configured(provider: str) -> bool:
    """檢查指定 provider 是否已設定金鑰"""
    config = load_api_config()
    provider_config = config.get(provider, {})

    required = SUPPORTED_PROVIDERS.get(provider, {}).get("required_fields", [])
    return all(provider_config.get(field) for field in required)


def get_api_key(provider: str) -> Optional[str]:
    """
    取得指定 provider 的 API 金鑰。

    NOTE: 不應在日誌或錯誤訊息中記錄金鑰內容。
    """
    config = load_api_config()
    return config.get(provider, {}).get("api_key")


def get_custom_config(provider: str = "custom") -> Dict:
    """取得自訂 API 的完整設定"""
    config = load_api_config()
    return config.get(provider, {})


def test_connection(provider: str) -> ApiStatus:
    """
    測試指定 API 的連線狀態。

    NOTE: 每個 provider 使用最輕量的 API 呼叫測試，
          避免消耗 token 或觸發計費。
    """
    import time

    status = ApiStatus(provider=provider)

    if not is_provider_configured(provider):
        status.message = "❌ 尚未設定金鑰"
        return status

    status.is_configured = True
    api_key = get_api_key(provider)
    start_time = time.time()

    try:
        if provider == "openai":
            status = _test_openai(api_key, status)
        elif provider == "gemini":
            status = _test_gemini(api_key, status)
        elif provider == "anthropic":
            status = _test_anthropic(api_key, status)
        elif provider == "tmdb":
            status = _test_tmdb(api_key, status)
        elif provider == "custom":
            custom_config = get_custom_config()
            status = _test_custom(custom_config, status)
        else:
            status.message = f"❌ 不支援的 provider: {provider}"

        status.latency_ms = (time.time() - start_time) * 1000

    except Exception as e:
        status.message = f"❌ 連線失敗: {str(e)}"
        status.latency_ms = (time.time() - start_time) * 1000
        logger.warning(f"API 連線測試失敗 ({provider}): {e}")

    return status


def _test_openai(api_key: str, status: ApiStatus) -> ApiStatus:
    """測試 OpenAI API 連線"""
    import requests

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # NOTE: 用 models endpoint 測試，不消耗 token
    resp = requests.get(
        "https://api.openai.com/v1/models",
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 200:
        status.is_connected = True
        status.message = "✅ 連線成功"
        status.model = SUPPORTED_PROVIDERS["openai"]["default_model"]
    elif resp.status_code == 401:
        status.message = "❌ API 金鑰無效"
    else:
        status.message = f"❌ HTTP {resp.status_code}"

    return status


def _test_gemini(api_key: str, status: ApiStatus) -> ApiStatus:
    """測試 Gemini API 連線"""
    import requests

    # NOTE: 用 models list endpoint 測試
    resp = requests.get(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        timeout=10,
    )
    if resp.status_code == 200:
        status.is_connected = True
        status.message = "✅ 連線成功"
        status.model = SUPPORTED_PROVIDERS["gemini"]["default_model"]
    elif resp.status_code == 400 or resp.status_code == 403:
        status.message = "❌ API 金鑰無效"
    else:
        status.message = f"❌ HTTP {resp.status_code}"

    return status


def _test_anthropic(api_key: str, status: ApiStatus) -> ApiStatus:
    """測試 Anthropic API 連線"""
    import requests

    # NOTE: 用最小 token 的請求測試連線
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        },
        timeout=10,
    )
    if resp.status_code == 200:
        status.is_connected = True
        status.message = "✅ 連線成功"
        status.model = SUPPORTED_PROVIDERS["anthropic"]["default_model"]
    elif resp.status_code == 401:
        status.message = "❌ API 金鑰無效"
    else:
        status.message = f"❌ HTTP {resp.status_code}"

    return status


def _test_tmdb(api_key: str, status: ApiStatus) -> ApiStatus:
    """測試 TMDB API 連線"""
    import requests

    resp = requests.get(
        f"https://api.themoviedb.org/3/configuration?api_key={api_key}",
        timeout=10,
    )
    if resp.status_code == 200:
        status.is_connected = True
        status.message = "✅ 連線成功"
    elif resp.status_code == 401:
        status.message = "❌ API 金鑰無效"
    else:
        status.message = f"❌ HTTP {resp.status_code}"

    return status


def _test_custom(config: Dict, status: ApiStatus) -> ApiStatus:
    """測試自訂 API 連線"""
    import requests

    base_url = config.get("base_url", "")
    if not base_url:
        status.message = "❌ 未設定 Base URL"
        return status

    headers = config.get("headers", {})
    api_key = config.get("api_key")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(base_url, headers=headers, timeout=10)
        if resp.status_code < 400:
            status.is_connected = True
            status.message = f"✅ 連線成功 (HTTP {resp.status_code})"
        else:
            status.message = f"❌ HTTP {resp.status_code}"
    except requests.exceptions.ConnectionError:
        status.message = "❌ 無法連線至指定 URL"

    return status


def list_configured_providers() -> List[str]:
    """列出所有已設定的 API provider"""
    return [p for p in SUPPORTED_PROVIDERS if is_provider_configured(p)]


def get_llm_provider() -> Optional[str]:
    """
    取得可用的 LLM provider。

    NOTE: 優先順序 OpenAI → Gemini → Anthropic。
          若都未設定則回傳 None（使用 fallback 規則引擎）。
    """
    if is_provider_configured("openai"):
        return "openai"
    elif is_provider_configured("gemini"):
        return "gemini"
    elif is_provider_configured("anthropic"):
        return "anthropic"
    return None

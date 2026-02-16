"""
🔌 API 設定 — 外部 API 金鑰管理與連線測試

一站式管理所有外部 API 設定，支援 OpenAI / Gemini / TMDB / 自訂 API。
"""
import streamlit as st

st.header("🔌 外部 API 設定")
st.markdown("管理外部 API 金鑰，啟用 AI 劇本分析與全球市場數據功能。")

from core.api_config import (
    SUPPORTED_PROVIDERS,
    load_api_config,
    save_api_config,
    test_connection,
    list_configured_providers,
)


# ============================================================
# 一、API 金鑰管理
# ============================================================
st.divider()
st.subheader("🔑 API 金鑰管理")

# 載入目前設定
config = load_api_config()

# NOTE: 將設定暫存於 session_state 以支援即時更新
if "api_config_draft" not in st.session_state:
    st.session_state.api_config_draft = config.copy()

draft = st.session_state.api_config_draft

# 分 tab 顯示各 provider
tab_openai, tab_gemini, tab_anthropic, tab_tmdb, tab_custom = st.tabs([
    "🧠 OpenAI", "✨ Gemini", "🤖 Anthropic", "🎬 TMDB", "🔧 自訂 API",
])

with tab_openai:
    st.markdown(f"**{SUPPORTED_PROVIDERS['openai']['description']}**")
    st.caption("預設模型：`gpt-4o-mini`（低成本、高速）")

    openai_key = st.text_input(
        "OpenAI API Key",
        value=draft.get("openai", {}).get("api_key", ""),
        type="password",
        placeholder="sk-...",
        key="openai_key_input",
    )
    if openai_key:
        if "openai" not in draft:
            draft["openai"] = {}
        draft["openai"]["api_key"] = openai_key

with tab_gemini:
    st.markdown(f"**{SUPPORTED_PROVIDERS['gemini']['description']}**")
    st.caption("預設模型：`gemini-2.0-flash`（免費額度高）")

    gemini_key = st.text_input(
        "Gemini API Key",
        value=draft.get("gemini", {}).get("api_key", ""),
        type="password",
        placeholder="AIza...",
        key="gemini_key_input",
    )
    if gemini_key:
        if "gemini" not in draft:
            draft["gemini"] = {}
        draft["gemini"]["api_key"] = gemini_key

with tab_anthropic:
    st.markdown(f"**{SUPPORTED_PROVIDERS['anthropic']['description']}**")
    st.caption("預設模型：`claude-3-5-sonnet`（高品質分析）")

    anthropic_key = st.text_input(
        "Anthropic API Key",
        value=draft.get("anthropic", {}).get("api_key", ""),
        type="password",
        placeholder="sk-ant-...",
        key="anthropic_key_input",
    )
    if anthropic_key:
        if "anthropic" not in draft:
            draft["anthropic"] = {}
        draft["anthropic"]["api_key"] = anthropic_key

with tab_tmdb:
    st.markdown(f"**{SUPPORTED_PROVIDERS['tmdb']['description']}**")
    st.caption("免費申請：[TMDB API](https://www.themoviedb.org/settings/api)")

    tmdb_key = st.text_input(
        "TMDB API Key",
        value=draft.get("tmdb", {}).get("api_key", ""),
        type="password",
        placeholder="TMDB v3 API Key...",
        key="tmdb_key_input",
    )
    if tmdb_key:
        if "tmdb" not in draft:
            draft["tmdb"] = {}
        draft["tmdb"]["api_key"] = tmdb_key

with tab_custom:
    st.markdown(f"**{SUPPORTED_PROVIDERS['custom']['description']}**")

    custom_url = st.text_input(
        "Base URL",
        value=draft.get("custom", {}).get("base_url", ""),
        placeholder="https://your-api.example.com/v1",
        key="custom_url_input",
    )
    custom_key = st.text_input(
        "API Key（選填）",
        value=draft.get("custom", {}).get("api_key", ""),
        type="password",
        placeholder="Bearer token...",
        key="custom_key_input",
    )
    custom_headers_str = st.text_area(
        "額外 Headers（JSON 格式，選填）",
        value=str(draft.get("custom", {}).get("headers", "{}")),
        height=80,
        placeholder='{"X-Custom-Header": "value"}',
        key="custom_headers_input",
    )

    if custom_url:
        if "custom" not in draft:
            draft["custom"] = {}
        draft["custom"]["base_url"] = custom_url
        if custom_key:
            draft["custom"]["api_key"] = custom_key
        if custom_headers_str:
            try:
                import json
                draft["custom"]["headers"] = json.loads(custom_headers_str)
            except (json.JSONDecodeError, ValueError):
                pass

# 儲存按鈕
col_save, col_reset = st.columns(2)
with col_save:
    if st.button("💾 儲存所有設定", type="primary"):
        save_api_config(draft)
        st.success("✅ API 設定已儲存！")
        st.session_state.api_config_draft = draft.copy()

with col_reset:
    if st.button("🗑️ 清除所有設定"):
        save_api_config({})
        st.session_state.api_config_draft = {}
        st.success("✅ 已清除所有 API 設定。")
        st.rerun()


# ============================================================
# 二、連線測試
# ============================================================
st.divider()
st.subheader("✅ 連線測試")

# NOTE: 先儲存 draft 才能測試最新設定
if st.button("🔄 測試所有已設定的 API", type="secondary"):
    # 先自動儲存
    save_api_config(draft)
    st.session_state.api_config_draft = draft.copy()

    providers_to_test = []
    for provider in SUPPORTED_PROVIDERS:
        provider_draft = draft.get(provider, {})
        required = SUPPORTED_PROVIDERS[provider].get("required_fields", [])
        if all(provider_draft.get(f) for f in required):
            providers_to_test.append(provider)

    if not providers_to_test:
        st.warning("⚠️ 尚未設定任何 API 金鑰。")
    else:
        for provider in providers_to_test:
            with st.spinner(f"測試 {SUPPORTED_PROVIDERS[provider]['label']}..."):
                status = test_connection(provider)

            col_name, col_status, col_latency = st.columns([2, 2, 1])
            with col_name:
                st.markdown(f"**{SUPPORTED_PROVIDERS[provider]['label']}**")
            with col_status:
                st.markdown(status.message)
            with col_latency:
                if status.is_connected:
                    st.caption(f"{status.latency_ms:.0f}ms")


# ============================================================
# 三、設定狀態總覽
# ============================================================
st.divider()
st.subheader("📊 設定狀態總覽")

configured = list_configured_providers()

for provider, info in SUPPORTED_PROVIDERS.items():
    is_set = provider in configured
    icon = "✅" if is_set else "⬜"
    st.markdown(f"{icon} **{info['label']}** — {info['description']}")

if not configured:
    st.info("""
ℹ️ **目前未設定任何外部 API。**

系統仍可正常使用所有基礎功能。外部 API 為選用功能，可提供：
- 🧠 LLM 劇本深度分析（需 OpenAI 或 Gemini）
- 🎬 全球電影市場數據（需 TMDB）
""")
else:
    st.success(f"已設定 {len(configured)} 個 API：{', '.join(SUPPORTED_PROVIDERS[p]['label'] for p in configured)}")


# ============================================================
# 四、安全提示
# ============================================================
st.divider()
with st.expander("🔐 安全注意事項"):
    st.markdown("""
- API 金鑰儲存於本機 `.api_config/` 目錄，**不會上傳至 git**
- 目錄已自動生成 `.gitignore` 保護
- 建議定期輪替 API 金鑰
- 金鑰於頁面上以密碼遮罩顯示
- 若需在伺服器部署，建議改用環境變數或 `st.secrets`

**環境變數設定方式（替代方案）：**
```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."
export TMDB_API_KEY="..."
```
    """)

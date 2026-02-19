"""
⚙️ 系統設定 — 專案管理 & API 連線

合併「專案管理」與「API 設定」功能。
"""
import streamlit as st
import pandas as pd

st.header("⚙️ 系統設定")

tab_projects, tab_api = st.tabs(["📂 專案紀錄", "🔌 API 連線"])


# ============================================================
# Tab 1: 專案紀錄（原 專案管理）
# ============================================================
with tab_projects:
    from utils.storage import save_project, load_project, list_projects, delete_project
    from core.simulation import get_decision_status

    # --- 一、儲存當前專案 ---
    st.subheader("💾 儲存當前模擬結果")

    sim = st.session_state.get('simulation_result')
    params = st.session_state.get('params')

    if sim is None:
        st.info("ℹ️ 尚無模擬結果。請先前往「🎬 風險分析」頁面執行模擬。")
    else:
        save_col1, save_col2 = st.columns([2, 1])
        with save_col1:
            notes = st.text_area("備註（選填）", placeholder="輸入此次模擬的備忘事項...", height=80)
        with save_col2:
            st.markdown(f"""
**當前專案：** {sim.get('project_name', 'N/A')}
- 預期淨利：{sim.get('expected_profit', 0):.1f} 百萬
- 虧損機率：{sim.get('prob_loss', 0):.1f}%
- ROI：{sim.get('expected_roi', 0):.1f}%
            """)

        if st.button("💾 儲存專案", type="primary"):
            results_to_save = {
                'expected_profit': sim.get('expected_profit', 0),
                'expected_roi': sim.get('expected_roi', 0),
                'prob_loss': sim.get('prob_loss', 0),
                'p5': sim.get('p5', 0),
                'p95': sim.get('p95', 0),
            }

            status, recommendation = get_decision_status(
                sim.get('prob_loss', 0), sim.get('expected_roi', 0),
            )
            results_to_save['status'] = status
            results_to_save['recommendation'] = recommendation

            filepath = save_project(sim, results_to_save, notes)
            st.success("✅ 專案已儲存！")
            st.rerun()

    # --- 二、歷史紀錄 ---
    st.divider()
    st.subheader("📋 歷史專案紀錄")

    projects = list_projects()

    if not projects:
        st.info("📁 目前沒有已儲存的專案。")
    else:
        st.markdown(f"共有 **{len(projects)}** 個已儲存專案。")

        table_data = []
        for p in projects:
            table_data.append({
                '專案名稱': p['project_name'],
                '類型': p['genre'],
                '預算 (百萬)': f"{p['budget']:.1f}",
                '預期 ROI (%)': f"{p['expected_roi']:.1f}",
                '虧損機率 (%)': f"{p['prob_loss']:.1f}",
                '燈號': p['status'],
                '儲存時間': p['saved_at'][:16].replace('T', ' ') if p['saved_at'] else '',
                '備註': p.get('notes', ''),
            })

        st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)

        # 載入 / 刪除
        st.markdown("#### 操作")
        action_col1, action_col2 = st.columns(2)

        with action_col1:
            project_names = [p['project_name'] for p in projects]
            selected_project = st.selectbox("選擇專案", project_names, key="load_select")
            selected_idx = project_names.index(selected_project) if selected_project else 0

            if st.button("📂 載入此專案參數"):
                project_data = load_project(projects[selected_idx]['filepath'])
                if project_data:
                    loaded_params = project_data['params']
                    st.session_state['params'] = loaded_params
                    st.success(f"✅ 已載入「{loaded_params.get('project_name', '')}」的參數。請重新執行模擬。")
                else:
                    st.error("❌ 載入失敗，檔案可能已損壞。")

        with action_col2:
            delete_name = st.selectbox("選擇專案", project_names, key="delete_select")
            delete_idx = project_names.index(delete_name) if delete_name else 0

            if st.button("🗑️ 刪除此專案", type="secondary"):
                if delete_project(projects[delete_idx]['filepath']):
                    st.success("✅ 已刪除。")
                    st.rerun()
                else:
                    st.error("❌ 刪除失敗。")

    # --- 三、多專案對比 ---
    st.divider()
    st.subheader("📊 多專案對比")

    if len(projects) < 2:
        st.info("ℹ️ 至少需要 2 個已儲存專案才能進行對比分析。")
    else:
        compare_names = st.multiselect(
            "選擇要對比的專案",
            [p['project_name'] for p in projects],
            default=[p['project_name'] for p in projects[:3]],
        )

        if len(compare_names) >= 2:
            compare_projects = [p for p in projects if p['project_name'] in compare_names]

            compare_data = []
            for p in compare_projects:
                compare_data.append({
                    '專案名稱': p['project_name'],
                    '類型': p['genre'],
                    '預算 (百萬)': f"{p['budget']:.1f}",
                    '預期淨利 (百萬)': f"{p['expected_profit']:.1f}",
                    '預期 ROI (%)': f"{p['expected_roi']:.1f}",
                    '虧損機率 (%)': f"{p['prob_loss']:.1f}",
                    '燈號': p['status'],
                })

            st.dataframe(pd.DataFrame(compare_data), hide_index=True, use_container_width=True)

            # 對比圖表
            import matplotlib.pyplot as plt
            from utils.charts import COLORS

            fig, axes = plt.subplots(1, 3, figsize=(15, 5))

            names = [p['project_name'][:8] for p in compare_projects]
            rois = [p['expected_roi'] for p in compare_projects]
            losses = [p['prob_loss'] for p in compare_projects]
            profits = [p['expected_profit'] for p in compare_projects]

            colors = [COLORS['profit'] if r > 0 else COLORS['loss'] for r in rois]
            axes[0].barh(names, rois, color=colors, alpha=0.8, edgecolor='white')
            axes[0].set_xlabel('ROI (%)', fontweight='bold')
            axes[0].set_title('ROI Comparison', fontweight='bold')
            axes[0].axvline(0, color=COLORS['dark'], linewidth=1.5)

            colors = [COLORS['loss'] if l > 40 else COLORS['warning'] if l > 25 else COLORS['profit'] for l in losses]
            axes[1].barh(names, losses, color=colors, alpha=0.8, edgecolor='white')
            axes[1].set_xlabel('Loss Probability (%)', fontweight='bold')
            axes[1].set_title('Risk Comparison', fontweight='bold')

            colors = [COLORS['profit'] if p > 0 else COLORS['loss'] for p in profits]
            axes[2].barh(names, profits, color=colors, alpha=0.8, edgecolor='white')
            axes[2].set_xlabel('Expected Net Profit (M)', fontweight='bold')
            axes[2].set_title('Profit Comparison', fontweight='bold')
            axes[2].axvline(0, color=COLORS['dark'], linewidth=1.5)

            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            best_roi_proj = max(compare_projects, key=lambda p: p['expected_roi'])
            lowest_risk_proj = min(compare_projects, key=lambda p: p['prob_loss'])

            st.info(f"""💡 **對比洞察：**
- 最高 ROI：**{best_roi_proj['project_name']}** ({best_roi_proj['expected_roi']:.1f}%)
- 最低風險：**{lowest_risk_proj['project_name']}** (虧損機率 {lowest_risk_proj['prob_loss']:.1f}%)""")
        else:
            st.warning("請至少選擇 2 個專案進行對比。")


# ============================================================
# Tab 2: API 連線（原 API 設定）
# ============================================================
with tab_api:
    from core.api_config import (
        SUPPORTED_PROVIDERS,
        load_api_config,
        save_api_config,
        test_connection,
        list_configured_providers,
    )

    st.subheader("🔑 API 金鑰管理")
    st.markdown("管理外部 API 金鑰，啟用 AI 劇本分析與全球市場數據功能。")

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
        if st.button("💾 儲存所有設定", type="primary", key="save_api_btn"):
            save_api_config(draft)
            st.success("✅ API 設定已儲存！")
            st.session_state.api_config_draft = draft.copy()

    with col_reset:
        if st.button("🗑️ 清除所有設定", key="reset_api_btn"):
            save_api_config({})
            st.session_state.api_config_draft = {}
            st.success("✅ 已清除所有 API 設定。")
            st.rerun()

    # --- 連線測試 ---
    st.divider()
    st.subheader("✅ 連線測試")

    if st.button("🔄 測試所有已設定的 API", type="secondary"):
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
                    api_status = test_connection(provider)

                col_name, col_status, col_latency = st.columns([2, 2, 1])
                with col_name:
                    st.markdown(f"**{SUPPORTED_PROVIDERS[provider]['label']}**")
                with col_status:
                    st.markdown(api_status.message)
                with col_latency:
                    if api_status.is_connected:
                        st.caption(f"{api_status.latency_ms:.0f}ms")

    # --- 設定狀態總覽 ---
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

    # --- 安全提示 ---
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

"""
🤖 AI 分析頁面

AI 票房預測（含信賴區間）、觀眾輪廓預測、題材熱度分析。
"""
import streamlit as st
import numpy as np
import os

st.header("🤖 AI 智能分析")

# 讀取共用參數
params = st.session_state.get('params')
if not params:
    st.warning("⚠️ 請先在側邊欄設定專案參數。")
    st.stop()


# ============================================================
# 一、AI 票房預測
# ============================================================
st.divider()
st.subheader("🎯 AI 票房預測")

from core.ai_engine import load_ai_model, predict_with_confidence, get_model_info

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "box_office_predictor.pkl")
model_bundle = load_ai_model(MODEL_PATH)

if model_bundle is None:
    st.warning("⚠️ AI 模型尚未訓練。請先執行 `python train_model.py` 產生模型檔案。")
    st.info("""
**訓練步驟：**
1. 開啟終端機
2. 執行 `cd "c:\\Users\\user\\GL model"`
3. 執行 `python train_model.py`
4. 重新載入此頁面
    """)
else:
    # 模型資訊
    model_info = get_model_info(model_bundle)
    with st.expander(f"ℹ️ 模型資訊 (v{model_info['version']})"):
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown(f"**版本：** {model_info['version']}")
            st.markdown(f"**訓練時間：** {model_info.get('trained_at', 'N/A')[:16]}")
            st.markdown(f"**信賴區間：** {'✅ 支援' if model_info['has_confidence'] else '❌ 不支援'}")
        with info_col2:
            metrics = model_info.get('metrics', {})
            if metrics:
                st.markdown(f"**MAE：** {metrics.get('mae', 'N/A'):.2f} 百萬")
                st.markdown(f"**R²：** {metrics.get('r2', 'N/A'):.4f}")
                st.markdown(f"**CV R² (5-fold)：** {metrics.get('cv_r2_mean', 'N/A'):.4f}")

    # 額外參數
    ai_col1, ai_col2, ai_col3 = st.columns(3)
    with ai_col1:
        release_month = st.selectbox(
            "預計上映月份", range(1, 13),
            index=6,  # 預設 7 月
            format_func=lambda x: f"{x} 月",
        )
    with ai_col2:
        is_sequel = st.checkbox("為續集 / 系列作品", value=False)
    with ai_col3:
        ip_score = st.slider("IP 知名度", 1, 5, 1,
                             help="1=原創 2=小眾IP 3=一般知名 4=知名IP 5=頂級IP")

    # 執行預測
    result = predict_with_confidence(
        model_bundle,
        genre=params['genre'],
        budget=params['budget'],
        marketing_pa=params['marketing_pa'],
        cast_level=params.get('cast_level', 3),
        director_score=params.get('director_score', 7),
        release_month=release_month,
        is_sequel=int(is_sequel),
        ip_score=ip_score,
    )

    # 顯示指標
    pred_col1, pred_col2, pred_col3 = st.columns(3)
    pred_col1.metric("AI 預測票房", f"{result['prediction']:.1f} 百萬")
    pred_col2.metric(
        f"下界 (P{(100 - result['confidence_pct']) // 2})",
        f"{result['lower']:.1f} 百萬",
    )
    pred_col3.metric(
        f"上界 (P{100 - (100 - result['confidence_pct']) // 2})",
        f"{result['upper']:.1f} 百萬",
    )

    # 信賴區間圖
    try:
        from utils.plotly_charts import plotly_confidence_interval
        fig_ci = plotly_confidence_interval(
            prediction=result['prediction'],
            lower=result['lower'],
            upper=result['upper'],
            manual_low=params.get('box_office_low', 20),
            manual_high=params.get('box_office_high', 150),
            confidence_pct=result['confidence_pct'],
        )
        st.plotly_chart(fig_ci, use_container_width=True)
    except ImportError:
        st.info("💡 安裝 plotly 可啟用互動圖表：`python -m pip install plotly`")


# ============================================================
# 二、觀眾輪廓分析
# ============================================================
st.divider()
st.subheader("👥 觀眾輪廓預測")

from core.audience import predict_audience_profile, get_audience_radar_data

profile = predict_audience_profile(
    genre=params['genre'],
    budget=params['budget'],
    cast_level=params.get('cast_level', 3),
    is_sequel=is_sequel if model_bundle else False,
)

# 觀眾指標
aud_col1, aud_col2, aud_col3, aud_col4 = st.columns(4)
aud_col1.metric("主要觀眾", profile.primary_segment.label)
aud_col2.metric("年齡層", profile.primary_segment.age_range)
aud_col3.metric("觀影人數指數", f"{profile.total_audience_index:.1f}x")
aud_col4.metric("重看意願", f"{profile.repeat_watch_factor:.1f}x")

# 觀眾分群詳情
audience_detail_col, radar_col = st.columns([1, 1])

with audience_detail_col:
    st.markdown("#### 觀眾分群")
    for seg in profile.segments:
        male_pct = seg.gender_ratio['male'] * 100
        female_pct = seg.gender_ratio['female'] * 100
        st.markdown(
            f"- **{seg.label}** ({seg.age_range}) — "
            f"佔 {seg.share:.0%} | 男 {male_pct:.0f}% 女 {female_pct:.0f}%"
        )

    if profile.family_friendly:
        st.success("✅ 適合家庭觀影（全年齡層）")
    else:
        st.info("🎯 目標觀眾較為明確（特定族群）")

with radar_col:
    # 雷達圖
    radar_data = get_audience_radar_data(profile)
    try:
        from utils.plotly_charts import plotly_radar_chart
        fig_radar = plotly_radar_chart(
            radar_data['categories'],
            radar_data['values'],
            title="Audience Radar",
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    except ImportError:
        st.info("💡 安裝 plotly 可啟用雷達圖：`python -m pip install plotly`")


# ============================================================
# 三、題材熱度分析
# ============================================================
st.divider()
st.subheader("🔥 題材熱度分析")
st.markdown("輸入劇本摘要的關鍵字，分析題材的市場熱度。")

from core.audience import estimate_topic_heat

keyword_input = st.text_input(
    "關鍵字（以空格或逗號分隔）",
    placeholder="例如：台灣 犯罪 復仇 真人真事",
)

if keyword_input:
    # 解析關鍵字
    keywords = [kw.strip() for kw in keyword_input.replace(',', ' ').replace('，', ' ').split() if kw.strip()]

    heat_result = estimate_topic_heat(keywords)

    # 熱度指標
    heat_col1, heat_col2 = st.columns([1, 2])
    with heat_col1:
        score = heat_result['overall_score']
        if score >= 75:
            color = "🔴"
        elif score >= 55:
            color = "🟡"
        else:
            color = "🔵"
        st.metric("綜合熱度", f"{color} {score:.0f}/100")
        st.markdown(heat_result['analysis'])

    with heat_col2:
        # 關鍵字熱度圖
        try:
            from utils.plotly_charts import plotly_topic_heatbar
            fig_heat = plotly_topic_heatbar(heat_result['matched_keywords'])
            if fig_heat:
                st.plotly_chart(fig_heat, use_container_width=True)
        except ImportError:
            pass

        if heat_result.get('unmatched_keywords'):
            st.caption(f"未識別關鍵字：{', '.join(heat_result['unmatched_keywords'])}")
else:
    st.caption("💡 輸入關鍵字後將即時分析題材熱度。可用關鍵字如：台灣、犯罪、復仇、校園、青春、搞笑、真人真事、續集...")


# ============================================================
# 四、LLM 劇本深度分析（外接 API）
# ============================================================
st.divider()
st.subheader("🧠 AI 劇本深度分析")

from core.api_config import get_llm_provider, is_provider_configured

llm_provider = get_llm_provider()

if llm_provider:
    provider_label = "OpenAI GPT" if llm_provider == "openai" else "Google Gemini"
    st.success(f"✅ 已連接 **{provider_label}**，可進行劇本深度分析。")

    synopsis_input = st.text_area(
        "劇本大綱 / 故事摘要",
        placeholder="輸入電影的故事大綱或摘要，AI 將提供深度市場分析...",
        height=150,
        key="llm_synopsis",
    )

    if synopsis_input and st.button("🚀 開始 AI 深度分析", type="primary"):
        from core.llm_analyzer import analyze_script

        with st.spinner(f"🧠 {provider_label} 正在分析劇本..."):
            analysis = analyze_script(
                synopsis=synopsis_input,
                genre=params['genre'],
                budget=params['budget'],
                cast_level=params.get('cast_level', 3),
                is_sequel=is_sequel if model_bundle else False,
            )

        if analysis.source == "llm":
            st.markdown("---")
            # 題材熱度
            llm_col1, llm_col2 = st.columns([1, 2])
            with llm_col1:
                heat_emoji = "🔴" if analysis.topic_heat_score >= 70 else "🟡" if analysis.topic_heat_score >= 40 else "🔵"
                st.metric("題材熱度", f"{heat_emoji} {analysis.topic_heat_score:.0f}/100")
                if analysis.expected_box_office:
                    st.metric("預估票房範圍", analysis.expected_box_office)

            with llm_col2:
                st.markdown(f"**📝 熱度分析：** {analysis.topic_heat_reasoning}")
                st.markdown(f"**🎯 主要觀眾：** {analysis.target_audience_primary} ({analysis.target_audience_age})")
                st.markdown(f"**⚖️ 性別傾向：** {analysis.target_audience_gender}")

            # 類似影片
            if analysis.comparable_films:
                st.markdown(f"**🎬 類似影片：** {', '.join(analysis.comparable_films)}")

            # 差異化
            if analysis.differentiation:
                st.markdown(f"**💎 差異化優勢：** {analysis.differentiation}")

            # 風險因素
            if analysis.risk_factors:
                st.markdown("**⚠️ 風險因素：**")
                for risk in analysis.risk_factors:
                    st.markdown(f"- {risk}")

            # 行銷建議
            if analysis.marketing_suggestions:
                st.markdown("**📣 行銷建議：**")
                for sug in analysis.marketing_suggestions:
                    st.markdown(f"- {sug}")

            # 總評
            if analysis.overall_assessment:
                st.info(f"**💡 總體評估：** {analysis.overall_assessment}")

        else:
            st.warning("⚠️ LLM 分析失敗，已使用規則引擎提供基礎分析。")
            st.markdown(f"**題材熱度：** {analysis.topic_heat_score:.0f}/100")
            st.markdown(f"**分析結果：** {analysis.overall_assessment}")

else:
    st.info("""
🔌 **尚未設定 LLM API**

設定 OpenAI 或 Gemini API 金鑰後，即可使用 AI 進行劇本深度分析，包括：
- 📊 題材熱度與市場定位
- 🎯 目標觀眾精準分析
- 🎬 類似影片比較
- ⚠️ 風險評估
- 📣 行銷策略建議

👉 前往「🔌 API 設定」頁面設定金鑰
    """)


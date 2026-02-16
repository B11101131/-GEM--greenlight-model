"""
📈 儀表板 — 專案決策總覽

一頁式整合各模組關鍵指標，提供快速決策參考。
"""
import streamlit as st
import numpy as np
import os

st.header("📈 專案決策儀表板")
st.markdown("一頁式專案綜合評估總覽，快速掌握關鍵決策資訊。")

# 讀取共用參數
params = st.session_state.get('params')
sim = st.session_state.get('simulation_result')

if not params:
    st.warning("⚠️ 請先在側邊欄設定專案參數。")
    st.stop()

if sim is None:
    st.warning("⚠️ 請先前往「🎬 風險模擬」頁面執行蒙地卡羅模擬，才能生成完整儀表板。")
    st.stop()

net_profit = np.array(sim['net_profit'])
total_cost = sim['budget'] + sim['marketing_pa']
expected_roi = sim['expected_roi']
prob_loss = sim['prob_loss']


# ============================================================
# 一、決策信號燈 + 綜合評分
# ============================================================
st.divider()

from core.simulation import get_decision_status

status, recommendation = get_decision_status(prob_loss, expected_roi)

# NOTE: 綜合評分公式：ROI 權重 40% + (100 - 虧損機率) 權重 40% + 安全邊際 20%
safety_score = max(0, min(100, (100 - prob_loss)))
roi_score = max(0, min(100, expected_roi * 2))
composite_score = roi_score * 0.4 + safety_score * 0.4 + min(100, roi_score * 0.5) * 0.2

signal_col, score_col, rec_col = st.columns([1, 1, 2])

with signal_col:
    st.markdown(f"### {status}")

with score_col:
    if composite_score >= 70:
        score_emoji = "🟢"
    elif composite_score >= 40:
        score_emoji = "🟡"
    else:
        score_emoji = "🔴"
    st.metric("綜合評分", f"{score_emoji} {composite_score:.0f}/100")

with rec_col:
    st.info(recommendation)


# ============================================================
# 二、關鍵指標速覽
# ============================================================
st.divider()
st.subheader("📊 關鍵指標")

from core.risk import calculate_var
from core.financial import calculate_breakeven

var_results = calculate_var(net_profit)
streaming_mid = (sim.get('streaming_low', 0.3) + sim.get('streaming_high', 0.5)) / 2
breakeven = calculate_breakeven(
    budget=sim['budget'],
    marketing_pa=sim['marketing_pa'],
    theatrical_share=sim.get('theatrical_share', 0.5),
    streaming_multiplier=streaming_mid,
    net_profit_array=net_profit,
)

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
kpi_col1.metric(
    "預期投資報酬率",
    f"{expected_roi:.1f}%",
    delta=f"淨利 {sim['expected_profit']:.1f}M",
)
kpi_col2.metric(
    "虧損風險機率",
    f"{prob_loss:.1f}%",
    delta=f"{prob_loss:.1f}%",
    delta_color="inverse",
)
kpi_col3.metric(
    "VaR (95%)",
    f"{var_results[1].var_value:.1f} 百萬",
    delta=f"CVaR: {var_results[1].cvar_value:.1f}M",
    delta_color="inverse" if var_results[1].cvar_value < 0 else "normal",
)
kpi_col4.metric(
    "損益兩平票房",
    f"{breakeven.breakeven_box_office:.1f} 百萬",
    delta=f"達到率 {breakeven.prob_breakeven:.0f}%",
)


# ============================================================
# 三、AI 預測 vs 手動設定
# ============================================================
st.divider()

ai_dash_col, audience_dash_col = st.columns(2)

with ai_dash_col:
    st.subheader("🤖 AI 預測速覽")

    from core.ai_engine import load_ai_model, predict_with_confidence

    MODEL_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "box_office_predictor.pkl",
    )
    model_bundle = load_ai_model(MODEL_PATH)

    if model_bundle:
        result = predict_with_confidence(
            model_bundle,
            genre=params['genre'],
            budget=params['budget'],
            marketing_pa=params['marketing_pa'],
            cast_level=params.get('cast_level', 3),
            director_score=params.get('director_score', 7),
        )

        ai_m1, ai_m2, ai_m3 = st.columns(3)
        ai_m1.metric("AI 預測", f"{result['prediction']:.1f}M")
        ai_m2.metric("手動低估", f"{params.get('box_office_low', 20):.1f}M")
        ai_m3.metric("手動高估", f"{params.get('box_office_high', 150):.1f}M")

        # NOTE: 若 AI 預測與手動設定差異大，顯示提示
        manual_mid = (params.get('box_office_low', 20) + params.get('box_office_high', 150)) / 2
        diff_pct = abs(result['prediction'] - manual_mid) / manual_mid * 100
        if diff_pct > 30:
            st.warning(f"⚠️ AI 預測與手動設定差異 {diff_pct:.0f}%，建議重新檢視參數。")
        else:
            st.success(f"✅ AI 預測與手動設定差異 {diff_pct:.0f}%，在合理範圍內。")
    else:
        st.warning("⚠️ AI 模型未載入。請先執行 `python train_model.py`。")


# ============================================================
# 四、觀眾速覽
# ============================================================
with audience_dash_col:
    st.subheader("👥 觀眾速覽")

    from core.audience import predict_audience_profile

    profile = predict_audience_profile(
        genre=params['genre'],
        budget=params['budget'],
        cast_level=params.get('cast_level', 3),
    )

    aud_m1, aud_m2 = st.columns(2)
    aud_m1.metric("主要觀眾", f"{profile.primary_segment.label}")
    aud_m2.metric("年齡層", f"{profile.primary_segment.age_range}")

    aud_m3, aud_m4 = st.columns(2)
    aud_m3.metric("觀影指數", f"{profile.total_audience_index:.1f}x")
    aud_m4.metric("重看意願", f"{profile.repeat_watch_factor:.1f}x")

    if profile.family_friendly:
        st.success("✅ 適合家庭觀影")
    else:
        st.info("🎯 目標觀眾較明確")


# ============================================================
# 五、檔期建議 Top-3
# ============================================================
st.divider()
st.subheader("📅 最佳檔期 Top-3")

from core.market import recommend_release_months

recommendations = recommend_release_months(params['genre'])

if recommendations:
    rec_cols = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]

    for i, rec in enumerate(recommendations[:3]):
        with rec_cols[i]:
            score_color = "🟢" if rec.score >= 60 else "🟡" if rec.score >= 40 else "🔴"
            st.metric(
                f"{medals[i]} {rec.month_label}",
                f"{score_color} {rec.score:.0f}/100",
            )
            for reason in rec.reasons[:2]:
                st.caption(reason)
else:
    st.info("暫無檔期推薦資料。")


# ============================================================
# 六、風險警告
# ============================================================
if prob_loss > 40:
    st.divider()
    st.error(f"""
🚨 **高風險警告**

虧損機率高達 **{prob_loss:.1f}%**，建議：
- 削減 20% 以上預算（目前 {sim['budget']:.1f}M → 建議 {sim['budget'] * 0.8:.1f}M）
- 尋求保底收入（輔導金、預售、品牌置入）
- 縮小票房預估區間以重新評估
""")
elif prob_loss > 25:
    st.divider()
    st.warning(f"""
⚠️ **中度風險提醒**

虧損機率 **{prob_loss:.1f}%**，建議先取得 30% 以上保底收入再啟動專案。
""")

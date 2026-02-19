"""
📈 決策總覽 — 專案儀表板 & 報告匯出

合併「儀表板」與「報表中心」功能。
一頁式整合各模組關鍵指標與報告下載。
"""
import streamlit as st
import numpy as np
import os
import matplotlib.pyplot as plt
from datetime import datetime

st.header("📈 決策總覽")
st.markdown("一頁式專案綜合評估總覽，快速掌握關鍵決策資訊並匯出報告。")

# 讀取共用參數
params = st.session_state.get('params')
sim = st.session_state.get('simulation_result')

if not params:
    st.warning("⚠️ 請先在側邊欄設定專案參數。")
    st.stop()

if sim is None:
    st.warning("⚠️ 請先前往「🎬 風險分析」頁面執行蒙地卡羅模擬，才能生成完整儀表板。")
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


# ============================================================
# 七、匯出報告（原報表中心功能）
# ============================================================
st.divider()
st.subheader("📥 匯出投資評估報告")

from core.simulation import run_sensitivity_analysis
from utils.charts import plot_profit_distribution, plot_tornado_chart
from utils.pdf_report import generate_pdf_report

# 準備圖表
fig_profit = plot_profit_distribution(
    net_profit, sim['expected_profit'], sim['p5'], sim['p95'],
)

sensitivity_df = st.session_state.get('sensitivity_df')
fig_sensitivity = None
if sensitivity_df is not None:
    fig_sensitivity = plot_tornado_chart(sensitivity_df)

var_text = "\n".join([
    f"• VaR {vr.confidence_level:.0f}%: {vr.var_value:.1f} 百萬 TWD, "
    f"CVaR: {vr.cvar_value:.1f} 百萬 TWD"
    for vr in var_results
])

breakeven_text = (
    f"損益兩平所需票房: {breakeven.breakeven_box_office:.1f} 百萬 TWD, "
    f"達到兩平機率: {breakeven.prob_breakeven:.1f}%, "
    f"安全邊際: {breakeven.safety_margin:.1%}"
)

col_export, col_info = st.columns([1, 2])

with col_export:
    # --- PDF 匯出 ---
    st.markdown("#### 📄 PDF 報告")
    try:
        pdf_bytes, font_warning = generate_pdf_report(
            project_name=sim['project_name'],
            genre=sim['genre'],
            budget=sim['budget'],
            marketing_pa=sim['marketing_pa'],
            expected_profit=sim['expected_profit'],
            expected_roi=sim['expected_roi'],
            prob_loss=sim['prob_loss'],
            p5=sim['p5'],
            p95=sim['p95'],
            status=status,
            recommendation=recommendation,
            fig_profit=fig_profit,
            fig_sensitivity=fig_sensitivity,
            var_text=var_text,
            breakeven_text=breakeven_text,
        )

        st.download_button(
            label="📥 下載 PDF 報告",
            data=pdf_bytes,
            file_name=f"GEM_Report_{sim['project_name']}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            type="primary",
        )

        if font_warning:
            st.warning("⚠️ 系統找不到中文字體，PDF 中的中文字元可能無法正常顯示。")
        else:
            st.success("✅ PDF 報告已準備完成！")

    except ImportError:
        st.warning("⚠️ 請先安裝 reportlab：`pip install reportlab`")
    except Exception as e:
        st.error(f"PDF 產生錯誤：{e}")

    st.markdown("---")

    # --- Excel 匯出 ---
    st.markdown("#### 📊 Excel 報告")
    try:
        from utils.excel_report import generate_excel_report
        from core.financial import generate_cash_flow

        # 產生現金流資料
        expected_box_office = (sim.get('box_office_low', 20) + sim.get('box_office_high', 150)) / 2
        streaming_rev = expected_box_office * streaming_mid
        cash_flow_df = generate_cash_flow(
            sim['budget'], sim['marketing_pa'], expected_box_office, streaming_rev,
        )

        excel_bytes = generate_excel_report(
            sim_result=sim,
            sensitivity_df=sensitivity_df,
            cash_flow_df=cash_flow_df,
            var_results=var_results,
            breakeven_result=breakeven,
            fig_profit=fig_profit,
            fig_tornado=fig_sensitivity,
        )

        st.download_button(
            label="📥 下載 Excel 報告",
            data=excel_bytes,
            file_name=f"GEM_Report_{sim['project_name']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.success("✅ Excel 報告已準備完成！")

    except ImportError:
        st.warning("⚠️ 請先安裝 openpyxl：`pip install openpyxl`")
    except Exception as e:
        st.error(f"Excel 產生錯誤：{e}")

# 清理圖表
plt.close(fig_profit)
if fig_sensitivity is not None:
    plt.close(fig_sensitivity)

with col_info:
    st.markdown("""
**報告內容包含：**
- 📋 專案基本資訊與成本結構
- 📊 風險評估關鍵指標（投資報酬率、虧損機率）
- 🚦 投資決策建議（紅黃綠燈）
- 📈 獲利分佈模擬圖
- 🌪️ 敏感度分析龍捲風圖
- 📉 VaR 風險值摘要
- 📍 損益兩平分析摘要

**Excel 額外包含：**
- 📊 模擬數據統計明細
- 💰 現金流逐月預測數據
- ⚠️ 敏感度分析完整數據
    """)

    st.markdown("---")

    st.markdown("#### 📊 報告摘要預覽")
    preview_data = {
        '項目': ['專案名稱', '總成本', '預期淨利', '投資報酬率', '虧損機率', '決策建議'],
        '數值': [
            sim['project_name'],
            f"{total_cost:.1f} 百萬",
            f"{sim['expected_profit']:.1f} 百萬",
            f"{sim['expected_roi']:.1f}%",
            f"{sim['prob_loss']:.1f}%",
            status,
        ],
    }
    st.dataframe(preview_data, hide_index=True, use_container_width=True)

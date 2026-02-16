"""
📄 報表中心 — PDF / Excel 匯出

自動產生專業投資評估報告（PDF 與 Excel）。
"""
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from core.simulation import run_sensitivity_analysis, get_decision_status
from core.risk import calculate_var
from core.financial import calculate_breakeven
from utils.charts import plot_profit_distribution, plot_tornado_chart
from utils.pdf_report import generate_pdf_report

st.header("📄 報表中心")

# 檢查模擬結果
sim = st.session_state.get('simulation_result')
if sim is None:
    st.warning("⚠️ 請先前往「🎬 風險模擬」頁面執行蒙地卡羅模擬。")
    st.stop()

net_profit = np.array(sim['net_profit'])
total_cost = sim['budget'] + sim['marketing_pa']

status, recommendation = get_decision_status(sim['prob_loss'], sim['expected_roi'])

# 共用計算
fig_profit = plot_profit_distribution(
    net_profit, sim['expected_profit'], sim['p5'], sim['p95'],
)

sensitivity_df = st.session_state.get('sensitivity_df')
fig_sensitivity = None
if sensitivity_df is not None:
    fig_sensitivity = plot_tornado_chart(sensitivity_df)

var_results = calculate_var(net_profit)
var_text = "\n".join([
    f"• VaR {vr.confidence_level:.0f}%: {vr.var_value:.1f} 百萬 TWD, "
    f"CVaR: {vr.cvar_value:.1f} 百萬 TWD"
    for vr in var_results
])

streaming_mid = (sim.get('streaming_low', 0.3) + sim.get('streaming_high', 0.5)) / 2
breakeven = calculate_breakeven(
    sim['budget'], sim['marketing_pa'],
    sim.get('theatrical_share', 0.5), streaming_mid, net_profit,
)
breakeven_text = (
    f"損益兩平所需票房: {breakeven.breakeven_box_office:.1f} 百萬 TWD, "
    f"達到兩平機率: {breakeven.prob_breakeven:.1f}%, "
    f"安全邊際: {breakeven.safety_margin:.1%}"
)


# ============================================================
# 報告匯出
# ============================================================
st.divider()
st.subheader("📥 匯出投資評估報告")

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

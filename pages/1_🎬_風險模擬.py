"""
🎬 風險模擬 — 蒙地卡羅模擬頁面

核心模擬引擎，計算獲利分佈與投資決策建議。
"""
import streamlit as st
import numpy as np

from core.simulation import run_simulation, get_decision_status
from utils.charts import plot_profit_distribution

st.header("🎬 風險模擬 — 蒙地卡羅模擬")
st.markdown("模擬數千次市場情境，計算獲利機率分佈與投資決策建議。")

# 讀取共用參數
params = st.session_state.get('params')
if params is None:
    st.warning("⚠️ 請先回到主頁面設定專案參數。")
    st.stop()

# 初始化
if 'simulation_result' not in st.session_state:
    st.session_state.simulation_result = None

# 執行模擬按鈕
if st.button("🚀 開始風險評估模擬", type="primary"):
    if params['box_office_low'] >= params['box_office_high']:
        st.error("⚠️ 悲觀票房預估必須小於樂觀票房預估，請調整數值後重試。")
        st.stop()

    with st.spinner("正在執行蒙地卡羅模擬..."):
        result = run_simulation(
            box_office_low=params['box_office_low'],
            box_office_high=params['box_office_high'],
            simulation_count=params['simulation_count'],
            budget=params['budget'],
            marketing_pa=params['marketing_pa'],
            streaming_multiplier_low=params['streaming_low'],
            streaming_multiplier_high=params['streaming_high'],
            theatrical_share=params['theatrical_share'],
        )

    st.session_state.simulation_result = {
        'net_profit': result[0].tolist(),
        'roi': result[1].tolist(),
        'expected_profit': result[2],
        'expected_roi': result[3],
        'prob_loss': result[4],
        'p5': result[5],
        'p95': result[6],
        'project_name': params['project_name'],
        'genre': params['genre'],
        'budget': params['budget'],
        'marketing_pa': params['marketing_pa'],
        'box_office_low': params['box_office_low'],
        'box_office_high': params['box_office_high'],
        'simulation_count': params['simulation_count'],
        'theatrical_share': params['theatrical_share'],
        'streaming_low': params['streaming_low'],
        'streaming_high': params['streaming_high'],
    }
    # NOTE: 清除下游快取，確保其他分頁重新計算
    st.session_state.pop('sensitivity_df', None)
    st.success("✅ 模擬完成！")

# --- 結果顯示 ---
sim = st.session_state.simulation_result
if sim is not None:
    net_profit = np.array(sim['net_profit'])
    expected_profit = sim['expected_profit']
    expected_roi = sim['expected_roi']
    prob_loss = sim['prob_loss']
    p5 = sim['p5']
    p95 = sim['p95']

    st.divider()
    st.subheader(f"📊 分析結果：{sim['project_name']}")

    # 指標卡片
    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="預估平均淨利",
        value=f"{expected_profit:.1f} 百萬",
        delta=f"{expected_roi:.1f}% 投資報酬率",
    )
    col2.metric(
        label="虧損風險機率",
        value=f"{prob_loss:.1f}%",
        delta=f"{prob_loss:.1f}%",
        delta_color="inverse",
    )

    status, recommendation = get_decision_status(prob_loss, expected_roi)
    col3.markdown(f"### {status}")

    # 分佈圖與建議
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("獲利/虧損分佈圖")
        import matplotlib.pyplot as plt
        tab_static, tab_interactive = st.tabs(["📊 靜態圖", "✨ 互動圖"])
        with tab_static:
            fig = plot_profit_distribution(net_profit, expected_profit, p5, p95)
            st.pyplot(fig)
            plt.close(fig)
        with tab_interactive:
            try:
                from utils.plotly_charts import plotly_profit_distribution
                fig_plotly = plotly_profit_distribution(net_profit, expected_profit, p5, p95)
                st.plotly_chart(fig_plotly, use_container_width=True)
            except ImportError:
                st.info("💡 安裝 plotly 可啟用互動圖表：`pip install plotly`")


    with col_chart2:
        st.subheader("決策建議與數據解讀")
        st.info(recommendation)
        st.markdown(f"""
**數據洞察：**
* **模擬次數：** {sim['simulation_count']:,} 次
* **院線分潤：** {sim['theatrical_share']:.0%}
* **串流倍數：** {sim['streaming_low']:.0%} ~ {sim['streaming_high']:.0%}
* **P5 下限：** {p5:.1f} 百萬（最糟情況）
* **P95 上限：** {p95:.1f} 百萬（最好情況）

**下一步：**
前往「💰 財務分析」查看損益兩平與現金流，
或前往「⚠️ 風險管理」查看 VaR 風險值。
        """)
else:
    st.info("👈 請在左側設定參數，並點擊上方「🚀 開始風險評估模擬」按鈕。")

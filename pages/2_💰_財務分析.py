"""
💰 財務分析 — 損益兩平 / 現金流 / 投資分攤

完整財務模型與投資結構分析。
"""
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from core.financial import (
    calculate_breakeven,
    generate_cash_flow,
    CashFlowConfig,
    InvestorProfile,
    simulate_investor_returns,
)
from utils.charts import plot_waterfall, plot_cash_flow, plot_investor_pie

st.header("💰 財務分析")

# 檢查模擬結果
sim = st.session_state.get('simulation_result')
params = st.session_state.get('params')

if sim is None:
    st.warning("⚠️ 請先前往「🎬 風險分析」頁面執行蒙地卡羅模擬。")
    st.stop()

net_profit = np.array(sim['net_profit'])
total_cost = sim['budget'] + sim['marketing_pa']
streaming_mid = (sim['streaming_low'] + sim['streaming_high']) / 2

# ============================================================
# 一、損益兩平分析
# ============================================================
st.divider()
st.subheader("📍 損益兩平分析")

breakeven = calculate_breakeven(
    budget=sim['budget'],
    marketing_pa=sim['marketing_pa'],
    theatrical_share=sim['theatrical_share'],
    streaming_multiplier=streaming_mid,
    net_profit_array=net_profit,
)

col_be1, col_be2, col_be3, col_be4 = st.columns(4)
col_be1.metric("損益兩平票房", f"{breakeven.breakeven_box_office:.1f} 百萬")
col_be2.metric("達到兩平機率", f"{breakeven.prob_breakeven:.1f}%")
col_be3.metric("安全邊際", f"{breakeven.safety_margin:.1%}")
col_be4.metric("總成本", f"{total_cost:.1f} 百萬")

# 瀑布圖：損益拆解
st.markdown("#### 損益拆解瀑布圖")
expected_box_office = (sim['box_office_low'] + sim['box_office_high']) / 2
theatrical_rev = expected_box_office * sim['theatrical_share']
streaming_rev = expected_box_office * streaming_mid
waterfall_net = theatrical_rev + streaming_rev - total_cost

waterfall_labels = [
    'Theatrical Revenue',
    'Streaming Revenue',
    'Production Budget',
    'Marketing (P&A)',
    'Net Profit',
]
waterfall_values = [
    theatrical_rev,
    streaming_rev,
    -sim['budget'],
    -sim['marketing_pa'],
    waterfall_net,
]

tab_wf_static, tab_wf_interactive = st.tabs(["📊 靜態圖", "✨ 互動圖"])
with tab_wf_static:
    fig_waterfall = plot_waterfall(waterfall_labels, waterfall_values, "Projected P&L Breakdown")
    st.pyplot(fig_waterfall)
    plt.close(fig_waterfall)
with tab_wf_interactive:
    try:
        from utils.plotly_charts import plotly_waterfall
        fig_wf_plotly = plotly_waterfall(
            budget=sim['budget'], marketing=sim['marketing_pa'],
            box_office_revenue=theatrical_rev, streaming_revenue=streaming_rev,
            net_profit=waterfall_net,
        )
        st.plotly_chart(fig_wf_plotly, use_container_width=True)
    except ImportError:
        st.info("💡 安裝 plotly 可啟用互動圖表：`pip install plotly`")

# 損益兩平比較表
with st.expander("📋 損益兩平詳細數據"):
    be_data = pd.DataFrame([
        {'項目': '製作預算', '金額 (百萬)': f"{sim['budget']:.1f}"},
        {'項目': '行銷宣發費', '金額 (百萬)': f"{sim['marketing_pa']:.1f}"},
        {'項目': '總成本', '金額 (百萬)': f"{total_cost:.1f}"},
        {'項目': '院線分潤比例', '金額 (百萬)': f"{sim['theatrical_share']:.0%}"},
        {'項目': '串流分潤倍數 (中)', '金額 (百萬)': f"{streaming_mid:.0%}"},
        {'項目': '損益兩平所需票房', '金額 (百萬)': f"{breakeven.breakeven_box_office:.1f}"},
        {'項目': '損益兩平總收入', '金額 (百萬)': f"{breakeven.breakeven_revenue:.1f}"},
    ])
    st.dataframe(be_data, hide_index=True, use_container_width=True)

# ============================================================
# 二、現金流預測
# ============================================================
st.divider()
st.subheader("📈 現金流預測")

st.markdown("模擬專案從前製到串流收入的完整現金流時間軸。")

# 可調整的時間參數
with st.expander("⚙️ 調整現金流時間參數"):
    cf_col1, cf_col2, cf_col3 = st.columns(3)
    with cf_col1:
        pre_prod = st.number_input("前製期 (月)", value=3, min_value=1, max_value=12)
        production = st.number_input("拍攝期 (月)", value=3, min_value=1, max_value=12)
    with cf_col2:
        post_prod = st.number_input("後製期 (月)", value=4, min_value=1, max_value=12)
        theatrical_window = st.number_input("院線窗口 (月)", value=3, min_value=1, max_value=6)
    with cf_col3:
        streaming_delay = st.number_input("串流延遲 (月)", value=6, min_value=3, max_value=18)
        streaming_income = st.number_input("串流收入期 (月)", value=6, min_value=3, max_value=12)

config = CashFlowConfig(
    pre_production_months=pre_prod,
    production_months=production,
    post_production_months=post_prod,
    theatrical_window_months=theatrical_window,
    streaming_delay_months=streaming_delay,
    streaming_income_months=streaming_income,
)

# 使用預期值計算現金流
expected_theatrical = expected_box_office * sim['theatrical_share']
expected_streaming = expected_box_office * streaming_mid

cf_df = generate_cash_flow(
    budget=sim['budget'],
    marketing_pa=sim['marketing_pa'],
    expected_box_office=expected_theatrical,
    streaming_revenue=expected_streaming,
    config=config,
)

# 現金流圖表
tab_cf_static, tab_cf_interactive = st.tabs(["📊 靜態圖", "✨ 互動圖"])
with tab_cf_static:
    fig_cf = plot_cash_flow(cf_df)
    st.pyplot(fig_cf)
    plt.close(fig_cf)
with tab_cf_interactive:
    try:
        from utils.plotly_charts import plotly_cash_flow
        fig_cf_plotly = plotly_cash_flow(cf_df)
        st.plotly_chart(fig_cf_plotly, use_container_width=True)
    except ImportError:
        st.info("💡 安裝 plotly 可啟用互動圖表：`pip install plotly`")

# 現金流數據表
with st.expander("📋 查看逐月現金流數據"):
    st.dataframe(cf_df, hide_index=True, use_container_width=True)

# 關鍵現金流指標
cf_col1, cf_col2, cf_col3 = st.columns(3)
min_cumulative = cf_df['累計現金流'].min()
payback_month_rows = cf_df[cf_df['累計現金流'] >= 0]
payback_month = payback_month_rows['月份'].iloc[0] if len(payback_month_rows) > 0 else None

cf_col1.metric("最大資金缺口", f"{min_cumulative:.1f} 百萬")
cf_col2.metric("回本月份", f"第 {payback_month} 月" if payback_month else "未回本")
cf_col3.metric("專案總時長", f"{len(cf_df)} 個月")

# ============================================================
# 三、投資人報酬分攤模擬
# ============================================================
st.divider()
st.subheader("🤝 投資人報酬分攤模擬")

st.markdown("設定多方投資結構，模擬不同淨利情境下各方的回報。")

# 投資方設定
st.markdown("#### 投資方設定")
num_investors = st.number_input("投資方數量", min_value=2, max_value=5, value=2)

investors = []
inv_cols = st.columns(num_investors)

for i in range(num_investors):
    with inv_cols[i]:
        default_names = ["製片方", "主要投資人", "輔導金", "預售收入", "其他投資"]
        name = st.text_input(
            f"投資方 {i + 1} 名稱",
            value=default_names[i] if i < len(default_names) else f"投資方 {i + 1}",
            key=f"inv_name_{i}",
        )

        # NOTE: 預設第一方為製片方（出資佔比較低但分潤較高）
        default_investment = total_cost * (0.3 if i == 0 else 0.7 / max(num_investors - 1, 1))
        investment = st.number_input(
            f"投資金額 (百萬)",
            value=round(default_investment, 1),
            step=1.0, min_value=0.0,
            key=f"inv_amount_{i}",
        )
        priority = st.number_input(
            f"回收優先順序",
            value=i + 1, min_value=1, max_value=5,
            key=f"inv_priority_{i}",
        )
        profit_share = st.number_input(
            f"淨利分紅 (%)",
            value=50.0 if i == 0 else 50.0 / max(num_investors - 1, 1),
            step=5.0, min_value=0.0, max_value=100.0,
            key=f"inv_share_{i}",
        )

        investors.append(InvestorProfile(
            name=name,
            investment=investment,
            recoup_priority=priority,
            profit_share_pct=profit_share,
        ))

# 驗證分潤總和
total_share = sum(inv.profit_share_pct for inv in investors)
if abs(total_share - 100.0) > 0.1:
    st.warning(f"⚠️ 各方分潤比例加總為 {total_share:.1f}%，建議調整為 100%。")

# 執行分攤模擬
if st.button("📊 計算投資報酬分配"):
    summary = simulate_investor_returns(net_profit, investors)

    st.markdown("#### 各方投資報酬分析")

    # 指標卡片
    inv_metric_cols = st.columns(len(investors))
    for i, inv in enumerate(investors):
        with inv_metric_cols[i]:
            s = summary[inv.name]
            st.metric(
                label=inv.name,
                value=f"投資報酬率 {s['avg_roi']:.1f}%",
                delta=f"回本率 {s['prob_recoup']:.0f}%",
            )
            st.caption(
                f"投資: {s['investment']:.1f}M → "
                f"淨報酬: {s['avg_net_return']:.1f}M"
            )

    # 投資結構圓餅圖
    col_pie, col_table = st.columns([1, 1])
    with col_pie:
        fig_pie = plot_investor_pie(summary)
        st.pyplot(fig_pie)
        plt.close(fig_pie)

    with col_table:
        st.markdown("#### 報酬比較表")
        table_data = []
        for inv in investors:
            s = summary[inv.name]
            table_data.append({
                '投資方': inv.name,
                '投資金額 (百萬)': f"{s['investment']:.1f}",
                '平均淨報酬 (百萬)': f"{s['avg_net_return']:.1f}",
                '投資報酬率 (%)': f"{s['avg_roi']:.1f}",
                '回本機率 (%)': f"{s['prob_recoup']:.1f}",
                'P5 報酬 (百萬)': f"{s['p5_return']:.1f}",
                'P95 報酬 (百萬)': f"{s['p95_return']:.1f}",
            })
        st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)

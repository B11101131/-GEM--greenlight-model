"""
⚠️ 風險管理 — VaR / 敏感度 / 情境比較

進階風險量化與多情境壓力測試。
"""
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from core.simulation import run_simulation, run_sensitivity_analysis
from core.risk import calculate_var, calculate_risk_metrics
from utils.charts import (
    plot_tornado_chart, plot_var_chart, plot_scenario_overlay,
)

st.header("⚠️ 風險管理")

# 檢查模擬結果
sim = st.session_state.get('simulation_result')
if sim is None:
    st.warning("⚠️ 請先前往「🎬 風險模擬」頁面執行蒙地卡羅模擬。")
    st.stop()

net_profit = np.array(sim['net_profit'])
total_cost = sim['budget'] + sim['marketing_pa']

# ============================================================
# 一、VaR 風險值計算
# ============================================================
st.divider()
st.subheader("📉 風險值 (VaR) 分析")

st.markdown("""
VaR 衡量在特定信心水準下的最大可能損失。CVaR（條件風險值）
進一步衡量超過 VaR 閾值時的平均損失程度，是更保守的風險指標。
""")

# 計算 VaR
var_results = calculate_var(net_profit)

# 指標卡片
var_cols = st.columns(3)
for i, vr in enumerate(var_results):
    with var_cols[i]:
        st.metric(
            label=f"VaR ({vr.confidence_level:.0f}%)",
            value=f"{vr.var_value:.1f} 百萬",
            delta=f"CVaR: {vr.cvar_value:.1f} 百萬",
            delta_color="inverse" if vr.cvar_value < 0 else "normal",
        )
        st.caption(vr.interpretation)

# VaR 分佈圖
fig_var = plot_var_chart(net_profit, var_results)
st.pyplot(fig_var)
plt.close(fig_var)

# 完整風險指標
risk_metrics = calculate_risk_metrics(net_profit, total_cost)

with st.expander("📋 完整風險指標報告"):
    rm_col1, rm_col2 = st.columns(2)
    with rm_col1:
        st.markdown("**收益指標**")
        st.write(f"- 預期淨利：{risk_metrics['expected_profit']:.1f} 百萬")
        st.write(f"- 預期投資報酬率：{risk_metrics['expected_roi']:.1f}%")
        st.write(f"- 最大獲利：{risk_metrics['max_profit']:.1f} 百萬")
        st.write(f"- 翻倍機率：{risk_metrics['prob_double']:.1f}%")
        st.write(f"- 中位數淨利：{risk_metrics['median']:.1f} 百萬")

    with rm_col2:
        st.markdown("**風險指標**")
        st.write(f"- 虧損機率：{risk_metrics['prob_loss']:.1f}%")
        st.write(f"- 最大損失：{risk_metrics['max_loss']:.1f} 百萬")
        st.write(f"- 最大回撤：{risk_metrics['max_drawdown_pct']:.1f}%")
        st.write(f"- 索提諾比率 (Sortino Ratio)：{risk_metrics['sortino_ratio']:.2f}")
        st.write(f"- 偏態：{risk_metrics['skewness']:.3f}")
        st.write(f"- 峰態：{risk_metrics['kurtosis']:.3f}")

    st.markdown("**分位數分佈**")
    percentile_data = pd.DataFrame([{
        'P5': f"{risk_metrics['p5']:.1f} 百萬",
        'P25': f"{risk_metrics['p25']:.1f} 百萬",
        '中位數': f"{risk_metrics['median']:.1f} 百萬",
        'P75': f"{risk_metrics['p75']:.1f} 百萬",
        'P95': f"{risk_metrics['p95']:.1f} 百萬",
    }])
    st.dataframe(percentile_data, hide_index=True, use_container_width=True)


# ============================================================
# 二、敏感度分析
# ============================================================
st.divider()
st.subheader("📈 敏感度分析")
st.markdown("顯示各參數變動 ±20% 對淨利的影響程度，幫助識別關鍵風險因子。")

# 快取敏感度計算
if 'sensitivity_df' not in st.session_state or st.session_state.get('sensitivity_df') is None:
    with st.spinner("正在計算敏感度..."):
        base_params = {
            'box_office_low': sim['box_office_low'],
            'box_office_high': sim['box_office_high'],
            'budget': sim['budget'],
            'marketing_pa': sim['marketing_pa'],
            'streaming_low': sim.get('streaming_low', 0.3),
            'streaming_high': sim.get('streaming_high', 0.5),
            'simulation_count': sim['simulation_count'],
            'theatrical_share': sim.get('theatrical_share', 0.5),
        }
        st.session_state.sensitivity_df = run_sensitivity_analysis(base_params)

sensitivity_df = st.session_state.sensitivity_df

# 龍捲風圖
tab_tn_static, tab_tn_interactive = st.tabs(["📊 靜態圖", "✨ 互動圖"])
with tab_tn_static:
    fig_tornado = plot_tornado_chart(sensitivity_df)
    st.pyplot(fig_tornado)
    plt.close(fig_tornado)
with tab_tn_interactive:
    try:
        from utils.plotly_charts import plotly_tornado_chart
        fig_tn_plotly = plotly_tornado_chart(sensitivity_df)
        st.plotly_chart(fig_tn_plotly, use_container_width=True)
    except ImportError:
        st.info("💡 安裝 plotly 可啟用互動圖表：`pip install plotly`")

# 關鍵洞察
most_sensitive = sensitivity_df.iloc[-1]['Parameter']
st.info(f"💡 **關鍵洞察：** 「{most_sensitive}」對專案獲利影響最大，建議優先管控此風險因子。")

# 敏感度數據表
with st.expander("📋 查看敏感度分析數據"):
    display_df = sensitivity_df[['Parameter', 'Low Impact', 'High Impact', 'Impact Range']].copy()
    display_df = display_df.rename(columns={'Parameter': '參數', 'Low Impact': '低值影響', 'High Impact': '高值影響', 'Impact Range': '影響範圍'})
    display_df = display_df.sort_values('影響範圍', ascending=False)
    display_df['低值影響'] = display_df['低值影響'].apply(lambda x: f"{x:+.2f} 百萬")
    display_df['高值影響'] = display_df['高值影響'].apply(lambda x: f"{x:+.2f} 百萬")
    display_df['影響範圍'] = display_df['影響範圍'].apply(lambda x: f"{x:.2f} 百萬")
    st.dataframe(display_df, hide_index=True, use_container_width=True)


# ============================================================
# 三、多情境比較分析
# ============================================================
st.divider()
st.subheader("🔄 多情境比較分析")
st.markdown("比較不同預算 / 行銷策略組合的風險與報酬。")

# 初始化情境列表
if 'scenarios' not in st.session_state:
    st.session_state.scenarios = []

col_scenario1, col_scenario2 = st.columns([1, 1])

with col_scenario1:
    st.markdown("#### 新增比較情境")
    scenario_name = st.text_input(
        "情境名稱",
        f"情境 {len(st.session_state.scenarios) + 1}",
    )

    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        sc_budget = st.number_input(
            "製作預算 (百萬)", value=sim['budget'], key="sc_budget",
        )
        sc_box_low = st.number_input(
            "悲觀票房 (百萬)", value=sim['box_office_low'], key="sc_box_low",
        )
    with sc_col2:
        sc_marketing = st.number_input(
            "行銷費 (百萬)", value=sim['marketing_pa'], key="sc_marketing",
        )
        sc_box_high = st.number_input(
            "樂觀票房 (百萬)", value=sim['box_office_high'], key="sc_box_high",
        )

    if st.button("➕ 加入比較", type="secondary"):
        if sc_box_low >= sc_box_high:
            st.error("⚠️ 悲觀票房預估必須小於樂觀票房預估。")
            st.stop()

        sc_result = run_simulation(
            sc_box_low, sc_box_high, sim['simulation_count'],
            sc_budget, sc_marketing,
            sim.get('streaming_low', 0.3),
            sim.get('streaming_high', 0.5),
            sim.get('theatrical_share', 0.5),
        )

        new_scenario = {
            'name': scenario_name,
            'budget': sc_budget,
            'marketing': sc_marketing,
            'box_low': sc_box_low,
            'box_high': sc_box_high,
            'expected_profit': sc_result[2],
            'expected_roi': sc_result[3],
            'prob_loss': sc_result[4],
            'net_profit_array': sc_result[0].tolist(),
        }
        st.session_state.scenarios.append(new_scenario)
        st.rerun()

with col_scenario2:
    st.markdown("#### 情境比較表")

    current_scenario = {
        'name': f"📌 {sim['project_name']} (基準)",
        'budget': sim['budget'],
        'marketing': sim['marketing_pa'],
        'expected_profit': sim['expected_profit'],
        'expected_roi': sim['expected_roi'],
        'prob_loss': sim['prob_loss'],
        'net_profit_array': sim['net_profit'],
    }

    all_scenarios = [current_scenario] + st.session_state.scenarios

    comparison_data = []
    for sc in all_scenarios:
        comparison_data.append({
            '情境': sc['name'],
            '總成本 (百萬)': f"{sc['budget'] + sc['marketing']:.1f}",
            '預估淨利 (百萬)': f"{sc['expected_profit']:.1f}",
            '投資報酬率 (%)': f"{sc['expected_roi']:.1f}",
            '虧損機率 (%)': f"{sc['prob_loss']:.1f}",
        })

    st.dataframe(
        pd.DataFrame(comparison_data),
        hide_index=True, use_container_width=True,
    )

    if st.button("🗑️ 清除所有情境"):
        st.session_state.scenarios = []
        st.rerun()

# 情境分佈疊加圖
if len(st.session_state.scenarios) > 0:
    st.markdown("#### 情境分佈比較圖")

    fig_compare = plot_scenario_overlay(
        net_profit,
        sim['project_name'],
        st.session_state.scenarios,
    )

    if fig_compare is not None:
        st.pyplot(fig_compare)
        plt.close(fig_compare)
    else:
        st.warning("⚠️ 請安裝 scipy 以啟用分佈比較圖：`pip install scipy`")

    # 情境比較洞察
    all_with_metrics = [
        {'name': sim['project_name'], 'roi': sim['expected_roi'], 'prob_loss': sim['prob_loss']},
    ]
    all_with_metrics += [
        {'name': sc['name'], 'roi': sc['expected_roi'], 'prob_loss': sc['prob_loss']}
        for sc in st.session_state.scenarios
    ]

    best_roi = max(all_with_metrics, key=lambda x: x['roi'])
    lowest_risk = min(all_with_metrics, key=lambda x: x['prob_loss'])

    st.info(f"""💡 **情境比較洞察：**
- 最高投資報酬率情境：**{best_roi['name']}** ({best_roi['roi']:.1f}%)
- 最低風險情境：**{lowest_risk['name']}** (虧損機率 {lowest_risk['prob_loss']:.1f}%)""")

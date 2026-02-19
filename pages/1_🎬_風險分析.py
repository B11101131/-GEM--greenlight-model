"""
🎬 風險分析 — 蒙地卡羅模擬 & 進階風險管理

合併「風險模擬」與「風險管理」功能，提供完整的風險評估流程。
"""
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from core.simulation import run_simulation, run_sensitivity_analysis, get_decision_status
from core.risk import calculate_var, calculate_risk_metrics
from utils.charts import (
    plot_profit_distribution, plot_tornado_chart,
    plot_var_chart, plot_scenario_overlay,
)

st.header("🎬 風險分析")
st.markdown("模擬數千次市場情境，計算獲利機率分佈、VaR 風險值與投資決策建議。")

# 讀取共用參數
params = st.session_state.get('params')
if params is None:
    st.warning("⚠️ 請先回到主頁面設定專案參數。")
    st.stop()

# 初始化
if 'simulation_result' not in st.session_state:
    st.session_state.simulation_result = None

# ============================================================
# 模擬執行按鈕（置於 tabs 外，確保所有標籤共享結果）
# ============================================================
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
    # NOTE: 清除下游快取，確保敏感度分析重新計算
    st.session_state.pop('sensitivity_df', None)
    st.success("✅ 模擬完成！")

# --- 結果顯示 ---
sim = st.session_state.simulation_result
if sim is None:
    st.info("👈 請在左側設定參數，並點擊上方「🚀 開始風險評估模擬」按鈕。")
    st.stop()

net_profit = np.array(sim['net_profit'])
total_cost = sim['budget'] + sim['marketing_pa']
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


# ============================================================
# 四個標籤頁
# ============================================================
tab_sim, tab_var, tab_sensitivity, tab_scenario = st.tabs([
    "📊 模擬結果", "📉 VaR / CVaR", "🌪️ 敏感度分析", "🔄 情境壓力測試",
])


# --- Tab 1: 模擬結果 ---
with tab_sim:
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("獲利/虧損分佈圖")
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
        """)


# --- Tab 2: VaR / CVaR ---
with tab_var:
    st.subheader("📉 風險值 (VaR) 分析")
    st.markdown("""
VaR 衡量在特定信心水準下的最大可能損失。CVaR（條件風險值）
進一步衡量超過 VaR 閾值時的平均損失程度，是更保守的風險指標。
""")

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


# --- Tab 3: 敏感度分析 ---
with tab_sensitivity:
    st.subheader("🌪️ 敏感度分析")
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
        display_df = display_df.rename(columns={
            'Parameter': '參數', 'Low Impact': '低值影響',
            'High Impact': '高值影響', 'Impact Range': '影響範圍',
        })
        display_df = display_df.sort_values('影響範圍', ascending=False)
        display_df['低值影響'] = display_df['低值影響'].apply(lambda x: f"{x:+.2f} 百萬")
        display_df['高值影響'] = display_df['高值影響'].apply(lambda x: f"{x:+.2f} 百萬")
        display_df['影響範圍'] = display_df['影響範圍'].apply(lambda x: f"{x:.2f} 百萬")
        st.dataframe(display_df, hide_index=True, use_container_width=True)


# --- Tab 4: 情境壓力測試 ---
with tab_scenario:
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

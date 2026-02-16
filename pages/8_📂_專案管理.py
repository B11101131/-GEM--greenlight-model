"""
📂 專案管理 — 儲存 / 載入 / 多專案對比

管理模擬歷史紀錄，支援多專案比較分析。
"""
import streamlit as st
import pandas as pd

from utils.storage import save_project, load_project, list_projects, delete_project
from core.simulation import get_decision_status

st.header("📂 專案管理")


# ============================================================
# 一、儲存當前專案
# ============================================================
st.divider()
st.subheader("💾 儲存當前模擬結果")

sim = st.session_state.get('simulation_result')
params = st.session_state.get('params')

if sim is None:
    st.info("ℹ️ 尚無模擬結果。請先前往「🎬 風險模擬」頁面執行模擬。")
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
        # 合併 params 和 results 供儲存
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
        st.success(f"✅ 專案已儲存！")
        st.rerun()


# ============================================================
# 二、歷史紀錄
# ============================================================
st.divider()
st.subheader("📋 歷史專案紀錄")

projects = list_projects()

if not projects:
    st.info("📁 目前沒有已儲存的專案。")
else:
    st.markdown(f"共有 **{len(projects)}** 個已儲存專案。")

    # 專案列表表格
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


# ============================================================
# 三、多專案對比
# ============================================================
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
        # 篩選選中的專案
        compare_projects = [p for p in projects if p['project_name'] in compare_names]

        # 對比表格
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

        # ROI 柱狀圖
        colors = [COLORS['profit'] if r > 0 else COLORS['loss'] for r in rois]
        axes[0].barh(names, rois, color=colors, alpha=0.8, edgecolor='white')
        axes[0].set_xlabel('ROI (%)', fontweight='bold')
        axes[0].set_title('ROI Comparison', fontweight='bold')
        axes[0].axvline(0, color=COLORS['dark'], linewidth=1.5)

        # 虧損機率柱狀圖
        colors = [COLORS['loss'] if l > 40 else COLORS['warning'] if l > 25 else COLORS['profit'] for l in losses]
        axes[1].barh(names, losses, color=colors, alpha=0.8, edgecolor='white')
        axes[1].set_xlabel('Loss Probability (%)', fontweight='bold')
        axes[1].set_title('Risk Comparison', fontweight='bold')

        # 預期淨利柱狀圖
        colors = [COLORS['profit'] if p > 0 else COLORS['loss'] for p in profits]
        axes[2].barh(names, profits, color=colors, alpha=0.8, edgecolor='white')
        axes[2].set_xlabel('Expected Net Profit (M)', fontweight='bold')
        axes[2].set_title('Profit Comparison', fontweight='bold')
        axes[2].axvline(0, color=COLORS['dark'], linewidth=1.5)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        # 洞察
        best_roi_proj = max(compare_projects, key=lambda p: p['expected_roi'])
        lowest_risk_proj = min(compare_projects, key=lambda p: p['prob_loss'])

        st.info(f"""💡 **對比洞察：**
- 最高 ROI：**{best_roi_proj['project_name']}** ({best_roi_proj['expected_roi']:.1f}%)
- 最低風險：**{lowest_risk_proj['project_name']}** (虧損機率 {lowest_risk_proj['prob_loss']:.1f}%)""")
    else:
        st.warning("請至少選擇 2 個專案進行對比。")

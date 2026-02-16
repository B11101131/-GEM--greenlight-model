"""
📊 市場分析頁面

歷史票房參考、競爭片分析、檔期選擇建議。
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from core.market import (
    load_historical_data,
    filter_comparables,
    get_genre_statistics,
    get_all_genre_statistics,
    load_release_calendar,
    analyze_competition,
    recommend_release_months,
    get_monthly_genre_performance,
)
from utils.charts import plot_genre_box_plot, plot_monthly_heatmap, plot_competition_bar

st.header("📊 市場分析")

# 讀取共用參數
sim = st.session_state.get('params')
if not sim:
    st.warning("⚠️ 請先在側邊欄設定專案參數。")
    st.stop()

current_genre = sim.get('genre', '動作')
current_budget = sim.get('budget', 50.0)


# ============================================================
# 一、歷史票房參考
# ============================================================
st.divider()
st.subheader("📚 歷史票房參考")
st.markdown("參考同類型 / 同規模國片的票房表現，評估專案定位。")

# 篩選控制
filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    filter_genre = st.selectbox(
        "篩選類型", ["全部", "動作", "愛情", "恐怖", "職人劇", "喜劇"],
        index=["全部", "動作", "愛情", "恐怖", "職人劇", "喜劇"].index(current_genre)
        if current_genre in ["動作", "愛情", "恐怖", "職人劇", "喜劇"] else 0,
    )
with filter_col2:
    budget_range = st.slider("預算範圍 (百萬 TWD)", 0.0, 100.0, (0.0, 100.0), step=5.0)
with filter_col3:
    year_range = st.slider("年份範圍", 2020, 2026, (2022, 2024))

# 載入與篩選資料
comparable_df = filter_comparables(
    genre=filter_genre if filter_genre != "全部" else None,
    budget_min=budget_range[0] if budget_range[0] > 0 else None,
    budget_max=budget_range[1] if budget_range[1] < 100 else None,
    year_min=year_range[0],
    year_max=year_range[1],
)

if not comparable_df.empty:
    # 統計摘要
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    stat_col1.metric("篩選結果", f"{len(comparable_df)} 部")
    stat_col2.metric("平均票房", f"{comparable_df['box_office'].mean():.1f} 百萬")
    stat_col3.metric("中位數票房", f"{comparable_df['box_office'].median():.1f} 百萬")
    stat_col4.metric("平均 ROI", f"{comparable_df['roi'].mean():.1f}%")

    # 箱形圖
    full_df = load_historical_data()
    if not full_df.empty and len(full_df['genre'].unique()) > 1:
        tab_box_static, tab_box_interactive = st.tabs(["📊 靜態圖", "✨ 互動圖"])
        with tab_box_static:
            fig_box = plot_genre_box_plot(full_df)
            st.pyplot(fig_box)
            plt.close(fig_box)
        with tab_box_interactive:
            try:
                from utils.plotly_charts import plotly_genre_comparison
                fig_box_plotly = plotly_genre_comparison(full_df)
                st.plotly_chart(fig_box_plotly, use_container_width=True)
            except ImportError:
                st.info("💡 安裝 plotly 可啟用互動圖表：`pip install plotly`")

    # 資料表格
    with st.expander("📋 查看詳細資料"):
        display_cols = ['title', 'year', 'genre', 'budget', 'marketing',
                        'box_office', 'streaming_revenue', 'roi']
        display_df = comparable_df[display_cols].copy()
        display_df = display_df.rename(columns={
            'title': '片名', 'year': '年份', 'genre': '類型',
            'budget': '預算 (百萬)', 'marketing': '行銷 (百萬)',
            'box_office': '票房 (百萬)', 'streaming_revenue': '串流收入 (百萬)',
            'roi': 'ROI (%)',
        })
        st.dataframe(display_df, hide_index=True, use_container_width=True)

    # 類型統計
    all_stats = get_all_genre_statistics()
    if all_stats:
        with st.expander("📊 各類型票房統計"):
            stats_data = []
            for genre_name, gs in all_stats.items():
                stats_data.append({
                    '類型': genre_name,
                    '作品數': gs.count,
                    '平均票房 (百萬)': f"{gs.mean_box_office:.1f}",
                    '中位數 (百萬)': f"{gs.median_box_office:.1f}",
                    'P25 (百萬)': f"{gs.p25_box_office:.1f}",
                    'P75 (百萬)': f"{gs.p75_box_office:.1f}",
                    '平均預算 (百萬)': f"{gs.mean_budget:.1f}",
                    '平均 ROI (%)': f"{gs.mean_roi:.1f}",
                })
            st.dataframe(pd.DataFrame(stats_data), hide_index=True, use_container_width=True)
else:
    st.info("目前篩選條件無符合資料，請調整篩選條件。")


# ============================================================
# 二、競爭片分析
# ============================================================
st.divider()
st.subheader("🎯 競爭片分析")
st.markdown("選擇預計上映月份，分析同檔期競爭強度與風險。")

release_month = st.slider("預計上映月份", 1, 12, 7)

competition = analyze_competition(release_month, current_genre)

comp_col1, comp_col2, comp_col3, comp_col4 = st.columns(4)
comp_col1.metric("檔期", competition.month_label)
comp_col2.metric(
    "競爭強度",
    f"{competition.competition_level}/5",
    delta="激烈" if competition.competition_level >= 4 else "適中",
    delta_color="inverse" if competition.competition_level >= 4 else "normal",
)
comp_col3.metric("假期效應", f"{competition.holiday_factor:.1f}x")
comp_col4.metric(
    "風險評級",
    competition.risk_assessment,
    delta="類型適合" if competition.genre_fit else "類型不符",
    delta_color="normal" if competition.genre_fit else "inverse",
)

# 競爭強度總覽圖
calendar_df = load_release_calendar()
if not calendar_df.empty:
    tab_comp_static, tab_comp_interactive = st.tabs(["📊 靜態圖", "✨ 互動圖"])
    with tab_comp_static:
        fig_comp = plot_competition_bar(calendar_df)
        st.pyplot(fig_comp)
        plt.close(fig_comp)
    with tab_comp_interactive:
        try:
            from utils.plotly_charts import plotly_competition_calendar
            fig_comp_plotly = plotly_competition_calendar(calendar_df)
            st.plotly_chart(fig_comp_plotly, use_container_width=True)
        except ImportError:
            st.info("💡 安裝 plotly 可啟用互動圖表：`pip install plotly`")

# 競爭分析詳情
if competition.genre_fit:
    st.success(f"✅ {release_month} 月為「{current_genre}」類型的旺季檔期，票房指數 {competition.avg_box_office_index:.1f}x。")
else:
    st.warning(f"⚠️ {release_month} 月非「{current_genre}」類型的理想檔期。建議參考下方檔期推薦。")


# ============================================================
# 三、檔期選擇建議
# ============================================================
st.divider()
st.subheader("📅 檔期選擇建議")
st.markdown(f"根據「**{current_genre}**」類型的歷史表現與市場環境，推薦最佳上映月份。")

# 熱力圖
pivot_df = get_monthly_genre_performance()
if not pivot_df.empty:
    fig_heatmap = plot_monthly_heatmap(pivot_df)
    st.pyplot(fig_heatmap)
    plt.close(fig_heatmap)

# 推薦排名
recommendations = recommend_release_months(current_genre)
if recommendations:
    st.markdown("#### 🏆 推薦月份排名")

    for i, rec in enumerate(recommendations[:6], 1):
        # NOTE: 前 3 名用金銀銅標記
        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"**#{i}**"
        score_color = "🟢" if rec.score >= 60 else "🟡" if rec.score >= 40 else "🔴"

        with st.expander(f"{medal} {rec.month_label} — 綜合評分 {score_color} {rec.score:.0f}/100"):
            for reason in rec.reasons:
                st.write(f"  {reason}")


# ============================================================
# 四、TMDB 全球市場數據（外接 API）
# ============================================================
st.divider()
st.subheader("🌐 全球市場數據 (TMDB)")

from core.api_config import is_provider_configured, get_api_key

if is_provider_configured("tmdb"):
    from core.tmdb_client import search_similar_movies, get_trending

    tmdb_key = get_api_key("tmdb")
    st.success("✅ 已連接 TMDB 電影資料庫")

    tmdb_tab_similar, tmdb_tab_trending = st.tabs(["🔍 同類型電影", "🔥 全球趨勢"])

    with tmdb_tab_similar:
        st.markdown(f"搜尋全球 **{current_genre}** 類型的近期熱門電影。")

        tmdb_col1, tmdb_col2 = st.columns(2)
        with tmdb_col1:
            year_from = st.number_input("起始年份", 2015, 2026, 2022, key="tmdb_year_from")
        with tmdb_col2:
            year_to = st.number_input("結束年份", 2015, 2026, 2025, key="tmdb_year_to")

        if st.button("🔍 搜尋 TMDB", key="tmdb_search"):
            with st.spinner("搜尋 TMDB 中..."):
                result = search_similar_movies(
                    genre=current_genre,
                    api_key=tmdb_key,
                    year_from=int(year_from),
                    year_to=int(year_to),
                )

            if result.movies:
                st.markdown(f"找到 **{result.total_results}** 筆結果，顯示前 10 筆：")
                import pandas as pd

                tmdb_df = pd.DataFrame([{
                    "片名": m.title,
                    "原始片名": m.original_title,
                    "上映日": m.release_date,
                    "評分": f"⭐ {m.vote_average:.1f}",
                    "人氣": f"{m.popularity:.0f}",
                    "投票數": m.vote_count,
                } for m in result.movies])

                st.dataframe(tmdb_df, hide_index=True, use_container_width=True)
            else:
                st.info("未找到符合條件的電影。")

    with tmdb_tab_trending:
        st.markdown("全球本週最熱門的電影。")
        if st.button("📈 取得全球趨勢", key="tmdb_trending"):
            with st.spinner("取得趨勢中..."):
                trending = get_trending(tmdb_key, "week")

            if trending.movies:
                for i, movie in enumerate(trending.movies[:5], 1):
                    st.markdown(
                        f"**{i}. {movie.title}** ({movie.original_title}) — "
                        f"⭐ {movie.vote_average:.1f} | 人氣 {movie.popularity:.0f}"
                    )
                    if movie.overview:
                        st.caption(movie.overview)
            else:
                st.info("無法取得趨勢資料。")
else:
    st.info("""
🔌 **尚未設定 TMDB API**

設定 TMDB API 金鑰後，即可查詢全球電影市場數據：
- 🔍 搜尋同類型熱門電影
- 📊 票房與評分比較
- 🔥 全球趨勢追蹤

TMDB API 完全免費，前往 [TMDB](https://www.themoviedb.org/settings/api) 申請。
👉 設定金鑰：前往「🔌 API 設定」頁面
    """)


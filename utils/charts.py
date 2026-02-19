"""
共用圖表繪製模組

統一管理所有 matplotlib 圖表的樣式與繪製邏輯，確保視覺一致性。
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.figure import Figure
from typing import List, Optional, Dict, Tuple

# NOTE: 自動偵測系統可用中文字型，優先使用繁體中文字型
_CJK_FONT_CANDIDATES = [
    'Microsoft JhengHei',   # Windows 繁體
    'Noto Sans TC',         # Google 繁體
    'Microsoft YaHei',      # Windows 簡體（備選）
    'SimHei',               # Windows 簡體（備選）
    'PingFang TC',          # macOS 繁體
    'Heiti TC',             # macOS 繁體
]

_available_fonts = {f.name for f in fm.fontManager.ttflist}
_cjk_font = None
for _candidate in _CJK_FONT_CANDIDATES:
    if _candidate in _available_fonts:
        _cjk_font = _candidate
        break

if _cjk_font:
    plt.rcParams['font.sans-serif'] = [_cjk_font] + plt.rcParams.get('font.sans-serif', [])
    plt.rcParams['axes.unicode_minus'] = False


# NOTE: 統一色票，確保全站視覺一致
COLORS = {
    'profit': '#27AE60',
    'loss': '#E74C3C',
    'primary': '#2980B9',
    'secondary': '#8E44AD',
    'warning': '#F39C12',
    'info': '#3498DB',
    'dark': '#2C3E50',
    'bg': '#f8f9fa',
    'white': '#ffffff',
}

SCENARIO_COLORS = ['#E74C3C', '#27AE60', '#9B59B6', '#F39C12', '#1ABC9C',
                   '#E67E22', '#2ECC71', '#3498DB', '#E91E63', '#00BCD4']


def _setup_figure(
    figsize: Tuple[float, float] = (10, 6),
) -> Tuple[Figure, plt.Axes]:
    """建立統一風格的 Figure + Axes"""
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(COLORS['bg'])
    ax.set_facecolor(COLORS['white'])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.3, linestyle='--')
    return fig, ax


def plot_profit_distribution(
    net_profit: np.ndarray,
    expected_profit: float,
    p5: float,
    p95: float,
) -> Figure:
    """
    繪製獲利/虧損分佈直方圖。

    Args:
        net_profit: 淨利陣列
        expected_profit: 預期平均淨利
        p5: 第 5 百分位
        p95: 第 95 百分位
    """
    fig, ax = _setup_figure(figsize=(10, 6))

    losses = net_profit[net_profit < 0]
    profits = net_profit[net_profit >= 0]

    auto_edges = np.histogram_bin_edges(net_profit, bins="auto")
    bin_edges = np.linspace(auto_edges[0], auto_edges[-1], 50)

    ax.hist(losses, bins=bin_edges, color=COLORS['loss'], alpha=0.85,
            edgecolor="white", linewidth=0.5, label="虧損區")
    ax.hist(profits, bins=bin_edges, color=COLORS['profit'], alpha=0.85,
            edgecolor="white", linewidth=0.5, label="獲利區")

    ax.axvline(0, color='#C0392B', linestyle="-", linewidth=2.5,
               label="損益兩平", zorder=5)
    ax.axvline(expected_profit, color=COLORS['primary'], linestyle="--",
               linewidth=2.5, label=f"預期值: {expected_profit:.1f}M", zorder=5)
    ax.axvline(p5, color=COLORS['secondary'], linestyle=":", linewidth=2,
               alpha=0.7, label=f"P5: {p5:.1f}M")
    ax.axvline(p95, color=COLORS['secondary'], linestyle=":", linewidth=2,
               alpha=0.7, label=f"P95: {p95:.1f}M")
    ax.axvspan(p5, p95, alpha=0.1, color=COLORS['info'],
               label='90% 信賴區間')

    ax.set_xlabel("淨利（百萬 TWD）", fontsize=12, fontweight='bold')
    ax.set_ylabel("次數", fontsize=12, fontweight='bold')
    ax.set_title("蒙地卡羅模擬 — 獲利分佈圖",
                 fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='upper right', framealpha=0.95, fancybox=True,
              shadow=True, fontsize=9)

    plt.tight_layout()
    return fig


def plot_tornado_chart(
    sensitivity_df: pd.DataFrame,
) -> Figure:
    """
    繪製龍捲風圖（敏感度分析）。

    Args:
        sensitivity_df: 包含 Parameter, Low Impact, High Impact 欄位的 DataFrame
    """
    fig, ax = _setup_figure(figsize=(11, 7))

    y_pos = np.arange(len(sensitivity_df))
    bar_height = 0.4

    ax.barh(y_pos, sensitivity_df['Low Impact'], height=bar_height,
            color=COLORS['loss'], alpha=0.9, edgecolor='white', linewidth=1,
            label='參數 -20%')
    ax.barh(y_pos, sensitivity_df['High Impact'], height=bar_height,
            color=COLORS['profit'], alpha=0.9, edgecolor='white', linewidth=1,
            label='參數 +20%')

    for i, (low, high) in enumerate(
        zip(sensitivity_df['Low Impact'], sensitivity_df['High Impact'])
    ):
        if low < 0:
            ax.text(low - 0.5, i, f'{low:.1f}', va='center', ha='right',
                    fontsize=9, fontweight='bold', color='#C0392B')
        if high > 0:
            ax.text(high + 0.5, i, f'+{high:.1f}', va='center', ha='left',
                    fontsize=9, fontweight='bold', color='#1E8449')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(sensitivity_df['Parameter'], fontsize=11, fontweight='medium')
    ax.axvline(0, color=COLORS['dark'], linestyle='-', linewidth=2, zorder=5)

    ax.set_xlabel('淨利影響幅度（百萬 TWD）', fontsize=12, fontweight='bold')
    ax.set_title('龍捲風圖 — 關鍵風險因子',
                 fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='lower right', framealpha=0.95, fancybox=True,
              shadow=True, fontsize=10)

    ax.spines['left'].set_linewidth(1.5)
    ax.spines['bottom'].set_linewidth(1.5)

    plt.tight_layout()
    return fig


def plot_cash_flow(
    df: pd.DataFrame,
) -> Figure:
    """
    繪製現金流預測圖：柱狀圖（淨月流量）+ 折線圖（累計）。

    Args:
        df: 現金流 DataFrame，需包含月份、淨現金流、累計現金流欄位
    """
    fig, ax1 = _setup_figure(figsize=(12, 6))

    months = df['月份']
    net_flow = df['淨現金流']
    cumulative = df['累計現金流']

    # 柱狀圖：淨現金流
    bar_colors = [
        COLORS['profit'] if v >= 0 else COLORS['loss'] for v in net_flow
    ]
    ax1.bar(months, net_flow, color=bar_colors, alpha=0.7,
            edgecolor='white', linewidth=0.5, label='月淨現金流', zorder=2)

    # 折線圖：累計現金流
    ax2 = ax1.twinx()
    ax2.plot(months, cumulative, color=COLORS['primary'], linewidth=2.5,
             marker='o', markersize=4, label='累計現金流', zorder=3)
    ax2.axhline(0, color=COLORS['dark'], linestyle='--', linewidth=1, alpha=0.5)
    ax2.spines['top'].set_visible(False)
    ax2.set_ylabel('累計現金流（百萬 TWD）', fontsize=11, fontweight='bold')

    # 標記階段分界
    phases = df['階段'].values
    prev_phase = phases[0]
    for i, phase in enumerate(phases):
        if phase != prev_phase:
            ax1.axvline(months.iloc[i] - 0.5, color='gray',
                        linestyle=':', alpha=0.4, linewidth=1)
            prev_phase = phase

    ax1.set_xlabel('月份', fontsize=12, fontweight='bold')
    ax1.set_ylabel('月淨現金流（百萬 TWD）', fontsize=12, fontweight='bold')
    ax1.set_title('現金流預測時間軸', fontsize=14, fontweight='bold', pad=15)

    # 合併圖例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='upper left', framealpha=0.95, fancybox=True, fontsize=9)

    plt.tight_layout()
    return fig


def plot_waterfall(
    labels: List[str],
    values: List[float],
    title: str = "P&L Waterfall",
) -> Figure:
    """
    繪製瀑布圖（損益拆解）。

    NOTE: 用於展示從成本到收入到淨利的逐項拆解。

    Args:
        labels: 各項目名稱
        values: 各項目金額（負數為支出）
        title: 圖表標題
    """
    fig, ax = _setup_figure(figsize=(10, 6))

    n = len(values)
    cumulative = np.zeros(n + 1)
    for i, v in enumerate(values):
        cumulative[i + 1] = cumulative[i] + v

    for i in range(n):
        bottom = min(cumulative[i], cumulative[i + 1])
        height = abs(values[i])
        color = COLORS['profit'] if values[i] >= 0 else COLORS['loss']
        ax.bar(labels[i], height, bottom=bottom, color=color,
               edgecolor='white', linewidth=1, alpha=0.85)

        # 數值標籤
        label_y = cumulative[i + 1]
        ax.text(i, label_y + (height * 0.05 if values[i] >= 0 else -height * 0.15),
                f'{values[i]:+.1f}M', ha='center', va='bottom' if values[i] >= 0 else 'top',
                fontsize=10, fontweight='bold')

        # 連接線
        if i < n - 1:
            ax.plot([i + 0.4, i + 0.6], [cumulative[i + 1], cumulative[i + 1]],
                    color='gray', linewidth=1, alpha=0.5)

    ax.axhline(0, color=COLORS['dark'], linewidth=1.5)
    ax.set_ylabel('金額（百萬 TWD）', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()

    return fig


def plot_var_chart(
    net_profit: np.ndarray,
    var_results: list,
) -> Figure:
    """
    繪製 VaR 分佈標注圖。

    Args:
        net_profit: 淨利陣列
        var_results: VaRResult 物件列表
    """
    fig, ax = _setup_figure(figsize=(10, 6))

    ax.hist(net_profit, bins=50, color=COLORS['info'], alpha=0.6,
            edgecolor='white', linewidth=0.5, label='獲利分佈')

    var_colors = ['#F39C12', '#E74C3C', '#8E44AD']
    for i, vr in enumerate(var_results):
        color = var_colors[i % len(var_colors)]
        ax.axvline(vr.var_value, color=color, linestyle='--', linewidth=2,
                   label=f'VaR {vr.confidence_level:.0f}%: {vr.var_value:.1f}M')

        # 標示尾端區域
        tail = net_profit[net_profit <= vr.var_value]
        if len(tail) > 0:
            ax.hist(tail, bins=30, color=color, alpha=0.3, edgecolor='none')

    ax.axvline(0, color=COLORS['dark'], linestyle='-', linewidth=2,
               label='損益兩平', zorder=5)

    ax.set_xlabel('淨利（百萬 TWD）', fontsize=12, fontweight='bold')
    ax.set_ylabel('次數', fontsize=12, fontweight='bold')
    ax.set_title('風險值 (VaR) 分佈圖', fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='upper right', framealpha=0.95, fancybox=True,
              shadow=True, fontsize=9)
    plt.tight_layout()

    return fig


def plot_investor_pie(
    investor_summary: Dict,
) -> Figure:
    """
    繪製投資人報酬佔比圓餅圖。

    Args:
        investor_summary: simulate_investor_returns 的回傳結果
    """
    fig, ax = _setup_figure(figsize=(8, 8))

    names = list(investor_summary.keys())
    investments = [investor_summary[n]['investment'] for n in names]

    colors = SCENARIO_COLORS[:len(names)]
    wedges, texts, autotexts = ax.pie(
        investments, labels=names, colors=colors,
        autopct='%1.1f%%', startangle=90, pctdistance=0.85,
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
    )

    for text in autotexts:
        text.set_fontsize(11)
        text.set_fontweight('bold')

    ax.set_title('投資結構', fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    return fig


def plot_scenario_overlay(
    base_profit: np.ndarray,
    base_name: str,
    scenarios: List[Dict],
) -> Optional[Figure]:
    """
    繪製多情境分佈疊加比較圖。

    Args:
        base_profit: 基準情境淨利陣列
        base_name: 基準情境名稱
        scenarios: 情境列表，每項需有 name 和 net_profit_array

    Returns:
        Figure 物件，若 scipy 不可用則返回 None
    """
    try:
        from scipy.stats import gaussian_kde
    except ImportError:
        return None

    fig, ax = _setup_figure(figsize=(12, 6))

    sc_arrays = [np.array(sc['net_profit_array']) for sc in scenarios]
    all_profits = [base_profit] + sc_arrays
    global_min = min(arr.min() for arr in all_profits)
    global_max = max(arr.max() for arr in all_profits)
    x_range = np.linspace(global_min, global_max, 300)

    # 基準情境
    kde_base = gaussian_kde(base_profit, bw_method=0.3)
    ax.fill_between(x_range, kde_base(x_range), alpha=0.35,
                    color=COLORS['info'], linewidth=0)
    ax.plot(x_range, kde_base(x_range), color=COLORS['primary'],
            linewidth=2.5, label=f"{base_name}（基準）")
    ax.axvline(float(np.mean(base_profit)), color=COLORS['primary'],
               linestyle='--', linewidth=1.5, alpha=0.7)

    # 其他情境
    for i, sc in enumerate(scenarios):
        color = SCENARIO_COLORS[i % len(SCENARIO_COLORS)]
        kde_sc = gaussian_kde(sc_arrays[i], bw_method=0.3)
        ax.fill_between(x_range, kde_sc(x_range), alpha=0.25,
                        color=color, linewidth=0)
        ax.plot(x_range, kde_sc(x_range), color=color,
                linewidth=2.5, label=sc['name'])
        ax.axvline(sc['expected_profit'], color=color,
                   linestyle='--', linewidth=1.5, alpha=0.7)

    ax.axvline(0, color='#C0392B', linestyle='-', linewidth=2.5,
               label='損益兩平', zorder=5)

    ax.set_xlabel('淨利（百萬 TWD）', fontsize=12, fontweight='bold')
    ax.set_ylabel('機率密度', fontsize=12, fontweight='bold')
    ax.set_title('情境比較 — 獲利分佈疊加圖',
                 fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='upper right', framealpha=0.95, fancybox=True,
              shadow=True, fontsize=10)
    plt.tight_layout()

    return fig


def plot_genre_box_plot(df: pd.DataFrame) -> Figure:
    """
    繪製各類型票房箱形圖。

    NOTE: 使用 DataFrame 的 genre 和 box_office 欄位。
          每個類型用不同顏色區分。
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    genres = sorted(df['genre'].unique())
    genre_data = [df[df['genre'] == g]['box_office'].values for g in genres]

    box_colors = [COLORS['primary'], COLORS['profit'], COLORS['warning'],
                  COLORS['secondary'], COLORS['info']]

    bp = ax.boxplot(
        genre_data, labels=genres, patch_artist=True,
        medianprops={'color': COLORS['dark'], 'linewidth': 2},
        whiskerprops={'linewidth': 1.5},
        capprops={'linewidth': 1.5},
        flierprops={'marker': 'o', 'markersize': 5, 'alpha': 0.5},
    )

    for patch, color in zip(bp['boxes'], box_colors[:len(genres)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_ylabel('票房（百萬 TWD）', fontsize=12, fontweight='bold')
    ax.set_title('各類型票房分佈', fontsize=14, fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()

    return fig


def plot_monthly_heatmap(pivot_df: pd.DataFrame) -> Figure:
    """
    繪製月份 × 類型票房表現熱力圖。

    NOTE: 使用 seaborn 風格但僅用 matplotlib imshow，
          避免額外依賴。
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    genres = list(pivot_df.columns)
    months = list(pivot_df.index)
    data = pivot_df.values

    im = ax.imshow(data.T, cmap='YlOrRd', aspect='auto', interpolation='nearest')

    ax.set_xticks(range(len(months)))
    ax.set_xticklabels([f"{m}月" for m in months], fontsize=10)
    ax.set_yticks(range(len(genres)))
    ax.set_yticklabels(genres, fontsize=10)

    # 在每格中顯示數值
    for i in range(len(genres)):
        for j in range(len(months)):
            val = data[j, i]
            if val > 0:
                text_color = 'white' if val > data.max() * 0.6 else COLORS['dark']
                ax.text(j, i, f'{val:.0f}', ha='center', va='center',
                        fontsize=9, fontweight='bold', color=text_color)

    ax.set_xlabel('上映月份', fontsize=12, fontweight='bold')
    ax.set_title('月份 × 類型 平均票房（百萬 TWD）',
                 fontsize=14, fontweight='bold', pad=15)

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('平均票房（百萬）', fontsize=10)
    plt.tight_layout()

    return fig


def plot_competition_bar(calendar_df: pd.DataFrame) -> Figure:
    """
    繪製各月份競爭強度柱狀圖。

    NOTE: 結合 competition_level 和 holiday_factor 兩項指標，
          以柱狀圖 + 折線圖雙軸呈現。
    """
    fig, ax1 = plt.subplots(figsize=(10, 5))

    months = calendar_df['month'].values
    competition = calendar_df['competition_level'].values
    holiday = calendar_df['holiday_factor'].values

    # 競爭強度柱狀圖
    bar_colors = []
    for c in competition:
        if c >= 4:
            bar_colors.append(COLORS['loss'])
        elif c >= 3:
            bar_colors.append(COLORS['warning'])
        else:
            bar_colors.append(COLORS['profit'])

    ax1.bar(months, competition, color=bar_colors, alpha=0.7, edgecolor='white',
            linewidth=0.5, label='競爭強度', zorder=2)
    ax1.set_xlabel('月份', fontsize=12, fontweight='bold')
    ax1.set_ylabel('競爭強度（1-5）', fontsize=12, fontweight='bold')
    ax1.set_xticks(months)
    ax1.set_xticklabels([f"{m}月" for m in months])
    ax1.set_ylim(0, 6)

    # 假期效應折線圖
    ax2 = ax1.twinx()
    ax2.plot(months, holiday, color=COLORS['primary'], linewidth=2.5,
             marker='o', markersize=6, label='假期效應', zorder=3)
    ax2.set_ylabel('假期效應係數', fontsize=12, fontweight='bold')
    ax2.set_ylim(0.5, 2.0)
    ax2.spines['top'].set_visible(False)

    ax1.set_title('各月份競爭強度與假期效應',
                  fontsize=14, fontweight='bold', pad=15)

    # 合併圖例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='upper left', framealpha=0.95, fancybox=True)

    ax1.grid(axis='y', alpha=0.3, zorder=0)
    plt.tight_layout()

    return fig

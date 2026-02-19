"""
Plotly 互動圖表模組

提供進階互動式視覺化，與現有 matplotlib 圖表並存。
用於 AI 分析頁面等需要互動功能的場景。
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional


def plotly_profit_distribution(
    net_profit: np.ndarray,
    expected_profit: float,
    p5: float,
    p95: float,
) -> object:
    """
    互動式獲利分佈直方圖。

    NOTE: 使用 plotly.graph_objects 以獲得更精細的控制。
          hover 顯示機率和累積機率。
    """
    import plotly.graph_objects as go

    fig = go.Figure()

    # 區分獲利 / 虧損
    profit_vals = net_profit[net_profit >= 0]
    loss_vals = net_profit[net_profit < 0]

    fig.add_trace(go.Histogram(
        x=profit_vals, name='Profit', marker_color='#27AE60',
        opacity=0.75, nbinsx=40,
    ))
    fig.add_trace(go.Histogram(
        x=loss_vals, name='Loss', marker_color='#E74C3C',
        opacity=0.75, nbinsx=20,
    ))

    # 標記線
    fig.add_vline(x=expected_profit, line_dash="dash", line_color="#2980B9",
                  annotation_text=f"Expected: {expected_profit:.1f}M")
    fig.add_vline(x=p5, line_dash="dot", line_color="#8E44AD",
                  annotation_text=f"P5: {p5:.1f}M")
    fig.add_vline(x=p95, line_dash="dot", line_color="#F39C12",
                  annotation_text=f"P95: {p95:.1f}M")

    fig.update_layout(
        title='Profit Distribution (Interactive)',
        xaxis_title='Net Profit (TWD, Millions)',
        yaxis_title='Frequency',
        barmode='overlay',
        template='plotly_white',
        height=450,
        showlegend=True,
        legend=dict(x=0.85, y=0.95),
    )

    return fig


def plotly_radar_chart(categories: List[str], values: List[float], title: str = "Audience Profile") -> object:
    """
    觀眾輪廓雷達圖。

    NOTE: 各維度分數以 0-100 表示。
    """
    import plotly.graph_objects as go

    # 閉合雷達圖
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(41, 128, 185, 0.3)',
        line=dict(color='#2980B9', width=2),
        name='Score',
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        title=title,
        template='plotly_white',
        height=400,
        showlegend=False,
    )

    return fig


def plotly_confidence_interval(
    prediction: float,
    lower: float,
    upper: float,
    manual_low: float,
    manual_high: float,
    confidence_pct: int = 80,
) -> object:
    """
    AI 預測信賴區間圖，對比手動設定。

    NOTE: 用 bar + error bar 方式呈現 AI 與手動設定的差異。
    """
    import plotly.graph_objects as go

    fig = go.Figure()

    # AI 預測
    fig.add_trace(go.Bar(
        x=['AI Prediction'],
        y=[prediction],
        error_y=dict(
            type='data',
            symmetric=False,
            array=[upper - prediction],
            arrayminus=[prediction - lower],
            color='#2980B9',
            thickness=2,
            width=10,
        ),
        marker_color='#2980B9',
        name=f'AI ({confidence_pct}% CI)',
        width=0.3,
    ))

    # 手動設定
    manual_mid = (manual_low + manual_high) / 2
    fig.add_trace(go.Bar(
        x=['Manual Estimate'],
        y=[manual_mid],
        error_y=dict(
            type='data',
            symmetric=False,
            array=[manual_high - manual_mid],
            arrayminus=[manual_mid - manual_low],
            color='#E67E22',
            thickness=2,
            width=10,
        ),
        marker_color='#E67E22',
        name='Manual Range',
        width=0.3,
    ))

    fig.update_layout(
        title='AI Prediction vs Manual Estimate',
        yaxis_title='Box Office (TWD, Millions)',
        template='plotly_white',
        height=400,
        showlegend=True,
        legend=dict(x=0.65, y=0.95),
    )

    return fig


def plotly_waterfall(
    budget: float,
    marketing: float,
    box_office_revenue: float,
    streaming_revenue: float,
    net_profit: float,
) -> object:
    """
    互動式瀑布圖（成本 → 收入 → 淨利）。
    """
    import plotly.graph_objects as go

    fig = go.Figure(go.Waterfall(
        name="Waterfall",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["Budget", "Marketing", "Box Office", "Streaming", "Net Profit"],
        y=[-budget, -marketing, box_office_revenue, streaming_revenue, 0],
        connector={"line": {"color": "#2C3E50", "width": 1}},
        decreasing={"marker": {"color": "#E74C3C"}},
        increasing={"marker": {"color": "#27AE60"}},
        totals={"marker": {"color": "#2980B9" if net_profit >= 0 else "#E74C3C"}},
        text=[
            f"-{budget:.1f}M", f"-{marketing:.1f}M",
            f"+{box_office_revenue:.1f}M", f"+{streaming_revenue:.1f}M",
            f"{net_profit:.1f}M",
        ],
        textposition="outside",
    ))

    fig.update_layout(
        title="Financial Waterfall (Interactive)",
        yaxis_title="TWD (Millions)",
        template="plotly_white",
        height=450,
        showlegend=False,
    )

    return fig


def plotly_topic_heatbar(matched_keywords: List[Dict]) -> object:
    """
    題材關鍵字熱度柱狀圖。

    NOTE: 每個匹配的關鍵字顯示其熱度貢獻。
    """
    import plotly.graph_objects as go

    if not matched_keywords:
        return None

    keywords = [kw['keyword'] for kw in matched_keywords]
    heats = [kw['heat'] for kw in matched_keywords]
    colors = ['#E74C3C' if h >= 1.2 else '#F39C12' if h >= 1.0 else '#3498DB' for h in heats]

    fig = go.Figure(go.Bar(
        x=keywords,
        y=heats,
        marker_color=colors,
        text=[f"{h:.1f}" for h in heats],
        textposition='outside',
    ))

    fig.update_layout(
        title='Keyword Topic Heat',
        xaxis_title='Keywords',
        yaxis_title='Heat Score',
        yaxis=dict(range=[0, max(heats) * 1.3]),
        template='plotly_white',
        height=350,
    )

    return fig


def plotly_tornado_chart(sensitivity_df: pd.DataFrame) -> object:
    """
    互動式龍捲風圖（敏感度分析）。

    NOTE: hover 顯示參數名稱與具體影響值，
          顏色區分正面/負面影響方向。
    """
    import plotly.graph_objects as go

    df = sensitivity_df.sort_values('Impact Range', ascending=True)

    fig = go.Figure()

    # 負面影響（參數下降時）
    fig.add_trace(go.Bar(
        y=df['Parameter'],
        x=df['Low Impact'],
        orientation='h',
        name='參數 -20%',
        marker_color='#E74C3C',
        opacity=0.85,
        text=[f"{v:+.1f}M" for v in df['Low Impact']],
        textposition='outside',
        hovertemplate='%{y}<br>影響: %{x:+.1f} 百萬<extra>參數 -20%</extra>',
    ))

    # 正面影響（參數上升時）
    fig.add_trace(go.Bar(
        y=df['Parameter'],
        x=df['High Impact'],
        orientation='h',
        name='參數 +20%',
        marker_color='#27AE60',
        opacity=0.85,
        text=[f"{v:+.1f}M" for v in df['High Impact']],
        textposition='outside',
        hovertemplate='%{y}<br>影響: %{x:+.1f} 百萬<extra>參數 +20%</extra>',
    ))

    # 零線
    fig.add_vline(x=0, line_color='#2C3E50', line_width=1.5)

    fig.update_layout(
        title='Sensitivity Analysis — Tornado Chart (Interactive)',
        xaxis_title='Impact on Net Profit (TWD, Millions)',
        template='plotly_white',
        height=400,
        barmode='overlay',
        legend=dict(x=0.7, y=1.05, orientation='h'),
        margin=dict(l=150),
    )

    return fig


def plotly_cash_flow(df: pd.DataFrame) -> object:
    """
    互動式現金流圖（柱狀 + 折線雙軸）。

    NOTE: 柱狀圖顯示每月淨現金流（正=綠、負=紅），
          折線圖顯示累計現金流，hover 顯示詳細數值。
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 每月淨現金流柱狀圖
    colors = ['#27AE60' if v >= 0 else '#E74C3C' for v in df['淨現金流']]
    fig.add_trace(
        go.Bar(
            x=df['月份'],
            y=df['淨現金流'],
            name='淨現金流',
            marker_color=colors,
            opacity=0.7,
            hovertemplate='月份 %{x}<br>淨現金流: %{y:.1f} 百萬<extra></extra>',
        ),
        secondary_y=False,
    )

    # 累計現金流折線圖
    fig.add_trace(
        go.Scatter(
            x=df['月份'],
            y=df['累計現金流'],
            name='累計現金流',
            line=dict(color='#2980B9', width=3),
            mode='lines+markers',
            marker=dict(size=6),
            hovertemplate='月份 %{x}<br>累計: %{y:.1f} 百萬<extra></extra>',
        ),
        secondary_y=True,
    )

    # 零線
    fig.add_hline(y=0, line_dash="dash", line_color="#7F8C8D",
                  line_width=1, secondary_y=True)

    fig.update_layout(
        title='Cash Flow Projection (Interactive)',
        template='plotly_white',
        height=450,
        legend=dict(x=0.01, y=0.99),
        hovermode='x unified',
    )
    fig.update_xaxes(title_text='月份')
    fig.update_yaxes(title_text='淨現金流 (百萬 TWD)', secondary_y=False)
    fig.update_yaxes(title_text='累計現金流 (百萬 TWD)', secondary_y=True)

    return fig


def plotly_competition_calendar(calendar_df: pd.DataFrame) -> object:
    """
    互動式檔期競爭日曆圖。

    NOTE: 結合 competition_level（柱狀）和 holiday_factor（折線）
          以雙軸呈現，hover 顯示適合類型與備註。
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 競爭強度柱狀圖——以顏色深淺表示強度
    level_colors = []
    for level in calendar_df['competition_level']:
        if level >= 5:
            level_colors.append('#E74C3C')
        elif level >= 4:
            level_colors.append('#E67E22')
        elif level >= 3:
            level_colors.append('#F39C12')
        else:
            level_colors.append('#27AE60')

    # NOTE: hover 同時顯示適合類型與備註
    hover_texts = []
    for _, row in calendar_df.iterrows():
        hover_texts.append(
            f"<b>{row['label']}</b><br>"
            f"競爭強度: {row['competition_level']}/5<br>"
            f"假期因子: {row['holiday_factor']:.1f}x<br>"
            f"適合類型: {row['best_genres']}<br>"
            f"說明: {row['notes']}"
        )

    fig.add_trace(
        go.Bar(
            x=calendar_df['label'],
            y=calendar_df['competition_level'],
            name='競爭強度',
            marker_color=level_colors,
            opacity=0.8,
            hovertext=hover_texts,
            hoverinfo='text',
        ),
        secondary_y=False,
    )

    # 假期因子折線圖
    fig.add_trace(
        go.Scatter(
            x=calendar_df['label'],
            y=calendar_df['holiday_factor'],
            name='假期加成',
            line=dict(color='#8E44AD', width=3),
            mode='lines+markers',
            marker=dict(size=8, symbol='diamond'),
        ),
        secondary_y=True,
    )

    # 票房指數折線
    fig.add_trace(
        go.Scatter(
            x=calendar_df['label'],
            y=calendar_df['avg_box_office_index'],
            name='票房指數',
            line=dict(color='#2980B9', width=2, dash='dot'),
            mode='lines+markers',
            marker=dict(size=6),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title='Release Calendar — Competition & Holiday Factor (Interactive)',
        template='plotly_white',
        height=450,
        legend=dict(x=0.01, y=1.12, orientation='h'),
        hovermode='x',
    )
    fig.update_yaxes(title_text='競爭強度 (1-5)', range=[0, 6], secondary_y=False)
    fig.update_yaxes(title_text='倍數', range=[0, 2.0], secondary_y=True)

    return fig


def plotly_genre_comparison(df: pd.DataFrame) -> object:
    """
    互動式各類型票房比較圖（箱形圖 + 散佈圖疊加）。

    NOTE: 箱形圖顯示各類型票房分佈，散佈圖疊加個別作品。
          hover 在散佈圖上顯示片名。
    """
    import plotly.graph_objects as go

    genres = sorted(df['genre'].unique())

    # NOTE: 為每個類型分配固定顏色
    genre_colors = {
        '動作': '#E74C3C', '愛情': '#E91E63', '恐怖': '#9B59B6',
        '職人劇': '#2980B9', '喜劇': '#F39C12',
    }

    fig = go.Figure()

    for genre in genres:
        genre_data = df[df['genre'] == genre]
        color = genre_colors.get(genre, '#7F8C8D')

        # 箱形圖
        fig.add_trace(go.Box(
            y=genre_data['box_office'],
            name=genre,
            marker_color=color,
            boxmean='sd',
            opacity=0.6,
            showlegend=False,
        ))

        # 散佈圖疊加——hover 顯示片名
        fig.add_trace(go.Scatter(
            x=[genre] * len(genre_data),
            y=genre_data['box_office'],
            mode='markers',
            marker=dict(color=color, size=7, opacity=0.8),
            name=genre,
            text=genre_data['title'],
            hovertemplate='<b>%{text}</b><br>票房: %{y:.1f} 百萬<extra></extra>',
            showlegend=False,
        ))

    fig.update_layout(
        title='Box Office by Genre (Interactive)',
        yaxis_title='Box Office (TWD, Millions)',
        template='plotly_white',
        height=450,
        hovermode='closest',
    )

    return fig

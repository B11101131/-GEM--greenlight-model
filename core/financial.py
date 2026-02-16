"""
財務分析模組

提供損益兩平分析、現金流預測、投資人報酬分攤模擬等核心財務計算。
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


# ============================================================
# 損益兩平分析 (Break-even Analysis)
# ============================================================

@dataclass
class BreakevenResult:
    """損益兩平分析結果"""
    breakeven_revenue: float       # 損益兩平總收入（百萬 TWD）
    breakeven_box_office: float    # 損益兩平所需票房（百萬 TWD）
    prob_breakeven: float          # 達到損益兩平的機率 (%)
    safety_margin: float           # 安全邊際：(預期收入 - 兩平收入) / 預期收入
    cost_breakdown: Dict[str, float]  # 成本拆解


def calculate_breakeven(
    budget: float,
    marketing_pa: float,
    theatrical_share: float = 0.5,
    streaming_multiplier: float = 0.4,
    net_profit_array: Optional[np.ndarray] = None,
) -> BreakevenResult:
    """
    計算損益兩平點。

    NOTE: 損益兩平票房 = 總成本 / (院線分潤率 + 串流倍數)
          這是簡化模型，假設串流收入與票房成正比。

    Args:
        budget: 製作預算（百萬 TWD）
        marketing_pa: 行銷費用（百萬 TWD）
        theatrical_share: 院線分潤比例
        streaming_multiplier: 串流收入倍數（取中間值）
        net_profit_array: 蒙地卡羅模擬的淨利陣列，用於計算達到兩平的機率

    Returns:
        BreakevenResult 物件
    """
    total_cost = budget + marketing_pa
    # 每單位票房帶來的實際收入 = 院線分潤 + 串流分潤
    revenue_per_box_office = theatrical_share + streaming_multiplier
    breakeven_box_office = total_cost / revenue_per_box_office
    breakeven_revenue = total_cost

    # 計算機率與安全邊際
    prob_breakeven = 0.0
    safety_margin = 0.0
    if net_profit_array is not None and len(net_profit_array) > 0:
        prob_breakeven = float(np.mean(net_profit_array >= 0) * 100)
        expected_profit = float(np.mean(net_profit_array))
        expected_revenue = expected_profit + total_cost
        if expected_revenue > 0:
            safety_margin = (expected_revenue - breakeven_revenue) / expected_revenue

    cost_breakdown = {
        '製作預算': budget,
        '行銷宣發 (P&A)': marketing_pa,
        '總成本': total_cost,
    }

    return BreakevenResult(
        breakeven_revenue=breakeven_revenue,
        breakeven_box_office=breakeven_box_office,
        prob_breakeven=prob_breakeven,
        safety_margin=safety_margin,
        cost_breakdown=cost_breakdown,
    )


# ============================================================
# 現金流預測 (Cash Flow Projection)
# ============================================================

@dataclass
class CashFlowConfig:
    """現金流預測的時間與比例設定"""
    # 時間軸（月）
    pre_production_months: int = 3     # 前製期
    production_months: int = 3         # 拍攝期
    post_production_months: int = 4    # 後製期
    marketing_ramp_months: int = 2     # 行銷加速期（上映前）
    theatrical_window_months: int = 3  # 院線上映窗口
    streaming_delay_months: int = 6    # 串流收入延遲（上映後）
    streaming_income_months: int = 6   # 串流收入持續期

    # 成本分配比例
    pre_production_cost_pct: float = 0.15   # 前製佔預算比例
    production_cost_pct: float = 0.60       # 拍攝佔預算比例
    post_production_cost_pct: float = 0.25  # 後製佔預算比例

    # 票房時間衰減模型（按週）
    # NOTE: 台灣院線票房通常前 2 週佔 60-70%，之後快速衰減
    weekly_decay_rate: float = 0.35  # 每週票房衰減率


def generate_cash_flow(
    budget: float,
    marketing_pa: float,
    expected_box_office: float,
    streaming_revenue: float,
    config: Optional[CashFlowConfig] = None,
) -> pd.DataFrame:
    """
    產生逐月現金流預測表。

    NOTE: 收入按院線票房週衰減模型分配，串流收入在延遲後平均進帳。
          成本按前製/拍攝/後製三階段分配。

    Args:
        budget: 製作預算（百萬 TWD）
        marketing_pa: 行銷費用（百萬 TWD）
        expected_box_office: 預期票房收入（百萬 TWD），已扣分潤
        streaming_revenue: 預期串流/版權收入（百萬 TWD）
        config: 時間與比例設定

    Returns:
        DataFrame 包含每月的支出、收入、淨流量、累計現金流
    """
    if config is None:
        config = CashFlowConfig()

    total_months = (
        config.pre_production_months
        + config.production_months
        + config.post_production_months
        + config.theatrical_window_months
        + config.streaming_delay_months
        + config.streaming_income_months
    )

    months = list(range(1, total_months + 1))
    outflows = np.zeros(total_months)
    inflows = np.zeros(total_months)
    phases = [''] * total_months

    idx = 0

    # --- 前製期支出 ---
    pre_cost = budget * config.pre_production_cost_pct
    monthly_pre = pre_cost / config.pre_production_months
    for i in range(config.pre_production_months):
        outflows[idx] = monthly_pre
        phases[idx] = '前製期'
        idx += 1

    # --- 拍攝期支出 ---
    prod_cost = budget * config.production_cost_pct
    monthly_prod = prod_cost / config.production_months
    for i in range(config.production_months):
        outflows[idx] = monthly_prod
        phases[idx] = '拍攝期'
        idx += 1

    # --- 後製期支出 + 行銷開始 ---
    post_cost = budget * config.post_production_cost_pct
    monthly_post = post_cost / config.post_production_months
    # 行銷費在後製最後幾個月開始加速
    marketing_start_idx = idx + max(0, config.post_production_months - config.marketing_ramp_months)
    for i in range(config.post_production_months):
        outflows[idx] = monthly_post
        # 行銷加速期
        if idx >= marketing_start_idx:
            marketing_month_pct = 0.3 / config.marketing_ramp_months
            outflows[idx] += marketing_pa * marketing_month_pct
        phases[idx] = '後製期'
        idx += 1

    # --- 院線上映期（收入進帳 + 剩餘行銷費）---
    # 票房按週衰減模型轉為月收入
    theatrical_weeks = config.theatrical_window_months * 4
    weekly_revenue = []
    remaining_revenue = expected_box_office
    for w in range(theatrical_weeks):
        # NOTE: 第一週收入最高，後續按衰減率遞減
        week_rev = remaining_revenue * (1 - config.weekly_decay_rate)
        if w == 0:
            week_rev = expected_box_office * 0.25  # 首週約 25%
        else:
            week_rev = weekly_revenue[-1] * (1 - config.weekly_decay_rate)
        weekly_revenue.append(max(week_rev, 0))

    # 將週收入彙總為月收入
    monthly_theatrical = []
    for m in range(config.theatrical_window_months):
        month_rev = sum(weekly_revenue[m * 4: (m + 1) * 4])
        monthly_theatrical.append(month_rev)

    # 剩餘行銷費分配到上映期
    remaining_marketing = marketing_pa * 0.7  # 70% 行銷費在上映期
    monthly_marketing_theatrical = remaining_marketing / config.theatrical_window_months

    for i in range(config.theatrical_window_months):
        inflows[idx] = monthly_theatrical[i] if i < len(monthly_theatrical) else 0
        outflows[idx] += monthly_marketing_theatrical
        phases[idx] = '院線上映'
        idx += 1

    # --- 串流延遲期（無收入）---
    streaming_start = idx + config.streaming_delay_months

    for i in range(config.streaming_delay_months):
        if idx < total_months:
            phases[idx] = '串流等待'
            idx += 1

    # --- 串流收入期 ---
    monthly_streaming = streaming_revenue / config.streaming_income_months
    for i in range(config.streaming_income_months):
        if idx < total_months:
            inflows[idx] = monthly_streaming
            phases[idx] = '串流收入'
            idx += 1

    net_flow = inflows - outflows
    cumulative = np.cumsum(net_flow)

    df = pd.DataFrame({
        '月份': months[:len(net_flow)],
        '階段': phases[:len(net_flow)],
        '支出': np.round(-outflows[:len(net_flow)], 2),
        '收入': np.round(inflows[:len(net_flow)], 2),
        '淨現金流': np.round(net_flow[:len(net_flow)], 2),
        '累計現金流': np.round(cumulative[:len(net_flow)], 2),
    })

    return df


# ============================================================
# 投資人報酬分攤模擬 (Investor Return Split)
# ============================================================

@dataclass
class InvestorProfile:
    """單一投資方設定"""
    name: str
    investment: float          # 投資金額（百萬 TWD）
    recoup_priority: int = 1   # 回收優先順序（1 = 最優先）
    profit_share_pct: float = 0.0  # 淨利分紅比例 (%)


@dataclass
class TieredSplit:
    """階梯分潤設定"""
    threshold: float    # 淨利門檻（百萬 TWD）
    producer_pct: float # 該級距製片方分成比例


def simulate_investor_returns(
    net_profit_array: np.ndarray,
    investors: List[InvestorProfile],
    tiered_splits: Optional[List[TieredSplit]] = None,
) -> Dict:
    """
    模擬多方投資人報酬分配。

    NOTE: 分配邏輯：
      1. 依優先順序回收投資本金
      2. 剩餘淨利按 profit_share_pct 分配
      3. 若有階梯分潤，則依淨利區間套用不同比例

    Args:
        net_profit_array: 蒙地卡羅模擬的淨利陣列
        investors: 投資方列表
        tiered_splits: 階梯分潤設定（可選）

    Returns:
        Dict 包含各投資方的平均報酬、ROI、回本機率
    """
    n_sims = len(net_profit_array)
    total_investment = sum(inv.investment for inv in investors)
    total_revenue_array = net_profit_array + total_investment

    # 按優先順序排列
    sorted_investors = sorted(investors, key=lambda x: x.recoup_priority)

    # 各方累計回收與收益
    results = {}
    for inv in investors:
        results[inv.name] = {
            'investment': inv.investment,
            'returns': np.zeros(n_sims),
            'profit_share_pct': inv.profit_share_pct,
        }

    for sim_idx in range(n_sims):
        remaining_revenue = total_revenue_array[sim_idx]

        # 步驟一：按優先順序回收本金
        for inv in sorted_investors:
            recoup = min(remaining_revenue, inv.investment)
            recoup = max(recoup, 0)
            results[inv.name]['returns'][sim_idx] += recoup
            remaining_revenue -= recoup

        # 步驟二：剩餘利潤按比例分配
        if remaining_revenue > 0:
            if tiered_splits:
                # 階梯分潤
                distributed = 0.0
                for tier_idx, tier in enumerate(tiered_splits):
                    if tier_idx == 0:
                        tier_amount = min(remaining_revenue, tier.threshold)
                    else:
                        prev_threshold = tiered_splits[tier_idx - 1].threshold
                        tier_amount = min(
                            max(remaining_revenue - prev_threshold, 0),
                            tier.threshold - prev_threshold,
                        )

                    # 製片方拿 producer_pct，其餘按投資比例分
                    investor_pool = tier_amount * (1 - tier.producer_pct)
                    for inv in investors:
                        inv_share = inv.profit_share_pct / 100
                        results[inv.name]['returns'][sim_idx] += investor_pool * inv_share
                    distributed += tier_amount

                # 超出最高門檻的部分
                excess = remaining_revenue - distributed
                if excess > 0:
                    for inv in investors:
                        inv_share = inv.profit_share_pct / 100
                        results[inv.name]['returns'][sim_idx] += excess * inv_share
            else:
                # 簡單按比例分配
                for inv in investors:
                    inv_share = inv.profit_share_pct / 100
                    results[inv.name]['returns'][sim_idx] += remaining_revenue * inv_share

    # 彙總統計
    summary = {}
    for inv in investors:
        returns = results[inv.name]['returns']
        net_return = returns - inv.investment
        summary[inv.name] = {
            'investment': inv.investment,
            'avg_return': float(np.mean(returns)),
            'avg_net_return': float(np.mean(net_return)),
            'avg_roi': float(np.mean(net_return / inv.investment) * 100) if inv.investment > 0 else 0,
            'prob_recoup': float(np.mean(returns >= inv.investment) * 100),
            'p5_return': float(np.percentile(net_return, 5)),
            'p95_return': float(np.percentile(net_return, 95)),
        }

    return summary

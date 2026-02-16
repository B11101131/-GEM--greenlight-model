"""
蒙地卡羅模擬核心引擎

從原始 greenlight_model.py 抽離，提供可重用的模擬計算功能。
所有模擬均基於三角分佈 (Triangular Distribution) 模型。
"""
import numpy as np
from typing import Tuple, Dict, Optional
import pandas as pd


def run_simulation(
    box_office_low: float,
    box_office_high: float,
    simulation_count: int,
    budget: float,
    marketing_pa: float,
    streaming_multiplier_low: float,
    streaming_multiplier_high: float,
    theatrical_share: float = 0.5,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, float, float, float, float, float]:
    """
    執行蒙地卡羅模擬，計算獲利分佈。

    NOTE: 使用三角分佈模擬票房不確定性，院線分潤比例可自訂（預設 50%）。

    Args:
        box_office_low: 悲觀票房預估（百萬 TWD）
        box_office_high: 樂觀票房預估（百萬 TWD）
        simulation_count: 模擬次數
        budget: 製作預算（百萬 TWD）
        marketing_pa: 行銷費用（百萬 TWD）
        streaming_multiplier_low: 串流分潤倍數下限
        streaming_multiplier_high: 串流分潤倍數上限
        theatrical_share: 院線票房分潤比例（預設 0.5）
        seed: 隨機種子（用於可重現結果）

    Returns:
        Tuple 包含 (net_profit, roi, expected_profit, expected_roi,
                     prob_loss_pct, p5, p95)
    """
    total_cost = budget + marketing_pa
    rng = np.random.default_rng(seed)

    box_office_mode = (box_office_low + box_office_high) / 2
    simulated_box_office = rng.triangular(
        left=box_office_low,
        mode=box_office_mode,
        right=box_office_high,
        size=simulation_count,
    )

    theatrical_revenue = simulated_box_office * theatrical_share
    streaming_multipliers = rng.uniform(
        streaming_multiplier_low, streaming_multiplier_high, simulation_count
    )
    ancillary_revenue = simulated_box_office * streaming_multipliers
    total_revenue = theatrical_revenue + ancillary_revenue

    net_profit = total_revenue - total_cost
    roi = (net_profit / total_cost) * 100

    expected_profit = float(np.mean(net_profit))
    expected_roi = float(np.mean(roi))
    prob_loss_pct = float(np.mean(net_profit < 0) * 100)

    p5, p95 = np.percentile(net_profit, [5, 95])

    return net_profit, roi, expected_profit, expected_roi, prob_loss_pct, float(p5), float(p95)


def run_sensitivity_analysis(
    base_params: Dict,
    variation_pct: float = 0.2,
) -> pd.DataFrame:
    """
    執行敏感度分析，計算各參數變動對淨利的影響。

    NOTE: 針對每個參數獨立變動 ±variation_pct，其餘參數保持不變。
          這是「一次一因子」(OAT) 敏感度分析法。

    Args:
        base_params: 基準參數字典，需包含所有 run_simulation 參數
        variation_pct: 變動百分比（預設 ±20%）

    Returns:
        包含各參數敏感度的 DataFrame，按 Impact Range 升序排列
    """
    sim_count = base_params.get('simulation_count', 2000)
    theatrical_share = base_params.get('theatrical_share', 0.5)

    base_result = run_simulation(
        base_params['box_office_low'],
        base_params['box_office_high'],
        sim_count,
        base_params['budget'],
        base_params['marketing_pa'],
        base_params['streaming_low'],
        base_params['streaming_high'],
        theatrical_share,
    )
    base_profit = base_result[2]

    sensitivity_results = []

    # NOTE: direction 表示參數增加時淨利的預期變動方向
    #       -1 = 成本類（增加→淨利減）、1 = 收入類（增加→淨利增）
    params_to_test = [
        ('Production Budget', 'budget', -1),
        ('Marketing (P&A)', 'marketing_pa', -1),
        ('Box Office (Low)', 'box_office_low', 1),
        ('Box Office (High)', 'box_office_high', 1),
        ('Streaming Rev. (Low)', 'streaming_low', 1),
        ('Streaming Rev. (High)', 'streaming_high', 1),
    ]

    for label, param_key, direction in params_to_test:
        test_params = base_params.copy()
        original_value = test_params[param_key]

        # 增加參數值
        test_params[param_key] = original_value * (1 + variation_pct)
        high_result = run_simulation(
            test_params['box_office_low'],
            test_params['box_office_high'],
            sim_count,
            test_params['budget'],
            test_params['marketing_pa'],
            test_params['streaming_low'],
            test_params['streaming_high'],
            theatrical_share,
        )
        high_profit = high_result[2]

        # 減少參數值
        test_params[param_key] = original_value * (1 - variation_pct)
        low_result = run_simulation(
            test_params['box_office_low'],
            test_params['box_office_high'],
            sim_count,
            test_params['budget'],
            test_params['marketing_pa'],
            test_params['streaming_low'],
            test_params['streaming_high'],
            theatrical_share,
        )
        low_profit = low_result[2]

        impact_range = abs(high_profit - low_profit)
        sensitivity_results.append({
            'Parameter': label,
            'Low Impact': low_profit - base_profit,
            'High Impact': high_profit - base_profit,
            'Impact Range': impact_range,
            'Direction': direction,
        })

    df = pd.DataFrame(sensitivity_results)
    df = df.sort_values('Impact Range', ascending=True)
    return df


def get_decision_status(
    prob_loss: float,
    expected_roi: float,
) -> Tuple[str, str]:
    """
    根據虧損機率與預期 ROI 判定綠燈 / 黃燈 / 紅燈。

    NOTE: 採用業界標準判定邏輯 —
          綠燈：虧損 <25% 且 ROI >20%
          黃燈：虧損 <45%
          紅燈：其餘

    Returns:
        (status_label, recommendation_text)
    """
    if prob_loss < 25 and expected_roi > 20:
        status = "🟢 綠燈 (Greenlight)"
        recommendation = "建議投資：風險極低且期望報酬達標。具備工業化規模潛力。"
    elif prob_loss < 45:
        status = "🟡 黃燈 (Caution)"
        recommendation = "審慎評估：虧損風險中等。建議先取得 30% 以上的保底收入（如輔導金或預售）再啟動。"
    else:
        status = "🔴 紅燈 (Pass)"
        recommendation = "建議擱置：虧損機率過高。需大幅削減 20% 以上預算或調整商業策略。"
    return status, recommendation

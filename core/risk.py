"""
風險管理模組

提供 VaR / CVaR 計算、風險指標彙總等功能。
敏感度分析已整合至 simulation.py。
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class VaRResult:
    """VaR 計算結果"""
    confidence_level: float    # 信心水準 (%)
    var_value: float           # VaR 值（百萬 TWD，負數表示損失）
    cvar_value: float          # CVaR 值（尾端平均損失）
    max_loss: float            # 最大損失
    interpretation: str        # 文字解讀


def calculate_var(
    net_profit_array: np.ndarray,
    confidence_levels: Optional[List[float]] = None,
) -> List[VaRResult]:
    """
    計算不同信心水準的 VaR 與 CVaR。

    NOTE: 使用歷史模擬法 (Historical Simulation Method)，
          直接從蒙地卡羅模擬結果取百分位數。
          CVaR (Conditional VaR) 又稱 Expected Shortfall，
          衡量超過 VaR 門檻時的平均損失，是更保守的風險指標。

    Args:
        net_profit_array: 蒙地卡羅模擬的淨利陣列
        confidence_levels: 信心水準列表（預設 [90, 95, 99]）

    Returns:
        各信心水準的 VaR 結果列表
    """
    if confidence_levels is None:
        confidence_levels = [90.0, 95.0, 99.0]

    results = []
    max_loss = float(np.min(net_profit_array))

    for cl in confidence_levels:
        # VaR = 第 (100 - confidence_level) 百分位數
        # NOTE: 這裡取「損失面」的百分位數
        percentile = 100 - cl
        var_value = float(np.percentile(net_profit_array, percentile))

        # CVaR = VaR 以下所有損失的平均值
        tail_losses = net_profit_array[net_profit_array <= var_value]
        cvar_value = float(np.mean(tail_losses)) if len(tail_losses) > 0 else var_value

        # 文字解讀
        if var_value >= 0:
            interpretation = (
                f"在 {cl:.0f}% 信心水準下，專案至少可獲利 "
                f"{var_value:.1f} 百萬 TWD。風險極低。"
            )
        else:
            interpretation = (
                f"在 {cl:.0f}% 信心水準下，最大可能損失為 "
                f"{abs(var_value):.1f} 百萬 TWD。"
                f"若發生極端虧損，平均損失約 {abs(cvar_value):.1f} 百萬 TWD。"
            )

        results.append(VaRResult(
            confidence_level=cl,
            var_value=var_value,
            cvar_value=cvar_value,
            max_loss=max_loss,
            interpretation=interpretation,
        ))

    return results


def calculate_risk_metrics(
    net_profit_array: np.ndarray,
    total_cost: float,
) -> Dict:
    """
    計算完整的風險指標摘要。

    Args:
        net_profit_array: 蒙地卡羅模擬的淨利陣列
        total_cost: 總投入成本

    Returns:
        Dict 包含各項風險指標
    """
    roi_array = (net_profit_array / total_cost) * 100

    # 下行風險指標
    # NOTE: Sortino Ratio 只考慮負面波動，比 Sharpe Ratio 更適合評估投資風險
    downside_returns = net_profit_array[net_profit_array < 0]
    downside_std = float(np.std(downside_returns)) if len(downside_returns) > 0 else 0.0

    expected_profit = float(np.mean(net_profit_array))
    sortino_ratio = expected_profit / downside_std if downside_std > 0 else float('inf')

    # 最大回撤（在此情境中為最大損失佔總成本的比例）
    max_drawdown = float(np.min(net_profit_array) / total_cost * 100) if total_cost > 0 else 0.0

    var_results = calculate_var(net_profit_array)

    return {
        'expected_profit': expected_profit,
        'expected_roi': float(np.mean(roi_array)),
        'profit_std': float(np.std(net_profit_array)),
        'roi_std': float(np.std(roi_array)),
        'prob_loss': float(np.mean(net_profit_array < 0) * 100),
        'prob_double': float(np.mean(net_profit_array > total_cost) * 100),  # 翻倍機率
        'max_profit': float(np.max(net_profit_array)),
        'max_loss': float(np.min(net_profit_array)),
        'max_drawdown_pct': max_drawdown,
        'sortino_ratio': sortino_ratio,
        'skewness': float(_safe_skewness(net_profit_array)),
        'kurtosis': float(_safe_kurtosis(net_profit_array)),
        'var_results': var_results,
        'p5': float(np.percentile(net_profit_array, 5)),
        'p25': float(np.percentile(net_profit_array, 25)),
        'median': float(np.median(net_profit_array)),
        'p75': float(np.percentile(net_profit_array, 75)),
        'p95': float(np.percentile(net_profit_array, 95)),
    }


def _safe_skewness(arr: np.ndarray) -> float:
    """計算偏態，避免 scipy 不可用時報錯"""
    try:
        from scipy.stats import skew
        return float(skew(arr))
    except ImportError:
        n = len(arr)
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            return 0.0
        return float(np.mean(((arr - mean) / std) ** 3))


def _safe_kurtosis(arr: np.ndarray) -> float:
    """計算峰態，避免 scipy 不可用時報錯"""
    try:
        from scipy.stats import kurtosis
        return float(kurtosis(arr))
    except ImportError:
        n = len(arr)
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            return 0.0
        return float(np.mean(((arr - mean) / std) ** 4) - 3)

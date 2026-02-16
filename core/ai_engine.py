"""
AI 票房預測引擎 (v2.1)

載入 GradientBoosting 模型進行票房預估，支援信賴區間。
若模型檔案不存在則優雅降級，不影響其他功能。
向下相容 v1.0 和 v2.0 模型。
"""
import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def load_ai_model(model_path: str) -> Optional[Dict]:
    """
    載入 AI 預測模型 bundle。

    NOTE: v2.0 模型儲存為 dict，包含 model / model_lower / model_upper。
          向下相容 v1.0（直接是 Pipeline 物件）。

    Args:
        model_path: 模型檔案路徑（.pkl）

    Returns:
        模型 bundle dict，或 None（若載入失敗）
    """
    try:
        import joblib
        import os
        if not os.path.exists(model_path):
            logger.info(f"AI 模型檔案不存在: {model_path}")
            return None
        raw = joblib.load(model_path)

        # NOTE: 向下相容 v1.0 格式（直接是 Pipeline）
        if isinstance(raw, dict) and 'model' in raw:
            logger.info(f"AI 模型已載入 (v{raw.get('version', '?')}): {model_path}")
            return raw
        else:
            # v1.0 格式包裝為 bundle
            logger.info(f"AI 模型已載入 (v1.0): {model_path}")
            return {
                'model': raw,
                'model_lower': None,
                'model_upper': None,
                'version': '1.0',
                'features': ['Budget', 'Marketing', 'Cast_Level', 'Director_Score', 'Genre'],
            }
    except Exception as e:
        logger.warning(f"AI 模型載入失敗: {e}")
        return None


def _build_input_df(
    genre: str,
    budget: float,
    marketing_pa: float,
    cast_level: int,
    director_score: int,
    release_month: int = 7,
    is_sequel: int = 0,
    ip_score: int = 1,
    version: str = "2.0",
) -> pd.DataFrame:
    """
    建構模型輸入 DataFrame。

    NOTE: v1.0 模型只需 4 個數值特徵 + Genre，
          v2.0 新增 Release_Month / Is_Sequel / IP_Score。
          v2.1 新增 Budget_Marketing_Ratio 衍生特徵。
    """
    data = {
        'Genre': [genre],
        'Budget': [budget],
        'Marketing': [marketing_pa],
        'Cast_Level': [cast_level],
        'Director_Score': [float(director_score)],
    }

    if version >= "2.0":
        data['Release_Month'] = [release_month]
        data['Is_Sequel'] = [is_sequel]
        data['IP_Score'] = [ip_score]

    # NOTE: v2.1 新增衍生特徵
    if version >= "2.1":
        data['Budget_Marketing_Ratio'] = [budget / (marketing_pa + 0.1)]

    return pd.DataFrame(data)


def predict_box_office(
    model_bundle: Dict,
    genre: str,
    budget: float,
    marketing_pa: float,
    cast_level: int,
    director_score: int,
    release_month: int = 7,
    is_sequel: int = 0,
    ip_score: int = 1,
) -> Tuple[float, float, float]:
    """
    使用 AI 模型預測票房。

    NOTE: 使用 DataFrame 輸入以正確匹配 Pipeline 中的 ColumnTransformer。

    Args:
        model_bundle: 模型 bundle（由 load_ai_model 載入）
        genre: 電影類型
        budget: 製作預算（百萬 TWD）
        marketing_pa: 行銷費用（百萬 TWD）
        cast_level: 卡司等級 (1-5)
        director_score: 導演評分 (1-10)
        release_month: 上映月份 (1-12)
        is_sequel: 是否為續集 (0/1)
        ip_score: IP 知名度 (1-5)

    Returns:
        (prediction, suggested_low, suggested_high)
    """
    version = model_bundle.get('version', '1.0')
    model = model_bundle['model']

    input_df = _build_input_df(
        genre, budget, marketing_pa, cast_level, director_score,
        release_month, is_sequel, ip_score, version,
    )

    prediction = float(model.predict(input_df)[0])
    prediction = max(prediction, 1.0)

    # NOTE: 使用 ±40% 作為預設區間
    suggested_low = max(prediction * 0.6, 5.0)
    suggested_high = prediction * 1.4

    return prediction, suggested_low, suggested_high


def predict_with_confidence(
    model_bundle: Dict,
    genre: str,
    budget: float,
    marketing_pa: float,
    cast_level: int,
    director_score: int,
    release_month: int = 7,
    is_sequel: int = 0,
    ip_score: int = 1,
) -> Dict:
    """
    使用 AI 模型預測票房，附帶信賴區間。

    NOTE: v2.0 模型使用 quantile regression 提供 P10/P90 區間。
          v1.0 模型回退為 ±40% 估算。

    Returns:
        Dict 包含 prediction, lower, upper, confidence_pct
    """
    version = model_bundle.get('version', '1.0')
    model = model_bundle['model']
    model_lower = model_bundle.get('model_lower')
    model_upper = model_bundle.get('model_upper')

    input_df = _build_input_df(
        genre, budget, marketing_pa, cast_level, director_score,
        release_month, is_sequel, ip_score, version,
    )

    prediction = float(model.predict(input_df)[0])
    prediction = max(prediction, 1.0)

    if model_lower is not None and model_upper is not None:
        lower = max(float(model_lower.predict(input_df)[0]), 1.0)
        upper = max(float(model_upper.predict(input_df)[0]), prediction)
        confidence_pct = 80  # P10-P90 = 80% 信賴區間
    else:
        lower = max(prediction * 0.6, 5.0)
        upper = prediction * 1.4
        confidence_pct = 60  # 估算

    return {
        'prediction': prediction,
        'lower': lower,
        'upper': upper,
        'confidence_pct': confidence_pct,
    }


def get_model_info(model_bundle: Dict) -> Dict:
    """
    取得模型版本與效能資訊。

    Returns:
        Dict 包含 version, features, metrics
    """
    return {
        'version': model_bundle.get('version', '1.0'),
        'features': model_bundle.get('features', []),
        'trained_at': model_bundle.get('trained_at', 'N/A'),
        'metrics': model_bundle.get('metrics', {}),
        'has_confidence': model_bundle.get('model_lower') is not None,
        'data_source': model_bundle.get('data_source', 'N/A'),
        'training_samples': model_bundle.get('training_samples', 'N/A'),
    }

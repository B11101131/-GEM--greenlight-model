"""
專案儲存與載入模組

將模擬參數和結果儲存為 JSON 檔案，支援歷史紀錄管理。
"""
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)

# NOTE: 專案儲存目錄，位於 GL model 根目錄下
SAVE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "saved_projects",
)


def _ensure_save_dir() -> None:
    """確保儲存目錄存在"""
    os.makedirs(SAVE_DIR, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    """
    清理檔名，移除不合法字元。

    NOTE: 保留中文字元，僅移除檔案系統不允許的特殊符號。
    """
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, '_')
    return name.strip()


def save_project(params: Dict, results: Dict, notes: str = "") -> str:
    """
    儲存專案模擬結果為 JSON。

    NOTE: net_profit 陣列因為太大（數千筆），僅儲存統計摘要而非原始資料。
          這樣保持 JSON 檔案體積合理（< 10KB）。

    Args:
        params: 模擬參數字典
        results: 模擬結果字典
        notes: 使用者備註

    Returns:
        儲存的檔案路徑
    """
    _ensure_save_dir()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    project_name = params.get('project_name', '未命名專案')
    filename = f"{timestamp}_{_sanitize_filename(project_name)}.json"
    filepath = os.path.join(SAVE_DIR, filename)

    # 建立儲存資料結構
    save_data = {
        "version": "2.0",
        "saved_at": datetime.now().isoformat(),
        "notes": notes,
        "params": {
            "project_name": params.get('project_name', ''),
            "genre": params.get('genre', ''),
            "budget": params.get('budget', 0),
            "marketing_pa": params.get('marketing_pa', 0),
            "cast_level": params.get('cast_level', 3),
            "director_score": params.get('director_score', 7),
            "theatrical_share": params.get('theatrical_share', 0.5),
            "streaming_low": params.get('streaming_low', 0.3),
            "streaming_high": params.get('streaming_high', 0.5),
            "box_office_low": params.get('box_office_low', 20.0),
            "box_office_high": params.get('box_office_high', 150.0),
            "simulation_count": params.get('simulation_count', 5000),
        },
        "results": {
            "expected_profit": results.get('expected_profit', 0),
            "expected_roi": results.get('expected_roi', 0),
            "prob_loss": results.get('prob_loss', 0),
            "p5": results.get('p5', 0),
            "p95": results.get('p95', 0),
            "status": results.get('status', ''),
            "recommendation": results.get('recommendation', ''),
        },
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    logger.info(f"專案已儲存: {filepath}")
    return filepath


def load_project(filepath: str) -> Optional[Dict]:
    """
    載入單一專案。

    Args:
        filepath: JSON 檔案路徑

    Returns:
        專案資料字典，格式錯誤或檔案不存在時回傳 None
    """
    if not os.path.exists(filepath):
        logger.warning(f"檔案不存在: {filepath}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"載入失敗: {filepath}, 錯誤: {e}")
        return None


def list_projects() -> List[Dict]:
    """
    列出所有已儲存的專案。

    Returns:
        專案列表，每項包含 filepath, project_name, saved_at, expected_roi, prob_loss, status
    """
    _ensure_save_dir()
    projects = []

    for filename in sorted(os.listdir(SAVE_DIR), reverse=True):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(SAVE_DIR, filename)
        data = load_project(filepath)
        if data is None:
            continue

        params = data.get('params', {})
        results = data.get('results', {})

        projects.append({
            'filepath': filepath,
            'filename': filename,
            'project_name': params.get('project_name', '未命名'),
            'genre': params.get('genre', ''),
            'budget': params.get('budget', 0),
            'saved_at': data.get('saved_at', ''),
            'notes': data.get('notes', ''),
            'expected_profit': results.get('expected_profit', 0),
            'expected_roi': results.get('expected_roi', 0),
            'prob_loss': results.get('prob_loss', 0),
            'status': results.get('status', ''),
        })

    return projects


def delete_project(filepath: str) -> bool:
    """
    刪除指定專案。

    Args:
        filepath: JSON 檔案路徑

    Returns:
        是否刪除成功
    """
    if not os.path.exists(filepath):
        return False

    try:
        os.remove(filepath)
        logger.info(f"專案已刪除: {filepath}")
        return True
    except OSError as e:
        logger.error(f"刪除失敗: {filepath}, 錯誤: {e}")
        return False

"""
🎬 影視專案綠燈評估模型 (GEM)
Greenlight Evaluation Model — 多頁應用主入口

結合財務工程與風險模擬的決策系統。
"""
import streamlit as st
import matplotlib.pyplot as plt
import os
import sys

# NOTE: 將專案根目錄加入 path，讓 pages 可以正確 import core/utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 全域 matplotlib 樣式設定（只需一次）
plt.style.use('seaborn-v0_8-whitegrid')

# 設定網頁標題與版面
st.set_page_config(
    page_title="影視專案綠燈評估模型 (GEM)",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 主頁面內容 ---
st.title("🎬 影視專案綠燈評估模型 (GEM)")
st.markdown("### 結合財務工程與風險模擬的影視投資決策系統")

st.markdown("---")

st.markdown("""
此工具模擬數千次市場情境，協助決策者判斷影視專案是否值得投資。

### 📋 功能總覽

| 頁面 | 功能 | 說明 |
|------|------|------|
| 🎬 風險模擬 | 蒙地卡羅模擬 | 核心模擬引擎，計算獲利分佈與投資決策建議 |
| 💰 財務分析 | 損益兩平 / 現金流 / 投資分攤 | 完整財務模型與投資結構分析 |
| ⚠️ 風險管理 | VaR / 敏感度 / 情境比較 | 進階風險量化與多情境壓力測試 |
| 📊 市場分析 | 歷史票房 / 競爭片 / 檔期建議 | 市場環境分析與上映檔期推薦 |
| 🤖 AI 分析 | 票房預測 / 觀眾輪廓 / 題材熱度 | AI 智能分析與觀眾輪廓預測 |
| 📈 儀表板 | 決策信號燈 / 綜合評分 / KPI | 一頁式專案決策總覽 |
| 📄 報表中心 | PDF / Excel 匯出 | 自動產生專業投資評估報告 |
| 📂 專案管理 | 儲存 / 載入 / 對比 | 專案歷史紀錄與多專案比較 |
| 🔌 API 設定 | OpenAI / Gemini / TMDB | 外接 AI 劇本分析與全球市場數據 |

### 🚀 使用流程

1. **設定參數** → 在左側邊欄輸入專案基本資訊
2. **執行模擬** → 前往「🎬 風險模擬」頁面啟動蒙地卡羅模擬
3. **深入分析** → 查看財務分析、風險管理等進階頁面
4. **匯出報告** → 在報表中心下載 PDF 報告

### 💡 系統說明

本系統採用工業工程中的 **蒙地卡羅模擬法**，針對影視專案的高不確定性進行壓力測試。

* **Input:** 製作預算、行銷費用、AI 預測 / 手動預估票房區間
* **Process:** 隨機生成數千種市場情境（包含串流分潤波動）
* **Output:** 獲利機率分佈、VaR 風險值、投資決策建議
""")

# --- 側邊欄：共用參數（所有頁面可讀取）---
st.sidebar.header("📁 專案參數設定")

# 基本資訊
project_name = st.sidebar.text_input("專案名稱", "範例電影：台北追緝令")
genre = st.sidebar.selectbox("類型", ["動作", "愛情", "恐怖", "職人劇", "喜劇"])

# 財務輸入
st.sidebar.subheader("💵 成本結構")
budget = st.sidebar.number_input("製作預算 (百萬 TWD)", value=50.0, step=5.0, min_value=1.0)
marketing_pa = st.sidebar.number_input("行銷宣發費 P&A (百萬 TWD)", value=10.0, step=1.0, min_value=0.0)

# 進階參數
st.sidebar.subheader("🎯 進階參數")
cast_level = st.sidebar.slider("卡司等級 (1=新人, 5=巨星)", 1, 5, 3)
director_score = st.sidebar.slider("導演/團隊評分 (1-10)", 1, 10, 7)

# 自訂分潤比例
st.sidebar.subheader("📊 分潤設定")
theatrical_share = st.sidebar.slider(
    "院線票房分潤比例",
    min_value=0.3, max_value=0.7, value=0.5, step=0.05,
    help="製片方從院線票房中可取得的比例（台灣通常為 45-55%）",
)
streaming_low = st.sidebar.slider(
    "串流分潤倍數（低）",
    min_value=0.1, max_value=0.6, value=0.3, step=0.05,
)
streaming_high = st.sidebar.slider(
    "串流分潤倍數（高）",
    min_value=0.2, max_value=0.8, value=0.5, step=0.05,
)

# AI 模型
from core.ai_engine import load_ai_model, predict_box_office

MODEL_PATH = os.path.join(os.path.dirname(__file__), "box_office_predictor.pkl")
model_bundle = load_ai_model(MODEL_PATH)

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 票房預測")
use_ai = st.sidebar.checkbox(
    "使用 AI 歷史數據預估票房",
    value=True if model_bundle else False,
    disabled=not model_bundle,
)

if use_ai and model_bundle:
    try:
        prediction, suggested_low, suggested_high = predict_box_office(
            model_bundle, genre, budget, marketing_pa, cast_level, director_score,
        )
        st.sidebar.info(f"AI 預測中位數：{prediction:.1f} M")
    except Exception as e:
        st.sidebar.error(f"AI 預測出錯: {e}")
        suggested_low, suggested_high = 20.0, 150.0
else:
    suggested_low, suggested_high = 20.0, 150.0
    if not model_bundle:
        st.sidebar.warning("⚠️ 找不到 AI 模型 (box_office_predictor.pkl)")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 票房預估區間")
box_office_low = st.sidebar.number_input(
    "悲觀票房預估 (Low Case)", value=float(suggested_low),
)
box_office_high = st.sidebar.number_input(
    "樂觀票房預估 (High Case)", value=float(suggested_high),
)
simulation_count = st.sidebar.slider("蒙地卡羅模擬次數", 1000, 10000, 5000)

# --- 將所有參數存入 session_state，供各分頁讀取 ---
st.session_state['params'] = {
    'project_name': project_name,
    'genre': genre,
    'budget': budget,
    'marketing_pa': marketing_pa,
    'cast_level': cast_level,
    'director_score': director_score,
    'theatrical_share': theatrical_share,
    'streaming_low': streaming_low,
    'streaming_high': streaming_high,
    'box_office_low': box_office_low,
    'box_office_high': box_office_high,
    'simulation_count': simulation_count,
}

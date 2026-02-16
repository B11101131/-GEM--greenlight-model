import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 設定網頁標題與版面
st.set_page_config(page_title="影視專案綠燈評估模型 (GEM)", layout="wide")

st.title("🎬 影視專案綠燈評估模型 (GEM)")
st.markdown("### 計畫一：結合財務工程與風險模擬的決策系統")
st.markdown("此工具模擬 5,000 次可能的市場情境，協助決策者判斷專案是否值得投資。")

# --- 側邊欄：輸入參數 (Input Parameters) ---
st.sidebar.header("1. 專案參數設定")

project_name = st.sidebar.text_input("專案名稱", "範例電影：台北追緝令")
genre = st.sidebar.selectbox("類型", ["動作", "愛情", "恐怖", "職人劇", "喜劇"])

# 財務輸入 (單位：百萬台幣)
st.sidebar.subheader("成本結構")
budget = st.sidebar.number_input("製作預算 (百萬 TWD)", value=50.0, step=5.0)
marketing_pa = st.sidebar.number_input("行銷宣發費 P&A (百萬 TWD)", value=10.0, step=1.0)
total_cost = budget + marketing_pa

st.sidebar.markdown("---")
st.sidebar.header("2. 風險模擬設定")

# 預估票房區間 (這通常來自計畫二的 AI 預測，這裡先用手動輸入模擬)
st.sidebar.subheader("市場預測區間")
box_office_low = st.sidebar.number_input("悲觀票房預估 (Low Case)", value=20.0)
box_office_high = st.sidebar.number_input("樂觀票房預估 (High Case)", value=150.0)
simulation_count = st.sidebar.slider("蒙地卡羅模擬次數", 1000, 10000, 5000)

# 簡單的回收分潤邏輯 (簡化版：票房的一半歸片方，加上串流與版權係數)
# 假設非票房收入 (串流/版權) 是票房的 30% ~ 50%
streaming_multiplier_low = 0.3
streaming_multiplier_high = 0.5

# --- 核心邏輯：蒙地卡羅模擬 (Monte Carlo Simulation) ---
if st.button("🚀 開始風險評估模擬"):
    
    # 1. 產生隨機分佈
    # 假設票房呈現對數常態分佈 (Log-Normal Distribution) 或 三角分佈
    # 這裡為了直觀，使用三角分佈 (Triangular Distribution) 模擬
    box_office_mode = (box_office_low + box_office_high) / 2 # 假設眾數在中間
    
    # 模擬票房
    simulated_box_office = np.random.triangular(
        left=box_office_low, 
        mode=box_office_mode, 
        right=box_office_high, 
        size=simulation_count
    )

    # 2. 計算總收入 (Revenue)
    # 片方票房分帳 (約 50%)
    theatrical_revenue = simulated_box_office * 0.5
    
    # 非票房收入 (隨機係數)
    streaming_multipliers = np.random.uniform(streaming_multiplier_low, streaming_multiplier_high, simulation_count)
    ancillary_revenue = simulated_box_office * streaming_multipliers
    
    total_revenue = theatrical_revenue + ancillary_revenue
    
    # 3. 計算淨利 (Net Profit) 與 投資報酬率 (ROI)
    net_profit = total_revenue - total_cost
    roi = (net_profit / total_cost) * 100

    # 4. 統計指標
    prob_loss = np.mean(net_profit < 0) * 100 # 虧損機率
    expected_roi = np.mean(roi)
    expected_profit = np.mean(net_profit)

    # --- 結果顯示區 (Dashboard) ---
    st.divider()
    st.header(f"📊 分析結果：{project_name}")
    
    # 顯示關鍵指標 (KPIs)
    col1, col2, col3 = st.columns(3)
    col1.metric(label="預估平均淨利 (Mean Net Profit)", value=f"{expected_profit:.1f} 百萬", delta=f"{expected_roi:.1f}% ROI")
    col2.metric(label="虧損風險機率 (Prob. of Loss)", value=f"{prob_loss:.1f}%", delta_color="inverse")
    
    # 紅綠燈判定邏輯
    if prob_loss < 20 and expected_roi > 15:
        status = "🟢 綠燈 (Greenlight)"
        color = "green"
        recommendation = "建議投資：風險可控，預期回報佳。符合工業化投資標準。"
    elif prob_loss < 40:
        status = "🟡 黃燈 (Caution)"
        color = "orange"
        recommendation = "審慎評估：建議申請政府輔導金、完片擔保，或降低 10% 預算以控制風險。"
    else:
        status = "🔴 紅燈 (Pass)"
        color = "red"
        recommendation = "建議擱置：虧損機率過高。建議退回開發階段 (Development) 修改劇本或調整卡司。"
        
    col3.markdown(f"### {status}")

    # 視覺化圖表
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("損益分佈模擬圖 (Profit/Loss Distribution)")
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 繪製直方圖
        n, bins, patches = ax.hist(net_profit, bins=50, color='#87CEEB', alpha=0.7, edgecolor='black')
        
        # 標示虧損區域 (紅色)
        for i in range(len(patches)):
            if bins[i] < 0:
                patches[i].set_facecolor('#FA8072') # Salmon color for loss
            else:
                patches[i].set_facecolor('#90EE90') # Light green for profit
        
        ax.axvline(0, color='red', linestyle='dashed', linewidth=2, label="損益平衡點 (Break-even Point)")
        ax.set_xlabel("淨利 (百萬 TWD)")
        ax.set_ylabel("模擬次數 (Frequency)")
        ax.legend()
        st.pyplot(fig)

    with col_chart2:
        st.subheader("決策建議與數據解讀")
        st.info(recommendation)
        st.markdown(f"""
        **數據洞察 (Data Insights)：**
        * **模擬次數：** {simulation_count} 次
        * **95% 信心水準下限：** {np.percentile(net_profit, 5):.1f} 百萬 (最糟情況)
        * **95% 信心水準上限：** {np.percentile(net_profit, 95):.1f} 百萬 (最好情況)
        
        **下一步 (Next Step)：**
        若此專案為紅燈或黃燈，建議啟動 **「計畫二：AI 內容橋樑」** 工具，
        分析市場缺口，調整劇本題材以提升基本盤。
        """)

else:
    st.info("👈 請在左側調整參數，並點擊「開始風險評估模擬」按鈕。")
    st.markdown("""
    ### 系統說明
    本系統採用工業工程 (Industrial Engineering) 中的 **蒙地卡羅模擬法**，
    針對影視專案的高不確定性進行壓力測試。
    
    * **Input:** 製作預算、行銷費用、市場預估區間。
    * **Process:** 隨機生成數千種市場情境 (包含串流分潤波動)。
    * **Output:** 獲利機率分佈與投資決策建議。
    """)

# --- 在側邊欄加入 AI 輔助功能 ---
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 票房預測輔助")

# 模擬一個簡單的查找表 (未來這裡會換成真正的 Scikit-learn 模型)
# 這裡模擬：動作片成本高但上限高，職人劇相對穩定
genre_baseline = {
    "動作": {"low": 40, "high": 200},
    "愛情": {"low": 15, "high": 80},
    "恐怖": {"low": 20, "high": 100},
    "職人劇": {"low": 10, "high": 50},
    "喜劇": {"low": 15, "high": 120}
}

use_ai_prediction = st.sidebar.checkbox("使用 AI 歷史數據預估票房")

if use_ai_prediction:
    # 根據上方選擇的類型 (genre) 自動填入數據
    suggested_low = genre_baseline[genre]["low"]
    suggested_high = genre_baseline[genre]["high"]
    
    st.sidebar.info(f"AI 根據歷史數據分析：{genre}片 預估區間為 {suggested_low}~{suggested_high} 百萬")
    
    # 覆蓋原本的手動輸入框
    box_office_low = st.sidebar.number_input("悲觀票房預估", value=float(suggested_low))
    box_office_high = st.sidebar.number_input("樂觀票房預估", value=float(suggested_high))
else:
    # 保持原本的手動輸入
    box_office_low = st.sidebar.number_input("悲觀票房預估 (Low Case)", value=20.0)
    box_office_high = st.sidebar.number_input("樂觀票房預估 (High Case)", value=150.0)
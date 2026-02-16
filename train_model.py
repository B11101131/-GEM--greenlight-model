"""
AI 票房預測模型訓練腳本（v2.1）

優先使用 historical_box_office.csv 真實資料，
以 data augmentation 擴增訓練集，提升模型的市場貼近度。
支援信賴區間預測（Quantile Regression）。
"""
import numpy as np
import pandas as pd
import os
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from datetime import datetime


# ==========================================
# 1. 載入資料（優先真實資料 + augmentation）
# ==========================================
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HISTORICAL_CSV = os.path.join(DATA_DIR, "historical_box_office.csv")
USE_REAL_DATA = os.path.exists(HISTORICAL_CSV)

rng = np.random.default_rng(42)

if USE_REAL_DATA:
    print("📂 偵測到真實歷史資料，優先使用 historical_box_office.csv")
    real_df = pd.read_csv(HISTORICAL_CSV)

    # NOTE: 將真實資料欄位對齊為模型訓練所需格式
    real_df = real_df.rename(columns={
        'genre': 'Genre',
        'budget': 'Budget',
        'marketing': 'Marketing',
        'cast_level': 'Cast_Level',
        'box_office': 'Box_Office',
        'release_month': 'Release_Month',
        'is_sequel': 'Is_Sequel',
    })

    # NOTE: 真實資料缺少 Director_Score 和 IP_Score，用合理代理值填充
    if 'Director_Score' not in real_df.columns:
        # 以 ROI 為代理：高 ROI 暗示導演執行力強
        roi = (real_df['Box_Office'] - real_df['Budget']) / real_df['Budget']
        real_df['Director_Score'] = np.clip(roi * 5 + 5, 1, 10).round(1)

    if 'IP_Score' not in real_df.columns:
        # 續集 IP 較高，否則依票房推估
        real_df['IP_Score'] = np.where(
            real_df['Is_Sequel'] == 1,
            rng.choice([3, 4, 5], len(real_df), p=[0.3, 0.5, 0.2]),
            rng.choice([1, 2, 3], len(real_df), p=[0.5, 0.35, 0.15]),
        )

    print(f"  真實資料：{len(real_df)} 筆")

    # ---- Data Augmentation ----
    # NOTE: 對真實資料加入受控隨機噪聲，擴增至約 500 筆
    # 這比完全模擬的資料更貼近真實市場分佈
    N_AUG_PER_SAMPLE = 8  # 每筆擴增 8 倍
    aug_rows = []

    for _, row in real_df.iterrows():
        for _ in range(N_AUG_PER_SAMPLE):
            aug_row = row.copy()
            # 預算 ±15%
            aug_row['Budget'] = max(5, row['Budget'] * rng.uniform(0.85, 1.15))
            # 行銷 ±20%
            aug_row['Marketing'] = max(1, row['Marketing'] * rng.uniform(0.80, 1.20))
            # 卡司微調 ±1
            aug_row['Cast_Level'] = int(np.clip(row['Cast_Level'] + rng.choice([-1, 0, 0, 1]), 1, 5))
            # 導演微調
            aug_row['Director_Score'] = float(np.clip(row['Director_Score'] + rng.uniform(-1.5, 1.5), 1, 10))
            # 月份偶爾微調
            if rng.random() < 0.3:
                aug_row['Release_Month'] = int(rng.choice(range(1, 13)))
            # 票房加噪聲 ±20%
            aug_row['Box_Office'] = max(2, row['Box_Office'] * rng.uniform(0.80, 1.20))
            aug_rows.append(aug_row)

    aug_df = pd.DataFrame(aug_rows)
    df = pd.concat([real_df, aug_df], ignore_index=True)
    print(f"  Data Augmentation 後：{len(df)} 筆（原始 {len(real_df)} + 擴增 {len(aug_df)}）")

else:
    print("⚠️ 找不到 historical_box_office.csv，使用模擬資料")
    N_SAMPLES = 2000

    genres = ['動作', '愛情', '恐怖', '職人劇', '喜劇']
    cast_levels = [1, 2, 3, 4, 5]

    data = {
        'Genre': rng.choice(genres, N_SAMPLES),
        'Budget': rng.uniform(10, 150, N_SAMPLES),
        'Marketing': rng.uniform(2, 30, N_SAMPLES),
        'Cast_Level': rng.choice(cast_levels, N_SAMPLES, p=[0.25, 0.30, 0.25, 0.15, 0.05]),
        'Director_Score': rng.uniform(1, 10, N_SAMPLES),
        'Release_Month': rng.choice(range(1, 13), N_SAMPLES),
        'Is_Sequel': rng.choice([0, 1], N_SAMPLES, p=[0.8, 0.2]),
        'IP_Score': rng.choice([1, 2, 3, 4, 5], N_SAMPLES, p=[0.35, 0.25, 0.20, 0.15, 0.05]),
    }
    df = pd.DataFrame(data)

    # 模擬票房生成邏輯
    genre_weights = {'動作': 1.8, '愛情': 0.8, '恐怖': 1.3, '職人劇': 0.7, '喜劇': 1.1}
    genre_factor = df['Genre'].map(genre_weights).astype(float)

    month_weights = {1: 1.3, 2: 1.5, 3: 0.7, 4: 0.6, 5: 0.8, 6: 0.9,
                     7: 1.4, 8: 1.3, 9: 0.7, 10: 0.8, 11: 0.7, 12: 1.1}
    month_factor = df['Release_Month'].map(month_weights).astype(float)

    sequel_bonus = df['Is_Sequel'] * 15
    ip_factor = 1 + (df['IP_Score'] - 1) * 0.1

    revenue = (
        5
        + (df['Budget'] * 1.1 * genre_factor * ip_factor)
        + (df['Marketing'] * 1.8)
        + (df['Cast_Level'] ** 2 * 2.5)
        + (df['Director_Score'] * 3)
        + sequel_bonus
    ) * month_factor * 0.8

    noise = rng.normal(0, 20, N_SAMPLES)
    final_revenue = np.maximum(2, revenue + noise)

    black_swan_mask = rng.random(N_SAMPLES) < 0.05
    final_revenue = np.where(black_swan_mask, final_revenue * 1.8, final_revenue)

    df['Box_Office'] = final_revenue
    print(f"  模擬資料：{len(df)} 筆")

# 匯出訓練資料備份
df.to_csv("taiwan_movie_data.csv", index=False)
print(f"數據已匯出：taiwan_movie_data.csv (共 {len(df)} 筆)")


# ==========================================
# 2. 特徵工程
# ==========================================
# NOTE: 新增衍生特徵——預算行銷比
df['Budget_Marketing_Ratio'] = df['Budget'] / (df['Marketing'] + 0.1)

print("開始訓練 AI 模型 (GradientBoosting v2.1)...")

X = df[['Genre', 'Budget', 'Marketing', 'Cast_Level', 'Director_Score',
        'Release_Month', 'Is_Sequel', 'IP_Score', 'Budget_Marketing_Ratio']]
y = df['Box_Office']

categorical_features = ['Genre']
numerical_features = ['Budget', 'Marketing', 'Cast_Level', 'Director_Score',
                       'Release_Month', 'Is_Sequel', 'IP_Score', 'Budget_Marketing_Ratio']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', 'passthrough', numerical_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features),
    ])

# 中位數預測模型
model_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', GradientBoostingRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
        loss='squared_error',
    )),
])

# 切分
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 訓練中位數模型
model_pipeline.fit(X_train, y_train)


# ==========================================
# 3. 信賴區間模型（上下界）
# ==========================================
print("訓練信賴區間模型...")

# NOTE: 使用 quantile regression 訓練上界（P90）和下界（P10）
model_lower = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', GradientBoostingRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
        loss='quantile',
        alpha=0.10,
    )),
])

model_upper = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', GradientBoostingRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
        loss='quantile',
        alpha=0.90,
    )),
])

model_lower.fit(X_train, y_train)
model_upper.fit(X_train, y_train)


# ==========================================
# 4. 評估
# ==========================================
y_pred = model_pipeline.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

# 交叉驗證
cv_scores = cross_val_score(model_pipeline, X, y, cv=5, scoring='r2')

print("-" * 40)
print(f"模型訓練完成！(v2.1 GradientBoosting)")
print(f"資料來源：{'真實資料 + augmentation' if USE_REAL_DATA else '模擬資料'}")
print(f"訓練集大小：{len(X_train)} 筆 / 測試集：{len(X_test)} 筆")
print(f"平均絕對誤差 (MAE): {mae:.2f} 百萬 TWD")
print(f"解釋力 (R²): {r2:.4f}")
print(f"交叉驗證 R² (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
print("-" * 40)


# ==========================================
# 5. 儲存模型與元資料
# ==========================================
model_bundle = {
    'model': model_pipeline,
    'model_lower': model_lower,
    'model_upper': model_upper,
    'version': '2.1',
    'features': numerical_features + categorical_features,
    'trained_at': datetime.now().isoformat(),
    'data_source': 'historical_box_office.csv + augmentation' if USE_REAL_DATA else 'simulated',
    'training_samples': len(df),
    'metrics': {
        'mae': float(mae),
        'r2': float(r2),
        'cv_r2_mean': float(cv_scores.mean()),
        'cv_r2_std': float(cv_scores.std()),
    },
}

joblib.dump(model_bundle, 'box_office_predictor.pkl')
print("模型已封裝為：box_office_predictor.pkl (v2.1)")
print(f"包含: 中位數模型 + P10 下界模型 + P90 上界模型")
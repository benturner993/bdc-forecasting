"""
Revenue Forecasting Model — Training Script
============================================
Trains a LightGBM model to forecast monthly practice revenue, with proper
quantile regression for confidence intervals and time-series cross-validation.

Usage
-----
From the project root:
    python model/train_model.py [--data-dir ./data] [--output-dir ./model]

Requirements
------------
    lightgbm>=4.3.0
    scikit-learn>=1.4.0
    pandas>=2.2.0
    numpy>=1.26.0

Feature contract
----------------
FEATURE_COLS and build_inference_features() are imported from forecasting.py
so that the feature vector at training time is IDENTICAL to inference time.
Retraining is required whenever FEATURE_COLS is changed.
"""

import os
import sys
import pickle
import argparse
import numpy as np
import pandas as pd
from datetime import date

# ── Resolve project root so forecasting.py is importable ──────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from forecasting import (          # noqa: E402
    FEATURE_COLS,
    BOOKING_PROFILE_ENC,
    build_inference_features,
)
from data_generator import SEASONALITY   # noqa: E402

# ── Args ───────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Train BDC LightGBM revenue model")
parser.add_argument("--data-dir",   default=os.path.join(_ROOT, "data"),  help="Path to data/ folder")
parser.add_argument("--output-dir", default=_HERE,                         help="Path to model/ output folder")
args = parser.parse_args()

DATA_DIR  = args.data_dir
MODEL_DIR = args.output_dir

# ── 1. Load data ───────────────────────────────────────────────────────────
print("Loading data …")
practices  = pd.read_csv(os.path.join(DATA_DIR, "practices.csv"))
historical = pd.read_csv(os.path.join(DATA_DIR, "bookings_historical.csv"))

# ── 2. Feature engineering ─────────────────────────────────────────────────
print("Engineering features …")

df = historical.merge(
    practices[[
        "id", "nhs_mix", "private_mix",
        "avg_nhs_value", "avg_private_value",
        "monthly_capacity", "target_utilization",
        "booking_profile", "connected_care",
    ]],
    left_on="practice_id", right_on="id", how="left",
)

df["seasonality_factor"] = df["month"].map(SEASONALITY)

# Sort chronologically within each practice before building lags
df = df.sort_values(["practice_id", "year", "month"]).reset_index(drop=True)

df["bookings_lag1"]  = df.groupby("practice_id")["bookings"].shift(1)
df["bookings_lag3"]  = df.groupby("practice_id")["bookings"].shift(3)
df["revenue_lag1"]   = df.groupby("practice_id")["revenue"].shift(1)
df["nhs_mix_lag1"]   = df.groupby("practice_id")["nhs_mix"].shift(1)
df["rolling_avg_3m"] = df.groupby("practice_id")["bookings"].transform(
    lambda x: x.shift(1).rolling(3, min_periods=2).mean()
)
df["rev_per_booking_lag1"] = df["revenue_lag1"] / df["bookings_lag1"].replace(0, np.nan)
df["booking_rate_vs_aop"]  = (
    df["bookings"] / df["aop_bookings"].replace(0, np.nan)
    if "aop_bookings" in df.columns
    else 1.0
)

df["booking_profile_encoded"] = (
    df["booking_profile"].map(BOOKING_PROFILE_ENC).fillna(1).astype(int)
)
df["connected_care_encoded"] = df["connected_care"].astype(int)

# Drop rows with insufficient lag history (first 3 months per practice)
df = df.dropna(subset=["bookings_lag1", "bookings_lag3", "rolling_avg_3m",
                        "revenue_lag1", "rev_per_booking_lag1"]).copy()

TARGET_COL = "revenue"

X = df[FEATURE_COLS].values.astype(float)
y = df[TARGET_COL].values.astype(float)
time_idx = (df["year"] * 100 + df["month"]).values

print(f"  Dataset: {len(df):,} rows, {len(FEATURE_COLS)} features")

# ── 3. Temporal train / test split ─────────────────────────────────────────
print("Splitting train / test …")
# Hold out the last ~15 % of time periods as an unseen test set
cutoff = np.quantile(time_idx, 0.85)
train_mask = time_idx <= cutoff
X_train, X_test = X[train_mask], X[~train_mask]
y_train, y_test = y[train_mask], y[~train_mask]
t_train = time_idx[train_mask]
print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

# Within train, hold out the latest 20 % as a validation set for early stopping
val_cut = np.quantile(t_train, 0.80)
val_mask = t_train > val_cut
X_tr,  X_val  = X_train[~val_mask], X_train[val_mask]
y_tr,  y_val  = y_train[~val_mask], y_train[val_mask]
print(f"  Sub-train: {len(X_tr):,}  |  Val (early-stop): {len(X_val):,}")

# ── 4. LightGBM training ───────────────────────────────────────────────────
try:
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, r2_score

    # ── Shared hyper-parameters ────────────────────────────────────────────
    BASE_PARAMS = dict(
        n_estimators     = 2000,
        learning_rate    = 0.02,
        num_leaves       = 31,
        min_child_samples= 20,
        subsample        = 0.8,
        colsample_bytree = 0.8,
        reg_alpha        = 0.05,
        reg_lambda       = 1.0,
        random_state     = 42,
        n_jobs           = -1,
        verbose          = -1,
    )
    CALLBACKS = [lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)]

    # ── 4a. Mean model ─────────────────────────────────────────────────────
    print("Training mean model …")
    model_mean = lgb.LGBMRegressor(**BASE_PARAMS)
    model_mean.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        callbacks=CALLBACKS,
    )
    y_pred_test = model_mean.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred_test)
    rmse = float(np.sqrt(np.mean((y_test - y_pred_test) ** 2)))
    r2   = r2_score(y_test, y_pred_test)
    print(f"  Test MAE : £{mae:,.0f}")
    print(f"  Test RMSE: £{rmse:,.0f}")
    print(f"  Test R²  : {r2:.4f}")

    # Residual std on training set (used as CI fallback when quantile models unavailable)
    train_resid = y_train - model_mean.predict(X_train)
    std_resid   = float(np.std(train_resid))
    print(f"  Train residual std: £{std_resid:,.0f}")

    # ── 4b. Quantile models for 80 % CI (10th / 90th percentile) ──────────
    print("Training quantile models …")
    Q_PARAMS = {**BASE_PARAMS, "objective": "quantile", "n_estimators": 1000}

    model_q10 = lgb.LGBMRegressor(**Q_PARAMS, alpha=0.10)
    model_q10.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], callbacks=CALLBACKS)

    model_q90 = lgb.LGBMRegressor(**Q_PARAMS, alpha=0.90)
    model_q90.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], callbacks=CALLBACKS)

    # Quantile coverage check
    q10_pred = model_q10.predict(X_test)
    q90_pred = model_q90.predict(X_test)
    coverage = float(np.mean((y_test >= q10_pred) & (y_test <= q90_pred)))
    print(f"  80 % CI empirical coverage on test set: {coverage:.1%} (target ≥ 80 %)")

    # ── 4c. Time-series cross-validation (diagnostic) ─────────────────────
    print("Running TimeSeriesSplit cross-validation …")
    from sklearn.model_selection import TimeSeriesSplit
    tscv   = TimeSeriesSplit(n_splits=4, gap=0)
    cv_mae = []
    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
        xtr, xvl = X_train[tr_idx], X_train[val_idx]
        ytr, yvl = y_train[tr_idx], y_train[val_idx]
        cv_m = lgb.LGBMRegressor(
            **{**BASE_PARAMS, "n_estimators": model_mean.best_iteration_ or 300}
        )
        cv_m.fit(xtr, ytr)
        cv_mae.append(mean_absolute_error(yvl, cv_m.predict(xvl)))
    print(f"  CV MAE: £{np.mean(cv_mae):,.0f} ± £{np.std(cv_mae):,.0f}")

    feature_importances = dict(zip(FEATURE_COLS,
                                   model_mean.feature_importances_.tolist()))

    print("\nFeature importances:")
    for k, v in sorted(feature_importances.items(), key=lambda x: -x[1]):
        bar = "█" * int(v / max(feature_importances.values()) * 20)
        print(f"  {k:<30s} {bar} {v:.0f}")

except ImportError:
    print("  lightgbm not installed — saving placeholder model.")
    print("  Install with: pip install lightgbm")
    model_mean = model_q10 = model_q90 = None
    mae = rmse = r2 = std_resid = None
    coverage = None
    feature_importances = {}

# ── 5. Generate predictions CSV ───────────────────────────────────────────
print("\nGenerating predictions …")
if model_mean is not None:
    y_all_pred  = model_mean.predict(X)
    q10_all     = model_q10.predict(X)
    q90_all     = model_q90.predict(X)

    pred_df = df[["practice_id", "year", "month"]].copy()
    pred_df["predicted_revenue"] = y_all_pred.round(2)
    pred_df["actual_revenue"]    = y
    pred_df["ci80_lower"]        = q10_all.round(2)
    pred_df["ci80_upper"]        = q90_all.round(2)
    pred_df["ci95_lower"]        = (y_all_pred - 1.96 * std_resid).round(2)
    pred_df["ci95_upper"]        = (y_all_pred + 1.96 * std_resid).round(2)
    out_path = os.path.join(MODEL_DIR, "predictions.csv")
    pred_df.to_csv(out_path, index=False)
    print(f"  Written {len(pred_df):,} rows → {out_path}")

# ── 6. Save model payload ─────────────────────────────────────────────────
model_payload = {
    "model_type":          "LightGBM",
    "version":             "2.0.0",
    "trained":             str(date.today()),
    "features":            FEATURE_COLS,
    "target":              TARGET_COL,
    "performance": {
        "mae":      mae,
        "rmse":     rmse,
        "r2":       r2,
        "ci80_cov": coverage,
    },
    "feature_importances": feature_importances,
    "std_resid":           std_resid,
    "model":               model_mean,
    "q10_model":           model_q10,
    "q90_model":           model_q90,
}

model_path = os.path.join(MODEL_DIR, "model.pkl")
with open(model_path, "wb") as f:
    pickle.dump(model_payload, f)
print(f"  Model saved → {model_path}")
print("\nTraining complete.")

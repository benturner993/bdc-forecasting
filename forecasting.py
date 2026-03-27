"""
Forecasting and analytics module for Bupa Dental Care.

This module serves two roles:
1.  Statistical fallback forecasting (no ML required) — always available.
2.  LightGBM-backed forecasting — used automatically when model/model.pkl
    contains a trained model produced by model/train_model.py.

Shared contract
---------------
FEATURE_COLS and build_inference_features() are defined here and imported by
train_model.py so that the feature vector produced at training time is
*identical* to the one produced at inference time.
"""

import os
import pickle
import numpy as np
from data_generator import SEASONALITY, FORECAST_MONTHS

# ── Price increase assumptions ─────────────────────────────────────────────
NHS_PRICE_INCREASE     = 0.025   # 2.5 % / year — NHS contract uplift
PRIVATE_PRICE_INCREASE = 0.05    # 5.0 % / year — private market inflation

# ── Shared feature contract ────────────────────────────────────────────────
# Any change here must be reflected by retraining model/train_model.py.
FEATURE_COLS = [
    "nhs_mix",
    "private_mix",
    "avg_nhs_value",
    "avg_private_value",
    "monthly_capacity",
    "target_utilization",
    "seasonality_factor",
    "bookings_lag1",
    "bookings_lag3",
    "rolling_avg_3m",
    "revenue_lag1",
    "nhs_mix_lag1",
    "booking_rate_vs_aop",
    "rev_per_booking_lag1",
    "booking_profile_encoded",
    "network_program_encoded",
]

BOOKING_PROFILE_ENC = {"early": 0, "mixed": 1, "late": 2}


def build_inference_features(
    practice: dict,
    target_month: int,
    target_year: int,
    lag_bookings: list,   # [oldest … newest], len >= 1
    lag_revenue: list,    # [oldest … newest], len >= 1
    lag_nhs_mix: list,    # [oldest … newest], len >= 1
) -> list:
    """
    Build a single feature row matching FEATURE_COLS exactly.
    Used at both training time (for validation) and inference time.
    """
    season = SEASONALITY[target_month]
    aop_b  = practice.get("aop_monthly_bookings", 600)

    b_lag1   = lag_bookings[-1]       if lag_bookings          else aop_b
    b_lag3   = lag_bookings[-3]       if len(lag_bookings) >= 3 else b_lag1
    rolling3 = float(np.mean(lag_bookings[-3:])) if lag_bookings else float(aop_b)
    r_lag1   = lag_revenue[-1]        if lag_revenue            else practice.get("aop_monthly_revenue", 50000)
    n_lag1   = lag_nhs_mix[-1]        if lag_nhs_mix            else practice.get("nhs_mix", 0.6)
    rpb_lag1 = (r_lag1 / b_lag1)      if b_lag1 > 0             else practice.get("blended_value", 80)

    bk_rate_vs_aop = (b_lag1 / aop_b) if aop_b > 0 else 1.0

    profile_enc = BOOKING_PROFILE_ENC.get(practice.get("booking_profile", "mixed"), 1)
    np_enc      = int(bool(practice.get("network_program", False)))

    return [
        practice["nhs_mix"],
        practice["private_mix"],
        practice["avg_nhs_value"],
        practice["avg_private_value"],
        practice["monthly_capacity"],
        practice["target_utilization"],
        season,
        b_lag1,
        b_lag3,
        rolling3,
        r_lag1,
        n_lag1,
        bk_rate_vs_aop,
        rpb_lag1,
        profile_enc,
        np_enc,
    ]


# ── Model loading (lazy, cached) ───────────────────────────────────────────
_MODEL_CACHE: dict = {}


def _load_model():
    """
    Load model/model.pkl once and cache the result.
    Returns None if the file doesn't exist or contains only a placeholder.
    """
    if "payload" not in _MODEL_CACHE:
        model_path = os.path.join(os.path.dirname(__file__), "model", "model.pkl")
        payload = None
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    candidate = pickle.load(f)
                # Accept only real trained models, not the placeholder
                if (candidate.get("model_type") not in ("placeholder",)
                        and candidate.get("model") is not None
                        and hasattr(candidate["model"], "predict")):
                    payload = candidate
            except Exception:
                pass
        _MODEL_CACHE["payload"] = payload
    return _MODEL_CACHE["payload"]


def ml_model_deployed() -> bool:
    """True when a trained model in model/model.pkl is used for practice-level forecasts."""
    return _load_model() is not None


# ── Price multiplier helper ────────────────────────────────────────────────

def _monthly_price_multiplier(base_month: int, base_year: int,
                               target_month: int, target_year: int,
                               nhs_mix: float) -> float:
    """Blended price-inflation multiplier from base period to target period."""
    years = (target_year - base_year) + (target_month - base_month) / 12
    nhs_m     = (1 + NHS_PRICE_INCREASE)     ** years
    private_m = (1 + PRIVATE_PRICE_INCREASE) ** years
    return nhs_mix * nhs_m + (1 - nhs_mix) * private_m


# ── Statistical fallback forecast ─────────────────────────────────────────

def _forecast_practice_statistical(practice: dict, months: list) -> dict:
    """
    Pure statistical forecast using a de-seasonalised 6-month baseline
    plus a trend adjustment from the current-month booking rate.
    Confidence intervals come from the historical standard deviation.
    """
    hist     = practice["historical_months"]
    recent   = hist[-6:]
    base_avg = np.mean([m["bookings"] for m in recent])
    base_sea = np.mean([SEASONALITY[m["month"]] for m in recent])
    baseline = base_avg / base_sea if base_sea > 0 else base_avg

    trend_adj   = float(np.clip(0.5 + 0.5 * practice["booking_rate"], 0.85, 1.10))
    hist_std_pct = max(0.04, float(
        np.std([m["bookings"] for m in hist]) / np.mean([m["bookings"] for m in hist])
    ) if hist else 0.06)

    data = []
    for fm in months:
        season     = SEASONALITY[fm["month"]]
        price_mult = _monthly_price_multiplier(3, 2026, fm["month"], fm["year"],
                                               practice["nhs_mix"])
        fc_bk  = baseline * season * trend_adj
        fc_rev = fc_bk * practice["blended_value"] * price_mult
        aop_bk = practice["aop_monthly_bookings"] * season / SEASONALITY[3] * 1.03
        aop_rv = practice["aop_monthly_revenue"]  * season / SEASONALITY[3] * 1.03 * price_mult
        s_bk   = fc_bk  * hist_std_pct
        s_rv   = fc_rev * hist_std_pct
        data.append({
            "month": fm["month"], "year": fm["year"], "label": fm["label"],
            "forecast_bookings":    round(fc_bk),
            "forecast_revenue":     round(fc_rev),
            "aop_bookings":         round(aop_bk),
            "aop_revenue":          round(aop_rv),
            "ci80_lower_bookings":  round(fc_bk  - 1.28 * s_bk),
            "ci80_upper_bookings":  round(fc_bk  + 1.28 * s_bk),
            "ci80_lower_revenue":   round(fc_rev - 1.28 * s_rv),
            "ci80_upper_revenue":   round(fc_rev + 1.28 * s_rv),
            "ci95_lower_revenue":   round(fc_rev - 1.96 * s_rv),
            "ci95_upper_revenue":   round(fc_rev + 1.96 * s_rv),
            "model_used": False,
        })
    return data


# ── LightGBM-backed forecast ───────────────────────────────────────────────

def _forecast_practice_ml(practice: dict, months: list, payload: dict) -> list:
    """
    Recursive multi-step forecast using trained LightGBM models.
    - payload['model']      → mean prediction model
    - payload['q10_model']  → 10th-percentile model (CI lower)
    - payload['q90_model']  → 90th-percentile model (CI upper)
    - payload['std_resid']  → fallback std of training residuals

    For each future step the predicted bookings/revenue are appended to the
    lag buffer so that lag features remain valid for subsequent steps.
    """
    model   = payload["model"]
    q10     = payload.get("q10_model")
    q90     = payload.get("q90_model")
    std_r   = float(payload.get("std_resid", 5000))

    # Initialise lag buffers from completed history + current-month estimate
    hist = practice["historical_months"]
    lag_bk  = [m["bookings"] for m in hist]
    lag_rv  = [m["revenue"]  for m in hist]
    lag_nhs = [m["nhs_mix"]  for m in hist]

    # Include current month's best estimate to anchor the first lag
    if practice.get("forecast_month_total", 0) > 0:
        lag_bk.append(practice["forecast_month_total"])
        lag_rv.append(practice["forecast_month_revenue"])
        lag_nhs.append(practice["current_nhs_mix"])

    data = []
    for fm in months:
        price_mult = _monthly_price_multiplier(3, 2026, fm["month"], fm["year"],
                                               practice["nhs_mix"])

        feats = build_inference_features(
            practice, fm["month"], fm["year"], lag_bk, lag_rv, lag_nhs
        )
        X = np.array([feats])

        # Mean prediction (model predicts in "base-year" £; scale for price drift)
        fc_rev = float(model.predict(X)[0]) * price_mult
        fc_rev = max(fc_rev, 0.0)

        # Quantile CI
        if q10 is not None and q90 is not None:
            ci_lo = float(q10.predict(X)[0]) * price_mult
            ci_hi = float(q90.predict(X)[0]) * price_mult
        else:
            ci_lo = fc_rev - 1.28 * std_r * price_mult
            ci_hi = fc_rev + 1.28 * std_r * price_mult

        blended  = practice["blended_value"] * price_mult
        fc_bk    = round(fc_rev / blended) if blended > 0 else round(fc_rev / 80)
        aop_bk   = practice["aop_monthly_bookings"] * SEASONALITY[fm["month"]] / SEASONALITY[3] * 1.03
        aop_rv   = practice["aop_monthly_revenue"]  * SEASONALITY[fm["month"]] / SEASONALITY[3] * 1.03 * price_mult

        data.append({
            "month": fm["month"], "year": fm["year"], "label": fm["label"],
            "forecast_bookings":   fc_bk,
            "forecast_revenue":    round(fc_rev),
            "aop_bookings":        round(aop_bk),
            "aop_revenue":         round(aop_rv),
            "ci80_lower_bookings": max(0, round(fc_bk * 0.90)),
            "ci80_upper_bookings": round(fc_bk * 1.10),
            "ci80_lower_revenue":  round(ci_lo),
            "ci80_upper_revenue":  round(ci_hi),
            "ci95_lower_revenue":  round(fc_rev - 1.96 * std_r * price_mult),
            "ci95_upper_revenue":  round(fc_rev + 1.96 * std_r * price_mult),
            "model_used": True,
        })

        # Extend lag buffer with this prediction for the next step
        lag_bk.append(fc_bk)
        lag_rv.append(fc_rev)
        lag_nhs.append(practice["nhs_mix"])

    return data


# ── Public API ─────────────────────────────────────────────────────────────

def forecast_practice(practice: dict, horizon_months: int = 12) -> dict:
    """
    Generate a forward forecast for a single practice.
    Tries the trained LightGBM model first; falls back to the statistical method.
    Returns a dict with keys:
        - 'monthly'    : list of per-month dicts
        - 'cumulative' : dict with 3m/6m/12m totals
        - 'model_used' : bool
    """
    months  = FORECAST_MONTHS[:horizon_months]
    payload = _load_model()

    if payload is not None:
        monthly = _forecast_practice_ml(practice, months, payload)
        model_used = True
    else:
        monthly = _forecast_practice_statistical(practice, months)
        model_used = False

    # Cumulative summaries (always 3m / 6m / 12m regardless of horizon)
    def _cum(n):
        rev = sum(m["forecast_revenue"] for m in monthly[:n])
        aop = sum(m["aop_revenue"]       for m in monthly[:n])
        return {
            f"{n}m_revenue":  rev,
            f"{n}m_aop":      aop,
            f"{n}m_gap":      rev - aop,
            f"{n}m_delivery": round(rev / aop, 4) if aop else 0,
        }

    cumulative = {}
    for n in (3, 6, 12):
        cumulative.update(_cum(min(n, horizon_months)))

    return {
        "monthly":    monthly,
        "cumulative": cumulative,
        "model_used": model_used,
    }


def forecast_area(area: dict, horizon_months: int = 12) -> dict:
    """Aggregate practice forecasts to area level."""
    pf_list = [forecast_practice(p, horizon_months) for p in area["practices"]]
    months  = FORECAST_MONTHS[:horizon_months]
    combined = []
    for i, fm in enumerate(months):
        fc_bk  = sum(pf["monthly"][i]["forecast_bookings"]  for pf in pf_list)
        fc_rv  = sum(pf["monthly"][i]["forecast_revenue"]   for pf in pf_list)
        aop_rv = sum(pf["monthly"][i]["aop_revenue"]        for pf in pf_list)
        ci_lo  = sum(pf["monthly"][i]["ci80_lower_revenue"] for pf in pf_list)
        ci_hi  = sum(pf["monthly"][i]["ci80_upper_revenue"] for pf in pf_list)
        combined.append({
            "month": fm["month"], "year": fm["year"], "label": fm["label"],
            "forecast_bookings":  fc_bk,
            "forecast_revenue":   fc_rv,
            "aop_revenue":        aop_rv,
            "ci80_lower_revenue": ci_lo,
            "ci80_upper_revenue": ci_hi,
        })
    return {"monthly": combined}


def forecast_national(areas: list, horizon_months: int = 12) -> dict:
    """Aggregate area forecasts to national level."""
    af_list = [forecast_area(a, horizon_months) for a in areas]
    months  = FORECAST_MONTHS[:horizon_months]
    combined = []
    for i, fm in enumerate(months):
        fc_bk  = sum(af["monthly"][i]["forecast_bookings"]  for af in af_list)
        fc_rv  = sum(af["monthly"][i]["forecast_revenue"]   for af in af_list)
        aop_rv = sum(af["monthly"][i]["aop_revenue"]        for af in af_list)
        ci_lo  = sum(af["monthly"][i]["ci80_lower_revenue"] for af in af_list)
        ci_hi  = sum(af["monthly"][i]["ci80_upper_revenue"] for af in af_list)
        combined.append({
            "month": fm["month"], "year": fm["year"], "label": fm["label"],
            "forecast_bookings":  fc_bk,
            "forecast_revenue":   fc_rv,
            "aop_revenue":        aop_rv,
            "ci80_lower_revenue": ci_lo,
            "ci80_upper_revenue": ci_hi,
            "delivery_rate":      round(fc_rv / aop_rv, 4) if aop_rv else 0,
        })
    return {"monthly": combined}


def build_booking_curve_chart_data(practice: dict) -> dict:
    """Day-by-day booking curve chart data for the practice detail page."""
    days          = list(range(1, 32))
    curve         = practice["booking_curve"]
    aop           = practice["aop_monthly_bookings"]
    hist_std_pct  = 0.06

    expected = [round(aop * curve[d]) for d in days]
    ci_lower = [round(aop * curve[d] * (1 - 1.96 * hist_std_pct)) for d in days]
    ci_upper = [round(aop * curve[d] * (1 + 1.96 * hist_std_pct)) for d in days]

    actual = []
    for d in days:
        if d <= 25:
            actual.append(round(
                practice["current_month_bookings"] * (curve[d] / curve[25])
                if curve[25] > 0 else 0
            ))
        else:
            actual.append(round(practice["forecast_month_total"] * curve[d]))

    return {
        "days":      days,
        "expected":  expected,
        "actual":    actual,
        "ci_lower":  ci_lower,
        "ci_upper":  ci_upper,
        "today_day": 25,
    }

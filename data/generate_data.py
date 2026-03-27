"""
Export synthetic data from data_generator.py to CSV files.

Run this script from the project root to populate the data/ folder:
    python data/generate_data.py

When you have real data, replace the CSV files with your actual exports and
update app.py to load from CSV instead of calling generate_all_data().
"""

import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_generator import generate_all_data

DATA = generate_all_data()
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def write_csv(filename: str, rows: list, fieldnames: list) -> None:
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ {filename}  ({len(rows)} rows)")


print("Exporting synthetic dataset to data/ …")

# ── practices.csv ──────────────────────────────────────────────────────────
practice_fields = [
    "id", "name", "location", "area_id", "area_name", "region",
    "nhs_mix", "private_mix", "avg_nhs_value", "avg_private_value",
    "blended_value", "monthly_capacity", "target_utilization",
    "booking_profile", "network_program",
    "aop_monthly_bookings", "aop_monthly_revenue", "aop_annual_revenue",
]
write_csv("practices.csv", DATA["practices"], practice_fields)

# ── bookings_historical.csv ────────────────────────────────────────────────
hist_rows = []
for p in DATA["practices"]:
    for m in p["historical_months"]:
        hist_rows.append({
            "practice_id": p["id"],
            "practice_name": p["name"],
            "area_id": p["area_id"],
            "year": m["year"],
            "month": m["month"],
            "month_label": m["label"],
            "bookings": m["bookings"],
            "nhs_bookings": m["nhs_bookings"],
            "private_bookings": m["private_bookings"],
            "nhs_mix": m["nhs_mix"],
            "revenue": m["revenue"],
            "aop_bookings": m["aop_bookings"],
            "aop_revenue": m["aop_revenue"],
        })
write_csv(
    "bookings_historical.csv",
    hist_rows,
    ["practice_id", "practice_name", "area_id", "year", "month", "month_label",
     "bookings", "nhs_bookings", "private_bookings", "nhs_mix",
     "revenue", "aop_bookings", "aop_revenue"],
)

# ── bookings_current_month.csv ─────────────────────────────────────────────
current_fields = [
    "practice_id", "practice_name", "area_id",
    "year", "month", "day_of_month",
    "current_month_bookings", "current_nhs_bookings", "current_private_bookings",
    "current_nhs_mix", "expected_bookings_by_now", "booking_rate",
    "forecast_month_total", "forecast_month_revenue",
    "aop_monthly_bookings", "aop_monthly_revenue",
    "aop_gap_bookings", "aop_gap_revenue",
    "ci_lower", "ci_upper", "within_ci",
    "whitespace", "traffic_light",
]
current_rows = [{
    **{f: p[f] for f in current_fields if f in p},
    "year": 2026, "month": 3, "day_of_month": 25,
} for p in DATA["practices"]]
write_csv("bookings_current_month.csv", current_rows, current_fields)

# ── aop_targets.csv ────────────────────────────────────────────────────────
from data_generator import HIST_MONTHS, FORECAST_MONTHS, SEASONALITY

aop_rows = []
all_months = HIST_MONTHS + [{"month": 3, "year": 2026, "label": "Mar 26"}] + FORECAST_MONTHS
for p in DATA["practices"]:
    for m in all_months:
        season = SEASONALITY[m["month"]]
        aop_rows.append({
            "practice_id": p["id"],
            "practice_name": p["name"],
            "area_id": p["area_id"],
            "year": m["year"],
            "month": m["month"],
            "month_label": m["label"],
            "aop_bookings": round(p["aop_monthly_bookings"] * season / SEASONALITY[3]),
            "aop_revenue": round(p["aop_monthly_revenue"] * season / SEASONALITY[3]),
        })
write_csv(
    "aop_targets.csv",
    aop_rows,
    ["practice_id", "practice_name", "area_id",
     "year", "month", "month_label", "aop_bookings", "aop_revenue"],
)

print("\nDone. 4 files written to data/")
print("Replace these files with your real data exports, keeping the same column names.")

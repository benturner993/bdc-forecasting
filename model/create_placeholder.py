"""
Creates a placeholder model.pkl file in the model/ directory.

Run from the project root:
    python model/create_placeholder.py

This produces a minimal, valid .pkl file that the application can load.
Replace it with a trained model by running train_model.py after you have real data.
"""

import pickle
import os
import json
from datetime import date

PLACEHOLDER = {
    "model_type": "placeholder",
    "description": (
        "This is a placeholder model. Train and replace using model/train_model.py "
        "once real booking and revenue data is available in the data/ folder."
    ),
    "version": "0.0.1",
    "created": str(date.today()),
    "features": [
        "nhs_mix",
        "private_mix",
        "booking_rate_lag1",
        "booking_rate_lag3",
        "historical_avg_bookings",
        "historical_std_bookings",
        "capacity_utilization",
        "seasonality_factor",
        "network_program",
        "booking_profile_encoded",
        "ytd_delivery_lag1",
        "revenue_per_booking_lag1",
    ],
    "target": "monthly_revenue",
    "performance": {
        "note": "No performance metrics — placeholder only",
        "rmse": None,
        "mae": None,
        "r2": None,
    },
    "predict": None,  # replace with trained model
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")
with open(out_path, "wb") as f:
    pickle.dump(PLACEHOLDER, f)

print(f"Placeholder model written to: {out_path}")
print("Replace with a trained model by running: python model/train_model.py")

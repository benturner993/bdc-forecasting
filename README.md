# Bupa Dental Care — Operational Forecasting Tool

A Flask web application providing operational visibility over bookings, expected revenue,
and AOP performance for Bupa Dental Care. Covers **380 practices** across **25 areas** in the UK.

> **Note:** This application currently uses **synthetic data** generated with a fixed random seed.
> Replace the files in `data/` with real exports and retrain the model in `model/` before production use.

---

## What It Does

The tool answers eight core operational questions:

1. What appointments are booked over the coming weeks/months?
2. How many patients and appointments are currently in the diary?
3. What is the expected revenue for the current and future months?
4. How are practices and areas tracking vs AOP (bookings and revenue)?
5. How many appointments should be booked at this point in the month (booking curve benchmark)?
6. Is performance within an acceptable range? (95% confidence intervals)
7. What does the next 3–12 months look like from a revenue forecasting perspective?
8. What actions should practices take? (Demand / Supply / Mix root-cause analysis)

---

## Pages

| Page | URL | Purpose |
|---|---|---|
| **Home** | `/` | Landing hub with key stats and quick navigation |
| **Headlines** | `/headlines` | National KPIs, traffic lights, area performance chart, booking rate distribution |
| **Performers** | `/performers` | Top and bottom practice rankings; configurable metric and N |
| **Areas** | `/areas` | All 25 areas sortable table + regional summary |
| **Area Detail** | `/area/<id>` | Individual area drill-down with practice table and 12-month forecast chart |
| **Practices** | `/practices` | Searchable and filterable directory of all 380 practices |
| **Practice Detail** | `/practice/<id>` | Full practice view: booking curve, mix, capacity, explainability, revenue forecast |
| **Forecast** | `/forecast` | 3 / 6 / 12-month revenue forecast at national or area level |

---

## Project Structure

```
bpc-forecasting/
├── app.py                      # Flask routes and filters
├── data_generator.py           # Synthetic data generation (replace with real loader)
├── forecasting.py              # Forecast calculations and confidence intervals
├── requirements.txt
│
├── data/                       # Data files (CSV format)
│   ├── README.md               # Column reference and migration guide
│   ├── practices.csv           # Practice master data (380 rows)
│   ├── bookings_historical.csv # Monthly actuals Apr 25 – Feb 26 (4,180 rows)
│   ├── bookings_current_month.csv  # Current month partial actuals (380 rows)
│   ├── aop_targets.csv         # AOP targets all periods (9,120 rows)
│   └── generate_data.py        # Script to regenerate synthetic CSVs
│
├── model/                      # ML forecasting model
│   ├── README.md               # Model architecture and training guide
│   ├── model.pkl               # Trained model (currently a placeholder)
│   ├── train_model.py          # Full training pipeline (requires scikit-learn)
│   ├── create_placeholder.py   # Creates a placeholder model.pkl
│   └── predictions_schema.csv  # Output column schema
│
├── templates/
│   ├── base.html               # Shared layout (Bupa header, nav, footer)
│   ├── home.html               # Landing page
│   ├── headlines.html          # National KPIs
│   ├── performers.html         # Top/bottom rankings
│   ├── areas_summary.html      # All-areas table
│   ├── practices.html          # Practice directory
│   ├── area.html               # Area detail
│   ├── practice.html           # Practice detail
│   └── forecast.html           # Revenue forecast module
│
└── static/
    ├── bupa.png                # Bupa logo
    └── css/style.css           # Component styles
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

### 3. (Optional) Regenerate synthetic data CSVs

```bash
python data/generate_data.py
```

---

## Replacing Synthetic Data with Real Data

1. **Practices** — Export your practice master list to `data/practices.csv` matching the schema in `data/README.md`.
2. **Historical bookings** — Export monthly actuals (per-practice × per-month) to `data/bookings_historical.csv`.
3. **Current month** — Export live booking counts to `data/bookings_current_month.csv`. This should refresh daily.
4. **AOP targets** — Export your AOP targets to `data/aop_targets.csv`.
5. **Update `app.py`** — Replace the `generate_all_data()` call with a CSV loader. The data structures expected by the templates are documented in `data_generator.py`.

---

## Training the Forecast Model

Once real data is available:

```bash
pip install scikit-learn
python model/train_model.py --data-dir ./data --output-dir ./model
```

See `model/README.md` for full documentation.

---

## Key Metrics Explained

| Metric | Definition |
|---|---|
| **Booking Rate** | `actual bookings ÷ expected bookings` at the current day of month, based on the practice's historical booking curve |
| **Revenue Delivery** | `forecast month-end revenue ÷ AOP monthly revenue target` |
| **YTD Delivery** | `YTD actual revenue ÷ YTD AOP revenue` (Apr–present) |
| **Traffic Light** | Percentile-based: Green = top 25% YTD delivery, Red = bottom 25% |
| **Confidence Interval** | 95% CI for end-of-month bookings based on historical performance variance |
| **Whitespace** | Fraction of monthly appointment capacity projected to be unused |
| **Revenue per Appointment** | Forecast monthly revenue ÷ forecast total appointments (indicates NHS/private mix quality) |

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, Flask 3.x |
| Data | NumPy, SciPy, Pandas |
| ML model | scikit-learn (GradientBoostingRegressor) |
| Frontend | Bootstrap 5.3, Chart.js 4.4, Font Awesome 6.5 |
| Fonts | Montserrat (Google Fonts) |

---

## Development Notes

- Data is generated at app startup with a fixed random seed (`SEED = 42`) — output is deterministic.
- All monetary values are in GBP (£).
- The current financial year is assumed to be April 2025 – March 2026.
- The forecast module projects into FY2026/27 (April 2026 – March 2027).
- Price increase assumptions: NHS +2.5%/yr, Private +5.0%/yr.

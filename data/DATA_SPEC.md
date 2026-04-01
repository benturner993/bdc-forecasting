# BPC Forecasting - Input Data Specification

## Purpose

This document defines the data contract for the four input datasets needed to run the BPC Forecasting app with real data.

Audience:
- Data Engineering
- BI/Data Platform
- Analytics Engineering

Scope:
- File-level metadata
- Column-level schema
- Keys and relationships
- Validation and quality rules
- Delivery expectations

## 1) Delivery contract (high level)

The app currently expects 4 CSV files in `data/`:

1. `practices.csv`
2. `bookings_historical.csv`
3. `bookings_current_month.csv`
4. `aop_targets.csv`

### Required file characteristics

- Format: UTF-8 CSV with header row
- Delimiter: comma
- Decimal separator: `.`
- Date decomposition: `year` and `month` integer columns (no datetime required)
- Currency: GBP (`£`) as numeric values only (no symbol in file)
- Null handling: blank values allowed only where explicitly documented

### ID standards

- `practice_id` / `id`: stable, unique practice key across all files
- `area_id`: stable area key across all files
- Keys must not be recycled across time

### Time standards

- Reporting timezone: Europe/London
- Financial year: April to March
- Historical month labels should follow `Mon YY` pattern (example: `Apr 25`)

## 2) Dataset summary

| Dataset | Grain | Primary key | Typical volume | Refresh cadence |
|---|---|---|---|---|
| `practices.csv` | 1 row per practice | `id` | ~380 rows | Weekly / monthly |
| `bookings_historical.csv` | 1 row per practice per completed month | (`practice_id`, `year`, `month`) | ~4k+ rows | Monthly close |
| `bookings_current_month.csv` | 1 row per practice for current month snapshot | `practice_id` | ~380 rows | Daily (recommended) |
| `aop_targets.csv` | 1 row per practice per month target | (`practice_id`, `year`, `month`) | ~9k+ rows | On plan update (monthly/quarterly) |

## 3) Schema details

## 3.1 `practices.csv`

Purpose:
- Practice master/reference table
- Commercial mix, capacity, and baseline AOP values used by forecasting and diagnostics

Required columns:

| Column | Type | Required | Description | Rules / accepted values |
|---|---|---|---|---|
| `id` | string | Yes | Practice identifier | Unique, non-null (example `P001`) |
| `name` | string | Yes | Practice display name | Non-null |
| `location` | string | Yes | Town or local area | Non-null |
| `area_id` | string | Yes | Area identifier | Must map to valid area |
| `area_name` | string | Yes | Area display name | Non-null |
| `region` | string | Yes | Region display name | Non-null |
| `nhs_mix` | decimal(5,4) | Yes | NHS share of appointments | 0 <= value <= 1 |
| `private_mix` | decimal(5,4) | Yes | Private share of appointments | 0 <= value <= 1 |
| `avg_nhs_value` | decimal(12,2) | Yes | Avg revenue per NHS appointment | > 0 |
| `avg_private_value` | decimal(12,2) | Yes | Avg revenue per private appointment | > 0 |
| `blended_value` | decimal(12,2) | Yes | Weighted avg revenue per appointment | > 0 |
| `monthly_capacity` | int | Yes | Total monthly slots | > 0 |
| `target_utilization` | decimal(5,4) | Yes | Capacity target | 0 < value <= 1 |
| `booking_profile` | string | Yes | Booking behavior profile | One of: `early`, `mixed`, `late` |
| `network_program` | boolean | Yes | Network programme membership flag | `true/false` |
| `aop_monthly_bookings` | int | Yes | Baseline monthly bookings target | >= 0 |
| `aop_monthly_revenue` | decimal(14,2) | Yes | Baseline monthly revenue target | >= 0 |
| `aop_annual_revenue` | decimal(14,2) | Yes | Annual revenue target | >= 0 |

Quality checks:
- `nhs_mix + private_mix` should equal 1.0 (+/- 0.01 tolerance)
- `id` uniqueness = 100%
- No duplicate (`id`, `area_id`) combinations

## 3.2 `bookings_historical.csv`

Purpose:
- Completed-month actuals used for trend, model features, and diagnostics

Required columns:

| Column | Type | Required | Description | Rules / accepted values |
|---|---|---|---|---|
| `practice_id` | string | Yes | Practice key | Must exist in `practices.id` |
| `practice_name` | string | Yes | Practice display name snapshot | Non-null |
| `area_id` | string | Yes | Area key | Must match practice area mapping |
| `year` | int | Yes | Calendar year | 4-digit integer |
| `month` | int | Yes | Month number | 1-12 |
| `month_label` | string | Yes | Display label | Example `Apr 25` |
| `bookings` | int | Yes | Actual appointments delivered | >= 0 |
| `nhs_bookings` | int | Yes | NHS appointments | >= 0 |
| `private_bookings` | int | Yes | Private appointments | >= 0 |
| `nhs_mix` | decimal(5,4) | Yes | NHS share for month | 0 <= value <= 1 |
| `revenue` | decimal(14,2) | Yes | Actual monthly revenue | >= 0 |
| `aop_bookings` | int | Yes | AOP monthly bookings target | >= 0 |
| `aop_revenue` | decimal(14,2) | Yes | AOP monthly revenue target | >= 0 |

Quality checks:
- Unique key: (`practice_id`, `year`, `month`)
- `nhs_bookings + private_bookings = bookings`
- No future months
- At least 11 complete months of history per practice (recommended minimum for current logic)

## 3.3 `bookings_current_month.csv`

Purpose:
- Daily in-month performance snapshot per practice
- Supports booking curve tracking, current month forecast, and RAG status

Required columns:

| Column | Type | Required | Description | Rules / accepted values |
|---|---|---|---|---|
| `practice_id` | string | Yes | Practice key | Must exist in `practices.id` |
| `practice_name` | string | Yes | Practice display name snapshot | Non-null |
| `area_id` | string | Yes | Area key | Must match practice area mapping |
| `year` | int | Yes | Current month year | 4-digit integer |
| `month` | int | Yes | Current month number | 1-12 |
| `day_of_month` | int | Yes | Snapshot day | 1-31 |
| `current_month_bookings` | int | Yes | Actual bookings to date | >= 0 |
| `current_nhs_bookings` | int | Yes | NHS bookings to date | >= 0 |
| `current_private_bookings` | int | Yes | Private bookings to date | >= 0 |
| `current_nhs_mix` | decimal(5,4) | Yes | NHS share in current month | 0 <= value <= 1 |
| `expected_bookings_by_now` | decimal(12,2) | Yes | Expected bookings at current day | >= 0 |
| `booking_rate` | decimal(7,4) | Yes | `current_month_bookings / expected_bookings_by_now` | >= 0 |
| `forecast_month_total` | int | Yes | Projected full-month bookings | >= 0 |
| `forecast_month_revenue` | decimal(14,2) | Yes | Projected full-month revenue | >= 0 |
| `aop_monthly_bookings` | int | Yes | AOP bookings target for current month | >= 0 |
| `aop_monthly_revenue` | decimal(14,2) | Yes | AOP revenue target for current month | >= 0 |
| `aop_gap_bookings` | int | Yes | `forecast_month_total - aop_monthly_bookings` | Integer |
| `aop_gap_revenue` | decimal(14,2) | Yes | `forecast_month_revenue - aop_monthly_revenue` | Numeric |
| `ci_lower` | int | Yes | 95% lower bound for month-end bookings | >= 0 |
| `ci_upper` | int | Yes | 95% upper bound for month-end bookings | >= `ci_lower` |
| `within_ci` | boolean | Yes | Whether AOP bookings target is within CI | `true/false` |
| `whitespace` | decimal(6,4) | Yes | Unused capacity proportion forecast | 0 <= value <= 1 |
| `traffic_light` | string | Yes | Current RAG status | One of: `green`, `amber`, `red` |

Quality checks:
- Unique key: `practice_id`
- `current_nhs_bookings + current_private_bookings = current_month_bookings`
- `0 <= whitespace <= 1`
- `ci_lower <= ci_upper`

## 3.4 `aop_targets.csv`

Purpose:
- Monthly plan baseline used in historical comparison and forward views

Required columns:

| Column | Type | Required | Description | Rules / accepted values |
|---|---|---|---|---|
| `practice_id` | string | Yes | Practice key | Must exist in `practices.id` |
| `practice_name` | string | Yes | Practice display name snapshot | Non-null |
| `area_id` | string | Yes | Area key | Must match practice area mapping |
| `year` | int | Yes | Target year | 4-digit integer |
| `month` | int | Yes | Target month | 1-12 |
| `month_label` | string | Yes | Display label | Example `Apr 26` |
| `aop_bookings` | int | Yes | AOP bookings target for month | >= 0 |
| `aop_revenue` | decimal(14,2) | Yes | AOP revenue target for month | >= 0 |

Quality checks:
- Unique key: (`practice_id`, `year`, `month`)
- Coverage must include:
  - all historical comparison months
  - current month
  - all forward forecast months required by the app

## 3.5 Example records (format reference)

Use these as formatting examples for data delivery. Values are illustrative.

### Example: `practices.csv`

```csv
id,name,location,area_id,area_name,region,nhs_mix,private_mix,avg_nhs_value,avg_private_value,blended_value,monthly_capacity,target_utilization,booking_profile,network_program,aop_monthly_bookings,aop_monthly_revenue,aop_annual_revenue
P001,Bupa Dental Care Aldgate,Aldgate,A01,London East,London,0.7200,0.2800,41.71,203.27,86.99,702,0.8650,early,true,606,52715.00,632580.00
P146,Bupa Dental Care York,York,A16,Yorkshire North,Yorkshire,0.5800,0.4200,47.50,186.40,106.72,768,0.8900,mixed,false,684,72996.48,875957.76
```

### Example: `bookings_historical.csv`

```csv
practice_id,practice_name,area_id,year,month,month_label,bookings,nhs_bookings,private_bookings,nhs_mix,revenue,aop_bookings,aop_revenue
P001,Bupa Dental Care Aldgate,A01,2025,4,Apr 25,571,414,157,0.7250,48762.00,606,52715.00
P001,Bupa Dental Care Aldgate,A01,2025,5,May 25,594,425,169,0.7155,51098.00,606,52715.00
```

### Example: `bookings_current_month.csv`

```csv
practice_id,practice_name,area_id,year,month,day_of_month,current_month_bookings,current_nhs_bookings,current_private_bookings,current_nhs_mix,expected_bookings_by_now,booking_rate,forecast_month_total,forecast_month_revenue,aop_monthly_bookings,aop_monthly_revenue,aop_gap_bookings,aop_gap_revenue,ci_lower,ci_upper,within_ci,whitespace,traffic_light
P001,Bupa Dental Care Aldgate,A01,2026,3,25,486,349,137,0.7181,540.20,0.8997,598,52044.00,606,52715.00,-8,-671.00,552,644,true,0.1480,amber
P146,Bupa Dental Care York,A16,2026,3,25,612,349,263,0.5703,589.40,1.0383,735,78439.00,684,72996.48,51,5442.52,689,781,true,0.0710,green
```

### Example: `aop_targets.csv`

```csv
practice_id,practice_name,area_id,year,month,month_label,aop_bookings,aop_revenue
P001,Bupa Dental Care Aldgate,A01,2025,4,Apr 25,606,52715.00
P001,Bupa Dental Care Aldgate,A01,2026,4,Apr 26,624,54296.45
```

Notes:
- Boolean values should be `true` / `false`.
- Keep numeric columns unformatted (no thousands separators, no currency symbol).
- Month labels should remain consistent with `year` and `month`.

## 4) Relationships and joins

Primary join paths:
- `practices.id = bookings_historical.practice_id`
- `practices.id = bookings_current_month.practice_id`
- `practices.id = aop_targets.practice_id`

Recommended referential integrity checks:
- 100% of fact records resolve to a valid `practices.id`
- `area_id` in fact files matches the `area_id` from `practices` for the same practice

## 5) Derived metric definitions (for consistent engineering logic)

These definitions should be treated as canonical if computed in ETL:

- `booking_rate = current_month_bookings / expected_bookings_by_now`
- `aop_gap_bookings = forecast_month_total - aop_monthly_bookings`
- `aop_gap_revenue = forecast_month_revenue - aop_monthly_revenue`
- `within_ci = (aop_monthly_bookings >= ci_lower and aop_monthly_bookings <= ci_upper)`
- `traffic_light` (practice): percentile-based using YTD delivery
  - green: top quartile
  - red: bottom quartile
  - amber: middle group

## 6) Data quality SLAs (recommended)

- Completeness:
  - 100% non-null on all required fields
- Freshness:
  - `bookings_current_month.csv` delivered daily by 07:00 Europe/London
  - all other files by agreed monthly close window
- Validity:
  - 0 schema-breaking records
  - 0 duplicate primary keys per dataset
- Referential integrity:
  - 100% successful joins to `practices.id`

## 7) File naming and handoff

Expected names (exact):

- `practices.csv`
- `bookings_historical.csv`
- `bookings_current_month.csv`
- `aop_targets.csv`

Delivery location for current app:
- Project path: `data/`

## 8) Implementation checklist for Data Engineering

Before first production handoff:

1. Confirm all four files are produced with exact names and schema.
2. Validate primary keys and referential integrity.
3. Run metric reconciliation checks (`booking_rate`, AOP gaps, CI bounds).
4. Confirm row counts are in expected ranges.
5. Provide sample extracts for UAT sign-off.
6. Set up scheduled pipeline and freshness alerts.
7. Hand over data dictionary and lineage notes.

---

For current synthetic export reference, see:
- `data/generate_data.py`
- `data/README.md`

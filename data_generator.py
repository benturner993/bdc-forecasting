"""
Synthetic data generator for Bupa Dental Care Forecasting Application.
Generates 380 practices across 25 UK areas with realistic booking,
revenue, and performance data.
"""

import numpy as np
from scipy import stats
import random
from datetime import date

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

TODAY = date(2026, 3, 25)
CURRENT_DAY = 25  # Day 25 of March 2026
FINANCIAL_YEAR_START = date(2025, 4, 1)  # FY2025/26

AREAS = [
    {"id": "A01", "name": "London East",           "region": "London",          "connected_care": True},
    {"id": "A02", "name": "London West",           "region": "London",          "connected_care": True},
    {"id": "A03", "name": "London North",          "region": "London",          "connected_care": True},
    {"id": "A04", "name": "London South",          "region": "London",          "connected_care": False},
    {"id": "A05", "name": "London Central",        "region": "London",          "connected_care": True},
    {"id": "A06", "name": "South East",            "region": "South East",      "connected_care": False},
    {"id": "A07", "name": "Kent & Sussex",         "region": "South East",      "connected_care": False},
    {"id": "A08", "name": "South West",            "region": "South West",      "connected_care": False},
    {"id": "A09", "name": "Bristol & Bath",        "region": "South West",      "connected_care": False},
    {"id": "A10", "name": "Midlands East",         "region": "Midlands",        "connected_care": False},
    {"id": "A11", "name": "Midlands West",         "region": "Midlands",        "connected_care": False},
    {"id": "A12", "name": "Midlands Central",      "region": "Midlands",        "connected_care": True},
    {"id": "A13", "name": "North West",            "region": "North West",      "connected_care": False},
    {"id": "A14", "name": "Manchester & Cheshire", "region": "North West",      "connected_care": True},
    {"id": "A15", "name": "North East",            "region": "North East",      "connected_care": False},
    {"id": "A16", "name": "Yorkshire North",       "region": "Yorkshire",       "connected_care": False},
    {"id": "A17", "name": "Yorkshire South",       "region": "Yorkshire",       "connected_care": False},
    {"id": "A18", "name": "East Anglia",           "region": "East",            "connected_care": False},
    {"id": "A19", "name": "East Midlands",         "region": "East",            "connected_care": False},
    {"id": "A20", "name": "Scotland North",        "region": "Scotland",        "connected_care": False},
    {"id": "A21", "name": "Scotland Central",      "region": "Scotland",        "connected_care": False},
    {"id": "A22", "name": "Wales North",           "region": "Wales",           "connected_care": False},
    {"id": "A23", "name": "Wales South",           "region": "Wales",           "connected_care": False},
    {"id": "A24", "name": "Northern Ireland",      "region": "N. Ireland",      "connected_care": False},
    {"id": "A25", "name": "Humber & Lincolnshire", "region": "East",            "connected_care": False},
]

# Area profiles: NHS mix tendency, private value multiplier, capacity range
AREA_PROFILES = {
    "A01": {"nhs_base": 0.68, "pv_mult": 0.90, "cap": (600, 900)},
    "A02": {"nhs_base": 0.32, "pv_mult": 1.35, "cap": (700, 1000)},
    "A03": {"nhs_base": 0.55, "pv_mult": 1.10, "cap": (650, 950)},
    "A04": {"nhs_base": 0.60, "pv_mult": 1.00, "cap": (600, 850)},
    "A05": {"nhs_base": 0.38, "pv_mult": 1.40, "cap": (700, 1000)},
    "A06": {"nhs_base": 0.45, "pv_mult": 1.20, "cap": (650, 900)},
    "A07": {"nhs_base": 0.50, "pv_mult": 1.10, "cap": (600, 850)},
    "A08": {"nhs_base": 0.52, "pv_mult": 1.00, "cap": (580, 830)},
    "A09": {"nhs_base": 0.46, "pv_mult": 1.12, "cap": (640, 900)},
    "A10": {"nhs_base": 0.65, "pv_mult": 0.90, "cap": (550, 800)},
    "A11": {"nhs_base": 0.62, "pv_mult": 0.92, "cap": (560, 810)},
    "A12": {"nhs_base": 0.60, "pv_mult": 0.95, "cap": (580, 830)},
    "A13": {"nhs_base": 0.70, "pv_mult": 0.85, "cap": (540, 790)},
    "A14": {"nhs_base": 0.64, "pv_mult": 0.90, "cap": (560, 820)},
    "A15": {"nhs_base": 0.75, "pv_mult": 0.80, "cap": (500, 740)},
    "A16": {"nhs_base": 0.65, "pv_mult": 0.85, "cap": (530, 780)},
    "A17": {"nhs_base": 0.66, "pv_mult": 0.85, "cap": (530, 780)},
    "A18": {"nhs_base": 0.50, "pv_mult": 1.00, "cap": (580, 830)},
    "A19": {"nhs_base": 0.60, "pv_mult": 0.92, "cap": (560, 810)},
    "A20": {"nhs_base": 0.65, "pv_mult": 0.85, "cap": (480, 720)},
    "A21": {"nhs_base": 0.60, "pv_mult": 0.90, "cap": (520, 780)},
    "A22": {"nhs_base": 0.72, "pv_mult": 0.80, "cap": (460, 700)},
    "A23": {"nhs_base": 0.68, "pv_mult": 0.83, "cap": (480, 720)},
    "A24": {"nhs_base": 0.62, "pv_mult": 0.85, "cap": (490, 730)},
    "A25": {"nhs_base": 0.60, "pv_mult": 0.90, "cap": (530, 780)},
}

# 16 locations per area (380 practices distributed: 5 London areas get 16 each, rest get 15)
LOCATIONS = {
    "A01": ["Aldgate", "Bethnal Green", "Bow", "Canary Wharf", "Dalston", "Hackney",
             "Homerton", "Leyton", "Limehouse", "Mile End", "Poplar", "Shoreditch",
             "Stepney", "Stratford", "Walthamstow", "Whitechapel"],
    "A02": ["Acton", "Bayswater", "Chiswick", "Ealing", "Fulham", "Hammersmith",
             "Holland Park", "Kensington", "Ladbroke Grove", "Maida Vale", "Notting Hill",
             "Paddington", "Shepherd's Bush", "Southall", "Turnham Green", "West Ealing"],
    "A03": ["Archway", "Camden", "Chalk Farm", "Cricklewood", "East Finchley",
             "Finsbury Park", "Golders Green", "Hampstead", "Hendon", "Highbury",
             "Highgate", "Holloway", "Islington", "Kentish Town", "Stoke Newington", "Tufnell Park"],
    "A04": ["Balham", "Brixton", "Camberwell", "Clapham", "Crystal Palace",
             "Dulwich", "Elephant & Castle", "Kennington", "Norwood", "Peckham",
             "Stockwell", "Streatham", "Thornton Heath", "Tooting", "Tulse Hill", "West Norwood"],
    "A05": ["Aldwych", "Bank", "Barbican", "Blackfriars", "Clerkenwell",
             "Covent Garden", "Holborn", "Liverpool Street", "Mayfair", "Moorgate",
             "Piccadilly", "Soho", "St James's", "Temple", "Victoria", "Westminster"],
    "A06": ["Brighton", "Burgess Hill", "Crawley", "Eastbourne", "Epsom",
             "Guildford", "Hastings", "Horsham", "Hove", "Lewes",
             "Redhill", "Reigate", "Sutton", "Woking", "Worthing"],
    "A07": ["Ashford", "Canterbury", "Deal", "Dover", "Faversham",
             "Folkestone", "Gillingham", "Herne Bay", "Maidstone", "Margate",
             "Rochester", "Sevenoaks", "Sittingbourne", "Tonbridge", "Tunbridge Wells"],
    "A08": ["Barnstaple", "Bideford", "Bridgwater", "Exeter", "Ilfracombe",
             "Minehead", "Okehampton", "Plymouth", "Taunton", "Tiverton",
             "Torquay", "Truro", "Weston-super-Mare", "Yeovil", "Launceston"],
    "A09": ["Bath", "Bedminster", "Brislington", "Clifton", "Filton",
             "Hanham", "Horfield", "Keynsham", "Kingswood", "Mangotsfield",
             "Nailsea", "Redland", "Southmead", "Thornbury", "Westbury-on-Trym"],
    "A10": ["Corby", "Derby", "Hinckley", "Kettering", "Leicester",
             "Loughborough", "Mansfield", "Melton Mowbray", "Newark", "Northampton",
             "Nottingham", "Oakham", "Peterborough", "Rugby", "Wellingborough"],
    "A11": ["Aldridge", "Bilston", "Brownhills", "Cannock", "Dudley",
             "Lichfield", "Oldbury", "Smethwick", "Stafford", "Stourbridge",
             "Sutton Coldfield", "Tamworth", "Walsall", "West Bromwich", "Wolverhampton"],
    "A12": ["Alcester", "Bewdley", "Bromsgrove", "Coventry", "Evesham",
             "Kenilworth", "Kidderminster", "Leamington Spa", "Nuneaton", "Pershore",
             "Redditch", "Stratford-upon-Avon", "Stourport", "Warwick", "Worcester"],
    "A13": ["Birkenhead", "Bootle", "Crosby", "Formby", "Huyton",
             "Leigh", "Liverpool", "Prescot", "Runcorn", "St Helens",
             "Skelmersdale", "Southport", "Wallasey", "Warrington", "Widnes"],
    "A14": ["Altrincham", "Cheadle", "Chester", "Crewe", "Didsbury",
             "Knutsford", "Macclesfield", "Manchester", "Nantwich", "Northwich",
             "Sale", "Salford", "Stockport", "Stretford", "Wilmslow"],
    "A15": ["Birtley", "Chester-le-Street", "Consett", "Darlington", "Durham",
             "Gateshead", "Hartlepool", "Houghton-le-Spring", "Jarrow", "Middlesbrough",
             "Newcastle", "Peterlee", "South Shields", "Sunderland", "Washington"],
    "A16": ["Filey", "Harrogate", "Helmsley", "Malton", "Northallerton",
             "Pickering", "Ripon", "Scarborough", "Selby", "Skipton",
             "Tadcaster", "Thirsk", "Whitby", "York", "Easingwold"],
    "A17": ["Barnsley", "Conisbrough", "Doncaster", "Hoyland", "Mexborough",
             "Penistone", "Rawmarsh", "Rotherham", "Sheffield Central", "Sheffield East",
             "Sheffield North", "Sheffield West", "Swinton", "Wath-upon-Dearne", "Worksop"],
    "A18": ["Bury St Edmunds", "Cambridge", "Dereham", "Ely", "Fakenham",
             "Great Yarmouth", "Huntingdon", "Ipswich", "Kings Lynn", "Lowestoft",
             "Newmarket", "Norwich", "Peterborough", "Thetford", "Wisbech"],
    "A19": ["Arnold", "Beeston", "Bingham", "Clifton", "Gedling",
             "Hucknall", "Ilkeston", "Long Eaton", "Mapperley", "Radford",
             "Sherwood", "Stapleford", "West Bridgford", "Kimberley", "Bulwell"],
    "A20": ["Aberdeen", "Buckie", "Elgin", "Fraserburgh", "Huntly",
             "Inverness", "Keith", "Nairn", "Peterhead", "Stonehaven",
             "Turriff", "Fort William", "Aviemore", "Dingwall", "Forres"],
    "A21": ["Ayr", "Clydebank", "Coatbridge", "Dunfermline", "Edinburgh",
             "Falkirk", "Glenrothes", "Glasgow", "Hamilton", "Kirkcaldy",
             "Livingston", "Motherwell", "Paisley", "Perth", "Stirling"],
    "A22": ["Bangor", "Caernarfon", "Colwyn Bay", "Conwy", "Denbigh",
             "Flint", "Holyhead", "Llandudno", "Llangefni", "Mold",
             "Pwllheli", "Rhyl", "Ruthin", "Wrexham", "Abergele"],
    "A23": ["Aberdare", "Barry", "Bridgend", "Cardiff Central", "Cardiff North",
             "Cwmbran", "Ebbw Vale", "Maesteg", "Merthyr Tydfil", "Neath",
             "Newport", "Pontypridd", "Port Talbot", "Swansea", "Llantrisant"],
    "A24": ["Belfast Central", "Belfast East", "Belfast North", "Belfast South", "Belfast West",
             "Bangor", "Coleraine", "Derry", "Dungannon", "Enniskillen",
             "Lisburn", "Newry", "Newtownabbey", "Newtownards", "Portadown"],
    "A25": ["Beverley", "Boston", "Brigg", "Cleethorpes", "Gainsborough",
             "Goole", "Grimsby", "Hull", "Immingham", "Lincoln",
             "Louth", "Scunthorpe", "Spalding", "Stamford", "Barnetby"],
}

# Monthly seasonality factors for dental bookings (UK)
SEASONALITY = {4: 0.97, 5: 1.02, 6: 0.98, 7: 0.93, 8: 0.86,
               9: 1.08, 10: 1.06, 11: 1.02, 12: 0.80, 1: 1.05, 2: 1.01, 3: 1.02}

# Historical months in current FY (completed months before current)
HIST_MONTHS = [
    {"month": 4,  "year": 2025, "label": "Apr 25"},
    {"month": 5,  "year": 2025, "label": "May 25"},
    {"month": 6,  "year": 2025, "label": "Jun 25"},
    {"month": 7,  "year": 2025, "label": "Jul 25"},
    {"month": 8,  "year": 2025, "label": "Aug 25"},
    {"month": 9,  "year": 2025, "label": "Sep 25"},
    {"month": 10, "year": 2025, "label": "Oct 25"},
    {"month": 11, "year": 2025, "label": "Nov 25"},
    {"month": 12, "year": 2025, "label": "Dec 25"},
    {"month": 1,  "year": 2026, "label": "Jan 26"},
    {"month": 2,  "year": 2026, "label": "Feb 26"},
]

# Forward months for forecasting (next FY)
FORECAST_MONTHS = [
    {"month": 4,  "year": 2026, "label": "Apr 26"},
    {"month": 5,  "year": 2026, "label": "May 26"},
    {"month": 6,  "year": 2026, "label": "Jun 26"},
    {"month": 7,  "year": 2026, "label": "Jul 26"},
    {"month": 8,  "year": 2026, "label": "Aug 26"},
    {"month": 9,  "year": 2026, "label": "Sep 26"},
    {"month": 10, "year": 2026, "label": "Oct 26"},
    {"month": 11, "year": 2026, "label": "Nov 26"},
    {"month": 12, "year": 2026, "label": "Dec 26"},
    {"month": 1,  "year": 2027, "label": "Jan 27"},
    {"month": 2,  "year": 2027, "label": "Feb 27"},
    {"month": 3,  "year": 2027, "label": "Mar 27"},
]


def generate_booking_curve(profile: str) -> list:
    """
    Returns cumulative booking fill-rate by day-of-month (indices 0–31, index 0 unused).
    Represents: "by day X, what % of the month's appointments are in the diary?"
    """
    days = np.arange(1, 32)
    params = {"early": (12, 0.24), "mixed": (16, 0.20), "late": (21, 0.22)}
    mid, steep = params.get(profile, params["mixed"])
    raw = stats.norm.cdf(days, loc=mid, scale=1.0 / steep)
    curve = (raw - raw[0]) / (raw[-1] - raw[0])
    curve = np.clip(curve, 0.0, 1.0)
    return [0.0] + curve.tolist()  # index 0 = 0%, indices 1-31 = days


def _practice_count_for_area(area_id: str) -> int:
    """London areas get 16 practices, all others get 15. Total = 5×16 + 20×15 = 380."""
    london_areas = {"A01", "A02", "A03", "A04", "A05"}
    return 16 if area_id in london_areas else 15


def generate_practice(area: dict, index: int, practice_id: str) -> dict:
    """Generate a single practice with all attributes."""
    profile = AREA_PROFILES[area["id"]]
    locations = LOCATIONS[area["id"]]
    location = locations[index % len(locations)]

    # NHS/Private mix (with per-practice variation)
    nhs_mix = float(np.clip(profile["nhs_base"] + np.random.normal(0, 0.08), 0.15, 0.90))
    private_mix = 1.0 - nhs_mix

    # Average appointment values
    avg_nhs = float(np.random.uniform(30, 46))
    avg_private = float(np.random.uniform(160, 270) * profile["pv_mult"])
    blended_value = nhs_mix * avg_nhs + private_mix * avg_private

    # Capacity and utilisation
    cap_min, cap_max = profile["cap"]
    monthly_capacity = int(np.random.randint(cap_min, cap_max))
    target_util = float(np.random.uniform(0.82, 0.92))

    # AOP targets
    aop_monthly_bookings = int(monthly_capacity * target_util)
    aop_monthly_revenue = int(aop_monthly_bookings * blended_value)

    # Booking profile: ~35% early, 40% mixed, 25% late
    rand_profile = np.random.random()
    if rand_profile < 0.35:
        booking_profile = "early"
    elif rand_profile < 0.75:
        booking_profile = "mixed"
    else:
        booking_profile = "late"

    booking_curve = generate_booking_curve(booking_profile)

    # Current-month performance modifier (realistic spread of outcomes)
    perf_rand = np.random.random()
    if perf_rand < 0.15:
        perf_mult = float(np.random.uniform(0.55, 0.72))   # Red: significantly below
    elif perf_rand < 0.35:
        perf_mult = float(np.random.uniform(0.72, 0.88))   # Amber: slightly below
    elif perf_rand < 0.75:
        perf_mult = float(np.random.uniform(0.88, 1.06))   # Amber/green: on track
    else:
        perf_mult = float(np.random.uniform(1.06, 1.22))   # Green: exceeding

    # NHS mix in current month can drift
    current_nhs_drift = float(np.random.normal(0, 0.04))
    current_nhs_mix = float(np.clip(nhs_mix + current_nhs_drift, 0.10, 0.95))

    # Expected bookings by day 25 of current month
    expected_by_now = aop_monthly_bookings * booking_curve[CURRENT_DAY]
    current_month_bookings = int(max(0, expected_by_now * perf_mult + np.random.normal(0, 5)))
    current_nhs_bookings = int(current_month_bookings * current_nhs_mix)
    current_private_bookings = current_month_bookings - current_nhs_bookings

    # Capacity whitespace (unused slots as % of capacity)
    # Remaining days in month: 6 days left (26-31)
    remaining_fraction = 1.0 - booking_curve[CURRENT_DAY]
    projected_remaining = int(aop_monthly_bookings * remaining_fraction * perf_mult)
    forecast_month_total = current_month_bookings + projected_remaining
    current_revenue = current_month_bookings * (current_nhs_mix * avg_nhs + (1 - current_nhs_mix) * avg_private)
    forecast_month_revenue = forecast_month_total * (current_nhs_mix * avg_nhs + (1 - current_nhs_mix) * avg_private)

    used_capacity = current_month_bookings + projected_remaining
    whitespace = float(max(0, 1.0 - (used_capacity / monthly_capacity)))

    # Generate 11 months of historical data (Apr 25 – Feb 26)
    historical_months = []
    for hm in HIST_MONTHS:
        m = hm["month"]
        season = SEASONALITY[m]
        hist_perf = float(np.random.uniform(0.88, 1.08))
        hist_bookings = int(aop_monthly_bookings * season * hist_perf + np.random.normal(0, 15))
        hist_nhs_mix = float(np.clip(nhs_mix + np.random.normal(0, 0.03), 0.10, 0.95))
        hist_nhs = int(hist_bookings * hist_nhs_mix)
        hist_private = hist_bookings - hist_nhs
        hist_revenue = int(hist_bookings * (hist_nhs_mix * avg_nhs * 0.976 + (1 - hist_nhs_mix) * avg_private * 0.952))
        historical_months.append({
            "month": m, "year": hm["year"], "label": hm["label"],
            "bookings": hist_bookings, "revenue": hist_revenue,
            "nhs_bookings": hist_nhs, "private_bookings": hist_private,
            "nhs_mix": round(hist_nhs_mix, 3),
            "aop_bookings": aop_monthly_bookings,
            "aop_revenue": aop_monthly_revenue,
        })

    # YTD calculations (11 full months + partial March)
    ytd_bookings = sum(m["bookings"] for m in historical_months) + current_month_bookings
    ytd_revenue = sum(m["revenue"] for m in historical_months) + int(current_revenue)
    # AOP YTD: 11 full months + 25/31 of March
    march_aop_fraction = CURRENT_DAY / 31
    ytd_aop_bookings = int(aop_monthly_bookings * (11 + march_aop_fraction))
    ytd_aop_revenue = int(aop_monthly_revenue * (11 + march_aop_fraction))
    ytd_delivery = ytd_revenue / ytd_aop_revenue if ytd_aop_revenue > 0 else 0.0

    # Booking rate: actual bookings this month vs expected by day 25
    booking_rate = current_month_bookings / expected_by_now if expected_by_now > 0 else 0.0

    # Revenue delivery rate for current month (forecast vs AOP)
    revenue_delivery = forecast_month_revenue / aop_monthly_revenue if aop_monthly_revenue > 0 else 0.0

    # 95% confidence interval for end-of-month bookings based on historical variance
    hist_performances = [m["bookings"] / aop_monthly_bookings for m in historical_months]
    hist_std = float(np.std(hist_performances)) * aop_monthly_bookings
    ci_lower = int(max(0, forecast_month_total - 1.96 * hist_std))
    ci_upper = int(forecast_month_total + 1.96 * hist_std)
    within_ci = ci_lower <= aop_monthly_bookings <= ci_upper

    # Revenue per booking (indicator of mix quality)
    rev_per_booking = forecast_month_revenue / forecast_month_total if forecast_month_total > 0 else 0.0

    return {
        "id": practice_id,
        "name": f"Bupa Dental Care {location}",
        "location": location,
        "area_id": area["id"],
        "area_name": area["name"],
        "region": area["region"],
        "connected_care": area["connected_care"],
        "nhs_mix": round(nhs_mix, 3),
        "private_mix": round(private_mix, 3),
        "avg_nhs_value": round(avg_nhs, 2),
        "avg_private_value": round(avg_private, 2),
        "blended_value": round(blended_value, 2),
        "monthly_capacity": monthly_capacity,
        "target_utilization": round(target_util, 3),
        "booking_profile": booking_profile,
        "booking_curve": [round(v, 4) for v in booking_curve],
        "aop_monthly_bookings": aop_monthly_bookings,
        "aop_monthly_revenue": aop_monthly_revenue,
        "aop_annual_revenue": aop_monthly_revenue * 12,
        # Current month
        "current_month_bookings": current_month_bookings,
        "current_nhs_bookings": current_nhs_bookings,
        "current_private_bookings": current_private_bookings,
        "current_nhs_mix": round(current_nhs_mix, 3),
        "expected_bookings_by_now": round(expected_by_now, 1),
        "forecast_month_total": forecast_month_total,
        "forecast_month_revenue": round(forecast_month_revenue),
        "whitespace": round(whitespace, 3),
        # Performance metrics
        "booking_rate": round(booking_rate, 4),
        "revenue_delivery": round(revenue_delivery, 4),
        "ytd_bookings": ytd_bookings,
        "ytd_revenue": ytd_revenue,
        "ytd_aop_bookings": ytd_aop_bookings,
        "ytd_aop_revenue": ytd_aop_revenue,
        "ytd_delivery": round(ytd_delivery, 4),
        "aop_gap_bookings": forecast_month_total - aop_monthly_bookings,
        "aop_gap_revenue": round(forecast_month_revenue - aop_monthly_revenue),
        # Confidence interval
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "within_ci": within_ci,
        "rev_per_booking": round(rev_per_booking, 2),
        # Historical
        "historical_months": historical_months,
        # Explainability (populated below)
        "issues": [],
        "traffic_light": "amber",  # assigned after all practices generated
    }


def classify_issues(practice: dict) -> list:
    """Identify performance root causes and generate recommended actions."""
    issues = []
    br = practice["booking_rate"]
    nhs = practice["nhs_mix"]
    rd = practice["revenue_delivery"]
    ws = practice["whitespace"]

    if br < 0.80:
        sev = "high" if br < 0.70 else "medium"
        issues.append({
            "type": "demand",
            "severity": sev,
            "title": "Low Patient Demand",
            "description": f"Booking rate is {br*100:.0f}% of expected — not enough patients booking in.",
            "actions": [
                "Review online booking availability and visibility",
                "Target NHS recall campaigns for lapsed patients",
                "Partner with local employers for corporate dental schemes",
                "Review Google Business listing and NHS Choices profile",
            ],
        })

    if nhs > 0.70 and rd < 0.92:
        sev = "high" if nhs > 0.80 else "medium"
        issues.append({
            "type": "mix",
            "severity": sev,
            "title": "NHS-Heavy Mix Suppressing Revenue",
            "description": f"NHS mix is {nhs*100:.0f}% — high NHS volume is diluting revenue per appointment.",
            "actions": [
                "Promote cosmetic and private treatment options at check-up",
                "Introduce private dental plans / membership schemes",
                "Review NHS contract utilisation — avoid over-delivery",
                "Train reception staff to discuss private options",
            ],
        })

    if br >= 0.90 and ws < 0.10 and rd < 0.88:
        issues.append({
            "type": "supply",
            "severity": "medium",
            "title": "Capacity Constraint",
            "description": "Demand appears strong but capacity may be limiting revenue growth.",
            "actions": [
                "Review dentist session scheduling and chair utilisation",
                "Consider extended hours or Saturday clinics",
                "Explore associate dentist recruitment",
                "Audit cancellation and DNA (did-not-attend) rates",
            ],
        })

    if ws > 0.25 and br >= 0.80:
        issues.append({
            "type": "whitespace",
            "severity": "low",
            "title": "Unused Appointment Capacity",
            "description": f"{ws*100:.0f}% of appointment slots are unfilled this month.",
            "actions": [
                "Run short-notice appointment promotions",
                "Review slot release strategy for online booking",
                "Consider recall automation for overdue patients",
            ],
        })

    return issues


def apply_traffic_lights(practices: list) -> list:
    """Assign traffic lights based on YTD delivery percentile ranking."""
    deliveries = [p["ytd_delivery"] for p in practices]
    p25 = float(np.percentile(deliveries, 25))
    p75 = float(np.percentile(deliveries, 75))
    for p in practices:
        d = p["ytd_delivery"]
        if d >= p75:
            p["traffic_light"] = "green"
        elif d <= p25:
            p["traffic_light"] = "red"
        else:
            p["traffic_light"] = "amber"
    return practices


def build_area_summary(area: dict, practices: list) -> dict:
    """Aggregate practice-level metrics to area summary."""
    total_bookings = sum(p["current_month_bookings"] for p in practices)
    total_expected = sum(p["expected_bookings_by_now"] for p in practices)
    total_forecast_rev = sum(p["forecast_month_revenue"] for p in practices)
    total_aop_rev = sum(p["aop_monthly_revenue"] for p in practices)
    total_aop_bookings = sum(p["aop_monthly_bookings"] for p in practices)
    ytd_rev = sum(p["ytd_revenue"] for p in practices)
    ytd_aop = sum(p["ytd_aop_revenue"] for p in practices)
    green = sum(1 for p in practices if p["traffic_light"] == "green")
    amber = sum(1 for p in practices if p["traffic_light"] == "amber")
    red = sum(1 for p in practices if p["traffic_light"] == "red")
    area_booking_rate = total_bookings / total_expected if total_expected > 0 else 0
    area_rev_delivery = total_forecast_rev / total_aop_rev if total_aop_rev > 0 else 0
    area_ytd_delivery = ytd_rev / ytd_aop if ytd_aop > 0 else 0

    # Area-level traffic light
    deliveries = [p["ytd_delivery"] for p in practices]
    area_ytd_d = ytd_rev / ytd_aop if ytd_aop > 0 else 0
    if area_ytd_d >= 0.98:
        tl = "green"
    elif area_ytd_d <= 0.90:
        tl = "red"
    else:
        tl = "amber"

    return {
        **area,
        "practice_count": len(practices),
        "total_bookings": total_bookings,
        "total_expected_bookings": round(total_expected),
        "total_aop_monthly_bookings": total_aop_bookings,
        "total_forecast_revenue": round(total_forecast_rev),
        "total_aop_monthly_revenue": total_aop_rev,
        "ytd_revenue": ytd_rev,
        "ytd_aop_revenue": ytd_aop,
        "booking_rate": round(area_booking_rate, 4),
        "revenue_delivery": round(area_rev_delivery, 4),
        "ytd_delivery": round(area_ytd_delivery, 4),
        "green_count": green,
        "amber_count": amber,
        "red_count": red,
        "traffic_light": tl,
        "aop_gap_revenue": round(total_forecast_rev - total_aop_rev),
    }


def generate_all_data() -> dict:
    """Generate all synthetic data. Returns a complete data payload."""
    practices = []
    pid = 1

    for area in AREAS:
        count = _practice_count_for_area(area["id"])
        for i in range(count):
            p = generate_practice(area, i, f"P{pid:03d}")
            p["issues"] = classify_issues(p)
            practices.append(p)
            pid += 1

    practices = apply_traffic_lights(practices)

    # Build area summaries
    area_map = {a["id"]: a for a in AREAS}
    area_practices = {a["id"]: [] for a in AREAS}
    for p in practices:
        area_practices[p["area_id"]].append(p)

    areas_with_summary = []
    for area in AREAS:
        summary = build_area_summary(area, area_practices[area["id"]])
        summary["practices"] = area_practices[area["id"]]
        areas_with_summary.append(summary)

    # Global summary
    total_bookings = sum(p["current_month_bookings"] for p in practices)
    total_expected = sum(p["expected_bookings_by_now"] for p in practices)
    total_forecast_rev = sum(p["forecast_month_revenue"] for p in practices)
    total_aop_rev = sum(p["aop_monthly_revenue"] for p in practices)
    total_ytd_rev = sum(p["ytd_revenue"] for p in practices)
    total_ytd_aop = sum(p["ytd_aop_revenue"] for p in practices)

    sorted_by_ytd = sorted(practices, key=lambda x: x["ytd_delivery"])
    worst_5 = sorted_by_ytd[:5]
    best_5 = sorted_by_ytd[-5:][::-1]

    # National booking rate distribution (for confidence bands on dashboard)
    booking_rates = sorted([p["booking_rate"] for p in practices])
    p25_br = float(np.percentile(booking_rates, 25))
    p75_br = float(np.percentile(booking_rates, 75))

    global_summary = {
        "total_practices": len(practices),
        "total_bookings_this_month": total_bookings,
        "total_expected_bookings": round(total_expected),
        "overall_booking_rate": round(total_bookings / total_expected, 4) if total_expected > 0 else 0,
        "total_forecast_revenue": round(total_forecast_rev),
        "total_aop_monthly_revenue": total_aop_rev,
        "overall_revenue_delivery": round(total_forecast_rev / total_aop_rev, 4) if total_aop_rev > 0 else 0,
        "total_ytd_revenue": total_ytd_rev,
        "total_ytd_aop": total_ytd_aop,
        "overall_ytd_delivery": round(total_ytd_rev / total_ytd_aop, 4) if total_ytd_aop > 0 else 0,
        "worst_performers": worst_5,
        "best_performers": best_5,
        "green_count": sum(1 for p in practices if p["traffic_light"] == "green"),
        "amber_count": sum(1 for p in practices if p["traffic_light"] == "amber"),
        "red_count": sum(1 for p in practices if p["traffic_light"] == "red"),
        "p25_booking_rate": round(p25_br, 4),
        "p75_booking_rate": round(p75_br, 4),
    }

    return {
        "today": str(TODAY),
        "current_day": CURRENT_DAY,
        "areas": areas_with_summary,
        "practices": practices,
        "practice_index": {p["id"]: p for p in practices},
        "area_index": {a["id"]: a for a in areas_with_summary},
        "global_summary": global_summary,
        "hist_months": HIST_MONTHS,
        "forecast_months": FORECAST_MONTHS,
    }

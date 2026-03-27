"""
Bupa Dental Care – Forecasting & Bookings Visibility App
Flask application providing operational decision-making support across
380 practices and 25 areas in the UK.
"""

import json
from flask import Flask, render_template, request, jsonify, abort
from data_generator import generate_all_data, FORECAST_MONTHS
from forecasting import (
    forecast_practice,
    forecast_area,
    forecast_national,
    ml_model_deployed,
    build_booking_curve_chart_data,
)

app = Flask(__name__)

# Generate data once at startup (fixed seed → deterministic)
DATA = generate_all_data()

# ── Pre-compute 3-month forward analysis for each area (once at startup) ──
# For each area: April / May / June forecast with per-month booking rate,
# revenue delivery, and practice traffic-light breakdown.
def _build_forward_analysis():
    for area in DATA["areas"]:
        fwd = []
        for fi in range(3):
            fm  = FORECAST_MONTHS[fi]
            g = a = r = 0
            fc_rv = fc_bk = aop_rv = aop_bk = 0
            for p in area["practices"]:
                pf  = forecast_practice(p, 3)
                m   = pf["monthly"][fi]
                d   = m["forecast_revenue"] / m["aop_revenue"] if m["aop_revenue"] > 0 else 0
                if d >= 0.97:   g += 1
                elif d < 0.90:  r += 1
                else:           a += 1
                fc_rv  += m["forecast_revenue"]
                fc_bk  += m["forecast_bookings"]
                aop_rv += m["aop_revenue"]
                aop_bk += m["aop_bookings"]
            n = len(area["practices"])
            fwd.append({
                "label":            fm["label"],
                "booking_rate":     round(fc_bk  / aop_bk,  4) if aop_bk  > 0 else 0,
                "revenue_delivery": round(fc_rv  / aop_rv,  4) if aop_rv  > 0 else 0,
                "green_count":  g, "amber_count": a, "red_count": r,
                "green_pct":  round(g / n * 100) if n else 0,
                "amber_pct":  round(a / n * 100) if n else 0,
                "red_pct":    round(r / n * 100) if n else 0,
            })
        area["forward_months"] = fwd

_build_forward_analysis()


def _build_regions_summary() -> dict:
    """
    Compute per-region aggregates: YTD performance + 3-month forward analysis.
    Called once at startup; result cached in DATA['_regions'].
    """
    regions: dict = {}
    for a in DATA["areas"]:
        rn = a["region"]
        if rn not in regions:
            regions[rn] = {
                "area_count": 0, "practice_count": 0,
                "total_ytd_rev": 0, "total_ytd_aop": 0,
                "green": 0, "amber": 0, "red": 0,
                "cur_bk": 0, "cur_exp": 0,
                "cur_fc_rv": 0, "cur_aop_rv": 0,
                "fwd": [{"g": 0, "a": 0, "r": 0,
                         "bk_rate_sum": 0.0, "rev_del_sum": 0.0, "area_count": 0}
                        for _ in range(3)],
            }
        reg = regions[rn]
        reg["area_count"]     += 1
        reg["practice_count"] += a["practice_count"]
        reg["total_ytd_rev"]  += a["ytd_revenue"]
        reg["total_ytd_aop"]  += a["ytd_aop_revenue"]
        reg["green"]          += a["green_count"]
        reg["amber"]          += a["amber_count"]
        reg["red"]            += a["red_count"]
        reg["cur_bk"]         += a["total_bookings"]
        reg["cur_exp"]        += sum(p["expected_bookings_by_now"] for p in a["practices"])
        reg["cur_fc_rv"]      += a["total_forecast_revenue"]
        reg["cur_aop_rv"]     += sum(p["aop_monthly_revenue"] for p in a["practices"])
        for fi, fm in enumerate(a["forward_months"]):
            reg["fwd"][fi]["g"]           += fm["green_count"]
            reg["fwd"][fi]["a"]           += fm["amber_count"]
            reg["fwd"][fi]["r"]           += fm["red_count"]
            reg["fwd"][fi]["bk_rate_sum"] += fm["booking_rate"]
            reg["fwd"][fi]["rev_del_sum"] += fm["revenue_delivery"]
            reg["fwd"][fi]["area_count"]  += 1

    for reg in regions.values():
        reg["ytd_delivery"] = round(
            reg["total_ytd_rev"] / reg["total_ytd_aop"], 4) if reg["total_ytd_aop"] else 0
        reg["cur_booking_rate"]     = round(reg["cur_bk"]    / reg["cur_exp"],    4) if reg["cur_exp"]    else 0
        reg["cur_revenue_delivery"] = round(reg["cur_fc_rv"] / reg["cur_aop_rv"], 4) if reg["cur_aop_rv"] else 0
        n = reg["practice_count"]
        reg["cur_green_pct"] = round(reg["green"] / n * 100) if n else 0
        reg["cur_amber_pct"] = round(reg["amber"] / n * 100) if n else 0
        reg["cur_red_pct"]   = round(reg["red"]   / n * 100) if n else 0
        for fm in reg["fwd"]:
            ac  = fm["area_count"] or 1
            fm["booking_rate"]     = round(fm["bk_rate_sum"] / ac, 4)
            fm["revenue_delivery"] = round(fm["rev_del_sum"] / ac, 4)
            tot = fm["g"] + fm["a"] + fm["r"]
            fm["green_pct"] = round(fm["g"] / tot * 100) if tot else 0
            fm["amber_pct"] = round(fm["a"] / tot * 100) if tot else 0
            fm["red_pct"]   = round(fm["r"] / tot * 100) if tot else 0
    return regions


DATA["_regions"] = _build_regions_summary()


# ─────────────────────────────────────────────────────────────────────────────
# Action-plan classification — maps practice data to the decision-tree
# framework from the BPC "Translating to Action" slide.
# ─────────────────────────────────────────────────────────────────────────────

def classify_action_plan(p: dict) -> dict:
    """
    Walk the 3-step decision tree:
      1. On track?
      2. Issue type: Demand / Supply / Mix
      3. Root causes → specific actions
    Returns a dict: {status, issue, issue_label, causes, actions}
    """
    br  = p["booking_rate"]
    rd  = p["revenue_delivery"]
    ytd = p["ytd_delivery"]
    nhs = p["nhs_mix"]
    ws  = p["whitespace"]
    bp  = p["booking_profile"]
    bv  = p["blended_value"]

    # ── Step 1: On track? ─────────────────────────────────────────────────
    # Align status with Practice Directory and issue flags shown on practice detail.
    if p.get("traffic_light") == "green" or not p.get("issues"):
        return {"status": "on_track", "issue": None, "issue_label": None,
                "causes": [], "actions": []}
    status = "off_track" if p.get("traffic_light") == "red" else "at_risk"

    # ── Step 2: Primary issue ─────────────────────────────────────────────
    # Supply: strong demand, low whitespace — capacity is the bottleneck
    if br >= 0.88 and ws < 0.12:
        issue = "supply"
        issue_label = "Supply"
        issue_desc  = (f"High utilisation ({(1-ws)*100:.0f}% full) with a strong booking "
                       f"rate ({br*100:.0f}%) — capacity is limiting revenue growth.")
    # Mix: revenue well below booking rate — NHS volume diluting value
    elif nhs > 0.65 and (rd < br - 0.06 or (rd < 0.92 and nhs > 0.72)):
        issue = "mix"
        issue_label = "Mix"
        issue_desc  = (f"NHS mix is {nhs*100:.0f}% — high NHS volume is diluting revenue "
                       f"per appointment (booking rate {br*100:.0f}% vs revenue delivery "
                       f"{rd*100:.0f}%).")
    # Demand: not enough patients booking in
    elif br < 0.83:
        issue = "demand"
        issue_label = "Demand"
        issue_desc  = (f"Booking rate is only {br*100:.0f}% of expected — insufficient "
                       f"patient demand relative to available capacity "
                       f"({ws*100:.0f}% whitespace).")
    else:
        # Edge case: mild underperformance — default to demand
        issue = "demand"
        issue_label = "Demand"
        issue_desc  = (f"Booking rate ({br*100:.0f}%) and revenue delivery ({rd*100:.0f}%) "
                       f"are below target.")

    # ── Step 3: Root causes and actions ───────────────────────────────────
    causes  = []
    actions = []

    if issue == "demand":
        # New patients - especially where booking profile suggests weaker demand capture.
        if bp in ("mixed", "late"):
            causes.append("new_patients")
            actions += [
                {"priority": "high", "cause": "New Patients",
                 "action": "Run targeted marketing campaigns and outbound activity (calls, corporate events, bespoke offers).",
                 "owner": "Area Manager"},
                {"priority": "high", "cause": "New Patients",
                 "action": "Review and optimise Google Business profile and NHS Choices listing.",
                 "owner": "Practice Manager"},
                {"priority": "medium", "cause": "New Patients",
                 "action": "Explore corporate dental scheme partnerships with local employers.",
                 "owner": "Area Manager"},
            ]
        # Patient conversion — late-bookers suggest low conversion at point of contact
        if bp == "late":
            causes.append("patient_conversion")
            actions += [
                {"priority": "high", "cause": "Patient Conversion",
                 "action": "Brief clinicians on recommending follow-up treatments and specialist referrals at each appointment.",
                 "owner": "Clinician Lead"},
                {"priority": "high", "cause": "Patient Conversion",
                 "action": "Introduce patient finance options (monthly plans) to reduce price barrier to treatment.",
                 "owner": "Reception / TCO"},
                {"priority": "medium", "cause": "Patient Conversion",
                 "action": "Ensure TCO follow-up call protocol is in place for all incomplete treatment plans.",
                 "owner": "TCO"},
            ]
        # Patient retention — core demand lever for all demand-issue practices
        causes.append("patient_retention")
        actions += [
            {"priority": "high", "cause": "Patient Retention",
             "action": "Activate automated recall campaigns for patients overdue for their check-up (6m, 12m, 18m bands).",
             "owner": "Practice Manager"},
            {"priority": "medium", "cause": "Patient Retention",
             "action": "Review and work the lapsed-patient list (12m+ since last visit) with targeted outreach.",
             "owner": "Practice Manager"},
        ]

    elif issue == "supply":
        # Dentist headcount / contracted hours
        causes.append("contracted_hours")
        actions += [
            {"priority": "high", "cause": "Contracted Hours",
             "action": "Initiate associate dentist recruitment to add session capacity.",
             "owner": "HR / Area Manager"},
            {"priority": "high", "cause": "Contracted Hours",
             "action": "Explore campus resource sharing with lower-utilisation nearby practices.",
             "owner": "Area Manager"},
            {"priority": "medium", "cause": "Contracted Hours",
             "action": "Review hours mix (private vs. NHS) per clinician to optimise revenue per contracted hour.",
             "owner": "Practice Manager"},
        ]
        # Worked hours — sessions lost to absence/DNA
        causes.append("worked_hours")
        actions += [
            {"priority": "medium", "cause": "Worked Hours",
             "action": "Schedule PM/clinician business-partnering sessions to close gap between contracted and worked hours.",
             "owner": "PM + Clinician"},
            {"priority": "medium", "cause": "Worked Hours",
             "action": "Run engagement activities targeting attendance and reducing avoidable session cancellations.",
             "owner": "Practice Manager"},
        ]
        # Surgery capacity — near-zero whitespace
        if ws < 0.06:
            causes.append("surgery_capacity")
            actions += [
                {"priority": "high", "cause": "Surgery Capacity",
                 "action": "Assess feasibility of new surgery, extended hours (evenings/Saturdays) or satellite location.",
                 "owner": "Area Manager"},
            ]

    elif issue == "mix":
        # NHS vs Private diary mix
        causes.append("nhs_vs_private")
        actions += [
            {"priority": "high", "cause": "NHS vs Private",
             "action": "Introduce private diary zoning for willing clinicians — ring-fence slots for private/BSP patients.",
             "owner": "Practice Manager"},
            {"priority": "high", "cause": "NHS vs Private",
             "action": "PM/clinician business partnering to review individual diary mix and agree shift targets.",
             "owner": "PM + Clinician"},
            {"priority": "medium", "cause": "NHS vs Private",
             "action": "Review NHS contract utilisation — avoid over-delivering UDAs beyond contracted target.",
             "owner": "Practice Manager"},
        ]
        # HVT / treatment value — low blended rate
        if bv < 130:
            causes.append("hvt_value")
            actions += [
                {"priority": "high", "cause": "HVT / Treatment Value",
                 "action": "Introduce diary zoning to prioritise high-value treatments (crowns, implants, ortho) over routine exams.",
                 "owner": "Practice Manager"},
                {"priority": "medium", "cause": "HVT / Treatment Value",
                 "action": "Brief clinicians on presenting comprehensive treatment plans and specialist services to private patients.",
                 "owner": "Clinician Lead"},
            ]
    # Sort: high → medium → low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda x: priority_order[x["priority"]])

    return {
        "status":       status,
        "issue":        issue,
        "issue_label":  issue_label,
        "issue_desc":   issue_desc,
        "causes":       causes,
        "actions":      actions,
    }


def _build_action_plans():
    """Attach a pre-computed action plan to every practice at startup."""
    for p in DATA["practices"]:
        p["action_plan"] = classify_action_plan(p)


_build_action_plans()


def fmt_currency(value: float) -> str:
    return f"£{int(value):,}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


app.jinja_env.filters["currency"] = fmt_currency
app.jinja_env.filters["pct"] = fmt_pct


# ─────────────────────────────────────────────────────────────────────────────
# Home — landing hub
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    gs = DATA["global_summary"]
    return render_template(
        "home.html",
        gs=gs,
        today=DATA["today"],
        current_day=DATA["current_day"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Headlines — national KPIs and area chart
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/headlines")
def headlines():
    gs = DATA["global_summary"]
    areas = DATA["areas"]

    area_labels = [a["name"] for a in areas]
    area_ytd = [round(a["ytd_delivery"] * 100, 1) for a in areas]
    area_ytd_amount = [int(a["ytd_revenue"]) for a in areas]
    # Peer-relative RAG colors (bottom quartile red, top quartile green).
    # This avoids overusing amber when absolute thresholds cluster tightly.
    rag_by_area_id = {a["id"]: "rgba(255,193,7,0.8)" for a in areas}
    ranked = sorted(areas, key=lambda a: a["ytd_delivery"])
    quartile_n = max(1, len(ranked) // 4)
    for a in ranked[:quartile_n]:
        rag_by_area_id[a["id"]] = "rgba(220,53,69,0.8)"
    for a in ranked[-quartile_n:]:
        rag_by_area_id[a["id"]] = "rgba(25,135,84,0.8)"
    area_tl_colors = [rag_by_area_id[a["id"]] for a in areas]

    # Booking rate distribution across all practices (histogram buckets)
    br_buckets = [0, 0, 0, 0, 0]  # <70, 70-80, 80-90, 90-100, >100
    br_labels = ["<70%", "70–80%", "80–90%", "90–100%", ">100%"]
    for p in DATA["practices"]:
        br = p["booking_rate"] * 100
        if br < 70:
            br_buckets[0] += 1
        elif br < 80:
            br_buckets[1] += 1
        elif br < 90:
            br_buckets[2] += 1
        elif br <= 100:
            br_buckets[3] += 1
        else:
            br_buckets[4] += 1

    return render_template(
        "headlines.html",
        gs=gs,
        areas=areas,
        area_labels=json.dumps(area_labels),
        area_ytd=json.dumps(area_ytd),
        area_ytd_amount=json.dumps(area_ytd_amount),
        area_tl_colors=json.dumps(area_tl_colors),
        br_buckets=json.dumps(br_buckets),
        br_labels=json.dumps(br_labels),
        today=DATA["today"],
        current_day=DATA["current_day"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Performers — top and bottom ranked practices
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/performers")
def performers():
    metric = request.args.get("metric", "ytd_delivery")
    n      = int(request.args.get("n", 10))
    region = request.args.get("region", "all")

    valid_metrics = ("ytd_delivery", "booking_rate", "revenue_delivery")
    if metric not in valid_metrics:
        metric = "ytd_delivery"
    n = max(5, min(20, n))

    # All unique regions for the filter bar
    all_regions = sorted(set(p["region"] for p in DATA["practices"]))

    # Apply region filter before ranking
    pool = DATA["practices"]
    if region != "all":
        pool = [p for p in pool if p["region"] == region]

    sorted_practices = sorted(pool, key=lambda p: p[metric])
    bottom_n = sorted_practices[:n]
    top_n    = sorted_practices[-n:][::-1]

    metric_labels = {
        "ytd_delivery":    "YTD Revenue Delivery",
        "booking_rate":    "Current Month Booking Rate",
        "revenue_delivery":"Forecast Revenue Delivery",
    }

    return render_template(
        "performers.html",
        top_n=top_n,
        bottom_n=bottom_n,
        metric=metric,
        metric_label=metric_labels[metric],
        n=n,
        region=region,
        all_regions=all_regions,
        pool_size=len(pool),
        today=DATA["today"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Areas summary — all 25 areas
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/areas")
def areas_summary():
    sort_by = request.args.get("sort", "name")
    order   = request.args.get("order", "asc")
    reverse = order == "desc"
    valid_sorts = ("name", "region", "ytd_delivery", "booking_rate",
                   "revenue_delivery", "practice_count")
    areas = DATA["areas"]
    if sort_by in valid_sorts:
        areas = sorted(areas, key=lambda a: a[sort_by], reverse=reverse)

    return render_template(
        "areas_summary.html",
        areas=areas,
        regions=DATA["_regions"],
        sort_by=sort_by,
        order=order,
        today=DATA["today"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Forward Looking Analysis — 3-month area outlook
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/forward")
def forward_looking():
    fwd_areas  = sorted(DATA["areas"], key=lambda a: (a["region"], a["name"]))
    fwd_labels = [FORECAST_MONTHS[i]["label"] for i in range(3)]
    return render_template(
        "forward_looking.html",
        fwd_areas=fwd_areas,
        fwd_labels=fwd_labels,
        regions=DATA["_regions"],
        today=DATA["today"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Take Action — decision-tree driven action recommendations
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/actions")
def take_action():
    region     = request.args.get("region", "all")
    issue_flt  = request.args.get("issue",  "all")
    status_flt = request.args.get("status", "needs_action")   # needs_action | all
    practice_id = request.args.get("practice", "").strip()

    if practice_id:
        target = DATA["practice_index"].get(practice_id)
        if not target:
            abort(404)
        pool = [target]
    else:
        pool = DATA["practices"]

        if region != "all":
            pool = [p for p in pool if p["region"] == region]
        if issue_flt != "all":
            pool = [p for p in pool if p["action_plan"]["issue"] == issue_flt]
        if status_flt == "needs_action":
            pool = [p for p in pool if p["action_plan"]["status"] != "on_track"]

    # Sort: off_track first, then at_risk, then by ytd ascending (worst first)
    status_order = {"off_track": 0, "at_risk": 1, "on_track": 2}
    pool = sorted(pool,
                  key=lambda p: (status_order[p["action_plan"]["status"]], p["ytd_delivery"]))

    # Summary counts across all 380 practices (before filters)
    all_p = DATA["practices"]
    summary = {
        "off_track": sum(1 for p in all_p if p["action_plan"]["status"] == "off_track"),
        "at_risk":   sum(1 for p in all_p if p["action_plan"]["status"] == "at_risk"),
        "on_track":  sum(1 for p in all_p if p["action_plan"]["status"] == "on_track"),
        "demand":    sum(1 for p in all_p if p["action_plan"]["issue"]  == "demand"),
        "supply":    sum(1 for p in all_p if p["action_plan"]["issue"]  == "supply"),
        "mix":       sum(1 for p in all_p if p["action_plan"]["issue"]  == "mix"),
    }

    all_regions = sorted(set(p["region"] for p in DATA["practices"]))

    return render_template(
        "take_action.html",
        practices=pool,
        summary=summary,
        region=region,
        issue_flt=issue_flt,
        status_flt=status_flt,
        all_regions=all_regions,
        focus_practice_id=practice_id,
        today=DATA["today"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Practices list — searchable / filterable
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/practices")
def practices_list():
    practices = DATA["practices"]
    area_filter    = request.args.get("area",    "all")
    status_filter  = request.args.get("status",  "all")
    profile_filter = request.args.get("profile", "all")
    limit_raw      = request.args.get("limit",   "5")

    if area_filter != "all":
        practices = [p for p in practices if p["area_id"]        == area_filter]
    if status_filter != "all":
        practices = [p for p in practices if p["traffic_light"]  == status_filter]
    if profile_filter != "all":
        practices = [p for p in practices if p["booking_profile"] == profile_filter]

    sort_by = request.args.get("sort", "name")
    order   = request.args.get("order", "asc")
    valid_sorts = ("name", "booking_rate", "ytd_delivery", "revenue_delivery",
                   "aop_monthly_revenue", "nhs_mix")
    if sort_by in valid_sorts:
        practices = sorted(practices, key=lambda p: p[sort_by],
                           reverse=(order == "desc"))

    filtered_count = len(practices)

    # Apply row limit
    limit = None if limit_raw == "all" else int(limit_raw) if limit_raw.isdigit() else 5
    if limit is not None:
        practices = practices[:limit]

    return render_template(
        "practices.html",
        practices=practices,
        areas=DATA["areas"],
        area_filter=area_filter,
        status_filter=status_filter,
        profile_filter=profile_filter,
        sort_by=sort_by,
        order=order,
        limit=limit_raw,
        filtered_count=filtered_count,
        total_count=len(DATA["practices"]),
        today=DATA["today"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Area detail
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/area/<area_id>")
def area_detail(area_id):
    area = DATA["area_index"].get(area_id)
    if not area:
        abort(404)

    practices = area["practices"]
    sort_by = request.args.get("sort", "ytd_delivery")
    order = request.args.get("order", "asc")
    reverse = order == "desc"
    if sort_by in ("ytd_delivery", "booking_rate", "revenue_delivery",
                   "aop_monthly_revenue", "current_month_bookings"):
        practices = sorted(practices, key=lambda p: p[sort_by], reverse=reverse)

    p_names = [p["location"] for p in practices]
    p_booking_rates = [round(p["booking_rate"] * 100, 1) for p in practices]
    p_rev_delivery = [round(p["revenue_delivery"] * 100, 1) for p in practices]
    p_colors = []
    for p in practices:
        if p["traffic_light"] == "green":
            p_colors.append("rgba(25,135,84,0.75)")
        elif p["traffic_light"] == "red":
            p_colors.append("rgba(220,53,69,0.75)")
        else:
            p_colors.append("rgba(255,193,7,0.75)")

    af = forecast_area(area, 12)
    fc_labels = [m["label"] for m in af["monthly"]]
    fc_revenue = [m["forecast_revenue"] for m in af["monthly"]]
    fc_aop = [m["aop_revenue"] for m in af["monthly"]]
    fc_ci_lower = [m["ci80_lower_revenue"] for m in af["monthly"]]
    fc_ci_upper = [m["ci80_upper_revenue"] for m in af["monthly"]]

    return render_template(
        "area.html",
        area=area,
        practices=practices,
        sort_by=sort_by,
        order=order,
        p_names=json.dumps(p_names),
        p_booking_rates=json.dumps(p_booking_rates),
        p_rev_delivery=json.dumps(p_rev_delivery),
        p_colors=json.dumps(p_colors),
        fc_labels=json.dumps(fc_labels),
        fc_revenue=json.dumps(fc_revenue),
        fc_aop=json.dumps(fc_aop),
        fc_ci_lower=json.dumps(fc_ci_lower),
        fc_ci_upper=json.dumps(fc_ci_upper),
        today=DATA["today"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Practice detail
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/practice/<practice_id>")
def practice_detail(practice_id):
    practice = DATA["practice_index"].get(practice_id)
    if not practice:
        abort(404)

    curve_data = build_booking_curve_chart_data(practice)
    pf = forecast_practice(practice, 12)
    fc_labels = [m["label"] for m in pf["monthly"]]
    fc_revenue = [m["forecast_revenue"] for m in pf["monthly"]]
    fc_aop = [m["aop_revenue"] for m in pf["monthly"]]
    fc_ci_lower = [m["ci80_lower_revenue"] for m in pf["monthly"]]
    fc_ci_upper = [m["ci80_upper_revenue"] for m in pf["monthly"]]

    hist_labels = [m["label"] for m in practice["historical_months"]] + ["Mar 26 (fcst)"]
    hist_bookings = [m["bookings"] for m in practice["historical_months"]] + [practice["forecast_month_total"]]
    hist_aop = [m["aop_bookings"] for m in practice["historical_months"]] + [practice["aop_monthly_bookings"]]
    hist_revenue = [m["revenue"] for m in practice["historical_months"]] + [practice["forecast_month_revenue"]]

    return render_template(
        "practice.html",
        p=practice,
        curve_data=json.dumps(curve_data),
        fc_labels=json.dumps(fc_labels),
        fc_revenue=json.dumps(fc_revenue),
        fc_aop=json.dumps(fc_aop),
        fc_ci_lower=json.dumps(fc_ci_lower),
        fc_ci_upper=json.dumps(fc_ci_upper),
        hist_labels=json.dumps(hist_labels),
        hist_bookings=json.dumps(hist_bookings),
        hist_aop=json.dumps(hist_aop),
        hist_revenue=json.dumps(hist_revenue),
        pf=pf,
        today=DATA["today"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Forecasting module
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/forecast")
def forecast_view():
    horizon     = max(3, min(12, int(request.args.get("horizon", 12))))
    area_id     = request.args.get("area", "all")
    practice_id = request.args.get("practice", "")

    # ── Resolve level ──────────────────────────────────────────────────────
    practice  = None
    area      = None
    pf_data   = None   # practice-level cumulative summary
    model_used = False

    if practice_id:
        practice = DATA["practice_index"].get(practice_id)
        if not practice:
            abort(404)
        area_id  = practice["area_id"]
        area     = DATA["area_index"].get(area_id)
        level    = "practice"
        raw_fc   = forecast_practice(practice, horizon)
        nf       = raw_fc            # monthly key used by shared chart logic
        pf_data  = raw_fc["cumulative"]
        model_used = raw_fc.get("model_used", False)
        title    = practice["name"]
    elif area_id != "all":
        area = DATA["area_index"].get(area_id)
        if not area:
            abort(404)
        level      = "area"
        nf         = forecast_area(area, horizon)
        title      = area["name"]
        model_used = ml_model_deployed()
    else:
        level      = "national"
        nf         = forecast_national(DATA["areas"], horizon)
        title      = "All Areas - National View"
        model_used = ml_model_deployed()

    # ── Build chart data ───────────────────────────────────────────────────
    fc_labels   = [m["label"]            for m in nf["monthly"]]
    fc_revenue  = [m["forecast_revenue"] for m in nf["monthly"]]
    fc_aop      = [m["aop_revenue"]      for m in nf["monthly"]]
    fc_ci_lower = [m["ci80_lower_revenue"] for m in nf["monthly"]]
    fc_ci_upper = [m["ci80_upper_revenue"] for m in nf["monthly"]]
    total_forecast = sum(fc_revenue)
    total_aop      = sum(fc_aop)

    # Lightweight practice list for JS-powered cascading dropdown
    practice_list = json.dumps([
        {"id": p["id"], "name": p["name"], "area_id": p["area_id"]}
        for p in DATA["practices"]
    ])

    return render_template(
        "forecast.html",
        nf=nf,
        pf_data=pf_data,
        level=level,
        practice=practice,
        area=area,
        practice_id=practice_id,
        title=title,
        horizon=horizon,
        area_id=area_id,
        areas=DATA["areas"],
        practice_list=practice_list,
        model_used=model_used,
        fc_labels=json.dumps(fc_labels),
        fc_revenue=json.dumps(fc_revenue),
        fc_aop=json.dumps(fc_aop),
        fc_ci_lower=json.dumps(fc_ci_lower),
        fc_ci_upper=json.dumps(fc_ci_upper),
        total_forecast=total_forecast,
        total_aop=total_aop,
        today=DATA["today"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# JSON API
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/summary")
def api_summary():
    return jsonify(DATA["global_summary"])


@app.route("/api/areas")
def api_areas():
    return jsonify([{k: v for k, v in a.items() if k != "practices"} for a in DATA["areas"]])


@app.route("/api/area/<area_id>")
def api_area(area_id):
    area = DATA["area_index"].get(area_id)
    if not area:
        abort(404)
    return jsonify({k: v for k, v in area.items() if k != "practices"})


@app.route("/api/practice/<practice_id>")
def api_practice(practice_id):
    practice = DATA["practice_index"].get(practice_id)
    if not practice:
        abort(404)
    return jsonify(practice)


@app.route("/api/practice/<practice_id>/forecast")
def api_practice_forecast(practice_id):
    practice = DATA["practice_index"].get(practice_id)
    if not practice:
        abort(404)
    horizon = int(request.args.get("horizon", 12))
    return jsonify(forecast_practice(practice, min(12, max(3, horizon))))


if __name__ == "__main__":
    app.run(debug=True, port=5000)

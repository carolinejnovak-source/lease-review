"""
VIP Lease Review Checklist — sourced from Master Lease Checklist v2
Anticipated actions: "redline" | "comment" | "redline_if_red_flag" | "comment_only"
"""

CHECKLIST = [
    # ── Commencement & Delivery ─────────────────────────────────────────────
    {"section": "Commencement Date", "what_to_look_for": "Trigger methodology",
     "vip_standard": "Commencement upon Substantial Completion (SC)",
     "others_acceptable": "Commencement on fixed date w/ protections",
     "red_flag": "Commencement BEFORE SC", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Rent Commencement", "what_to_look_for": "When rent begins",
     "vip_standard": "Rent begins AFTER SC + abatement period",
     "others_acceptable": "Rent begins at Commencement",
     "red_flag": "Rent due before SC", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Substantial Completion Definition",
     "what_to_look_for": "Detailed SC definition",
     "vip_standard": "SC = all LL work complete except punch list",
     "others_acceptable": "Typical SC definition",
     "red_flag": "SC includes unfinished major items", "priority": "High",
     "anticipated_action": "redline_if_red_flag"},

    {"section": "SC Trigger", "what_to_look_for": "Objective or subjective?",
     "vip_standard": "Objective checklist",
     "others_acceptable": "Standard",
     "red_flag": "LL subjective declaration", "priority": "High",
     "anticipated_action": "comment"},

    {"section": "Punch List Timing", "what_to_look_for": "Duration + obligations",
     "vip_standard": "LL completes punch list within 30 days",
     "others_acceptable": "45 days",
     "red_flag": ">45 days or no deadline", "priority": "Medium",
     "anticipated_action": "comment"},

    {"section": "Delivery Condition", "what_to_look_for": "Condition at delivery",
     "vip_standard": "Delivered broom clean + HVAC/electrical/plumbing in good working order",
     "others_acceptable": "Standard delivery",
     "red_flag": "As-is delivery with no LL obligations", "priority": "High",
     "anticipated_action": "redline"},

    # ── HVAC ────────────────────────────────────────────────────────────────
    {"section": "HVAC – Repair Responsibility",
     "what_to_look_for": "Who repairs HVAC?",
     "vip_standard": "LL responsible for all HVAC repairs",
     "others_acceptable": "Shared responsibility",
     "red_flag": "Tenant responsible for repairs", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "HVAC – Replacement Responsibility",
     "what_to_look_for": "Who replaces HVAC?",
     "vip_standard": "LL responsible for replacement",
     "others_acceptable": "Standard",
     "red_flag": "Tenant responsible for replacement", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "HVAC – Age Disclosure",
     "what_to_look_for": "LL provides age, maintenance records, warranty",
     "vip_standard": "LL provides age, maintenance records, warranty",
     "others_acceptable": "Partial disclosure",
     "red_flag": "No disclosure", "priority": "Low",
     "anticipated_action": "comment"},

    {"section": "HVAC – Warranty",
     "what_to_look_for": "LL warranties HVAC for 12 months minimum",
     "vip_standard": "LL warranties HVAC for 12 months minimum",
     "others_acceptable": "Standard warranty",
     "red_flag": "No warranty", "priority": "Low",
     "anticipated_action": "comment"},

    # ── Building Systems ─────────────────────────────────────────────────────
    {"section": "Roof", "what_to_look_for": "Who is responsible for roof?",
     "vip_standard": "LL responsible",
     "others_acceptable": "Standard",
     "red_flag": "Tenant responsible for roof", "priority": "Medium",
     "anticipated_action": "redline_if_red_flag"},

    {"section": "Fire Sprinkler System",
     "what_to_look_for": "Who is responsible?",
     "vip_standard": "LL responsible",
     "others_acceptable": "Standard",
     "red_flag": "Tenant responsible for sprinklers", "priority": "Medium",
     "anticipated_action": "redline_if_red_flag"},

    {"section": "Electrical Capacity",
     "what_to_look_for": "Sufficient capacity for ultrasound + exam chairs + IT",
     "vip_standard": "Verified capacity for ultrasound + exam chairs + IT",
     "others_acceptable": "Standard medical office power",
     "red_flag": "Insufficient capacity or no LL confirmation", "priority": "High",
     "anticipated_action": "redline_if_red_flag"},

    {"section": "Water Supply", "what_to_look_for": "LL confirms adequate water capacity",
     "vip_standard": "LL confirms capacity",
     "others_acceptable": "Standard",
     "red_flag": "Tenant must install own water heater; no capacity confirmation",
     "priority": "Medium", "anticipated_action": "redline_if_red_flag"},

    {"section": "Generator / Backup Power",
     "what_to_look_for": "Power stability and backup provisions",
     "vip_standard": "LL confirms power stability",
     "others_acceptable": "Standard",
     "red_flag": "No backup power; no LL warranty on power stability",
     "priority": "High", "anticipated_action": "redline"},

    {"section": "Utility Interruptions",
     "what_to_look_for": "LL remedies for utility outages",
     "vip_standard": "LL provides remedies for outages (rent abatement or termination right)",
     "others_acceptable": "Standard",
     "red_flag": "No remedy for extended outages", "priority": "Medium",
     "anticipated_action": "redline"},

    # ── Use & Zoning ────────────────────────────────────────────────────────
    {"section": "Use Clause", "what_to_look_for": "Permitted use defined?",
     "vip_standard": "Medical use, specifically vascular medicine and associated minimally invasive procedures",
     "others_acceptable": "General medical office",
     "red_flag": "Overly restrictive use clause", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Zoning Guarantee",
     "what_to_look_for": "LL confirms zoning for medical use",
     "vip_standard": "LL confirms zoning for medical use",
     "others_acceptable": "Standard",
     "red_flag": "No LL zoning confirmation", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Exclusivity",
     "what_to_look_for": "Exclusive right for vein/IR procedures",
     "vip_standard": "Exclusive for vein/IR",
     "others_acceptable": "No exclusivity",
     "red_flag": "Competing vein practice in building", "priority": "Low",
     "anticipated_action": "comment"},

    # ── Operating Expenses ──────────────────────────────────────────────────
    {"section": "Operating Expenses (OPEX) Cap",
     "what_to_look_for": "Annual cap on OPEX increases",
     "vip_standard": "5% non-compounding, non-cumulative cap based on prior year",
     "others_acceptable": "5% cumulative",
     "red_flag": "No cap; cumulative cap", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Operating Expense Definition",
     "what_to_look_for": "What is excluded from OPEX?",
     "vip_standard": "Clear exclusions: capital costs, LL legal fees, depreciation, executive salaries",
     "others_acceptable": "Standard exclusions",
     "red_flag": "Capital costs or LL legal fees included in OPEX", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Base Year",
     "what_to_look_for": "Base year methodology",
     "vip_standard": "Base year = next full calendar year after commencement",
     "others_acceptable": "Fixed NNN rate",
     "red_flag": "No base year; fixed rate without escalation methodology",
     "priority": "Medium", "anticipated_action": "redline"},

    {"section": "Proportionate Share",
     "what_to_look_for": "Fixed proportionate share for term",
     "vip_standard": "Fixed PS for term",
     "others_acceptable": "Standard recalculation",
     "red_flag": "PS can be recalculated to tenant's detriment", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Janitorial",
     "what_to_look_for": "Who handles janitorial?",
     "vip_standard": "Tenant handles interior only",
     "others_acceptable": "Standard",
     "red_flag": "Tenant responsible for exterior/common areas", "priority": "Low",
     "anticipated_action": "redline_if_red_flag"},

    {"section": "Trash Removal",
     "what_to_look_for": "Who handles trash?",
     "vip_standard": "Included in OPEX",
     "others_acceptable": "Standard",
     "red_flag": "Medical waste removal entirely on Tenant", "priority": "Medium",
     "anticipated_action": "redline_if_red_flag"},

    {"section": "Electricity",
     "what_to_look_for": "How is electricity handled?",
     "vip_standard": "Included in OPEX or separate meter — not direct-metered at inflated rates",
     "others_acceptable": "Separate metering at utility rates",
     "red_flag": "Submetered at above-utility rates", "priority": "Medium",
     "anticipated_action": "redline"},

    # ── TI & Construction ───────────────────────────────────────────────────
    {"section": "TI Allowance",
     "what_to_look_for": "Amount and structure of TI",
     "vip_standard": "$100–$130 per RSF",
     "others_acceptable": "$80–$100 per RSF",
     "red_flag": "<$80/RSF or no TI", "priority": "Medium",
     "anticipated_action": "comment"},

    {"section": "TI Disbursement",
     "what_to_look_for": "How/when TI is paid out",
     "vip_standard": "Progress draws + 10% retainage released at substantial completion",
     "others_acceptable": "Standard disbursement",
     "red_flag": "Tenant fronts >30% of costs", "priority": "Medium",
     "anticipated_action": "comment"},

    {"section": "TI Expiration Deadline",
     "what_to_look_for": "Deadline to use TI funds",
     "vip_standard": "18–24 months (less critical if rent begins at SC)",
     "others_acceptable": "12 months",
     "red_flag": "<12 months or no deadline defined", "priority": "Medium",
     "anticipated_action": "comment"},

    {"section": "Modifications and Buildout",
     "what_to_look_for": "Who performs the buildout?",
     "vip_standard": "Landlord performs and is wholly responsible",
     "others_acceptable": "Tenant with LL oversight",
     "red_flag": "Tenant solely responsible for buildout", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "TI Change Orders",
     "what_to_look_for": "LL approval of change orders",
     "vip_standard": "LL cannot unreasonably withhold approval of change orders",
     "others_acceptable": "Standard",
     "red_flag": "LL has absolute veto on all change orders", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Construction Management Fee",
     "what_to_look_for": "Is there a CM fee?",
     "vip_standard": "Up to 3% of construction costs",
     "others_acceptable": "Up to 5%",
     "red_flag": ">5% CM fee", "priority": "Medium",
     "anticipated_action": "comment"},

    {"section": "Permits",
     "what_to_look_for": "Who is responsible for building permits?",
     "vip_standard": "LL responsible for all building permits",
     "others_acceptable": "Shared",
     "red_flag": "Tenant responsible for permits", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Construction Schedule",
     "what_to_look_for": "Timeline with LL delay penalties",
     "vip_standard": "Detailed timeline with LL delay penalties",
     "others_acceptable": "Timeline without penalties",
     "red_flag": "No timeline; no LL accountability", "priority": "High",
     "anticipated_action": "comment"},

    {"section": "As-Builts",
     "what_to_look_for": "LL provides as-built drawings",
     "vip_standard": "LL provides complete as-built drawings at no cost",
     "others_acceptable": "Standard",
     "red_flag": "No as-built obligation", "priority": "High",
     "anticipated_action": "comment"},

    {"section": "ADA Compliance",
     "what_to_look_for": "Who is responsible for ADA base building compliance?",
     "vip_standard": "LL responsible for base building ADA compliance",
     "others_acceptable": "Shared",
     "red_flag": "Tenant responsible for all ADA", "priority": "High",
     "anticipated_action": "redline"},

    # ── Financial ───────────────────────────────────────────────────────────
    {"section": "Holdover Rent",
     "what_to_look_for": "Holdover rent rate",
     "vip_standard": "110% of then-current rent (1.1x)",
     "others_acceptable": "120%",
     "red_flag": ">150% of then-current rent", "priority": "Low",
     "anticipated_action": "redline"},

    {"section": "Security Deposit",
     "what_to_look_for": "Amount and structure",
     "vip_standard": "1 month rent",
     "others_acceptable": "2 months",
     "red_flag": ">2 months or no burn-down provision", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Personal Guaranty",
     "what_to_look_for": "Is a personal or corporate guaranty required?",
     "vip_standard": "No guaranty preferred; corporate guaranty from local billing entity acceptable",
     "others_acceptable": "Corporate guaranty only",
     "red_flag": "Personal guaranty required",
     "priority": "High",
     "anticipated_action": "redline",
     "notes": (
         "Strike any personal guaranty language. "
         "For corporate guaranties, redline to substitute the applicable local billing entity: "
         "Texas → 'Medical Services of Texas LLC'; "
         "New York → 'Medical Services of Manhattan LLC'; "
         "New Jersey → 'Vein Treatment New Jersey LLC'; "
         "Long Island → 'Shore Medical Services LLC'; "
         "Connecticut → 'Medical Services of Connecticut LLC'; "
         "California → 'Ellison Medical Services LLC'."
     )},

    {"section": "Late Fees",
     "what_to_look_for": "Late fee percentage",
     "vip_standard": "Less than 5% of monthly rent",
     "others_acceptable": "5%",
     "red_flag": ">5%", "priority": "Low",
     "anticipated_action": "redline"},

    {"section": "Rent Payment Method",
     "what_to_look_for": "ACH/wire accepted?",
     "vip_standard": "ACH/wire required; no physical check option",
     "others_acceptable": "ACH accepted",
     "red_flag": "Certified check only; no electronic payment", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Default + Cure Periods",
     "what_to_look_for": "Cure periods for default",
     "vip_standard": "10 days to cure rent defaults; 30 days (with extension) for other defaults",
     "others_acceptable": "Standard",
     "red_flag": "<5 days cure for rent; <10 days for other defaults", "priority": "Medium",
     "anticipated_action": "redline"},

    # ── Parking & Signage ────────────────────────────────────────────────────
    {"section": "Parking Ratio",
     "what_to_look_for": "Number of parking spaces",
     "vip_standard": "Pro-rata included free",
     "others_acceptable": "Pro-rata with fee",
     "red_flag": "Insufficient parking; parking fee above market", "priority": "Medium",
     "anticipated_action": "comment"},

    {"section": "Reserved Parking",
     "what_to_look_for": "Reserved spaces for Tenant",
     "vip_standard": "2 reserved spaces",
     "others_acceptable": "1 reserved space",
     "red_flag": "No reserved spaces", "priority": "Medium",
     "anticipated_action": "comment"},

    {"section": "Signage – Door",
     "what_to_look_for": "Suite door signage rights",
     "vip_standard": "Suite door signage included",
     "others_acceptable": "Standard",
     "red_flag": "No door signage rights", "priority": "High",
     "anticipated_action": "comment"},

    {"section": "Signage – Directory",
     "what_to_look_for": "Building directory listing",
     "vip_standard": "Building directory listing included",
     "others_acceptable": "Standard",
     "red_flag": "No directory signage rights", "priority": "High",
     "anticipated_action": "comment"},

    {"section": "Signage – Monument",
     "what_to_look_for": "Monument sign panel",
     "vip_standard": "Monument panel available (may be for a fee)",
     "others_acceptable": "Not available",
     "red_flag": "Explicitly prohibited", "priority": "High",
     "anticipated_action": "comment"},

    {"section": "Building-Mounted Signs",
     "what_to_look_for": "Exterior building signage",
     "vip_standard": "Allowed subject to code and LL approval",
     "others_acceptable": "Not included",
     "red_flag": "Explicitly prohibited", "priority": "Medium",
     "anticipated_action": "comment"},

    # ── HVAC / Utilities (operational) ──────────────────────────────────────
    {"section": "After-Hours HVAC",
     "what_to_look_for": "After-hours HVAC cost and availability",
     "vip_standard": "$20–$40/hr; Not an issue if building HVAC hours cover our clinic hours",
     "others_acceptable": "Up to $50/hr",
     "red_flag": ">$50/hr or HVAC unavailable during clinic hours", "priority": "Medium",
     "anticipated_action": "comment"},

    # ── Legal / Structural ───────────────────────────────────────────────────
    {"section": "Relocation Clause",
     "what_to_look_for": "Can LL relocate Tenant?",
     "vip_standard": "No relocation clause",
     "others_acceptable": "Relocation with protections",
     "red_flag": "LL can relocate Tenant without meaningful protection", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "LL Access",
     "what_to_look_for": "Landlord access to premises",
     "vip_standard": "48-hour notice except emergencies",
     "others_acceptable": "24-hour notice",
     "red_flag": "LL can enter without notice", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Quiet Enjoyment",
     "what_to_look_for": "Quiet enjoyment covenant",
     "vip_standard": "Strong quiet enjoyment covenant",
     "others_acceptable": "Standard",
     "red_flag": "No quiet enjoyment covenant", "priority": "Medium",
     "anticipated_action": "comment"},

    {"section": "Insurance – Tenant",
     "what_to_look_for": "Tenant insurance requirements",
     "vip_standard": "Reasonable medical office limits ($1M/$2M CGL + professional liability)",
     "others_acceptable": "Standard",
     "red_flag": "Excessive insurance requirements", "priority": "High",
     "anticipated_action": "comment"},

    {"section": "Insurance – LL",
     "what_to_look_for": "LL maintains building insurance",
     "vip_standard": "LL maintains building and liability insurance",
     "others_acceptable": "Standard",
     "red_flag": "No LL insurance obligation", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Indemnity",
     "what_to_look_for": "Indemnification structure",
     "vip_standard": "Mutual indemnity based on negligence",
     "others_acceptable": "Standard",
     "red_flag": "One-sided indemnity favoring LL", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "SNDA",
     "what_to_look_for": "Subordination, Non-Disturbance and Attornment",
     "vip_standard": "LL provides SNDA protecting Tenant",
     "others_acceptable": "Standard subordination without NDA",
     "red_flag": "No SNDA; Tenant subordinated without protection", "priority": "Low",
     "anticipated_action": "redline"},

    {"section": "Estoppel Certificates",
     "what_to_look_for": "Frequency of estoppel demands",
     "vip_standard": "Once per year maximum",
     "others_acceptable": "Standard",
     "red_flag": "Uncapped estoppel demands", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Surrender",
     "what_to_look_for": "Surrender obligations",
     "vip_standard": "Broom clean + remove specialty items only",
     "others_acceptable": "Standard",
     "red_flag": "Tenant must restore to original condition", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Restoration",
     "what_to_look_for": "Restoration obligations",
     "vip_standard": "LL cannot require restoration unless specialty alterations",
     "others_acceptable": "Standard",
     "red_flag": "LL can require full restoration of all improvements", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "LL Default",
     "what_to_look_for": "Tenant rights if LL defaults",
     "vip_standard": "Tenant has termination and self-help rights if LL fails to cure",
     "others_acceptable": "Standard cure period",
     "red_flag": "No Tenant remedy for LL default", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Arbitration / Legal Venue",
     "what_to_look_for": "Dispute resolution venue",
     "vip_standard": "Tenant-friendly or neutral venue",
     "others_acceptable": "Standard",
     "red_flag": "LL-favorable venue; mandatory arbitration without carve-outs", "priority": "Medium",
     "anticipated_action": "redline"},

    # ── Environmental & Building Integrity ───────────────────────────────────
    {"section": "Environmental / Mold",
     "what_to_look_for": "LL handles environmental hazards",
     "vip_standard": "LL handles all pre-existing environmental hazards and mold",
     "others_acceptable": "Standard",
     "red_flag": "Tenant assumes environmental liability", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Roof Leaks",
     "what_to_look_for": "LL responsible for roof repairs",
     "vip_standard": "LL repairs all roof leaks promptly",
     "others_acceptable": "Standard",
     "red_flag": "Tenant responsible for roof leak repairs", "priority": "High",
     "anticipated_action": "redline"},

    {"section": "Plumbing Issues",
     "what_to_look_for": "LL responsible for plumbing",
     "vip_standard": "LL repairs all plumbing except Tenant-caused damage",
     "others_acceptable": "Standard",
     "red_flag": "Tenant responsible for plumbing", "priority": "High",
     "anticipated_action": "redline"},

    # ── Technology & Access ──────────────────────────────────────────────────
    {"section": "Telecom / Fiber Access",
     "what_to_look_for": "Multiple telecom vendors allowed",
     "vip_standard": "Multiple telecom vendors permitted; LL provides conduit access",
     "others_acceptable": "Single preferred vendor",
     "red_flag": "Single exclusive vendor; no fiber access", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "IT Room Location",
     "what_to_look_for": "LL provides access to IT/telecom room",
     "vip_standard": "LL provides reasonable access to building IT/telecom room",
     "others_acceptable": "Standard",
     "red_flag": "No IT room access", "priority": "Medium",
     "anticipated_action": "redline"},

    {"section": "Access Control System",
     "what_to_look_for": "Suite access control",
     "vip_standard": "Tenant controls suite access system",
     "others_acceptable": "Building access only",
     "red_flag": "LL controls suite access", "priority": "Medium",
     "anticipated_action": "redline"},

    # ── LL Work Letter ───────────────────────────────────────────────────────
    {"section": "LL Work Letter",
     "what_to_look_for": "Detailed scope of LL work + timeline",
     "vip_standard": "Detailed scope + construction timeline + penalty provisions",
     "others_acceptable": "Basic scope",
     "red_flag": "No work letter; vague scope", "priority": "High",
     "anticipated_action": "redline"},

    # ── Entity Name ──────────────────────────────────────────────────────────
    {"section": "Entity Name",
     "what_to_look_for": "Legal entity name used as Tenant throughout the lease",
     "vip_standard": "National VIP Centers Management LLC",
     "others_acceptable": "",
     "red_flag": "Any other entity name (e.g. 'VIP Medical Group', individual name, or any variation)",
     "priority": "High",
     "anticipated_action": "redline"},
]


DEAL_SUMMARY_FIELDS = [
    # ── Always included in summary paragraph ────────────────────────────────
    {"field": "RSF",                    "vip_standard": "Fixed at lease execution",            "include_in_paragraph": True},
    {"field": "Annual Escalation",      "vip_standard": "3% standard",                         "include_in_paragraph": True},
    {"field": "Term Length",            "vip_standard": "60–120 months",                        "include_in_paragraph": True},
    {"field": "Abatement Months",       "vip_standard": "3–6 months depending on TI",           "include_in_paragraph": True},
    {"field": "TI Allowance",           "vip_standard": "$100–$130 per RSF",                    "include_in_paragraph": True},
    {"field": "Total Buildout Cost",    "vip_standard": "Varies",                               "include_in_paragraph": True},

    # ── Included only when variance from VIP standard ────────────────────────
    {"field": "Security Deposit",       "vip_standard": "1–2 months",                          "include_in_paragraph": "variance"},
    {"field": "Guaranty Required",      "vip_standard": "No personal; corporate acceptable",   "include_in_paragraph": "variance"},
    {"field": "Commencement Date",      "vip_standard": "Upon SC",                             "include_in_paragraph": "variance"},
    {"field": "Rent Commencement",      "vip_standard": "Post-SC + abatement",                 "include_in_paragraph": "variance"},
    {"field": "Relocation Clause",      "vip_standard": "Not permitted",                       "include_in_paragraph": "variance"},

    # ── In the table only (not in paragraph) ────────────────────────────────
    {"field": "Base Rent (Year 1)",     "vip_standard": "Market rate",                         "include_in_paragraph": False},
    {"field": "TI Deadline",            "vip_standard": "18–24 months minimum",                "include_in_paragraph": False},
    {"field": "Construction Mgmt Fee",  "vip_standard": "0–3%",                                "include_in_paragraph": False},
    {"field": "Operating Expenses",     "vip_standard": "Capped 5% non-cumulative",            "include_in_paragraph": False},
    {"field": "Proportionate Share",    "vip_standard": "Fixed for term",                      "include_in_paragraph": False},
    {"field": "Parking",                "vip_standard": "Pro-rata free parking",               "include_in_paragraph": False},
    {"field": "Signage (Door)",         "vip_standard": "Included",                            "include_in_paragraph": False},
    {"field": "Signage (Directory)",    "vip_standard": "Included",                            "include_in_paragraph": False},
    {"field": "Signage (Monument)",     "vip_standard": "Panel included when available",       "include_in_paragraph": False},
    {"field": "Use Clause",             "vip_standard": "Medical office without restriction",  "include_in_paragraph": False},
    {"field": "Zoning Guarantee",       "vip_standard": "LL confirms medical use permitted",   "include_in_paragraph": False},
    {"field": "Holdover Rate",          "vip_standard": "110% (1.1x)",                         "include_in_paragraph": False},
    {"field": "SNDA",                   "vip_standard": "LL provides",                         "include_in_paragraph": False},
    {"field": "Tenant Entity Name",     "vip_standard": "National VIP Centers Management LLC", "include_in_paragraph": False},
]


# ── Compatibility aliases ────────────────────────────────────────────────────
CHECKLIST_ITEMS = CHECKLIST   # analyzer.py uses this name


def build_checklist_text() -> str:
    """Build the checklist text block sent to Claude in the prompt."""
    lines = []
    for item in CHECKLIST:
        action = item.get("anticipated_action", "comment")
        notes = item.get("notes", "")
        line = (
            f"• {item['section']} [{item['priority']}]: "
            f"VIP Standard = {item['vip_standard']} | "
            f"Red Flag = {item['red_flag']} | "
            f"Anticipated Action = {action}"
        )
        if notes:
            line += f" | Notes = {notes}"
        lines.append(line)
    return "\n".join(lines)

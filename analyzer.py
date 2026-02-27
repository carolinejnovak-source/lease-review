"""
Claude lease analysis — returns structured review table and redline suggestions.
"""
import json, os, re
import anthropic
from checklist import CHECKLIST_ITEMS, DEAL_SUMMARY_FIELDS, KEY_TERMS_PROMPT, build_checklist_text

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-5")

# VIP standards that are ranges — for these we insert comments, not redlines
RANGE_PATTERN = re.compile(
    r'\d[\d,\.]*\s*[–\-]\s*\d|'       # numeric range: 3–6, 100–130, $40–$60
    r'\d+%\s*[–\-]\s*\d+%|'            # percent range: 4–5%
    r'\$\d.*\$\d|'                      # dollar ranges: $100–$130
    r'\d+\s*(months?|weeks?|days?)\s*(minimum|max|or|to)\s*\d+',  # time ranges
    re.IGNORECASE
)


def _is_range_standard(vip_standard: str) -> bool:
    return bool(RANGE_PATTERN.search(vip_standard or ""))


def get_client():
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


SYSTEM_PROMPT = """You are a senior commercial real estate attorney specializing in medical office leases for VIP Medical Group (a multi-location vein treatment and interventional radiology practice). You review leases with a tenant-favorable perspective, ensuring they meet VIP Medical Group's specific standards.

You must return ONLY valid JSON — no markdown, no code fences, no extra commentary. Just the raw JSON object."""


ANALYSIS_PROMPT_TEMPLATE = """Review the following commercial lease against VIP Medical Group's standards. Extract deal terms and identify issues.

=== VIP MEDICAL GROUP CHECKLIST ===
{checklist}

{loi_section}=== LEASE TEXT ===
{lease_text}

Return a single JSON object with this exact structure:
{{
  "property_name": "name/address of the property if identifiable",
  "key_terms": [
    {{"label": "Location", "level": 1, "value": "full address as extracted from lease"}},
    {{"label": "Size", "level": 1, "value": "square footage"}},
    "... (see KEY TERMS STRUCTURE below for all required items)"
  ],
  "deal_summary": [
    {{
      "field": "field name",
      "lease_value": "what the lease actually says (quote directly from the lease — do NOT say 'not specified' unless you have read the full relevant section and it truly is absent)",
      "vip_standard": "our standard",
      "status": "ok" | "issue" | "not_found"
    }}
  ],
  "review": [
    {{
      "section": "Lease Section name",
      "priority": "High" | "Medium" | "Low",
      "vip_standard": "our standard",
      "lease_says": "verbatim quote or summary of what the lease actually says; 'Not addressed' if truly silent",
      "status": "pass" | "fail" | "review",
      "issue": "specific problem description if fail/review, else null",
      "proposed_language": "proposed lease language to fix the issue — see rules below",
      "lease_section": "REQUIRED — the section number where this clause appears (e.g. '3.1', '14.3', 'Article IV', 'Exhibit C §2'). If the clause is absent from the lease, use '999'. This field is mandatory for every item."
    }}
  ],
  "redlines": [
    {{
      "section": "section name",
      "find": "EXACT verbatim text from the lease to be replaced (keep short — one sentence or clause only)",
      "replace": "proposed replacement language",
      "reason": "brief reason for change"
    }}
  ],
  "additional_issues": [
    {{
      "title": "short title for the issue",
      "description": "description of the non-standard or unusual clause",
      "lease_text": "verbatim quote from the lease",
      "concern": "why this is a red flag or unusual",
      "suggested_action": "what VIP's attorney should do"
    }}
  ]
}}

=== CRITICAL RULES FOR PROPOSED LANGUAGE ===
1. RANGE STANDARDS: If the VIP standard is expressed as a range (e.g., "3–6 months", "$100–$130 per RSF", "4–5%", "100–120%"), set proposed_language to null. The system will automatically insert a comment annotation in the document for the attorney to negotiate the specific number.
2. NO INVENTED NUMBERS: Never choose a specific number from within a range on your own. Do not write "4 months" when the standard says "3–6 months". Do not write "$115 per RSF" when the standard says "$100–$130 per RSF".
3. MISSING CLAUSES: If the lease is entirely silent on a topic (no text to replace), set proposed_language to language that can be ADDED to the lease. Do NOT generate a redline entry for it (since there is no "find" text).
4. VERBATIM FIND TEXT: The "find" field in redlines must be EXACT verbatim text from the lease — copy it character-for-character. Keep it short: one sentence or clause, not a full paragraph. IMPORTANT: redlines are applied to EVERY occurrence of the find text in the document — so make the find text specific enough that it only matches the clause you intend to change. For example, use "shall commence on JUNE 1, 2026" rather than just "JUNE 1, 2026" if the date appears in other contexts.
5. DEAL SUMMARY ACCURACY: For deal_summary fields, read the FULL lease text carefully before saying a value is "not specified." Many leases define base rent, escalation, and RSF in early sections (Basic Terms, Summary of Basic Lease Terms, or similar). Quote the actual lease value.
6. LOI SUPERSEDES VIP STANDARD: If an LOI was provided, agreed LOI terms override VIP standards. Example: if the LOI specifies 7% annual escalation, the lease must match 7% — do NOT flag this as an issue just because VIP standard is 3%. Do flag it if the lease deviates from the LOI. CRITICAL EXCEPTION: A fixed calendar Commencement Date (e.g. "June 1, 2026") is NEVER treated as an LOI-agreed term unless the LOI explicitly states that specific date as the Commencement Date. "The parties have agreed that [date] shall be the Commencement Date" language in the lease body is NOT evidence of LOI agreement — it is a red flag requiring a redline. Always redline fixed-date commencement to SC-triggered language.
7. DEFAULT TO COMMENT: If you are uncertain whether a clause warrants a redline, or if the lease language is ambiguous, default to generating a comment annotation rather than a redline. A comment is always safer than an incorrect redline. EXCEPTION: Entity Name ALWAYS gets a redline — never a comment, regardless of uncertainty.
8. ADDITIONAL ISSUES: After reviewing all checklist items, identify any unusual, non-standard, or red-flag clauses in the lease that are NOT covered by the checklist.
9. LEASE_SECTION IS MANDATORY: Every review item MUST include a "lease_section" field with the actual section number (e.g. "3.1", "14.3", "Article IV"). Do not omit this field. If the clause is absent from the lease, use "999". This is used to sort issues in document order. Add these to the "additional_issues" array. Examples: unusual termination rights, atypical assignment restrictions, non-standard force majeure, unusual co-tenancy requirements, etc. If none, return an empty array.

=== RULES FOR REDLINES ===
- A single checklist item CAN generate multiple redline entries if the same issue appears in multiple places with different text (e.g. "06/01/2026" and "JUNE 1, 2026" are two separate occurrences of a fixed Commencement Date — generate a separate redline entry for each with its own "find" text).
- Each checklist item has an "Anticipated Action" — follow it:
  • "redline" → generate a redlines entry for this section when it fails
  • "comment" → do NOT generate a redline; use proposed_language in review item only (system inserts comment annotation)
  • "redline_if_red_flag" → only generate a redline if the red flag condition is explicitly present; otherwise comment only
  • "comment_only" → always comment, never redline regardless of severity
- When in doubt, default to comment (never generate a redline you are not confident about)
- Only for genuine issues (fail or review status)
- Skip redline entry entirely if the clause is MISSING from the lease (nothing to replace)
- Maximum 20 redlines — High and Medium priority only
- If VIP standard is a range → no redline, system inserts comment instead
- ENTITY NAME: This is NON-NEGOTIABLE — do NOT default to comment. If the tenant entity name anywhere in the lease is not exactly "National VIP Centers Management LLC", you MUST generate a redline entry. Use the shortest verbatim wrong name as the "find" field (e.g. if the lease says "VIP Medical Group, a Texas corporation" use "VIP Medical Group" as find). The "replace" must be "National VIP Centers Management LLC". Generate one redline per distinct wrong name found. If you cannot identify the exact find text, still generate a redline with your best verbatim match — do NOT fall back to a comment for entity name.
- ESTOPPEL CERTIFICATES: "Once per year maximum" is NOT a range — it is a specific limit. You MUST generate a redline that ADDS the following sentence after the existing estoppel request language: "Notwithstanding the foregoing, Landlord shall not request more than one (1) estoppel certificate from Tenant in any twelve (12) month period, except in connection with a bona fide sale or refinancing of the Building." Find the last sentence of the estoppel clause and use it as the "find" text; the "replace" text is that same sentence followed by the new limitation sentence.
- RENT PAYMENT METHOD: VIP standard is ACH/wire ONLY. (a) If the lease requires certified check or physical mail only, status="fail", replace with "ACH/wire transfer to Landlord's designated bank account." (b) If the lease allows ACH but ALSO allows mailing/physical check (e.g., "ACH or wire transfer... or mailed to Landlord at the following address"), status="fail" — NOT pass — because the mailing option must be removed. Generate a redline that REMOVES the mailing/physical-payment option. Find the mailing clause verbatim and replace it with a period or nothing. Do NOT leave any physical-mail payment option in the proposed language. CRITICAL: If ACH + mailing exist together, the status is "fail" even though ACH is present.
- CERTIFICATE OF OCCUPANCY RESPONSIBILITY: If the lease says Landlord is responsible for obtaining the CO but includes softening language ("however, Landlord agrees to assist and cooperate" or similar), the redline replace text must DELETE the softening clause entirely. The replace should state only that Landlord is solely responsible at Landlord's sole cost and expense. Do not preserve any language suggesting Tenant bears any co-responsibility.
{loi_rules}"""


DEAL_SUMMARY_FIELDS_TEXT = "\n".join([
    f"- {f['field']}: VIP Standard = {f['vip_standard']}"
    for f in DEAL_SUMMARY_FIELDS
])


def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def _repair_truncated_json(text: str) -> dict:
    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found in response")
    text = text[start:]

    depth = 0
    in_str = False
    escape = False
    last_valid_end = -1
    for i, c in enumerate(text):
        if escape:
            escape = False
            continue
        if c == '\\' and in_str:
            escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c in '{[':
            depth += 1
        elif c in '}]':
            depth -= 1
            if depth == 0:
                last_valid_end = i
                break

    if last_valid_end > 0:
        try:
            return json.loads(text[:last_valid_end + 1])
        except Exception:
            pass

    last_brace = text.rfind('}')
    if last_brace > 0:
        snippet = text[:last_brace + 1]
        try:
            return json.loads(snippet)
        except Exception:
            pass

    raise ValueError("Could not repair truncated JSON")


def analyze_lease(lease_text: str, loi_text: str = None) -> dict:
    """
    Send lease text (and optional LOI text) to Claude for full analysis.
    Returns dict with deal_summary, review, redlines.
    """
    client = get_client()

    # Allow up to ~400k chars — well within Claude's 200k token window
    MAX_CHARS = 400000
    if len(lease_text) > MAX_CHARS:
        lease_text = lease_text[:MAX_CHARS] + "\n\n[DOCUMENT TRUNCATED — remaining text exceeds extraction limit]"

    if loi_text and len(loi_text) > 50000:
        loi_text = loi_text[:50000] + "\n\n[LOI TRUNCATED]"

    checklist_text = build_checklist_text()
    full_checklist = checklist_text + "\n\nDEAL SUMMARY FIELDS TO EXTRACT:\n" + DEAL_SUMMARY_FIELDS_TEXT + "\n\n" + KEY_TERMS_PROMPT

    # Mark range standards in checklist so Claude sees which ones apply
    range_sections = [
        item['section'] for item in CHECKLIST_ITEMS
        if _is_range_standard(item.get('vip_standard', ''))
    ]
    range_note = ""
    if range_sections:
        range_note = (
            "\nRANGE STANDARD SECTIONS (set proposed_language=null for these if they fail): "
            + ", ".join(range_sections)
        )

    # LOI section
    if loi_text:
        loi_section = f"""=== LETTER OF INTENT (LOI) ===
{loi_text}

IMPORTANT: Cross-reference the LOI against the lease. For each term negotiated in the LOI,
verify it is reflected in the lease. Flag any LOI term that is:
- Missing from the lease entirely
- Less favorable in the lease than what was agreed in the LOI
- Materially different from what the LOI specified
Add these as HIGH priority "LOI Discrepancy" issues in the review array.

"""
        loi_rules = "- LOI DISCREPANCIES: Flag as HIGH priority with section = 'LOI: [term name]'"
    else:
        loi_section = ""
        loi_rules = ""

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        checklist=full_checklist + range_note,
        lease_text=lease_text,
        loi_section=loi_section,
        loi_rules=loi_rules,
    )

    response = client.messages.create(
        model=MODEL,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=16000,
        temperature=0.1,
    )

    raw = _extract_json(response.content[0].text)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = _repair_truncated_json(raw)

    result.setdefault("property_name", "Unknown Property")
    result.setdefault("deal_summary", [])
    result.setdefault("review", [])
    result.setdefault("redlines", [])

    # Remove redlines for range standards — comments will be used instead
    result["redlines"] = [
        r for r in result["redlines"]
        if not _is_range_standard(
            next((i.get('vip_standard','') for i in CHECKLIST_ITEMS if i['section'] == r.get('section','')), '')
        )
    ]

    return result

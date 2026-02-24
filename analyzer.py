"""
Claude lease analysis — returns structured review table and redline suggestions.
"""
import json, os, re
import anthropic
from checklist import CHECKLIST_ITEMS, DEAL_SUMMARY_FIELDS, build_checklist_text

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
      "proposed_language": "proposed lease language to fix the issue — see rules below"
    }}
  ],
  "redlines": [
    {{
      "section": "section name",
      "find": "EXACT verbatim text from the lease to be replaced (keep short — one sentence or clause only)",
      "replace": "proposed replacement language",
      "reason": "brief reason for change"
    }}
  ]
}}

=== CRITICAL RULES FOR PROPOSED LANGUAGE ===
1. RANGE STANDARDS: If the VIP standard is expressed as a range (e.g., "3–6 months", "$100–$130 per RSF", "4–5%", "100–120%"), set proposed_language to null. The system will automatically insert a comment annotation in the document for the attorney to negotiate the specific number.
2. NO INVENTED NUMBERS: Never choose a specific number from within a range on your own. Do not write "4 months" when the standard says "3–6 months". Do not write "$115 per RSF" when the standard says "$100–$130 per RSF".
3. MISSING CLAUSES: If the lease is entirely silent on a topic (no text to replace), set proposed_language to language that can be ADDED to the lease. Do NOT generate a redline entry for it (since there is no "find" text).
4. VERBATIM FIND TEXT: The "find" field in redlines must be EXACT verbatim text from the lease — copy it character-for-character. Keep it short: one sentence or clause, not a full paragraph.
5. DEAL SUMMARY ACCURACY: For deal_summary fields, read the FULL lease text carefully before saying a value is "not specified." Many leases define base rent, escalation, and RSF in early sections (Basic Terms, Summary of Basic Lease Terms, or similar). Quote the actual lease value.

=== RULES FOR REDLINES ===
- Only for genuine issues (fail or review status)
- Skip redline entry entirely if the clause is MISSING from the lease (nothing to replace)
- Maximum 20 redlines — High and Medium priority only
- If VIP standard is a range → no redline, system inserts comment instead
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
    full_checklist = checklist_text + "\n\nDEAL SUMMARY FIELDS TO EXTRACT:\n" + DEAL_SUMMARY_FIELDS_TEXT

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

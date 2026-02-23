"""
Claude lease analysis — returns structured review table and redline suggestions.
"""
import json, os, re
import anthropic
from checklist import CHECKLIST_ITEMS, DEAL_SUMMARY_FIELDS, build_checklist_text

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-5")

def get_client():
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a senior commercial real estate attorney specializing in medical office leases for VIP Medical Group (a multi-location vein treatment and interventional radiology practice). You review leases with a tenant-favorable perspective, ensuring they meet VIP Medical Group's specific standards.

You must return ONLY valid JSON — no markdown, no code fences, no extra commentary. Just the raw JSON object."""

ANALYSIS_PROMPT_TEMPLATE = """Review the following commercial lease against VIP Medical Group's standards. Extract deal terms and identify issues.

=== VIP MEDICAL GROUP CHECKLIST ===
{checklist}

=== LEASE TEXT ===
{lease_text}

Return a single JSON object with this exact structure:
{{
  "property_name": "name/address of the property if identifiable",
  "deal_summary": [
    {{
      "field": "field name",
      "lease_value": "what the lease says or 'Not specified'",
      "vip_standard": "our standard",
      "status": "ok" | "issue" | "not_found"
    }}
  ],
  "review": [
    {{
      "section": "Lease Section name",
      "priority": "High" | "Medium" | "Low",
      "vip_standard": "our standard",
      "lease_says": "verbatim quote or summary of what the lease actually says; 'Not addressed' if silent",
      "status": "pass" | "fail" | "review",
      "issue": "specific problem description if fail/review, else null",
      "proposed_language": "proposed lease language to fix the issue if fail/review, else null"
    }}
  ],
  "redlines": [
    {{
      "section": "section name",
      "find": "EXACT verbatim text from the lease to be replaced (keep short and specific — one sentence or clause, not a full paragraph)",
      "replace": "proposed replacement language",
      "reason": "brief reason for change"
    }}
  ]
}}

IMPORTANT for redlines:
- Only include redlines for genuine issues (fail or review status)
- The "find" text must be EXACTLY as it appears in the lease document (verbatim)
- Keep "find" text short and specific — just the offending clause, not an entire section
- If a clause is missing entirely (not in the lease), skip the redline for that item
- Maximum 20 redlines — focus on High and Medium priority issues
"""

DEAL_SUMMARY_FIELDS_TEXT = "\n".join([
    f"- {f['field']}: VIP Standard = {f['vip_standard']}"
    for f in DEAL_SUMMARY_FIELDS
])


def _extract_json(text: str) -> str:
    """Strip markdown fences and extract raw JSON from model output."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def analyze_lease(lease_text: str) -> dict:
    """
    Send lease text to Claude for full analysis.
    Returns dict with deal_summary, review, redlines.
    """
    client = get_client()

    # Truncate to ~100k chars to stay within context limits
    if len(lease_text) > 100000:
        lease_text = lease_text[:100000] + "\n\n[DOCUMENT TRUNCATED DUE TO LENGTH]"

    checklist_text = build_checklist_text()
    full_checklist = checklist_text + "\n\nDEAL SUMMARY FIELDS TO EXTRACT:\n" + DEAL_SUMMARY_FIELDS_TEXT

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        checklist=full_checklist,
        lease_text=lease_text,
    )

    response = client.messages.create(
        model=MODEL,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt},
        ],
        max_tokens=8000,
        temperature=0.1,
    )

    raw = _extract_json(response.content[0].text)
    result = json.loads(raw)

    # Ensure all expected keys are present
    result.setdefault("property_name", "Unknown Property")
    result.setdefault("deal_summary", [])
    result.setdefault("review", [])
    result.setdefault("redlines", [])

    return result

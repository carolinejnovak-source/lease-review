"""
Apply tracked changes (redlines) and comment annotations to a .docx file.
Produces real attorney-style tracked changes (w:ins/w:del) plus highlighted
comment annotations for issues that can't be redlined directly.
"""
import re
from copy import deepcopy
from datetime import datetime, timezone
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

AUTHOR = "VIP Medical Legal"
DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Text helpers ─────────────────────────────────────────────────────────────

def _normalize(text):
    """Collapse whitespace for fuzzy matching."""
    return re.sub(r'\s+', ' ', text).strip()


# ── XML helpers ──────────────────────────────────────────────────────────────

def _make_run(text, rpr=None):
    r = OxmlElement("w:r")
    if rpr is not None:
        r.append(deepcopy(rpr))
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def _make_del(text, rpr, change_id):
    del_el = OxmlElement("w:del")
    del_el.set(qn("w:id"), str(change_id))
    del_el.set(qn("w:author"), AUTHOR)
    del_el.set(qn("w:date"), DATE)
    r = OxmlElement("w:r")
    if rpr is not None:
        r.append(deepcopy(rpr))
    dt = OxmlElement("w:delText")
    dt.set(qn("xml:space"), "preserve")
    dt.text = text
    r.append(dt)
    del_el.append(r)
    return del_el


def _make_ins(text, rpr, change_id):
    ins_el = OxmlElement("w:ins")
    ins_el.set(qn("w:id"), str(change_id))
    ins_el.set(qn("w:author"), AUTHOR)
    ins_el.set(qn("w:date"), DATE)
    r = OxmlElement("w:r")
    if rpr is not None:
        r.append(deepcopy(rpr))
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    ins_el.append(r)
    return ins_el


def _get_rpr(para):
    for run in para.runs:
        rpr = run._r.find(qn("w:rPr"))
        if rpr is not None:
            return deepcopy(rpr)
    return None


# ── Apply a single redline to one paragraph ──────────────────────────────────

def _apply_to_para(para, find_text, replace_text, change_id):
    """
    Try exact then normalized-whitespace match.
    Returns (new_change_id, found_bool).
    """
    full_text = "".join(run.text for run in para.runs)

    actual_find = find_text
    actual_full = full_text

    if find_text not in full_text:
        norm_full = _normalize(full_text)
        norm_find = _normalize(find_text)
        if norm_find in norm_full:
            actual_find = norm_find
            actual_full = norm_full
        else:
            return change_id, False

    rpr = _get_rpr(para)
    idx = actual_full.index(actual_find)
    before = actual_full[:idx]
    after  = actual_full[idx + len(actual_find):]

    pPr = para._p.find(qn("w:pPr"))
    for child in list(para._p):
        if child.tag != qn("w:pPr"):
            para._p.remove(child)
    if pPr is not None and para._p.find(qn("w:pPr")) is None:
        para._p.insert(0, pPr)

    if before:
        para._p.append(_make_run(before, rpr))
    para._p.append(_make_del(actual_find, rpr, change_id))
    change_id += 1
    para._p.append(_make_ins(replace_text, rpr, change_id))
    change_id += 1
    if after:
        para._p.append(_make_run(after, rpr))

    return change_id, True


# ── Comment annotation ────────────────────────────────────────────────────────

def _insert_comment_annotation(doc, section_name, issue_text, vip_standard="") -> int:
    """
    Insert a visually distinctive yellow-highlighted comment annotation
    near the relevant section of the document.
    Returns the paragraph index (0-based) where the annotation was anchored,
    or 999999 if no anchor was found.
    """
    # Find the best paragraph: keywords from section name
    target_para = None
    target_para_idx = 999999
    keywords = [w for w in section_name.lower().split() if len(w) > 3]

    for para_idx, para in enumerate(doc.paragraphs):
        if not para.text.strip():
            continue
        para_lower = para.text.lower()
        if keywords and any(kw in para_lower for kw in keywords):
            target_para = para
            target_para_idx = para_idx
            break

    # Also search tables if not found
    if target_para is None:
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        para_lower = para.text.lower()
                        if keywords and any(kw in para_lower for kw in keywords):
                            target_para = para
                            break
                    if target_para: break
                if target_para: break
            if target_para: break

    # Build the comment paragraph element
    comment_para = OxmlElement('w:p')

    # Paragraph properties: yellow background
    pPr = OxmlElement('w:pPr')
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'FFFF99')
    pPr.append(shd)
    comment_para.append(pPr)

    # Run: bold, red, yellow highlight
    r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    bold = OxmlElement('w:b')
    color = OxmlElement('w:color')
    color.set(qn('w:val'), 'CC0000')
    highlight = OxmlElement('w:highlight')
    highlight.set(qn('w:val'), 'yellow')
    shd2 = OxmlElement('w:shd')
    shd2.set(qn('w:val'), 'clear')
    shd2.set(qn('w:color'), 'auto')
    shd2.set(qn('w:fill'), 'FFFF99')
    rPr.extend([bold, color, highlight, shd2])
    r.append(rPr)

    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    text = f'⚑ VIP LEGAL REVIEW \u2014 {section_name.upper()}: {issue_text}'
    if vip_standard:
        text += f'  |  VIP STANDARD: {vip_standard}'
    t.text = text
    r.append(t)
    comment_para.append(r)

    # Insert after target paragraph; if no match found, append to end of document
    if target_para is not None:
        target_para._p.addnext(comment_para)
    else:
        doc.element.body.append(comment_para)

    return target_para_idx


# ── Public API ───────────────────────────────────────────────────────────────

def apply_redlines(input_path: str, redlines: list, output_path: str,
                   issues: list = None) -> dict:
    """
    Apply tracked-change redlines to a .docx.
    For redlines where the find-text can't be located, insert a comment annotation.
    For High/Medium issues with no associated redline, also insert comment annotations.

    Returns: {applied, comments, skipped, section_actions}
      section_actions: {section_name: "redline"|"comment"}
    """
    doc = Document(input_path)
    change_id = 1
    applied = 0
    comments = 0
    section_actions = {}   # section -> "redline" | "comment"
    section_positions = {} # section -> paragraph index in document (for lease-order sort)

    # Index issues by section for quick lookup
    issues_by_section = {}
    for item in (issues or []):
        sec = item.get('section', '')
        if sec:
            issues_by_section[sec] = item

    # ── Step 1: Apply redlines ────────────────────────────────────────────────
    for redline in redlines:
        find    = (redline.get("find") or "").strip()
        replace = (redline.get("replace") or "").strip()
        reason  = redline.get("reason", "")
        section = redline.get("section", "")

        if not find or not replace or find == replace:
            continue

        found = False

        # Search paragraphs
        for para_idx, para in enumerate(doc.paragraphs):
            change_id, ok = _apply_to_para(para, find, replace, change_id)
            if ok:
                found = True
                applied += 1
                section_actions[section] = "redline"
                section_positions[section] = para_idx
                break

        # Search table cells
        if not found:
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            change_id, ok = _apply_to_para(para, find, replace, change_id)
                            if ok:
                                found = True
                                applied += 1
                                section_actions[section] = "redline"
                                # Tables don't have a simple global para_idx; use 999998
                                section_positions[section] = 999998
                                break
                        if found: break
                    if found: break
                if found: break

        # Text not found → fall back to comment annotation
        if not found and section not in section_actions:
            issue_obj  = issues_by_section.get(section, {})
            issue_text = issue_obj.get('issue') or reason or "Review required per VIP standards"
            vip_std    = issue_obj.get('vip_standard') or ""
            para_idx = _insert_comment_annotation(doc, section, issue_text, vip_std)
            section_actions[section] = "comment"
            section_positions[section] = para_idx
            comments += 1

    # ── Step 2: Comments for High/Medium issues without any redline ───────────
    if issues:
        for issue in issues:
            sec      = issue.get('section', '')
            priority = issue.get('priority', 'Low')
            status   = issue.get('status', 'pass')

            if status == 'pass' or priority not in ('High', 'Medium'):
                continue
            if sec in section_actions:
                continue  # Already handled

            issue_text = issue.get('issue') or 'Review required per VIP standards'
            vip_std    = issue.get('vip_standard') or ''
            para_idx = _insert_comment_annotation(doc, sec, issue_text, vip_std)
            section_actions[sec] = "comment"
            section_positions[sec] = para_idx
            comments += 1

    doc.save(output_path)
    return {
        "applied": applied,
        "comments": comments,
        "skipped": 0,
        "section_actions": section_actions,
        "section_positions": section_positions,
    }


def extract_text(docx_path: str) -> str:
    """Extract full text from a .docx file."""
    doc = Document(docx_path)
    parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            row_parts = []
            for cell in row.cells:
                if cell.text.strip():
                    row_parts.append(cell.text.strip())
            if row_parts:
                parts.append(" | ".join(row_parts))
    return "\n\n".join(parts)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF using pdfplumber."""
    import pdfplumber
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def create_docx_from_text(text: str, output_path: str) -> str:
    """
    Create a basic .docx from plain text (used for PDF → redlineable Word doc).
    Preserves paragraph structure.
    """
    doc = Document()
    for line in text.split('\n'):
        doc.add_paragraph(line)
    doc.save(output_path)
    return output_path

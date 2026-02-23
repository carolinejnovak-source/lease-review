"""
Apply tracked changes (redlines) to a .docx file using proper Word XML.
Produces a Word document with w:ins / w:del revision marks — real attorney-style redlines.
"""
import re
from copy import deepcopy
from datetime import datetime, timezone
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

AUTHOR = "VIP Medical Legal"
DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── XML helpers ──────────────────────────────────────────────────────────────

def _make_rpr(source_rpr=None):
    """Clone run properties or return None."""
    if source_rpr is not None:
        return deepcopy(source_rpr)
    return None


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


# ── Paragraph text extraction ────────────────────────────────────────────────

def _para_full_text(para):
    """Get full text of a paragraph including all runs."""
    return "".join(
        node.text or ""
        for node in para._p.iter()
        if node.tag in (qn("w:t"), qn("w:delText"))
    )


def _get_rpr(para):
    """Get run properties from first run in paragraph."""
    for run in para.runs:
        rpr = run._r.find(qn("w:rPr"))
        if rpr is not None:
            return deepcopy(rpr)
    return None


# ── Apply a single redline to one paragraph ──────────────────────────────────

def _apply_to_para(para, find_text, replace_text, change_id):
    """
    If find_text appears in para, replace it with tracked del+ins.
    Returns new change_id after applying.
    """
    full_text = "".join(run.text for run in para.runs)
    if find_text not in full_text:
        return change_id, False

    rpr = _get_rpr(para)
    idx = full_text.index(find_text)
    before = full_text[:idx]
    after  = full_text[idx + len(find_text):]

    # Remove all existing content runs (keep pPr and bookmarks etc.)
    pPr = para._p.find(qn("w:pPr"))
    # Clear paragraph children except pPr
    for child in list(para._p):
        if child.tag != qn("w:pPr"):
            para._p.remove(child)

    # Re-add pPr if it existed
    if pPr is not None and para._p.find(qn("w:pPr")) is None:
        para._p.insert(0, pPr)

    # Before text
    if before:
        para._p.append(_make_run(before, rpr))

    # Tracked deletion
    para._p.append(_make_del(find_text, rpr, change_id))
    change_id += 1

    # Tracked insertion
    para._p.append(_make_ins(replace_text, rpr, change_id))
    change_id += 1

    # After text
    if after:
        para._p.append(_make_run(after, rpr))

    return change_id, True


# ── Public API ───────────────────────────────────────────────────────────────

def apply_redlines(input_path: str, redlines: list, output_path: str) -> dict:
    """
    Apply list of {find, replace, reason} redlines to a .docx file.

    Returns a summary dict: {applied: int, skipped: int, skipped_items: list}
    """
    doc = Document(input_path)
    change_id = 1
    applied = 0
    skipped = []

    for redline in redlines:
        find    = (redline.get("find") or "").strip()
        replace = (redline.get("replace") or "").strip()
        reason  = redline.get("reason", "")
        section = redline.get("section", "")

        if not find or not replace or find == replace:
            continue

        found = False
        for para in doc.paragraphs:
            change_id, ok = _apply_to_para(para, find, replace, change_id)
            if ok:
                found = True
                applied += 1
                break

        if not found:
            # Try tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            change_id, ok = _apply_to_para(para, find, replace, change_id)
                            if ok:
                                found = True
                                applied += 1
                                break
                        if found:
                            break
                    if found:
                        break
                if found:
                    break

        if not found:
            skipped.append({"section": section, "find": find[:80], "reason": reason})

    doc.save(output_path)
    return {
        "applied": applied,
        "skipped": len(skipped),
        "skipped_items": skipped,
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

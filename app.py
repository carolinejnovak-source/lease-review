import os, uuid, threading, tempfile, subprocess, shutil, json
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file)
from auth import login_required, check_credentials
from error_log import register_error_handlers, log_error
from analyzer import analyze_lease
from redline import apply_redlines, extract_text, extract_text_from_pdf, create_docx_from_text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vip-lease-review-2026")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

register_error_handlers(app)

# ── Job persistence directory ─────────────────────────────────────────────────
JOBS_DIR = "/tmp/lease_jobs"
os.makedirs(JOBS_DIR, exist_ok=True)

# ── In-memory job store ───────────────────────────────────────────────────────
# {job_id: {status, progress, result, error, redlined_path, original_filename}}
JOBS = {}
JOBS_LOCK = threading.Lock()


def _persist_job(job_id, job):
    """Write a completed job to disk so it survives a container restart."""
    try:
        job_dir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        meta = {k: v for k, v in job.items() if k != "redlined_path"}
        with open(os.path.join(job_dir, "meta.json"), "w") as f:
            json.dump(meta, f)
        # Copy redlined docx into the job dir for durability
        if job.get("redlined_path") and os.path.exists(job["redlined_path"]):
            dest = os.path.join(job_dir, "redlined.docx")
            shutil.copy2(job["redlined_path"], dest)
            # Update in-memory entry to point to durable path
            with JOBS_LOCK:
                if job_id in JOBS:
                    JOBS[job_id]["redlined_path"] = dest
    except Exception:
        pass  # Persistence is best-effort; don't crash the main flow


def _load_job_from_disk(job_id):
    """Try to load a completed job from disk (fallback after restart)."""
    try:
        job_dir = os.path.join(JOBS_DIR, job_id)
        meta_path = os.path.join(job_dir, "meta.json")
        if not os.path.exists(meta_path):
            return None
        with open(meta_path) as f:
            job = json.load(f)
        redlined = os.path.join(job_dir, "redlined.docx")
        job["redlined_path"] = redlined if os.path.exists(redlined) else None
        return job
    except Exception:
        return None


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        if check_credentials(u, p):
            session["logged_in"] = True
            session["username"] = u
            return redirect(request.args.get("next") or url_for("index"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    if "lease" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("index"))

    f = request.files["lease"]
    if not f.filename:
        flash("No file selected.", "danger")
        return redirect(url_for("index"))

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".docx", ".doc", ".pdf"):
        flash("Please upload a .docx, .doc, or .pdf file.", "danger")
        return redirect(url_for("index"))

    # Save lease file to temp
    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    f.save(tmp_in.name)
    tmp_in.close()

    # Handle optional LOI file
    loi_path = None
    loi_f = request.files.get("loi")
    has_loi = request.form.get("has_loi") == "yes"
    if has_loi and loi_f and loi_f.filename:
        loi_ext = os.path.splitext(loi_f.filename)[1].lower()
        if loi_ext in (".docx", ".doc", ".pdf"):
            tmp_loi = tempfile.NamedTemporaryFile(delete=False, suffix=loi_ext)
            loi_f.save(tmp_loi.name)
            tmp_loi.close()
            loi_path = tmp_loi.name

    job_id = str(uuid.uuid4())
    original_filename = f.filename

    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "processing",
            "progress": "Extracting lease text…",
            "result": None,
            "error": None,
            "redlined_path": None,
            "original_filename": original_filename,
        }

    # Start background analysis
    t = threading.Thread(target=_run_analysis, args=(job_id, tmp_in.name, original_filename, loi_path))
    t.daemon = True
    t.start()

    return render_template("loading.html", job_id=job_id, filename=original_filename)


def _find_libreoffice():
    """Find the LibreOffice/soffice binary."""
    candidates = [
        "libreoffice", "soffice",
        "/usr/bin/libreoffice", "/usr/bin/soffice",
        "/usr/lib/libreoffice/program/soffice",
        "/opt/libreoffice/program/soffice",
    ]
    for c in candidates:
        found = shutil.which(c) or (os.path.isfile(c) and os.access(c, os.X_OK) and c)
        if found:
            return found
    raise RuntimeError(
        "LibreOffice not found. Please upload a .docx file instead, "
        "or convert your .doc file using Word: File → Save As → .docx"
    )


def _convert_to_docx(doc_path: str) -> str:
    """
    Convert a .doc file to .docx using LibreOffice headless.
    First tries opening directly as docx (some .doc files are actually OOXML).
    Falls back to LibreOffice conversion.
    Returns the path of the new .docx file (caller must delete it).
    """
    # Fast path: try opening as docx directly (handles misnamed files)
    try:
        from docx import Document as _Doc
        tmp_try = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_try.close()
        import shutil as _sh
        _sh.copy2(doc_path, tmp_try.name)
        _Doc(tmp_try.name)  # will raise if not valid docx
        return tmp_try.name
    except Exception:
        try:
            os.unlink(tmp_try.name)
        except Exception:
            pass

    # LibreOffice path
    soffice = _find_libreoffice()
    out_dir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [soffice, "--headless", "--convert-to", "docx",
             "--outdir", out_dir, doc_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
        base = os.path.splitext(os.path.basename(doc_path))[0]
        converted = os.path.join(out_dir, base + ".docx")
        if not os.path.exists(converted):
            files = [f for f in os.listdir(out_dir) if f.endswith(".docx")]
            if not files:
                raise RuntimeError("LibreOffice produced no .docx output.")
            converted = os.path.join(out_dir, files[0])
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp.close()
        shutil.move(converted, tmp.name)
        return tmp.name
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def _extract_lease_text(input_path: str) -> tuple:
    """
    Extract text from .docx, .doc, or .pdf.
    Returns (lease_text, processing_path, converted_path)
    where processing_path is the .docx to apply redlines to.
    """
    ext = input_path.lower().split('.')[-1]
    converted_path = None

    if ext == 'pdf':
        lease_text = extract_text_from_pdf(input_path)
        # Create a basic .docx for redlining (PDF can't be redlined directly)
        tmp_docx = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_docx.close()
        create_docx_from_text(lease_text, tmp_docx.name)
        processing_path = tmp_docx.name
        converted_path = tmp_docx.name
    elif ext == 'doc':
        converted_path = _convert_to_docx(input_path)
        processing_path = converted_path
        lease_text = extract_text(processing_path)
    else:
        processing_path = input_path
        lease_text = extract_text(processing_path)

    return lease_text, processing_path, converted_path


def _extract_loi_text(loi_path: str) -> str:
    """Extract text from LOI file (.docx, .doc, or .pdf)."""
    ext = loi_path.lower().split('.')[-1]
    if ext == 'pdf':
        return extract_text_from_pdf(loi_path)
    elif ext == 'doc':
        converted = _convert_to_docx(loi_path)
        try:
            return extract_text(converted)
        finally:
            try:
                os.unlink(converted)
            except Exception:
                pass
    else:
        return extract_text(loi_path)


def _run_analysis(job_id, input_path, original_filename, loi_path=None):
    tmp_out = None
    converted_path = None
    try:
        # Extract text and get the processing .docx path
        _update_job(job_id, progress="Extracting lease text…")
        lease_text, processing_path, converted_path = _extract_lease_text(input_path)

        if len(lease_text.strip()) < 100:
            raise ValueError("Could not extract readable text. Is this a valid document?")

        # Extract LOI text if provided
        loi_text = None
        if loi_path:
            _update_job(job_id, progress="Extracting LOI text…")
            try:
                loi_text = _extract_loi_text(loi_path)
            except Exception as e:
                log_error(e, context=f"LOI extraction job {job_id}")
                # Continue without LOI rather than failing the whole job

        loi_note = " (cross-referencing with LOI)" if loi_text else ""
        _update_job(job_id, progress=f"Sending to Claude AI for analysis{loi_note} — this takes 30–60 seconds…")
        result = analyze_lease(lease_text, loi_text=loi_text)

        # Gather all fail/review issues for comment annotation fallback
        all_issues = [
            item for item in result.get("review", [])
            if item.get("status") in ("fail", "review")
        ]

        _update_job(job_id, progress=f"Analysis complete. Applying redlines and comment annotations…")

        base = os.path.splitext(original_filename)[0]
        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_out.close()

        redline_summary = apply_redlines(
            processing_path,
            result.get("redlines", []),
            tmp_out.name,
            issues=all_issues,
            additional_issues=result.get("additional_issues", []),
        )
        result["redline_summary"] = redline_summary

        # Enrich each review item with action_taken (badge) and lease_position (sort order)
        section_actions    = redline_summary.get("section_actions", {})
        section_positions  = redline_summary.get("section_positions", {})
        import sys as _sys
        _sys.stderr.write(f"[positions] {sorted(section_positions.items(), key=lambda x:x[1])[:12]}\n")
        def _section_sort_key(lease_section: str) -> float:
            """Convert a lease section reference to a sortable float.
            '3.1' → 3.1, 'Article IV' → 4.0, 'Exhibit C' → 900.0, '999'/missing → 999.0
            """
            import re as _re2
            if not lease_section:
                return 999.0
            s = (lease_section or '').strip().lower()
            if s in ('999', 'not found', 'not addressed', 'n/a', ''):
                return 999.0
            roman = {'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7,'viii':8,
                     'ix':9,'x':10,'xi':11,'xii':12,'xiii':13,'xiv':14,'xv':15,
                     'xvi':16,'xvii':17,'xviii':18,'xix':19,'xx':20}
            # Exhibits → 800+
            if 'exhibit' in s:
                m = _re2.search(r'exhibit\s+([a-z])', s)
                base = 800 + (ord(m.group(1)) - ord('a')) if m else 800
                m2 = _re2.search(r'section\s+(\d+)', s)
                return base + (int(m2.group(1)) * 0.1 if m2 else 0)
            # "Article IV" or "Article 4"
            m = _re2.search(r'article\s+([ivxlcdm]+|\d+)', s)
            if m:
                g = m.group(1)
                val = roman.get(g) or (int(g) if g.isdigit() else 999)
                return float(val)
            # "Section 14.3" or bare "14.3" or "14"
            m = _re2.search(r'(\d+)(?:\.(\d+))?', s)
            if m:
                major = int(m.group(1))
                minor = int(m.group(2)) if m.group(2) else 0
                return major + minor * 0.01
            # Basic Terms / Summary at the top
            if any(w in s for w in ('basic terms', 'summary', 'recital', 'preamble')):
                return 0.5
            return 999.0

        # Exact "not addressed / not specified" phrases — always sort to bottom
        # regardless of whether a comment was inserted (comment could be a keyword
        # false-match anywhere in the doc, not a reliable position signal).
        EXACT_NOT_PRESENT = {
            "not addressed", "not specified", "not addressed.", "not specified.",
            "not found", "not mentioned", "not discussed", "silent",
        }

        def _is_exactly_absent(s: str) -> bool:
            """True when the AI said the clause is simply missing — no lease text quoted."""
            return s.strip().lower() in EXACT_NOT_PRESENT

        def _is_vaguely_absent(s: str) -> bool:
            """True when absent but with some extra context (e.g. 'Not addressed – no deadline')."""
            sl = s.strip().lower()
            return (sl.startswith("not addressed") or sl.startswith("not specified")) \
                   and sl not in EXACT_NOT_PRESENT

        for idx, item in enumerate(result.get("review", [])):
            sec         = item.get("section")
            lease_says  = (item.get("lease_says") or "")
            action      = section_actions.get(sec)
            pos         = section_positions.get(sec, 999999)

            if _is_exactly_absent(lease_says):
                # Clause is simply missing — keyword comment positions are unreliable
                pos = 999999
            elif _is_vaguely_absent(lease_says) and not action:
                # Absent with context but no action taken — still unreliable
                pos = 999999

            # Primary sort: section number from AI (most accurate)
            # Fallback: paragraph position from doc scan
            sec_ref  = item.get("lease_section") or ""
            sec_sort = _section_sort_key(sec_ref)
            if sec_sort >= 999.0 and pos < 999999:
                # AI didn't give a section number — fall back to paragraph position
                sec_sort = pos / 10000.0   # normalize to same scale

            item["action_taken"]    = action
            item["lease_position"]  = pos
            item["lease_section"]   = sec_ref
            item["checklist_index"] = idx
            item["lease_sort_key"]  = sec_sort * 10000 + idx   # stable tiebreaker
            if pos < 50:
                _sys.stderr.write(f"[pos-early] sec={sec!r} pos={pos} sec_ref={sec_ref!r} sec_sort={sec_sort}\n")

        with JOBS_LOCK:
            JOBS[job_id].update({
                "status": "done",
                "progress": "Done",
                "result": result,
                "redlined_path": tmp_out.name,
                "redlined_filename": f"{base}_REDLINED.docx",
            })
        # Persist WITHOUT holding JOBS_LOCK — _persist_job acquires the lock
        # internally. Calling it inside a JOBS_LOCK context causes a deadlock
        # since Python's Lock is not reentrant.
        with JOBS_LOCK:
            job_snapshot = dict(JOBS[job_id])
        _persist_job(job_id, job_snapshot)

    except Exception as e:
        log_error(e, context=f"job {job_id}")
        with JOBS_LOCK:
            JOBS[job_id].update({
                "status": "error",
                "error": str(e),
            })
    finally:
        for path in [input_path, loi_path, converted_path]:
            if path:
                try:
                    os.unlink(path)
                except Exception:
                    pass


def _update_job(job_id, **kwargs):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(kwargs)


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/status/<job_id>")
@login_required
def api_status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        job = _load_job_from_disk(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify({
        "status": job["status"],
        "progress": job.get("progress", "Done"),
        "error": job.get("error"),
    })


@app.route("/results/<job_id>")
@login_required
def results(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        job = _load_job_from_disk(job_id)
    if not job:
        flash("Job not found. The server may have restarted — please upload your lease again.", "warning")
        return redirect(url_for("index"))
    if job["status"] == "error":
        flash(f"Analysis failed: {job.get('error', 'Unknown error')}. Please try again.", "danger")
        return redirect(url_for("index"))
    if job["status"] != "done":
        flash("Results not ready yet — please wait for the analysis to complete.", "warning")
        return redirect(url_for("index"))

    result = job["result"]
    review = result.get("review", [])

    # Ensure lease_position exists on every item (older persisted jobs may lack it)
    _EXACT_NOT_PRESENT = {
        "not addressed", "not specified", "not addressed.", "not specified.",
        "not found", "not mentioned", "not discussed", "silent",
    }

    def _disk_is_exactly_absent(s):
        return (s or "").strip().lower() in _EXACT_NOT_PRESENT

    def _disk_is_vaguely_absent(s):
        sl = (s or "").strip().lower()
        return (sl.startswith("not addressed") or sl.startswith("not specified")) \
               and sl not in _EXACT_NOT_PRESENT

    import re as _re3
    def _disk_section_sort_key(lease_section):
        if not lease_section:
            return 999.0
        s = (lease_section or '').strip().lower()
        if s in ('999', 'not found', 'not addressed', 'n/a', ''):
            return 999.0
        roman = {'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7,'viii':8,
                 'ix':9,'x':10,'xi':11,'xii':12,'xiii':13,'xiv':14,'xv':15,
                 'xvi':16,'xvii':17,'xviii':18,'xix':19,'xx':20}
        if 'exhibit' in s:
            m = _re3.search(r'exhibit\s+([a-z])', s)
            base = 800 + (ord(m.group(1)) - ord('a')) if m else 800
            m2 = _re3.search(r'section\s+(\d+)', s)
            return base + (int(m2.group(1)) * 0.1 if m2 else 0)
        m = _re3.search(r'article\s+([ivxlcdm]+|\d+)', s)
        if m:
            g = m.group(1)
            val = roman.get(g) or (int(g) if g.isdigit() else 999)
            return float(val)
        m = _re3.search(r'(\d+)(?:\.(\d+))?', s)
        if m:
            return int(m.group(1)) + (int(m.group(2)) * 0.01 if m.group(2) else 0)
        if any(w in s for w in ('basic terms', 'summary', 'recital', 'preamble')):
            return 0.5
        return 999.0

    for idx, r in enumerate(review):
        lease_says  = r.get("lease_says") or ""
        action_done = r.get("action_taken")
        if _disk_is_exactly_absent(lease_says):
            r["lease_position"] = 999999
            r["lease_sort_key"] = 999999 * 10000 + idx
        elif _disk_is_vaguely_absent(lease_says) and not action_done:
            r["lease_position"] = 999999
            r["lease_sort_key"] = 999999 * 10000 + idx
        else:
            if "lease_position" not in r:
                r["lease_position"] = idx * 100
            sec_ref  = r.get("lease_section") or ""
            sec_sort = _disk_section_sort_key(sec_ref)
            pos_fb   = r.get("lease_position", idx * 100)
            if sec_sort >= 999.0 and pos_fb < 999999:
                sec_sort = pos_fb / 10000.0
            r["lease_sort_key"] = sec_sort * 10000 + idx

    high   = [r for r in review if r.get("priority") == "High"   and r.get("status") != "pass"]
    medium = [r for r in review if r.get("priority") == "Medium" and r.get("status") != "pass"]
    low    = [r for r in review if r.get("priority") == "Low"    and r.get("status") != "pass"]
    passed = [r for r in review if r.get("status") == "pass"]

    fails  = len([r for r in review if r.get("status") == "fail"])
    passes = len(passed)
    total  = len(review)

    return render_template("results.html",
        job_id=job_id,
        property_name=result.get("property_name", "Unknown Property"),
        key_terms=result.get("key_terms", []),
        deal_summary=result.get("deal_summary", []),
        high_issues=high,
        medium_issues=medium,
        low_issues=low,
        passed=passed,
        fails=fails,
        passes=passes,
        total=total,
        additional_issues=result.get("additional_issues", []),
        redline_summary=result.get("redline_summary", {}),
        original_filename=job["original_filename"],
    )


@app.route("/debug/<job_id>")
@login_required
def debug_job(job_id):
    """Temporary debug: show section_positions and review section names for a job."""
    import json as _json
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        job = _load_job_from_disk(job_id)
    if not job:
        return "job not found", 404
    result = job.get("result", {})
    positions = result.get("redline_summary", {}).get("section_positions", {})
    review = result.get("review", [])
    rows = []
    for item in review:
        sec = item.get("section", "")
        rows.append({
            "section": sec,
            "status": item.get("status"),
            "priority": item.get("priority"),
            "lease_position": item.get("lease_position", "NOT SET"),
            "lease_section": item.get("lease_section", "NOT SET"),
            "lease_sort_key": item.get("lease_sort_key", "NOT SET"),
            "in_positions": sec in positions,
            "positions_value": positions.get(sec, "MISSING"),
            "lease_says": item.get("lease_says", ""),
            "action_taken": item.get("action_taken", ""),
        })
    rows.sort(key=lambda x: float(x["lease_sort_key"]) if isinstance(x["lease_sort_key"], (int, float)) else 999999)
    return "<pre>" + _json.dumps(rows, indent=2) + "</pre>"


@app.route("/download/<job_id>")
@login_required
def download(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        job = _load_job_from_disk(job_id)
    if not job or not job.get("redlined_path"):
        flash("Redlined document not available.", "danger")
        return redirect(url_for("index"))

    path     = job["redlined_path"]
    filename = job.get("redlined_filename", "lease_redlined.docx")

    if not os.path.exists(path):
        flash("Redlined document file not found (server may have restarted).", "warning")
        return redirect(url_for("index"))

    return send_file(path, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


if __name__ == "__main__":
    app.run(debug=True)

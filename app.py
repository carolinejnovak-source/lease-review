import os, uuid, threading, tempfile, subprocess, shutil
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file)
from auth import login_required, check_credentials
from error_log import register_error_handlers, log_error
from analyzer import analyze_lease
from redline import apply_redlines, extract_text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vip-lease-review-2026")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

register_error_handlers(app)

# ── In-memory job store ───────────────────────────────────────────────────────
# {job_id: {status, progress, result, error, redlined_path, original_filename}}
JOBS = {}
JOBS_LOCK = threading.Lock()


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
    if ext not in (".docx", ".doc"):
        flash("Please upload a .docx file.", "danger")
        return redirect(url_for("index"))

    # Save uploaded file to temp
    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    f.save(tmp_in.name)
    tmp_in.close()

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
    t = threading.Thread(target=_run_analysis, args=(job_id, tmp_in.name, original_filename))
    t.daemon = True
    t.start()

    return render_template("loading.html", job_id=job_id, filename=original_filename)


def _convert_to_docx(doc_path: str) -> str:
    """
    Convert a .doc file to .docx using LibreOffice headless.
    Returns the path of the new .docx file (caller must delete it).
    Raises RuntimeError if conversion fails.
    """
    out_dir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "docx",
             "--outdir", out_dir, doc_path],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
        # LibreOffice names the output file based on the input filename
        base = os.path.splitext(os.path.basename(doc_path))[0]
        converted = os.path.join(out_dir, base + ".docx")
        if not os.path.exists(converted):
            # Try any .docx in the output dir
            files = [f for f in os.listdir(out_dir) if f.endswith(".docx")]
            if not files:
                raise RuntimeError("LibreOffice produced no .docx output.")
            converted = os.path.join(out_dir, files[0])
        # Move to a temp file so we can clean up out_dir
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp.close()
        shutil.move(converted, tmp.name)
        return tmp.name
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def _run_analysis(job_id, input_path, original_filename):
    tmp_out = None
    converted_path = None  # Track converted .doc→.docx so we can delete it
    try:
        # Convert .doc → .docx if needed
        if input_path.lower().endswith(".doc"):
            _update_job(job_id, progress="Converting .doc to .docx…")
            converted_path = _convert_to_docx(input_path)
            processing_path = converted_path
        else:
            processing_path = input_path

        _update_job(job_id, progress="Extracting lease text…")
        lease_text = extract_text(processing_path)

        if len(lease_text.strip()) < 100:
            raise ValueError("Could not extract readable text from the document. Is it a valid .docx file?")

        _update_job(job_id, progress="Sending to GPT-4o for analysis (this takes 30–60 seconds)…")
        result = analyze_lease(lease_text)

        _update_job(job_id, progress=f"Analysis complete. Applying {len(result.get('redlines', []))} redlines to document…")

        # Generate redlined docx
        base = os.path.splitext(original_filename)[0]
        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_out.close()

        redline_summary = apply_redlines(processing_path, result.get("redlines", []), tmp_out.name)
        result["redline_summary"] = redline_summary

        with JOBS_LOCK:
            JOBS[job_id].update({
                "status": "done",
                "progress": "Done",
                "result": result,
                "redlined_path": tmp_out.name,
                "redlined_filename": f"{base}_REDLINED.docx",
            })

    except Exception as e:
        log_error(e, context=f"job {job_id}")
        with JOBS_LOCK:
            JOBS[job_id].update({
                "status": "error",
                "error": str(e),
            })
    finally:
        for path in [input_path, converted_path]:
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
        return jsonify({"status": "not_found"}), 404
    return jsonify({
        "status": job["status"],
        "progress": job["progress"],
        "error": job.get("error"),
    })


@app.route("/results/<job_id>")
@login_required
def results(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job or job["status"] != "done":
        flash("Results not ready yet or job not found.", "warning")
        return redirect(url_for("index"))

    result = job["result"]
    review = result.get("review", [])

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
        deal_summary=result.get("deal_summary", []),
        high_issues=high,
        medium_issues=medium,
        low_issues=low,
        passed=passed,
        fails=fails,
        passes=passes,
        total=total,
        redline_summary=result.get("redline_summary", {}),
        original_filename=job["original_filename"],
    )


@app.route("/download/<job_id>")
@login_required
def download(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
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

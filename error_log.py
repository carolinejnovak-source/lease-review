import traceback
from collections import deque
from datetime import datetime, timezone
from flask import render_template_string, session, redirect, url_for

_errors = deque(maxlen=200)

def log_error(err, context=""):
    _errors.appendleft({
        "time": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "error": str(err),
        "traceback": traceback.format_exc(),
    })

def register_error_handlers(app):
    from auth import login_required

    @app.errorhandler(Exception)
    def handle_exception(e):
        log_error(e, context="unhandled")
        return f"<h2>Internal Error</h2><pre>{traceback.format_exc()}</pre>", 500

    @app.route("/errors")
    def errors_page():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        html = """
        <html><head><title>Error Log</title>
        <style>body{font-family:monospace;padding:20px;background:#1a1a2e;color:#e0e0e0}
        .err{background:#2a2a3e;padding:12px;margin:8px 0;border-radius:6px;border-left:3px solid #e74c3c}
        .time{color:#888;font-size:.8rem} .ctx{color:#e74c3c;font-weight:bold}
        pre{white-space:pre-wrap;font-size:.75rem;color:#aaa}h1{color:#e74c3c}</style></head>
        <body><h1>Error Log (last 200)</h1>
        {% if not errors %}<p style="color:#888">No errors recorded.</p>{% endif %}
        {% for e in errors %}
        <div class="err">
          <div class="time">{{ e.time }}</div>
          <div class="ctx">{{ e.context or 'unknown' }}</div>
          <div>{{ e.error }}</div>
          <pre>{{ e.traceback }}</pre>
        </div>{% endfor %}
        </body></html>"""
        from flask import render_template_string as rts
        return rts(html, errors=list(_errors))

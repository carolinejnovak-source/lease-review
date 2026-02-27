from functools import wraps
from flask import session, redirect, url_for, request

# username (lowercase) → password (case-insensitive check)
USERS = {
    "carolinejnovak": "crap",
    "kelly": "wahoo",
}

# Keep for backwards compat
APP_USERNAME = "carolinejnovak"
APP_PASSWORD = "crap"

def check_credentials(username, password):
    pw = USERS.get(username.lower())
    return pw is not None and password.lower() == pw.lower()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

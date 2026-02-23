from functools import wraps
from flask import session, redirect, url_for, request

APP_USERNAME = "carolinejnovak"
APP_PASSWORD = "crap"

def check_credentials(username, password):
    return (username.lower() == APP_USERNAME.lower() and
            password.lower() == APP_PASSWORD.lower())

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

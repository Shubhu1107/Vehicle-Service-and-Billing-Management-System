from functools import wraps
from flask import session, redirect, url_for, flash, abort, request

def login_required(view):
    """
    Decorator to ensure user is logged in.
    Redirects to login page if session does not contain 'user_id'.
    """
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        return view(*args, **kwargs)
    return wrapped_view

def role_required(*allowed_roles):
    """
    Decorator to ensure logged-in user possesses one of the allowed roles.
    Aborts with 403 Forbidden if user role is not permitted.
    """
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for('auth.login', next=request.path))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash("Access denied. You do not have permission to view this resource.", "danger")
                abort(403)
            return view(*args, **kwargs)
        return wrapped_view
    return decorator

def admin_required(view):
    """Decorator requiring 'admin' role."""
    return role_required('admin')(view)

def customer_required(view):
    """Decorator requiring 'customer' role."""
    return role_required('customer')(view)

def mechanic_required(view):
    """Decorator requiring 'mechanic' role."""
    return role_required('mechanic')(view)

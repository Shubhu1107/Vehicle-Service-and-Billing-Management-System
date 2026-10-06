from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import query_db, execute_db
from utils.helpers import is_valid_email, is_valid_phone

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login handling Admin, Customer, and Mechanic roles.
    """
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'mechanic':
            return redirect(url_for('mechanic.dashboard'))
        elif role == 'customer':
            return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template('auth/login.html', email=email)

        user = query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)

        if not user or not check_password_hash(user['password_hash'], password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('auth/login.html', email=email)

        if user['status'] != 'active':
            flash("Your account has been deactivated. Please contact support.", "danger")
            return render_template('auth/login.html', email=email)

        # Populate session
        session.clear()
        session['user_id'] = user['id']
        session['name'] = user['name']
        session['email'] = user['email']
        session['role'] = user['role']
        if remember:
            session.permanent = True

        # Fetch role-specific details
        if user['role'] == 'customer':
            cust = query_db("SELECT id FROM customers WHERE user_id = %s", (user['id'],), one=True)
            if cust:
                session['customer_id'] = cust['id']
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('customer.dashboard'))

        elif user['role'] == 'mechanic':
            mech = query_db("SELECT id FROM mechanics WHERE user_id = %s", (user['id'],), one=True)
            if mech:
                session['mechanic_id'] = mech['id']
            flash(f"Welcome back, {user['name']}! Ready for today's service queue.", "success")
            return redirect(url_for('mechanic.dashboard'))

        elif user['role'] == 'admin':
            flash(f"Welcome to the Admin Command Center, {user['name']}.", "success")
            return redirect(url_for('admin.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Customer self-registration portal.
    """
    if 'user_id' in session:
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-side validation
        errors = []
        if not name or len(name) < 2:
            errors.append("Please enter your full name (at least 2 characters).")
        if not is_valid_email(email):
            errors.append("Please enter a valid email address.")
        if not is_valid_phone(phone):
            errors.append("Please enter a valid phone number.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('auth/register.html', name=name, email=email, phone=phone, address=address)

        # Check existing email
        existing_user = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
        if existing_user:
            flash("An account with this email address already exists. Please login instead.", "warning")
            return render_template('auth/register.html', name=name, phone=phone, address=address)

        try:
            # Create user
            pw_hash = generate_password_hash(password)
            user_id = execute_db(
                "INSERT INTO users (name, email, password_hash, phone, role, status) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, email, pw_hash, phone, 'customer', 'active')
            )

            # Create customer profile
            execute_db(
                "INSERT INTO customers (user_id, address) VALUES (%s, %s)",
                (user_id, address)
            )

            flash("Account created successfully! You can now log in with your credentials.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f"An error occurred during registration: {e}", "danger")
            return render_template('auth/register.html', name=name, email=email, phone=phone, address=address)

    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    """
    Log out user and clear session.
    """
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('auth.login'))

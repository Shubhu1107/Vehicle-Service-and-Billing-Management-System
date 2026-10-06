from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from database.db import query_db, execute_db
from utils.auth import admin_required
from utils.helpers import (
    generate_invoice_number,
    log_service_update,
    format_currency,
    get_workshop_settings,
    is_valid_email,
    is_valid_phone
)
import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    Admin Command Center: summary metrics, recent bookings, status breakdowns, and revenue statistics.
    """
    stats = {}

    # Total Customers
    cust_res = query_db("SELECT COUNT(*) AS count FROM customers", one=True)
    stats['total_customers'] = cust_res['count'] if cust_res else 0

    # Total Vehicles
    veh_res = query_db("SELECT COUNT(*) AS count FROM vehicles", one=True)
    stats['total_vehicles'] = veh_res['count'] if veh_res else 0

    # Pending Bookings
    pend_res = query_db("SELECT COUNT(*) AS count FROM bookings WHERE status = 'Pending'", one=True)
    stats['pending_bookings'] = pend_res['count'] if pend_res else 0

    # Active Services
    act_res = query_db(
        """SELECT COUNT(*) AS count FROM bookings 
           WHERE status IN ('Approved', 'Mechanic Assigned', 'Vehicle Received', 'In Service', 'Waiting for Parts')""",
        one=True
    )
    stats['active_services'] = act_res['count'] if act_res else 0

    # Completed Services
    comp_res = query_db("SELECT COUNT(*) AS count FROM bookings WHERE status IN ('Completed', 'Delivered')", one=True)
    stats['completed_services'] = comp_res['count'] if comp_res else 0

    # Total Mechanics
    mech_res = query_db("SELECT COUNT(*) AS count FROM mechanics", one=True)
    stats['total_mechanics'] = mech_res['count'] if mech_res else 0

    # Total Revenue (Paid bills)
    rev_res = query_db("SELECT SUM(grand_total) AS total FROM bills WHERE payment_status = 'Paid'", one=True)
    stats['total_revenue'] = float(rev_res['total'] or 0.0) if rev_res else 0.0

    # Pending Revenue (Unpaid bills)
    unpaid_res = query_db("SELECT SUM(grand_total) AS total FROM bills WHERE payment_status = 'Unpaid'", one=True)
    stats['pending_revenue'] = float(unpaid_res['total'] or 0.0) if unpaid_res else 0.0

    # Recent 8 Bookings
    recent_bookings = query_db(
        """SELECT b.*, s.service_name, v.registration_number, v.brand, v.model,
           u_cust.name AS customer_name,
           u_mech.name AS mechanic_name
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN customers c ON b.customer_id = c.id
           JOIN users u_cust ON c.user_id = u_cust.id
           LEFT JOIN mechanics m ON b.mechanic_id = m.id
           LEFT JOIN users u_mech ON m.user_id = u_mech.id
           ORDER BY b.id DESC LIMIT 8"""
    )

    # Status distribution counts
    status_counts = query_db(
        "SELECT status, COUNT(*) AS count FROM bookings GROUP BY status"
    )
    status_map = {row['status']: row['count'] for row in status_counts}

    # Available mechanics for quick view
    mechanics_list = query_db(
        """SELECT m.*, u.name, u.phone,
           (SELECT COUNT(*) FROM bookings WHERE mechanic_id = m.id AND status NOT IN ('Completed', 'Delivered', 'Cancelled')) AS active_jobs
           FROM mechanics m
           JOIN users u ON m.user_id = u.id
           ORDER BY active_jobs ASC"""
    )

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_bookings=recent_bookings,
        status_map=status_map,
        mechanics_list=mechanics_list
    )

# ---------------------------------------------------------------------
# CUSTOMER MANAGEMENT
# ---------------------------------------------------------------------

@admin_bp.route('/customers', methods=['GET', 'POST'])
@admin_required
def customers():
    """
    Admin customer directory with search, filter, and add customer features.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', 'customer123').strip()

        if not name or not email or not phone:
            flash("Name, email, and phone number are required.", "danger")
        elif not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
        elif not is_valid_phone(phone):
            flash("Please enter a valid phone number.", "danger")
        else:
            existing = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
            if existing:
                flash(f"User with email '{email}' already exists.", "danger")
            else:
                pw_hash = generate_password_hash(password)
                uid = execute_db(
                    "INSERT INTO users (name, email, password_hash, phone, role, status) VALUES (%s, %s, %s, %s, 'customer', 'active')",
                    (name, email, pw_hash, phone)
                )
                execute_db("INSERT INTO customers (user_id, address) VALUES (%s, %s)", (uid, address))
                flash(f"Customer '{name}' registered successfully.", "success")
                return redirect(url_for('admin.customers'))

    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')

    sql = """SELECT c.id AS customer_id, u.id AS user_id, u.name, u.email, u.phone, u.status, u.created_at, c.address,
             (SELECT COUNT(*) FROM vehicles WHERE customer_id = c.id) AS vehicles_count,
             (SELECT COUNT(*) FROM bookings WHERE customer_id = c.id) AS services_count
             FROM customers c
             JOIN users u ON c.user_id = u.id
             WHERE 1=1"""
    params = []

    if search:
        sql += " AND (u.name LIKE %s OR u.email LIKE %s OR u.phone LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if status_filter != 'all':
        sql += " AND u.status = %s"
        params.append(status_filter)

    sql += " ORDER BY c.id DESC"
    customers_list = query_db(sql, params)

    return render_template(
        'admin/customers.html',
        customers=customers_list,
        search=search,
        status_filter=status_filter
    )

@admin_bp.route('/customers/<int:customer_id>')
@admin_required
def customer_detail(customer_id):
    """
    Detailed profile view of a customer with their vehicles, bookings, and invoices.
    """
    customer = query_db(
        """SELECT c.id AS customer_id, c.address, c.created_at,
           u.id AS user_id, u.name, u.email, u.phone, u.status
           FROM customers c
           JOIN users u ON c.user_id = u.id
           WHERE c.id = %s""",
        (customer_id,),
        one=True
    )
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('admin.customers'))

    vehicles = query_db("SELECT * FROM vehicles WHERE customer_id = %s ORDER BY id DESC", (customer_id,))
    bookings = query_db(
        """SELECT b.*, s.service_name, v.registration_number, v.brand, v.model,
           u_mech.name AS mechanic_name
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           JOIN vehicles v ON b.vehicle_id = v.id
           LEFT JOIN mechanics m ON b.mechanic_id = m.id
           LEFT JOIN users u_mech ON m.user_id = u_mech.id
           WHERE b.customer_id = %s
           ORDER BY b.id DESC""",
        (customer_id,)
    )
    invoices = query_db(
        """SELECT bill.*, bk.booking_number, bk.preferred_date
           FROM bills bill
           JOIN bookings bk ON bill.booking_id = bk.id
           WHERE bk.customer_id = %s
           ORDER BY bill.id DESC""",
        (customer_id,)
    )

    return render_template(
        'admin/customer_detail.html',
        customer=customer,
        vehicles=vehicles,
        bookings=bookings,
        invoices=invoices
    )

@admin_bp.route('/customers/<int:customer_id>/edit', methods=['POST'])
@admin_required
def edit_customer(customer_id):
    """
    Update customer details and status.
    """
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    status = request.form.get('status', 'active')

    cust = query_db("SELECT user_id FROM customers WHERE id = %s", (customer_id,), one=True)
    if not cust:
        flash("Customer not found.", "danger")
        return redirect(url_for('admin.customers'))

    execute_db("UPDATE users SET name = %s, phone = %s, status = %s WHERE id = %s", (name, phone, status, cust['user_id']))
    execute_db("UPDATE customers SET address = %s WHERE id = %s", (address, customer_id))
    flash("Customer profile updated successfully.", "success")
    return redirect(url_for('admin.customer_detail', customer_id=customer_id))

# ---------------------------------------------------------------------
# VEHICLE MANAGEMENT
# ---------------------------------------------------------------------

@admin_bp.route('/vehicles', methods=['GET', 'POST'])
@admin_required
def vehicles():
    """
    Vehicle inventory management: list, search, add, edit, and delete vehicles.
    """
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        reg_number = request.form.get('registration_number', '').strip().upper()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'Car')
        year = request.form.get('manufacturing_year', '').strip()
        fuel_type = request.form.get('fuel_type', 'Petrol')
        color = request.form.get('color', '').strip()
        current_km = request.form.get('current_km', '0').strip()

        if not customer_id or not reg_number or not brand or not model or not year or not color:
            flash("All vehicle fields are mandatory.", "danger")
        else:
            existing = query_db("SELECT id FROM vehicles WHERE registration_number = %s", (reg_number,), one=True)
            if existing:
                flash(f"Vehicle registration number '{reg_number}' already exists in database.", "danger")
            else:
                try:
                    execute_db(
                        """INSERT INTO vehicles 
                           (customer_id, registration_number, brand, model, vehicle_type, manufacturing_year, fuel_type, color, current_km)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (customer_id, reg_number, brand, model, vehicle_type, int(year), fuel_type, color, int(current_km))
                    )
                    flash(f"Vehicle {brand} {model} ({reg_number}) added successfully.", "success")
                    return redirect(url_for('admin.vehicles'))
                except ValueError:
                    flash("Invalid year or KM values provided.", "danger")

    search = request.args.get('search', '').strip()
    type_filter = request.args.get('type', 'all')

    sql = """SELECT v.*, u.name AS customer_name, u.phone AS customer_phone,
             (SELECT COUNT(*) FROM bookings WHERE vehicle_id = v.id) AS service_count,
             (SELECT status FROM bookings WHERE vehicle_id = v.id ORDER BY id DESC LIMIT 1) AS latest_service_status
             FROM vehicles v
             JOIN customers c ON v.customer_id = c.id
             JOIN users u ON c.user_id = u.id
             WHERE 1=1"""
    params = []

    if search:
        sql += " AND (v.registration_number LIKE %s OR v.brand LIKE %s OR v.model LIKE %s OR u.name LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    if type_filter != 'all':
        sql += " AND v.vehicle_type = %s"
        params.append(type_filter)

    sql += " ORDER BY v.id DESC"
    vehicles_list = query_db(sql, params)

    customers_dropdown = query_db(
        "SELECT c.id, u.name, u.phone FROM customers c JOIN users u ON c.user_id = u.id ORDER BY u.name ASC"
    )

    return render_template(
        'admin/vehicles.html',
        vehicles=vehicles_list,
        customers=customers_dropdown,
        search=search,
        type_filter=type_filter
    )

@admin_bp.route('/vehicles/<int:vehicle_id>/edit', methods=['POST'])
@admin_required
def edit_vehicle(vehicle_id):
    """Update vehicle specifications."""
    reg_number = request.form.get('registration_number', '').strip().upper()
    brand = request.form.get('brand', '').strip()
    model = request.form.get('model', '').strip()
    vehicle_type = request.form.get('vehicle_type')
    year = request.form.get('manufacturing_year')
    fuel_type = request.form.get('fuel_type')
    color = request.form.get('color', '').strip()
    current_km = request.form.get('current_km', '0').strip()

    dup = query_db("SELECT id FROM vehicles WHERE registration_number = %s AND id != %s", (reg_number, vehicle_id), one=True)
    if dup:
        flash(f"Vehicle registration '{reg_number}' belongs to another vehicle record.", "danger")
        return redirect(url_for('admin.vehicles'))

    try:
        execute_db(
            """UPDATE vehicles 
               SET registration_number = %s, brand = %s, model = %s, vehicle_type = %s,
                   manufacturing_year = %s, fuel_type = %s, color = %s, current_km = %s
               WHERE id = %s""",
            (reg_number, brand, model, vehicle_type, int(year), fuel_type, color, int(current_km), vehicle_id)
        )
        flash(f"Vehicle '{reg_number}' updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update vehicle: {e}", "danger")

    return redirect(url_for('admin.vehicles'))

@admin_bp.route('/vehicles/<int:vehicle_id>/delete', methods=['POST'])
@admin_required
def delete_vehicle(vehicle_id):
    """Delete a vehicle record."""
    try:
        execute_db("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        flash("Vehicle record deleted successfully.", "info")
    except Exception as e:
        flash(f"Cannot delete vehicle: it may have related bookings or records ({e})", "danger")
    return redirect(url_for('admin.vehicles'))

# ---------------------------------------------------------------------
# SERVICES CATALOG
# ---------------------------------------------------------------------

@admin_bp.route('/services', methods=['GET', 'POST'])
@admin_required
def services():
    """
    Catalog of repair, maintenance, and diagnostic packages.
    """
    if request.method == 'POST':
        service_name = request.form.get('service_name', '').strip()
        description = request.form.get('description', '').strip()
        base_price = request.form.get('base_price', '0').strip()
        duration = request.form.get('estimated_duration', '').strip()
        status = request.form.get('status', 'Active')

        if not service_name or not base_price or not duration:
            flash("Service name, base price, and duration are required.", "danger")
        else:
            try:
                execute_db(
                    """INSERT INTO services (service_name, description, base_price, estimated_duration, status)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (service_name, description, float(base_price), duration, status)
                )
                flash(f"Service package '{service_name}' added successfully.", "success")
                return redirect(url_for('admin.services'))
            except ValueError:
                flash("Base price must be a valid number.", "danger")

    search = request.args.get('search', '').strip()
    sql = "SELECT * FROM services WHERE 1=1"
    params = []
    if search:
        sql += " AND (service_name LIKE %s OR description LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
    sql += " ORDER BY id ASC"

    services_list = query_db(sql, params)
    return render_template('admin/services.html', services=services_list, search=search)

@admin_bp.route('/services/<int:service_id>/edit', methods=['POST'])
@admin_required
def edit_service(service_id):
    """Update service catalog item."""
    service_name = request.form.get('service_name', '').strip()
    description = request.form.get('description', '').strip()
    base_price = request.form.get('base_price', '0').strip()
    duration = request.form.get('estimated_duration', '').strip()
    status = request.form.get('status', 'Active')

    try:
        execute_db(
            """UPDATE services 
               SET service_name = %s, description = %s, base_price = %s, estimated_duration = %s, status = %s
               WHERE id = %s""",
            (service_name, description, float(base_price), duration, status, service_id)
        )
        flash(f"Service '{service_name}' updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating service: {e}", "danger")

    return redirect(url_for('admin.services'))

# ---------------------------------------------------------------------
# MECHANIC MANAGEMENT
# ---------------------------------------------------------------------

@admin_bp.route('/mechanics', methods=['GET', 'POST'])
@admin_required
def mechanics():
    """
    Mechanic staff management: list, add, edit, and view active workload.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        specialization = request.form.get('specialization', '').strip()
        experience = request.form.get('experience', '1').strip()
        status = request.form.get('status', 'Available')
        joining_date = request.form.get('joining_date', datetime.date.today().isoformat())
        password = request.form.get('password', 'mechanic123').strip()

        if not name or not email or not phone or not specialization:
            flash("All mechanic details are required.", "danger")
        elif not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
        elif not is_valid_phone(phone):
            flash("Please enter a valid phone number.", "danger")
        else:
            existing = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
            if existing:
                flash(f"User with email '{email}' already exists.", "danger")
            else:
                pw_hash = generate_password_hash(password)
                uid = execute_db(
                    "INSERT INTO users (name, email, password_hash, phone, role, status) VALUES (%s, %s, %s, %s, 'mechanic', 'active')",
                    (name, email, pw_hash, phone)
                )
                execute_db(
                    """INSERT INTO mechanics (user_id, specialization, experience, status, joining_date)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (uid, specialization, int(experience), status, joining_date)
                )
                flash(f"Mechanic '{name}' registered successfully.", "success")
                return redirect(url_for('admin.mechanics'))

    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')

    sql = """SELECT m.*, u.id AS user_id, u.name, u.email, u.phone, u.status AS user_status,
             (SELECT COUNT(*) FROM bookings WHERE mechanic_id = m.id AND status NOT IN ('Completed', 'Delivered', 'Cancelled')) AS active_workload,
             (SELECT COUNT(*) FROM bookings WHERE mechanic_id = m.id AND status IN ('Completed', 'Delivered')) AS completed_count
             FROM mechanics m
             JOIN users u ON m.user_id = u.id
             WHERE 1=1"""
    params = []

    if search:
        sql += " AND (u.name LIKE %s OR m.specialization LIKE %s OR u.email LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if status_filter != 'all':
        sql += " AND m.status = %s"
        params.append(status_filter)

    sql += " ORDER BY m.id ASC"
    mechanics_list = query_db(sql, params)

    return render_template(
        'admin/mechanics.html',
        mechanics=mechanics_list,
        search=search,
        status_filter=status_filter
    )

@admin_bp.route('/mechanics/<int:mechanic_id>/edit', methods=['POST'])
@admin_required
def edit_mechanic(mechanic_id):
    """Update mechanic profile."""
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    specialization = request.form.get('specialization', '').strip()
    experience = request.form.get('experience', '1')
    status = request.form.get('status', 'Available')

    mech = query_db("SELECT user_id FROM mechanics WHERE id = %s", (mechanic_id,), one=True)
    if not mech:
        flash("Mechanic record not found.", "danger")
        return redirect(url_for('admin.mechanics'))

    execute_db("UPDATE users SET name = %s, phone = %s WHERE id = %s", (name, phone, mech['user_id']))
    execute_db(
        "UPDATE mechanics SET specialization = %s, experience = %s, status = %s WHERE id = %s",
        (specialization, int(experience), status, mechanic_id)
    )
    flash("Mechanic profile updated successfully.", "success")
    return redirect(url_for('admin.mechanics'))

# ---------------------------------------------------------------------
# BOOKING MANAGEMENT & WORKFLOW
# ---------------------------------------------------------------------

@admin_bp.route('/bookings')
@admin_required
def bookings():
    """
    Master bookings log with comprehensive filters (status, date, mechanic, search).
    """
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    mechanic_filter = request.args.get('mechanic_id', '')

    sql = """SELECT b.*, s.service_name, s.base_price,
             v.registration_number, v.brand, v.model,
             u_cust.name AS customer_name, u_cust.phone AS customer_phone,
             u_mech.name AS mechanic_name,
             bill.id AS bill_id, bill.invoice_number, bill.payment_status
             FROM bookings b
             JOIN services s ON b.service_id = s.id
             JOIN vehicles v ON b.vehicle_id = v.id
             JOIN customers c ON b.customer_id = c.id
             JOIN users u_cust ON c.user_id = u_cust.id
             LEFT JOIN mechanics m ON b.mechanic_id = m.id
             LEFT JOIN users u_mech ON m.user_id = u_mech.id
             LEFT JOIN bills bill ON bill.booking_id = b.id
             WHERE 1=1"""
    params = []

    if search:
        sql += " AND (b.booking_number LIKE %s OR u_cust.name LIKE %s OR v.registration_number LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if status_filter != 'all':
        sql += " AND b.status = %s"
        params.append(status_filter)

    if mechanic_filter:
        sql += " AND b.mechanic_id = %s"
        params.append(mechanic_filter)

    sql += " ORDER BY b.id DESC"
    bookings_list = query_db(sql, params)

    mechanics = query_db("SELECT m.id, u.name FROM mechanics m JOIN users u ON m.user_id = u.id ORDER BY u.name ASC")

    return render_template(
        'admin/bookings.html',
        bookings=bookings_list,
        mechanics=mechanics,
        search=search,
        status_filter=status_filter,
        mechanic_filter=mechanic_filter
    )

@admin_bp.route('/bookings/<int:booking_id>')
@admin_required
def booking_detail(booking_id):
    """
    Detailed booking overview: vehicle details, customer details, mechanic assignment,
    service update timeline, and billing link.
    """
    booking = query_db(
        """SELECT b.*, s.service_name, s.description AS service_description, s.base_price, s.estimated_duration,
           v.registration_number, v.brand, v.model, v.vehicle_type, v.fuel_type, v.color, v.current_km,
           u_cust.name AS customer_name, u_cust.email AS customer_email, u_cust.phone AS customer_phone,
           c.address AS customer_address,
           u_mech.name AS mechanic_name, u_mech.phone AS mechanic_phone, m.specialization AS mechanic_specialization,
           bill.id AS bill_id, bill.invoice_number, bill.grand_total, bill.payment_status
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN customers c ON b.customer_id = c.id
           JOIN users u_cust ON c.user_id = u_cust.id
           LEFT JOIN mechanics m ON b.mechanic_id = m.id
           LEFT JOIN users u_mech ON m.user_id = u_mech.id
           LEFT JOIN bills bill ON bill.booking_id = b.id
           WHERE b.id = %s""",
        (booking_id,),
        one=True
    )

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('admin.bookings'))

    # Available mechanics list (sorted so 'Available' comes first)
    mechanics_list = query_db(
        """SELECT m.id, u.name, m.specialization, m.status,
           (SELECT COUNT(*) FROM bookings WHERE mechanic_id = m.id AND status NOT IN ('Completed', 'Delivered', 'Cancelled')) AS current_jobs
           FROM mechanics m
           JOIN users u ON m.user_id = u.id
           WHERE m.status != 'Inactive'
           ORDER BY CASE m.status WHEN 'Available' THEN 1 WHEN 'Busy' THEN 2 ELSE 3 END, current_jobs ASC"""
    )

    # Timeline updates
    updates = query_db(
        """SELECT su.*, u.name AS updated_by_name, u.role AS updated_by_role
           FROM service_updates su
           JOIN users u ON su.updated_by = u.id
           WHERE su.booking_id = %s
           ORDER BY su.created_at DESC""",
        (booking_id,)
    )

    return render_template(
        'admin/booking_detail.html',
        booking=booking,
        mechanics=mechanics_list,
        updates=updates
    )

@admin_bp.route('/bookings/<int:booking_id>/approve', methods=['POST'])
@admin_required
def approve_booking(booking_id):
    """Admin approves a pending customer booking."""
    remarks = request.form.get('remarks', 'Booking verified and approved by Service Admin.').strip()
    execute_db("UPDATE bookings SET status = 'Approved', updated_at = NOW() WHERE id = %s", (booking_id,))
    log_service_update(booking_id, 'Approved', remarks, session['user_id'])
    flash("Booking has been approved successfully.", "success")
    return redirect(url_for('admin.booking_detail', booking_id=booking_id))

@admin_bp.route('/bookings/<int:booking_id>/assign-mechanic', methods=['POST'])
@admin_required
def assign_mechanic(booking_id):
    """Admin assigns or reassigns a mechanic to the booking."""
    mechanic_id = request.form.get('mechanic_id')
    remarks = request.form.get('remarks', '').strip()

    if not mechanic_id:
        flash("Please select a mechanic to assign.", "danger")
        return redirect(url_for('admin.booking_detail', booking_id=booking_id))

    mech = query_db("SELECT m.id, u.name FROM mechanics m JOIN users u ON m.user_id = u.id WHERE m.id = %s", (mechanic_id,), one=True)
    if not mech:
        flash("Mechanic not found.", "danger")
        return redirect(url_for('admin.booking_detail', booking_id=booking_id))

    execute_db(
        "UPDATE bookings SET mechanic_id = %s, status = 'Mechanic Assigned', updated_at = NOW() WHERE id = %s",
        (mechanic_id, booking_id)
    )

    full_remarks = f"Assigned to Mechanic {mech['name']}."
    if remarks:
        full_remarks += f" Note: {remarks}"

    log_service_update(booking_id, 'Mechanic Assigned', full_remarks, session['user_id'])
    flash(f"Booking assigned to {mech['name']} successfully.", "success")
    return redirect(url_for('admin.booking_detail', booking_id=booking_id))

@admin_bp.route('/bookings/<int:booking_id>/update-status', methods=['POST'])
@admin_required
def update_booking_status(booking_id):
    """Admin manually updates the booking status with remarks."""
    new_status = request.form.get('status')
    remarks = request.form.get('remarks', '').strip()

    allowed = ['Pending', 'Approved', 'Mechanic Assigned', 'Vehicle Received', 'In Service', 'Waiting for Parts', 'Completed', 'Cancelled', 'Delivered']
    if new_status not in allowed:
        flash("Invalid status specified.", "danger")
    elif not remarks:
        flash("Please provide remarks for this status change.", "danger")
    else:
        execute_db("UPDATE bookings SET status = %s, updated_at = NOW() WHERE id = %s", (new_status, booking_id))
        log_service_update(booking_id, new_status, remarks, session['user_id'])
        flash(f"Booking status updated to '{new_status}'.", "success")

    return redirect(url_for('admin.booking_detail', booking_id=booking_id))

@admin_bp.route('/bookings/<int:booking_id>/reschedule', methods=['POST'])
@admin_required
def reschedule_booking(booking_id):
    """Reschedule booking appointment date and time."""
    preferred_date = request.form.get('preferred_date')
    preferred_time = request.form.get('preferred_time')
    remarks = request.form.get('remarks', 'Appointment rescheduled by admin.').strip()

    if not preferred_date or not preferred_time:
        flash("Date and time are required to reschedule.", "danger")
    else:
        execute_db(
            "UPDATE bookings SET preferred_date = %s, preferred_time = %s, updated_at = NOW() WHERE id = %s",
            (preferred_date, preferred_time, booking_id)
        )
        log_service_update(booking_id, 'Approved', f"Rescheduled to {preferred_date} at {preferred_time}. Reason: {remarks}", session['user_id'])
        flash("Booking rescheduled successfully.", "info")

    return redirect(url_for('admin.booking_detail', booking_id=booking_id))

# ---------------------------------------------------------------------
# SERVICE HISTORY
# ---------------------------------------------------------------------

@admin_bp.route('/history')
@admin_required
def history():
    """
    Complete service history across all vehicles and customers.
    """
    search = request.args.get('search', '').strip()
    sql = """SELECT b.*, s.service_name, v.registration_number, v.brand, v.model,
             u_cust.name AS customer_name, u_cust.phone AS customer_phone,
             u_mech.name AS mechanic_name,
             bill.id AS bill_id, bill.invoice_number, bill.grand_total, bill.payment_status,
             (SELECT remarks FROM service_updates WHERE booking_id = b.id ORDER BY id DESC LIMIT 1) AS last_remark
             FROM bookings b
             JOIN services s ON b.service_id = s.id
             JOIN vehicles v ON b.vehicle_id = v.id
             JOIN customers c ON b.customer_id = c.id
             JOIN users u_cust ON c.user_id = u_cust.id
             LEFT JOIN mechanics m ON b.mechanic_id = m.id
             LEFT JOIN users u_mech ON m.user_id = u_mech.id
             LEFT JOIN bills bill ON bill.booking_id = b.id
             WHERE b.status IN ('Completed', 'Delivered')"""
    params = []

    if search:
        sql += " AND (v.registration_number LIKE %s OR u_cust.name LIKE %s OR b.booking_number LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])

    sql += " ORDER BY b.updated_at DESC, b.id DESC"
    history_records = query_db(sql, params)

    return render_template('admin/history.html', history_records=history_records, search=search)

# ---------------------------------------------------------------------
# BILLING & INVOICES
# ---------------------------------------------------------------------

@admin_bp.route('/bills')
@admin_required
def bills():
    """
    Billing & Invoice ledger with payment status filters.
    """
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('payment_status', 'all')

    sql = """SELECT b.*, bk.booking_number, bk.preferred_date,
             s.service_name, v.registration_number, v.brand, v.model,
             u_cust.name AS customer_name, u_cust.phone AS customer_phone
             FROM bills b
             JOIN bookings bk ON b.booking_id = bk.id
             JOIN services s ON bk.service_id = s.id
             JOIN vehicles v ON bk.vehicle_id = v.id
             JOIN customers c ON bk.customer_id = c.id
             JOIN users u_cust ON c.user_id = u_cust.id
             WHERE 1=1"""
    params = []

    if search:
        sql += " AND (b.invoice_number LIKE %s OR bk.booking_number LIKE %s OR u_cust.name LIKE %s OR v.registration_number LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    if status_filter != 'all':
        sql += " AND b.payment_status = %s"
        params.append(status_filter)

    sql += " ORDER BY b.id DESC"
    bills_list = query_db(sql, params)

    return render_template('admin/bills.html', bills=bills_list, search=search, status_filter=status_filter)

@admin_bp.route('/bills/generate/<int:booking_id>', methods=['GET', 'POST'])
@admin_required
def generate_bill(booking_id):
    """
    Generate itemized bill from service record.
    Calculations:
    Subtotal = Service Charge + Additional Charges + Parts Charges
    Grand Total = Subtotal - Discount + Tax (e.g. 18%)
    """
    # Check if bill already exists
    existing = query_db("SELECT id FROM bills WHERE booking_id = %s", (booking_id,), one=True)
    if existing:
        flash("An invoice for this service has already been generated.", "info")
        return redirect(url_for('admin.invoice', bill_id=existing['id']))

    booking = query_db(
        """SELECT b.*, s.service_name, s.base_price,
           v.registration_number, v.brand, v.model,
           u_cust.name AS customer_name, u_cust.phone AS customer_phone,
           u_mech.name AS mechanic_name
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN customers c ON b.customer_id = c.id
           JOIN users u_cust ON c.user_id = u_cust.id
           LEFT JOIN mechanics m ON b.mechanic_id = m.id
           LEFT JOIN users u_mech ON m.user_id = u_mech.id
           WHERE b.id = %s""",
        (booking_id,),
        one=True
    )

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('admin.bookings'))

    settings = get_workshop_settings()
    default_tax_rate = float(settings.get('default_tax_rate', 18.0))

    if request.method == 'POST':
        service_charge = float(request.form.get('service_charge', booking['base_price']) or 0.0)
        additional_charge = float(request.form.get('additional_charge', 0.0) or 0.0)
        discount = float(request.form.get('discount', 0.0) or 0.0)
        tax_rate = float(request.form.get('tax_rate', default_tax_rate) or 0.0)
        payment_status = request.form.get('payment_status', 'Unpaid')
        payment_method = request.form.get('payment_method', 'Cash')
        notes = request.form.get('notes', '').strip()

        # Parse itemized parts/labor from form
        item_names = request.form.getlist('item_name[]')
        item_descriptions = request.form.getlist('item_description[]')
        item_qtys = request.form.getlist('item_qty[]')
        item_prices = request.form.getlist('item_price[]')

        parts_charge = 0.0
        parsed_items = []
        for i in range(len(item_names)):
            name = item_names[i].strip()
            if name:
                desc = item_descriptions[i].strip() if i < len(item_descriptions) else ''
                qty = int(item_qtys[i]) if i < len(item_qtys) and item_qtys[i] else 1
                price = float(item_prices[i]) if i < len(item_prices) and item_prices[i] else 0.0
                total = qty * price
                parts_charge += total
                parsed_items.append({
                    'name': name,
                    'desc': desc,
                    'qty': qty,
                    'unit_price': price,
                    'total': total
                })

        # Calculate exact totals
        subtotal = service_charge + additional_charge + parts_charge
        taxable_amount = max(0.0, subtotal - discount)
        tax = (taxable_amount * tax_rate) / 100.0
        grand_total = taxable_amount + tax

        # Generate invoice number
        invoice_number = generate_invoice_number()

        # Insert bill record
        bill_id = execute_db(
            """INSERT INTO bills 
               (invoice_number, booking_id, service_charge, additional_charge, parts_charge, discount, tax, subtotal, grand_total, payment_status, payment_method, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (invoice_number, booking_id, service_charge, additional_charge, parts_charge, discount, tax, subtotal, grand_total, payment_status, payment_method, notes)
        )

        # Insert bill items
        for item in parsed_items:
            execute_db(
                """INSERT INTO bill_items (bill_id, item_name, description, quantity, unit_price, total)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (bill_id, item['name'], item['desc'], item['qty'], item['unit_price'], item['total'])
            )

        # Update booking status to Delivered or Completed
        new_status = 'Delivered' if payment_status == 'Paid' else 'Completed'
        execute_db("UPDATE bookings SET status = %s, updated_at = NOW() WHERE id = %s", (new_status, booking_id))

        log_service_update(
            booking_id=booking_id,
            status=new_status,
            remarks=f"Invoice {invoice_number} generated. Total: {format_currency(grand_total)}, Status: {payment_status}.",
            updated_by=session['user_id']
        )

        flash(f"Invoice {invoice_number} generated successfully! Grand Total: {format_currency(grand_total)}", "success")
        return redirect(url_for('admin.invoice', bill_id=bill_id))

    return render_template(
        'admin/generate_bill.html',
        booking=booking,
        settings=settings,
        default_tax_rate=default_tax_rate
    )

@admin_bp.route('/bills/<int:bill_id>/payment-status', methods=['POST'])
@admin_required
def update_payment_status(bill_id):
    """Update invoice payment status and payment method."""
    payment_status = request.form.get('payment_status')
    payment_method = request.form.get('payment_method', 'Cash')

    bill = query_db("SELECT * FROM bills WHERE id = %s", (bill_id,), one=True)
    if not bill:
        flash("Invoice not found.", "danger")
        return redirect(url_for('admin.bills'))

    execute_db(
        "UPDATE bills SET payment_status = %s, payment_method = %s WHERE id = %s",
        (payment_status, payment_method, bill_id)
    )

    # If marked Paid, auto mark booking Delivered
    if payment_status == 'Paid':
        execute_db("UPDATE bookings SET status = 'Delivered', updated_at = NOW() WHERE id = %s", (bill['booking_id'],))
        log_service_update(
            booking_id=bill['booking_id'],
            status='Delivered',
            remarks=f"Payment received in full via {payment_method}. Vehicle ready for handover.",
            updated_by=session['user_id']
        )

    flash(f"Payment status for {bill['invoice_number']} updated to '{payment_status}'.", "success")
    return redirect(url_for('admin.bills'))

@admin_bp.route('/invoice/<int:bill_id>')
@admin_required
def invoice(bill_id):
    """
    Professional printable invoice document.
    """
    bill = query_db(
        """SELECT b.*, bk.booking_number, bk.preferred_date, bk.complaint,
           s.service_name, s.description AS service_description,
           v.registration_number, v.brand, v.model, v.vehicle_type, v.fuel_type, v.current_km,
           u_cust.name AS customer_name, u_cust.email AS customer_email, u_cust.phone AS customer_phone,
           c.address AS customer_address,
           u_mech.name AS mechanic_name
           FROM bills b
           JOIN bookings bk ON b.booking_id = bk.id
           JOIN customers c ON bk.customer_id = c.id
           JOIN users u_cust ON c.user_id = u_cust.id
           JOIN services s ON bk.service_id = s.id
           JOIN vehicles v ON bk.vehicle_id = v.id
           LEFT JOIN mechanics m ON bk.mechanic_id = m.id
           LEFT JOIN users u_mech ON m.user_id = u_mech.id
           WHERE b.id = %s""",
        (bill_id,),
        one=True
    )

    if not bill:
        flash("Invoice not found.", "danger")
        return redirect(url_for('admin.bills'))

    bill_items = query_db("SELECT * FROM bill_items WHERE bill_id = %s ORDER BY id ASC", (bill_id,))
    settings = get_workshop_settings()

    return render_template('admin/invoice.html', bill=bill, items=bill_items, settings=settings)

# ---------------------------------------------------------------------
# REPORTS & ANALYTICS
# ---------------------------------------------------------------------

@admin_bp.route('/reports')
@admin_required
def reports():
    """
    Workshop Performance Reports: services volume, financial revenue, mechanic workload,
    and service type distribution.
    """
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status_filter = request.args.get('status', 'all')
    mechanic_filter = request.args.get('mechanic_id', 'all')
    service_filter = request.args.get('service_id', 'all')

    # Base conditions
    conds = ["1=1"]
    params = []

    if start_date:
        conds.append("b.preferred_date >= %s")
        params.append(start_date)
    if end_date:
        conds.append("b.preferred_date <= %s")
        params.append(end_date)
    if status_filter != 'all':
        conds.append("b.status = %s")
        params.append(status_filter)
    if mechanic_filter != 'all':
        conds.append("b.mechanic_id = %s")
        params.append(mechanic_filter)
    if service_filter != 'all':
        conds.append("b.service_id = %s")
        params.append(service_filter)

    where_clause = " AND ".join(conds)

    # Report Summary Metrics
    total_services = query_db(f"SELECT COUNT(*) AS count FROM bookings b WHERE {where_clause}", params, one=True)
    completed_services = query_db(f"SELECT COUNT(*) AS count FROM bookings b WHERE {where_clause} AND b.status IN ('Completed', 'Delivered')", params, one=True)
    pending_bookings = query_db(f"SELECT COUNT(*) AS count FROM bookings b WHERE {where_clause} AND b.status = 'Pending'", params, one=True)
    cancelled_bookings = query_db(f"SELECT COUNT(*) AS count FROM bookings b WHERE {where_clause} AND b.status = 'Cancelled'", params, one=True)

    # Financials in scope
    revenue_res = query_db(
        f"""SELECT 
            SUM(CASE WHEN bill.payment_status = 'Paid' THEN bill.grand_total ELSE 0 END) AS paid_revenue,
            SUM(CASE WHEN bill.payment_status = 'Unpaid' THEN bill.grand_total ELSE 0 END) AS pending_revenue,
            SUM(bill.grand_total) AS total_billed
            FROM bookings b
            JOIN bills bill ON b.id = bill.booking_id
            WHERE {where_clause}""",
        params,
        one=True
    )

    metrics = {
        'total_services': total_services['count'] if total_services else 0,
        'completed_services': completed_services['count'] if completed_services else 0,
        'pending_bookings': pending_bookings['count'] if pending_bookings else 0,
        'cancelled_bookings': cancelled_bookings['count'] if cancelled_bookings else 0,
        'paid_revenue': float(revenue_res['paid_revenue'] or 0.0) if revenue_res else 0.0,
        'pending_revenue': float(revenue_res['pending_revenue'] or 0.0) if revenue_res else 0.0,
        'total_billed': float(revenue_res['total_billed'] or 0.0) if revenue_res else 0.0
    }

    # Mechanic workload report
    mechanic_stats = query_db(
        """SELECT m.id, u.name, m.specialization,
           COUNT(b.id) AS total_assigned,
           SUM(CASE WHEN b.status IN ('In Service', 'Waiting for Parts', 'Mechanic Assigned', 'Vehicle Received') THEN 1 ELSE 0 END) AS in_progress,
           SUM(CASE WHEN b.status IN ('Completed', 'Delivered') THEN 1 ELSE 0 END) AS completed,
           COALESCE(SUM(bill.grand_total), 0) AS revenue_generated
           FROM mechanics m
           JOIN users u ON m.user_id = u.id
           LEFT JOIN bookings b ON b.mechanic_id = m.id
           LEFT JOIN bills bill ON bill.booking_id = b.id
           GROUP BY m.id, u.name, m.specialization
           ORDER BY total_assigned DESC"""
    )

    # Service Popularity
    service_stats = query_db(
        """SELECT s.service_name, s.base_price,
           COUNT(b.id) AS booking_count,
           COALESCE(SUM(bill.grand_total), 0) AS total_revenue
           FROM services s
           LEFT JOIN bookings b ON b.service_id = s.id
           LEFT JOIN bills bill ON bill.booking_id = b.id
           GROUP BY s.id, s.service_name, s.base_price
           ORDER BY booking_count DESC"""
    )

    # Master Report Filtered Table (max 50 rows)
    report_rows = query_db(
        f"""SELECT b.*, s.service_name, v.registration_number, v.brand, v.model,
            u_cust.name AS customer_name,
            u_mech.name AS mechanic_name,
            bill.invoice_number, bill.grand_total, bill.payment_status
            FROM bookings b
            JOIN services s ON b.service_id = s.id
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN customers c ON b.customer_id = c.id
            JOIN users u_cust ON c.user_id = u_cust.id
            LEFT JOIN mechanics m ON b.mechanic_id = m.id
            LEFT JOIN users u_mech ON m.user_id = u_mech.id
            LEFT JOIN bills bill ON bill.booking_id = b.id
            WHERE {where_clause}
            ORDER BY b.preferred_date DESC LIMIT 50""",
        params
    )

    all_mechanics = query_db("SELECT m.id, u.name FROM mechanics m JOIN users u ON m.user_id = u.id ORDER BY u.name ASC")
    all_services = query_db("SELECT id, service_name FROM services ORDER BY service_name ASC")

    return render_template(
        'admin/reports.html',
        metrics=metrics,
        mechanic_stats=mechanic_stats,
        service_stats=service_stats,
        report_rows=report_rows,
        all_mechanics=all_mechanics,
        all_services=all_services,
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter,
        mechanic_filter=mechanic_filter,
        service_filter=service_filter
    )

# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """
    Manage workshop profile, business info, tax rate, and invoice parameters.
    """
    if request.method == 'POST':
        workshop_name = request.form.get('workshop_name', '').strip()
        workshop_address = request.form.get('workshop_address', '').strip()
        workshop_phone = request.form.get('workshop_phone', '').strip()
        workshop_email = request.form.get('workshop_email', '').strip()
        workshop_gstin = request.form.get('workshop_gstin', '').strip()
        default_tax_rate = request.form.get('default_tax_rate', '18.00').strip()
        currency_symbol = request.form.get('currency_symbol', '₹').strip()

        updates = {
            'workshop_name': workshop_name,
            'workshop_address': workshop_address,
            'workshop_phone': workshop_phone,
            'workshop_email': workshop_email,
            'workshop_gstin': workshop_gstin,
            'default_tax_rate': default_tax_rate,
            'currency_symbol': currency_symbol
        }

        for key, val in updates.items():
            execute_db(
                """INSERT INTO settings (setting_key, setting_value)
                   VALUES (%s, %s)
                   ON DUPLICATE KEY UPDATE setting_value = %s""",
                (key, val, val)
            )

        flash("Workshop settings saved successfully.", "success")
        return redirect(url_for('admin.settings'))

    current_settings = get_workshop_settings()
    return render_template('admin/settings.html', settings=current_settings)

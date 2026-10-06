from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import query_db, execute_db
from utils.auth import customer_required
from utils.helpers import (
    generate_booking_number,
    log_service_update,
    format_currency,
    get_workshop_settings
)
import datetime

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

def get_current_customer_id():
    """Ensure customer ID is available in session or retrieve it from DB."""
    if 'customer_id' in session:
        return session['customer_id']
    cust = query_db("SELECT id FROM customers WHERE user_id = %s", (session.get('user_id'),), one=True)
    if cust:
        session['customer_id'] = cust['id']
        return cust['id']
    return None

@customer_bp.route('/dashboard')
@customer_required
def dashboard():
    """
    Customer overview dashboard with vehicle cards, key metrics, and recent service updates.
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        flash("Customer profile not found. Please contact administration.", "danger")
        return redirect(url_for('auth.logout'))

    # Metrics
    stats = {}
    total_vehicles = query_db("SELECT COUNT(*) AS count FROM vehicles WHERE customer_id = %s", (customer_id,), one=True)
    stats['total_vehicles'] = total_vehicles['count'] if total_vehicles else 0

    pending_bookings = query_db(
        "SELECT COUNT(*) AS count FROM bookings WHERE customer_id = %s AND status = 'Pending'",
        (customer_id,), one=True
    )
    stats['pending_bookings'] = pending_bookings['count'] if pending_bookings else 0

    active_services = query_db(
        """SELECT COUNT(*) AS count FROM bookings 
           WHERE customer_id = %s 
           AND status IN ('Approved', 'Mechanic Assigned', 'Vehicle Received', 'In Service', 'Waiting for Parts')""",
        (customer_id,), one=True
    )
    stats['active_services'] = active_services['count'] if active_services else 0

    completed_services = query_db(
        "SELECT COUNT(*) AS count FROM bookings WHERE customer_id = %s AND status IN ('Completed', 'Delivered')",
        (customer_id,), one=True
    )
    stats['completed_services'] = completed_services['count'] if completed_services else 0

    pending_bills = query_db(
        """SELECT COUNT(b.id) AS count FROM bills b
           JOIN bookings bk ON b.booking_id = bk.id
           WHERE bk.customer_id = %s AND b.payment_status = 'Unpaid'""",
        (customer_id,), one=True
    )
    stats['pending_bills'] = pending_bills['count'] if pending_bills else 0

    # Customer Vehicles with latest service status and last service date
    vehicles = query_db(
        """SELECT v.*, 
           (SELECT b.status FROM bookings b WHERE b.vehicle_id = v.id ORDER BY b.id DESC LIMIT 1) AS latest_service_status,
           (SELECT b.preferred_date FROM bookings b WHERE b.vehicle_id = v.id AND b.status IN ('Completed', 'Delivered') ORDER BY b.id DESC LIMIT 1) AS last_service_date
           FROM vehicles v
           WHERE v.customer_id = %s
           ORDER BY v.id DESC""",
        (customer_id,)
    )

    # Recent 5 Bookings
    recent_bookings = query_db(
        """SELECT b.*, s.service_name, v.registration_number, v.brand, v.model,
           u.name AS mechanic_name
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           JOIN vehicles v ON b.vehicle_id = v.id
           LEFT JOIN mechanics m ON b.mechanic_id = m.id
           LEFT JOIN users u ON m.user_id = u.id
           WHERE b.customer_id = %s
           ORDER BY b.id DESC LIMIT 5""",
        (customer_id,)
    )

    return render_template(
        'customer/dashboard.html',
        stats=stats,
        vehicles=vehicles,
        recent_bookings=recent_bookings
    )

@customer_bp.route('/vehicles', methods=['GET', 'POST'])
@customer_required
def vehicles():
    """
    List and add customer vehicles.
    """
    customer_id = get_current_customer_id()

    if request.method == 'POST':
        reg_number = request.form.get('registration_number', '').strip().upper()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'Car')
        year = request.form.get('manufacturing_year', '').strip()
        fuel_type = request.form.get('fuel_type', 'Petrol')
        color = request.form.get('color', '').strip()
        current_km = request.form.get('current_km', '0').strip()

        # Validation
        if not reg_number or not brand or not model or not year or not color:
            flash("All vehicle fields are required. Please check your input.", "danger")
        else:
            try:
                year_int = int(year)
                km_int = int(current_km) if current_km else 0
                current_year = datetime.datetime.now().year

                if year_int < 1980 or year_int > current_year + 1:
                    flash(f"Please enter a realistic manufacturing year (1980 - {current_year + 1}).", "danger")
                else:
                    # Check duplicate registration number
                    existing = query_db("SELECT id FROM vehicles WHERE registration_number = %s", (reg_number,), one=True)
                    if existing:
                        flash(f"A vehicle with registration number '{reg_number}' already exists in the system.", "danger")
                    else:
                        execute_db(
                            """INSERT INTO vehicles 
                               (customer_id, registration_number, brand, model, vehicle_type, manufacturing_year, fuel_type, color, current_km)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (customer_id, reg_number, brand, model, vehicle_type, year_int, fuel_type, color, km_int)
                        )
                        flash(f"Vehicle {brand} {model} ({reg_number}) registered successfully!", "success")
                        return redirect(url_for('customer.vehicles'))
            except ValueError:
                flash("Manufacturing year and Current KM must be valid integers.", "danger")

    # Fetch all vehicles owned by this customer
    vehicles_list = query_db(
        """SELECT v.*,
           (SELECT b.status FROM bookings b WHERE b.vehicle_id = v.id ORDER BY b.id DESC LIMIT 1) AS latest_service_status,
           (SELECT b.preferred_date FROM bookings b WHERE b.vehicle_id = v.id AND b.status IN ('Completed', 'Delivered') ORDER BY b.id DESC LIMIT 1) AS last_service_date,
           (SELECT COUNT(*) FROM bookings b WHERE b.vehicle_id = v.id) AS total_services_count
           FROM vehicles v
           WHERE v.customer_id = %s
           ORDER BY v.id DESC""",
        (customer_id,)
    )

    return render_template('customer/vehicles.html', vehicles=vehicles_list)

@customer_bp.route('/vehicles/edit/<int:vehicle_id>', methods=['POST'])
@customer_required
def edit_vehicle(vehicle_id):
    """
    Update vehicle specifications.
    """
    customer_id = get_current_customer_id()
    vehicle = query_db("SELECT * FROM vehicles WHERE id = %s AND customer_id = %s", (vehicle_id, customer_id), one=True)
    if not vehicle:
        flash("Vehicle not found or unauthorized.", "danger")
        return redirect(url_for('customer.vehicles'))

    reg_number = request.form.get('registration_number', '').strip().upper()
    brand = request.form.get('brand', '').strip()
    model = request.form.get('model', '').strip()
    vehicle_type = request.form.get('vehicle_type', vehicle['vehicle_type'])
    year = request.form.get('manufacturing_year', '').strip()
    fuel_type = request.form.get('fuel_type', vehicle['fuel_type'])
    color = request.form.get('color', '').strip()
    current_km = request.form.get('current_km', '0').strip()

    # Check duplicate registration on other vehicle
    dup = query_db("SELECT id FROM vehicles WHERE registration_number = %s AND id != %s", (reg_number, vehicle_id), one=True)
    if dup:
        flash(f"Registration number '{reg_number}' is already assigned to another vehicle.", "danger")
        return redirect(url_for('customer.vehicles'))

    try:
        execute_db(
            """UPDATE vehicles 
               SET registration_number = %s, brand = %s, model = %s, vehicle_type = %s,
                   manufacturing_year = %s, fuel_type = %s, color = %s, current_km = %s
               WHERE id = %s AND customer_id = %s""",
            (reg_number, brand, model, vehicle_type, int(year), fuel_type, color, int(current_km), vehicle_id, customer_id)
        )
        flash(f"Vehicle details for '{reg_number}' updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update vehicle: {e}", "danger")

    return redirect(url_for('customer.vehicles'))

@customer_bp.route('/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@customer_required
def delete_vehicle(vehicle_id):
    """
    Remove vehicle if there are no active bookings in progress.
    """
    customer_id = get_current_customer_id()
    vehicle = query_db("SELECT * FROM vehicles WHERE id = %s AND customer_id = %s", (vehicle_id, customer_id), one=True)
    if not vehicle:
        flash("Vehicle not found or unauthorized.", "danger")
        return redirect(url_for('customer.vehicles'))

    # Check for active bookings
    active = query_db(
        """SELECT id FROM bookings WHERE vehicle_id = %s 
           AND status NOT IN ('Completed', 'Delivered', 'Cancelled')""",
        (vehicle_id,), one=True
    )
    if active:
        flash("Cannot delete vehicle with active service bookings. Please wait until completed or cancel first.", "warning")
        return redirect(url_for('customer.vehicles'))

    execute_db("DELETE FROM vehicles WHERE id = %s AND customer_id = %s", (vehicle_id, customer_id))
    flash(f"Vehicle '{vehicle['registration_number']}' was removed successfully.", "info")
    return redirect(url_for('customer.vehicles'))

@customer_bp.route('/book-service', methods=['GET', 'POST'])
@customer_required
def book_service():
    """
    Service booking workflow form.
    """
    customer_id = get_current_customer_id()
    vehicles_list = query_db("SELECT * FROM vehicles WHERE customer_id = %s ORDER BY brand, model", (customer_id,))
    services_list = query_db("SELECT * FROM services WHERE status = 'Active' ORDER BY service_name")

    if not vehicles_list:
        flash("Please register at least one vehicle before booking a service.", "warning")
        return redirect(url_for('customer.vehicles'))

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        service_id = request.form.get('service_id')
        preferred_date = request.form.get('preferred_date')
        preferred_time = request.form.get('preferred_time')
        complaint = request.form.get('complaint', '').strip()
        notes = request.form.get('notes', '').strip()

        # Validation
        if not vehicle_id or not service_id or not preferred_date or not preferred_time or not complaint:
            flash("Please fill in all required booking fields (vehicle, service, date, time, complaint).", "danger")
            return render_template('customer/book_service.html', vehicles=vehicles_list, services=services_list)

        # Ensure vehicle belongs to customer
        v = query_db("SELECT id FROM vehicles WHERE id = %s AND customer_id = %s", (vehicle_id, customer_id), one=True)
        if not v:
            flash("Invalid vehicle selected.", "danger")
            return render_template('customer/book_service.html', vehicles=vehicles_list, services=services_list)

        # Check date not in the past
        try:
            booking_date = datetime.date.fromisoformat(preferred_date)
            if booking_date < datetime.date.today():
                flash("Preferred service date cannot be in the past.", "danger")
                return render_template('customer/book_service.html', vehicles=vehicles_list, services=services_list)
        except ValueError:
            flash("Invalid date format selected.", "danger")
            return render_template('customer/book_service.html', vehicles=vehicles_list, services=services_list)

        # Generate unique booking number
        booking_number = generate_booking_number()

        # Insert booking with status Pending
        booking_id = execute_db(
            """INSERT INTO bookings 
               (booking_number, customer_id, vehicle_id, service_id, preferred_date, preferred_time, complaint, notes, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pending')""",
            (booking_number, customer_id, vehicle_id, service_id, preferred_date, preferred_time, complaint, notes)
        )

        # Audit update
        log_service_update(
            booking_id=booking_id,
            status='Pending',
            remarks=f"Service booking request submitted by customer. Problem: {complaint}",
            updated_by=session['user_id']
        )

        flash(f"Booking {booking_number} submitted successfully! Our service manager will review and confirm shortly.", "success")
        return redirect(url_for('customer.booking_detail', booking_id=booking_id))

    return render_template('customer/book_service.html', vehicles=vehicles_list, services=services_list)

@customer_bp.route('/bookings')
@customer_required
def bookings():
    """
    List of all bookings made by customer with filter options.
    """
    customer_id = get_current_customer_id()
    status_filter = request.args.get('status', 'all')

    sql = """SELECT b.*, s.service_name, s.base_price, v.registration_number, v.brand, v.model,
             u.name AS mechanic_name,
             bill.id AS bill_id, bill.invoice_number, bill.grand_total, bill.payment_status
             FROM bookings b
             JOIN services s ON b.service_id = s.id
             JOIN vehicles v ON b.vehicle_id = v.id
             LEFT JOIN mechanics m ON b.mechanic_id = m.id
             LEFT JOIN users u ON m.user_id = u.id
             LEFT JOIN bills bill ON bill.booking_id = b.id
             WHERE b.customer_id = %s"""
    params = [customer_id]

    if status_filter != 'all':
        sql += " AND b.status = %s"
        params.append(status_filter)

    sql += " ORDER BY b.id DESC"
    bookings_list = query_db(sql, params)

    return render_template('customer/bookings.html', bookings=bookings_list, current_status=status_filter)

@customer_bp.route('/bookings/<int:booking_id>')
@customer_required
def booking_detail(booking_id):
    """
    Detailed booking status tracking page with complete service update timeline.
    """
    customer_id = get_current_customer_id()
    booking = query_db(
        """SELECT b.*, s.service_name, s.description AS service_description, s.base_price, s.estimated_duration,
           v.registration_number, v.brand, v.model, v.vehicle_type, v.fuel_type, v.color, v.current_km,
           u_mech.name AS mechanic_name, u_mech.phone AS mechanic_phone, m.specialization AS mechanic_specialization,
           bill.id AS bill_id, bill.invoice_number, bill.grand_total, bill.payment_status
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           JOIN vehicles v ON b.vehicle_id = v.id
           LEFT JOIN mechanics m ON b.mechanic_id = m.id
           LEFT JOIN users u_mech ON m.user_id = u_mech.id
           LEFT JOIN bills bill ON bill.booking_id = b.id
           WHERE b.id = %s AND b.customer_id = %s""",
        (booking_id, customer_id),
        one=True
    )

    if not booking:
        flash("Booking not found or access denied.", "danger")
        return redirect(url_for('customer.bookings'))

    # Service update timeline
    updates = query_db(
        """SELECT su.*, u.name AS updated_by_name, u.role AS updated_by_role
           FROM service_updates su
           JOIN users u ON su.updated_by = u.id
           WHERE su.booking_id = %s
           ORDER BY su.created_at DESC""",
        (booking_id,)
    )

    return render_template('customer/booking_detail.html', booking=booking, updates=updates)

@customer_bp.route('/history')
@customer_required
def history():
    """
    Vehicle service history view for customer.
    """
    customer_id = get_current_customer_id()
    vehicle_filter = request.args.get('vehicle_id', '')

    sql = """SELECT b.*, s.service_name, v.registration_number, v.brand, v.model,
             u.name AS mechanic_name,
             bill.id AS bill_id, bill.invoice_number, bill.grand_total, bill.payment_status,
             (SELECT remarks FROM service_updates WHERE booking_id = b.id ORDER BY id DESC LIMIT 1) AS last_remark
             FROM bookings b
             JOIN services s ON b.service_id = s.id
             JOIN vehicles v ON b.vehicle_id = v.id
             LEFT JOIN mechanics m ON b.mechanic_id = m.id
             LEFT JOIN users u ON m.user_id = u.id
             LEFT JOIN bills bill ON bill.booking_id = b.id
             WHERE b.customer_id = %s AND b.status IN ('Completed', 'Delivered')"""
    params = [customer_id]

    if vehicle_filter:
        sql += " AND b.vehicle_id = %s"
        params.append(vehicle_filter)

    sql += " ORDER BY b.preferred_date DESC, b.id DESC"
    history_records = query_db(sql, params)

    vehicles = query_db("SELECT id, registration_number, brand, model FROM vehicles WHERE customer_id = %s", (customer_id,))
    return render_template('customer/history.html', history_records=history_records, vehicles=vehicles, selected_vehicle=vehicle_filter)

@customer_bp.route('/bills')
@customer_required
def bills():
    """
    Customer bills and invoices listing.
    """
    customer_id = get_current_customer_id()
    bills_list = query_db(
        """SELECT b.*, bk.booking_number, bk.preferred_date, s.service_name,
           v.registration_number, v.brand, v.model
           FROM bills b
           JOIN bookings bk ON b.booking_id = bk.id
           JOIN services s ON bk.service_id = s.id
           JOIN vehicles v ON bk.vehicle_id = v.id
           WHERE bk.customer_id = %s
           ORDER BY b.id DESC""",
        (customer_id,)
    )
    return render_template('customer/bills.html', bills=bills_list)

@customer_bp.route('/invoice/<int:bill_id>')
@customer_required
def invoice(bill_id):
    """
    Customer printable invoice view.
    """
    customer_id = get_current_customer_id()
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
           WHERE b.id = %s AND bk.customer_id = %s""",
        (bill_id, customer_id),
        one=True
    )

    if not bill:
        flash("Invoice not found or unauthorized.", "danger")
        return redirect(url_for('customer.bills'))

    bill_items = query_db("SELECT * FROM bill_items WHERE bill_id = %s ORDER BY id ASC", (bill_id,))
    settings = get_workshop_settings()

    return render_template('customer/invoice.html', bill=bill, items=bill_items, settings=settings)

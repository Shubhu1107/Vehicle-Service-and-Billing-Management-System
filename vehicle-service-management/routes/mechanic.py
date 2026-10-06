from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import query_db, execute_db
from utils.auth import mechanic_required
from utils.helpers import log_service_update
import datetime

mechanic_bp = Blueprint('mechanic', __name__, url_prefix='/mechanic')

def get_current_mechanic_id():
    """Retrieve mechanic profile ID associated with current user."""
    if 'mechanic_id' in session:
        return session['mechanic_id']
    mech = query_db("SELECT id FROM mechanics WHERE user_id = %s", (session.get('user_id'),), one=True)
    if mech:
        session['mechanic_id'] = mech['id']
        return mech['id']
    return None

@mechanic_bp.route('/dashboard')
@mechanic_required
def dashboard():
    """
    Mechanic dashboard with workload stats and assigned service queue.
    """
    mechanic_id = get_current_mechanic_id()
    if not mechanic_id:
        flash("Mechanic profile not found. Please contact administration.", "danger")
        return redirect(url_for('auth.logout'))

    # Stats
    stats = {}
    assigned = query_db(
        """SELECT COUNT(*) AS count FROM bookings 
           WHERE mechanic_id = %s AND status NOT IN ('Completed', 'Delivered', 'Cancelled')""",
        (mechanic_id,), one=True
    )
    stats['assigned_services'] = assigned['count'] if assigned else 0

    pending = query_db(
        """SELECT COUNT(*) AS count FROM bookings 
           WHERE mechanic_id = %s AND status IN ('Mechanic Assigned', 'Vehicle Received')""",
        (mechanic_id,), one=True
    )
    stats['pending_work'] = pending['count'] if pending else 0

    in_service = query_db(
        """SELECT COUNT(*) AS count FROM bookings 
           WHERE mechanic_id = %s AND status = 'In Service'""",
        (mechanic_id,), one=True
    )
    stats['in_service'] = in_service['count'] if in_service else 0

    completed_today = query_db(
        """SELECT COUNT(*) AS count FROM bookings 
           WHERE mechanic_id = %s AND status IN ('Completed', 'Delivered') 
           AND DATE(updated_at) = CURRENT_DATE""",
        (mechanic_id,), one=True
    )
    stats['completed_today'] = completed_today['count'] if completed_today else 0

    # Assigned Active Bookings
    bookings = query_db(
        """SELECT b.*, s.service_name, s.estimated_duration,
           v.registration_number, v.brand, v.model, v.fuel_type,
           u_cust.name AS customer_name, u_cust.phone AS customer_phone
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN customers c ON b.customer_id = c.id
           JOIN users u_cust ON c.user_id = u_cust.id
           WHERE b.mechanic_id = %s
           ORDER BY 
             CASE b.status
               WHEN 'In Service' THEN 1
               WHEN 'Waiting for Parts' THEN 2
               WHEN 'Vehicle Received' THEN 3
               WHEN 'Mechanic Assigned' THEN 4
               ELSE 5
             END, b.preferred_date ASC""",
        (mechanic_id,)
    )

    return render_template('mechanic/dashboard.html', stats=stats, bookings=bookings)

@mechanic_bp.route('/services')
@mechanic_required
def services():
    """
    List all assigned services with status filter.
    """
    mechanic_id = get_current_mechanic_id()
    status_filter = request.args.get('status', 'active')

    sql = """SELECT b.*, s.service_name, s.estimated_duration,
             v.registration_number, v.brand, v.model, v.fuel_type,
             u_cust.name AS customer_name, u_cust.phone AS customer_phone
             FROM bookings b
             JOIN services s ON b.service_id = s.id
             JOIN vehicles v ON b.vehicle_id = v.id
             JOIN customers c ON b.customer_id = c.id
             JOIN users u_cust ON c.user_id = u_cust.id
             WHERE b.mechanic_id = %s"""
    params = [mechanic_id]

    if status_filter == 'active':
        sql += " AND b.status IN ('Mechanic Assigned', 'Vehicle Received', 'In Service', 'Waiting for Parts')"
    elif status_filter == 'completed':
        sql += " AND b.status IN ('Completed', 'Delivered')"
    elif status_filter != 'all':
        sql += " AND b.status = %s"
        params.append(status_filter)

    sql += " ORDER BY b.id DESC"
    services_list = query_db(sql, params)

    return render_template('mechanic/services.html', bookings=services_list, current_filter=status_filter)

@mechanic_bp.route('/services/<int:booking_id>', methods=['GET', 'POST'])
@mechanic_required
def service_detail(booking_id):
    """
    Detailed service job screen: update status, enter remarks, log parts required or completed work.
    """
    mechanic_id = get_current_mechanic_id()
    booking = query_db(
        """SELECT b.*, s.service_name, s.description AS service_description, s.estimated_duration,
           v.registration_number, v.brand, v.model, v.vehicle_type, v.fuel_type, v.color, v.current_km,
           u_cust.name AS customer_name, u_cust.phone AS customer_phone, u_cust.email AS customer_email,
           c.address AS customer_address
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN customers c ON b.customer_id = c.id
           JOIN users u_cust ON c.user_id = u_cust.id
           WHERE b.id = %s AND b.mechanic_id = %s""",
        (booking_id, mechanic_id),
        one=True
    )

    if not booking:
        flash("Service job not found or not assigned to you.", "danger")
        return redirect(url_for('mechanic.dashboard'))

    if request.method == 'POST':
        new_status = request.form.get('status')
        remarks = request.form.get('remarks', '').strip()
        work_done = request.form.get('work_done', '').strip()

        allowed_statuses = ['Vehicle Received', 'In Service', 'Waiting for Parts', 'Completed']
        if new_status not in allowed_statuses:
            flash("Invalid service status selected.", "danger")
        elif not remarks:
            flash("Please enter remarks/details about the update.", "danger")
        else:
            full_remarks = remarks
            if work_done:
                full_remarks += f"\n[Work Performed: {work_done}]"

            # Update booking status
            execute_db(
                "UPDATE bookings SET status = %s, updated_at = NOW() WHERE id = %s",
                (new_status, booking_id)
            )

            # Insert audit update
            log_service_update(
                booking_id=booking_id,
                status=new_status,
                remarks=full_remarks,
                updated_by=session['user_id']
            )

            # Update mechanic status based on active load
            if new_status == 'Completed':
                # Check remaining active jobs
                active_remaining = query_db(
                    """SELECT COUNT(*) AS count FROM bookings 
                       WHERE mechanic_id = %s AND id != %s 
                       AND status IN ('Mechanic Assigned', 'Vehicle Received', 'In Service', 'Waiting for Parts')""",
                    (mechanic_id, booking_id),
                    one=True
                )
                if not active_remaining or active_remaining['count'] == 0:
                    execute_db("UPDATE mechanics SET status = 'Available' WHERE id = %s", (mechanic_id,))
            else:
                execute_db("UPDATE mechanics SET status = 'Busy' WHERE id = %s", (mechanic_id,))

            flash(f"Service status updated to '{new_status}' successfully!", "success")
            return redirect(url_for('mechanic.service_detail', booking_id=booking_id))

    # Fetch previous update timeline
    updates = query_db(
        """SELECT su.*, u.name AS updated_by_name, u.role AS updated_by_role
           FROM service_updates su
           JOIN users u ON su.updated_by = u.id
           WHERE su.booking_id = %s
           ORDER BY su.created_at DESC""",
        (booking_id,)
    )

    return render_template('mechanic/service_detail.html', booking=booking, updates=updates)

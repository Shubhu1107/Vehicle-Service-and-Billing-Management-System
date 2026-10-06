import datetime
import re
from database.db import query_db, execute_db
from config import Config

def generate_booking_number():
    """
    Generates a unique sequential booking reference, e.g., 'BK-2026-0008'.
    """
    current_year = datetime.datetime.now().year
    row = query_db(
        "SELECT booking_number FROM bookings WHERE booking_number LIKE %s ORDER BY id DESC LIMIT 1",
        (f"BK-{current_year}-%",),
        one=True
    )
    if row and row.get('booking_number'):
        try:
            last_seq = int(row['booking_number'].split('-')[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1
    return f"BK-{current_year}-{new_seq:04d}"

def generate_invoice_number():
    """
    Generates a unique sequential invoice reference, e.g., 'INV-2026-0003'.
    """
    current_year = datetime.datetime.now().year
    row = query_db(
        "SELECT invoice_number FROM bills WHERE invoice_number LIKE %s ORDER BY id DESC LIMIT 1",
        (f"INV-{current_year}-%",),
        one=True
    )
    if row and row.get('invoice_number'):
        try:
            last_seq = int(row['invoice_number'].split('-')[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1
    return f"INV-{current_year}-{new_seq:04d}"

def format_currency(value):
    """
    Formats a decimal or float as a formatted currency string, e.g. '₹ 2,500.00'.
    """
    try:
        val = float(value or 0.0)
        return f"₹ {val:,.2f}"
    except (ValueError, TypeError):
        return "₹ 0.00"

def format_datetime(value, fmt="%d %b %Y, %I:%M %p"):
    """
    Formats a datetime object or string.
    """
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.datetime.fromisoformat(value)
        except Exception:
            return value
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.strftime(fmt)
    return str(value)

def format_date(value, fmt="%d %b %Y"):
    """
    Formats a date object or string into a clean readable date.
    """
    return format_datetime(value, fmt=fmt)

def get_status_badge(status):
    """
    Returns HTML badge classes and styling based on booking or payment status.
    """
    mapping = {
        'Pending': 'bg-warning text-dark',
        'Approved': 'bg-info text-dark',
        'Mechanic Assigned': 'bg-primary text-white',
        'Vehicle Received': 'bg-secondary text-white',
        'In Service': 'bg-primary text-white',
        'Waiting for Parts': 'bg-warning text-dark',
        'Completed': 'bg-success text-white',
        'Delivered': 'bg-success text-white',
        'Cancelled': 'bg-danger text-white',
        'Available': 'bg-success text-white',
        'Busy': 'bg-warning text-dark',
        'Inactive': 'bg-secondary text-white',
        'Active': 'bg-success text-white',
        'Paid': 'bg-success text-white',
        'Unpaid': 'bg-danger text-white',
        'Partial': 'bg-warning text-dark'
    }
    return mapping.get(str(status), 'bg-secondary text-white')

def get_workshop_settings():
    """
    Retrieves workshop configuration settings as a key-value dictionary.
    Falls back to Config constants if not configured in the database.
    """
    settings = {
        'workshop_name': Config.COMPANY_NAME,
        'workshop_address': Config.COMPANY_ADDRESS,
        'workshop_phone': Config.COMPANY_PHONE,
        'workshop_email': Config.COMPANY_EMAIL,
        'workshop_gstin': Config.GST_NUMBER,
        'default_tax_rate': Config.TAX_RATE_PERCENT,
        'currency_symbol': '₹'
    }
    try:
        rows = query_db("SELECT setting_key, setting_value FROM settings")
        for row in rows:
            settings[row['setting_key']] = row['setting_value']
    except Exception:
        pass
    return settings

def log_service_update(booking_id, status, remarks, updated_by):
    """
    Logs an audit event in the service_updates table whenever booking status changes.
    """
    try:
        execute_db(
            "INSERT INTO service_updates (booking_id, status, remarks, updated_by) VALUES (%s, %s, %s, %s)",
            (booking_id, status, remarks, updated_by)
        )
    except Exception as e:
        print(f"Error logging service update: {e}")

def is_valid_email(email):
    """Validates email format using regex."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email.strip()) is not None

def is_valid_phone(phone):
    """Validates phone number (standard 10 digits or with optional country code)."""
    if not phone:
        return False
    cleaned = re.sub(r'[\s\-\+\(\)]', '', phone)
    return len(cleaned) >= 8 and len(cleaned) <= 15

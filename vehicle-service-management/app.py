from flask import Flask, render_template, redirect, url_for, session, request
from config import Config
from database.db import close_db
from utils.helpers import (
    format_currency,
    format_datetime,
    format_date,
    get_status_badge,
    get_workshop_settings
)

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.customer import customer_bp
from routes.mechanic import mechanic_bp

def create_app():
    """Application factory for Vehicle Service Management and Billing System."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register Database teardown hook
    app.teardown_appcontext(close_db)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(mechanic_bp)

    # Custom Jinja Template Filters
    @app.template_filter('currency')
    def jinja_currency(value):
        return format_currency(value)

    @app.template_filter('format_datetime')
    def jinja_datetime(value, fmt="%d %b %Y, %I:%M %p"):
        return format_datetime(value, fmt=fmt)

    @app.template_filter('format_date')
    def jinja_date(value, fmt="%d %b %Y"):
        return format_date(value, fmt=fmt)

    @app.template_filter('status_badge')
    def jinja_status_badge(status):
        return get_status_badge(status)

    # Global Context Processor for Templates
    @app.context_processor
    def inject_global_data():
        settings = get_workshop_settings()
        return {
            'app_name': Config.APP_NAME,
            'workshop_settings': settings,
            'current_user': {
                'id': session.get('user_id'),
                'name': session.get('name'),
                'email': session.get('email'),
                'role': session.get('role'),
                'customer_id': session.get('customer_id'),
                'mechanic_id': session.get('mechanic_id')
            } if 'user_id' in session else None
        }

    # Root Gateway Route
    @app.route('/')
    def index():
        if 'user_id' in session:
            role = session.get('role')
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'mechanic':
                return redirect(url_for('mechanic.dashboard'))
            elif role == 'customer':
                return redirect(url_for('customer.dashboard'))
        return redirect(url_for('auth.login'))

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    import pymysql
    @app.errorhandler(pymysql.MySQLError)
    def database_error(error):
        return render_template('errors/db_error.html', error_msg=str(error)), 503

    return app

app = create_app()

if __name__ == '__main__':
    # Run development server
    app.run(host='127.0.0.1', port=5000, debug=True)

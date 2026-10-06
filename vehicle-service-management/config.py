import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base application configuration class."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-vsm-secret-key-college-2026')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    
    # MySQL Database Connection Settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
    DB_NAME = os.getenv('DB_NAME', 'vehicle_service_management')
    
    # System Info
    APP_NAME = "AutoCare Pro - Vehicle Service & Billing"
    COMPANY_NAME = "AutoCare Service Center & Workshop"
    COMPANY_ADDRESS = "Plot 42, Industrial Area, Ring Road, Tech City - 400001"
    COMPANY_PHONE = "+91 98765 43210"
    COMPANY_EMAIL = "support@autocare.com"
    GST_NUMBER = "27ABCDE1234F1Z5"
    TAX_RATE_PERCENT = 18.00  # Default 18% GST / Sales Tax

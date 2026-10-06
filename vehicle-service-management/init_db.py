"""
Database Initializer Script
Usage:
    python init_db.py

This script connects to your MySQL server using the credentials in .env or config.py,
creates the 'vehicle_service_management' database, builds all tables, and populates
realistic demonstration data.
"""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database.db import init_db

def main():
    print("=" * 65)
    print(" AutoCare Pro - Vehicle Service Management & Billing System")
    print(" MySQL Database Setup & Seed Data Initialization")
    print("=" * 65)
    print(f"Target Host:     {Config.DB_HOST}:{Config.DB_PORT}")
    print(f"Database User:   {Config.DB_USER}")
    print(f"Database Name:   {Config.DB_NAME}")
    print("-" * 65)

    try:
        print("Connecting to MySQL and executing schema.sql ...")
        init_db()
        print("\n[SUCCESS] Database initialized and seeded successfully!")
        print("  1. Admin:    admin@autocare.com      | Password: admin123")
        print("  2. Mechanic: rajesh.kumar@autocare.com | Password: mechanic123")
        print("  3. Customer: amit.sharma@gmail.com    | Password: customer123")
        print("=" * 65)
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize database: {e}")
        print("\nTroubleshooting Tips:")
        print("1. Ensure MySQL Server or XAMPP / WampServer MySQL service is RUNNING.")
        print("2. Check credentials in .env file (DB_HOST, DB_USER, DB_PASSWORD, DB_PORT).")
        print("3. Alternatively, you can open MySQL Workbench and run 'database/schema.sql' directly.")
        print("=" * 65)
        sys.exit(1)

if __name__ == '__main__':
    main()

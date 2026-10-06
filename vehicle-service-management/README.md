# AutoCare Pro — Vehicle Service Management and Billing System

A complete, production-ready, full-stack web application designed for modern automotive service centers and workshops. Built with **Python Flask**, **MySQL**, **Bootstrap 5**, and **Vanilla JavaScript**, this system eliminates manual paperwork, automates repair order workflows, tracks vehicle service history, and computes itemized GST-compliant invoices.

---

## 📌 Problem Statement

Traditional automotive repair shops face major operational bottlenecks:
- **Paper job cards and lost physical records** leading to missed customer history.
- **Unclear appointment scheduling** causing workshop bay congestion and customer wait times.
- **Opaque technician allocation** resulting in unbalanced workloads and delayed repair times.
- **Error-prone billing calculations** with manual spare parts pricing, labor estimates, and tax computation errors.
- **Zero real-time visibility** for vehicle owners regarding their car or motorcycle status.

**AutoCare Pro** solves these challenges by centralizing vehicle registration, booking appointments, mechanic assignment, step-by-step progress tracking, audit logging, and digital invoicing.

---

## 👥 User Roles & Permissions

The application implements strict Role-Based Access Control (RBAC) via secure Flask sessions and server-side decorators:

### 1. Customer
- **Self-Registration & Authentication:** Sign up, login, and manage account details.
- **Multi-Vehicle Garage:** Register multiple 2-wheelers and 4-wheelers (Cars, Bikes, Scooters, EVs) with engine, fuel, and odometer specifications.
- **Service Booking:** Schedule service packages (General Service, Oil Change, Brake Overhaul, AC Diagnostics, etc.) with preferred time slots and symptom descriptions.
- **Real-Time Bay Tracking:** View live status transitions (`Pending` &rarr; `Approved` &rarr; `Mechanic Assigned` &rarr; `Vehicle Received` &rarr; `In Service` &rarr; `Waiting for Parts` &rarr; `Completed` &rarr; `Delivered`).
- **Service History:** Access complete chronological logs of past maintenance and repairs.
- **Digital Invoices:** View, verify, and print detailed GST invoices.

### 2. Admin (Workshop Supervisor / Manager)
- **Executive Command Center:** Real-time KPI summary cards (Total Customers, Vehicles, Pending Bookings, Active Bay Jobs, Completed Jobs, Mechanics Count, Revenue Collected, and Pending Dues).
- **Customer & Vehicle Management:** Full CRUD operations, registration validation, and customer relationship history.
- **Service Catalog Management:** Add/edit maintenance packages, set base prices, estimated duration, and package descriptions.
- **Mechanic Management:** Register mechanics, define specializations (Engine, Electrical, Transmission), track experience, and monitor real-time workload.
- **Booking Workflow Control:** Approve/reject bookings, assign mechanics based on availability, reschedule appointment slots, and override bay statuses.
- **Dynamic Billing Engine:** Calculate labor charges, itemized spare parts, discounts, and applicable GST (18%) to generate unique invoice numbers (e.g. `INV-2026-0001`).
- **Payment Reconciliation:** Update payment status (`Paid`, `Unpaid`, `Partial`) and method (`Cash`, `UPI`, `Card`, `Net Banking`).
- **Workshop Analytics & Reports:** Multi-criteria filtering by Date Range, Status, Technician, and Service Package with financial summaries and exportable reports.
- **System Settings:** Configure workshop trade name, phone, email, physical address, GSTIN, and tax rates.

### 3. Mechanic (Bay Technician)
- **Dedicated Bay Dashboard:** View assigned jobs, pending vehicle check-ins, vehicles currently on the ramp, and jobs finished today.
- **Assigned Services Ledger:** Access customer contact, vehicle specifications, and reported complaints.
- **Live Progress Updater:** Update service milestones (`Vehicle Received`, `In Service`, `Waiting for Parts`, `Completed`) with detailed technical remarks and parts replaced notes.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python 3.11+ / Flask 3.0+ (Modular Blueprints architecture) |
| **Database** | MySQL 5.7+ / 8.0+ / MariaDB (Relational schema with foreign keys & indexes) |
| **Database Driver** | PyMySQL (Pure Python client with Dictionary Cursors & Parameterized Queries) |
| **Frontend UI** | HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons |
| **Client Scripting** | Vanilla JavaScript (Dynamic invoice calculations, modal handlers, print styling) |
| **Authentication** | Werkzeug Security (Scrypt password hashing, session cookies) |

---

## 📂 Project Structure

```text
vehicle-service-management/
├── app.py                     # Application factory, Jinja filters, error handlers, gateway route
├── config.py                  # Environment-driven configuration class
├── requirements.txt           # Python dependency specifications
├── init_db.py                 # Automated MySQL database setup & seed script
├── README.md                  # Comprehensive technical documentation & viva guide
├── .env                       # Local environment variables
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules for venv, cache, and env files
│
├── database/
│   ├── db.py                  # PyMySQL connection management, DictCursor, and parameterized query helpers
│   └── schema.sql             # Complete DDL statements, relational foreign keys, indexes, and seed data
│
├── routes/
│   ├── __init__.py            # Routes package marker
│   ├── auth.py                # Authentication blueprint (Login, Customer Registration, Logout)
│   ├── admin.py               # Admin blueprint (Dashboard, Customers, Vehicles, Services, Bookings, Billing, Reports, Settings)
│   ├── customer.py            # Customer blueprint (Dashboard, Vehicle CRUD, Booking, History, Invoices)
│   └── mechanic.py            # Mechanic blueprint (Bay Dashboard, Workload Queue, Status & Remarks updater)
│
├── utils/
│   ├── __init__.py            # Utils package marker
│   ├── auth.py                # RBAC decorators (@login_required, @admin_required, @customer_required, @mechanic_required)
│   └── helpers.py             # Number generators (BK-XXXX, INV-XXXX), currency formatters, date helpers, audit logger
│
├── static/
│   ├── css/
│   │   └── style.css          # Responsive SaaS dashboard styling, badges, timeline, and @media print rules
│   └── js/
│       └── app.js             # Dynamic itemized bill calculator, table row management, alert dismissals
│
└── templates/
    ├── base.html              # Master layout with responsive dark sidebar, top navbar, user avatar, and flash alerts
    ├── auth/
    │   ├── login.html         # Premium split-screen login page with feature showcase and quick demo credentials
    │   └── register.html      # Customer self-registration form with client/server validation
    ├── admin/
    │   ├── dashboard.html     # Operations command center with 8 KPI cards, pipeline pills, and recent bookings
    │   ├── customers.html     # Customer management directory with search, filter, and registration modal
    │   ├── customer_detail.html # Comprehensive customer profile, vehicle garage, bookings, and billing history
    │   ├── vehicles.html      # Workshop vehicle fleet inventory with search and CRUD modals
    │   ├── services.html      # Service catalog management (standard rates, duration, status)
    │   ├── mechanics.html     # Technician roster, specialization tracking, and live workload
    │   ├── bookings.html      # Bookings master ledger with status and technician filters
    │   ├── booking_detail.html# Booking management (Approve, Assign Mechanic, Update Status, Reschedule)
    │   ├── history.html       # Master workshop-wide service history ledger
    │   ├── bills.html         # Billing and invoice registry with payment settlement modals
    │   ├── generate_bill.html # Dynamic itemized bill generator with live calculation of parts, labor, discount, and tax
    │   ├── invoice.html       # Official printable tax invoice with company details, GSTIN, and signatures
    │   ├── reports.html       # Multi-criteria analytics with technician throughput and service popularity tables
    │   └── settings.html      # Workshop profile, contact info, GSTIN, tax rate, and currency configuration
    ├── customer/
    │   ├── dashboard.html     # Customer dashboard with vehicle cards, key metrics, and quick actions
    │   ├── vehicles.html      # Customer garage with Add/Edit/Delete vehicle modals
    │   ├── book_service.html  # Interactive service booking form with appointment slot picker
    │   ├── bookings.html      # Customer bookings list with status filters
    │   ├── booking_detail.html# Booking tracking screen with live audit timeline of service updates
    │   ├── history.html       # Vehicle service history log
    │   ├── bills.html         # Invoices ledger for customer bookings
    │   └── invoice.html       # Customer printable invoice document
    ├── mechanic/
    │   ├── dashboard.html     # Technician bay dashboard with workload metrics and assigned service queue
    │   ├── services.html      # Assigned services list with status filter
    │   └── service_detail.html# Bay execution interface with progress dropdown, technical remarks, and work log
    └── errors/
        ├── 403.html           # Professional 403 Access Denied page
        ├── 404.html           # Clean 404 Page Not Found error page
        ├── 500.html           # 500 Internal Server Error page
        └── db_error.html      # Clear MySQL connection guidance & setup diagnostics
```

---

## 🗄️ Database Architecture & Relational Schema

Database Name: `vehicle_service_management`

### Tables & Relationships
1. **`users`**: Core user authentication table storing `id`, `name`, `email` (UNIQUE), `password_hash`, `phone`, `role` (`admin`, `customer`, `mechanic`), `status` (`active`, `inactive`), and `created_at`.
2. **`customers`**: Customer profiles linked via `user_id` &rarr; `users(id)` ON DELETE CASCADE, storing address and registration timestamp.
3. **`mechanics`**: Staff profiles linked via `user_id` &rarr; `users(id)` ON DELETE CASCADE, storing `specialization`, `experience` (years), `status` (`Available`, `Busy`, `Inactive`), and `joining_date`.
4. **`vehicles`**: Customer motor vehicles linked via `customer_id` &rarr; `customers(id)` ON DELETE CASCADE, storing `registration_number` (UNIQUE), `brand`, `model`, `vehicle_type` (`Car`, `Bike`, `Scooter`, `Other`), `manufacturing_year`, `fuel_type`, `color`, and `current_km`.
5. **`services`**: Standard service catalog storing `service_name`, `description`, `base_price`, `estimated_duration`, and `status` (`Active`, `Inactive`).
6. **`bookings`**: Service orders linking `customer_id`, `vehicle_id`, `service_id`, and `mechanic_id`, storing `booking_number` (UNIQUE), `preferred_date`, `preferred_time`, `complaint`, `notes`, `status`, and timestamps.
7. **`service_updates`**: Audit log / timeline storing `booking_id`, `status`, `remarks`, `updated_by` &rarr; `users(id)`, and `created_at`.
8. **`bills`**: Tax invoices linked via `booking_id` &rarr; `bookings(id)` (UNIQUE), storing `invoice_number` (UNIQUE), `service_charge`, `additional_charge`, `parts_charge`, `discount`, `tax`, `subtotal`, `grand_total`, `payment_status` (`Unpaid`, `Paid`, `Partial`), `payment_method`, and notes.
9. **`bill_items`**: Itemized spare parts and consumables linked via `bill_id` &rarr; `bills(id)` ON DELETE CASCADE, storing `item_name`, `description`, `quantity`, `unit_price`, and `total`.
10. **`settings`**: Key-value workshop configuration storing trade name, address, phone, email, GSTIN, default tax rate, and currency symbol.

---

## 🚀 Installation & Setup Instructions

### Step 1: Clone or Open Project Directory
```powershell
cd vehicle-service-management
```

### Step 2: Create and Activate Virtual Environment
```powershell
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure MySQL Connection
Copy `.env.example` to `.env` (or edit existing `.env`):
```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=vsm-super-secret-key-college-project-2026

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_root_password
DB_NAME=vehicle_service_management
```

### Step 5: Initialize Database & Seed Demo Data
You can initialize the database using either of the following two methods:

#### Method A: Automated Python Initializer (Recommended)
```powershell
python init_db.py
```
*This connects to your MySQL server, creates the database `vehicle_service_management`, builds all tables with relational constraints, and populates comprehensive demo records.*

#### Method B: MySQL Workbench
1. Open **MySQL Workbench**.
2. Connect to your local MySQL instance.
3. Open `database/schema.sql` via **File &rarr; Open SQL Script**.
4. Click the **Execute** lightning bolt icon (`Ctrl+Shift+Enter`).

### Step 6: Start the Application Server
```powershell
python app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🔄 Complete Step-by-Step Demonstration Workflow

Follow this exact end-to-end flow during your practical demonstration or project viva:

1. **Customer Login:**
   - Go to `http://127.0.0.1:5000/auth/login`.
   - Sign in as `amit.sharma@gmail.com` with password `customer123`.
2. **Register a Vehicle:**
   - Click **My Vehicles** on the sidebar &rarr; Click **Register New Vehicle**.
   - Enter `MH-12-PQ-9999`, Brand: `Volkswagen`, Model: `Polo GT`, Type: `Car`, Fuel: `Petrol`, Year: `2021`, Color: `Flash Red`, KM: `35000`.
   - Click **Add to Garage**. The vehicle is immediately saved to the database.
3. **Book a Service:**
   - Click **Book Service** on the sidebar.
   - Select your new vehicle, choose `Engine Oil & Filter Replacement` (Base: ₹ 1,200.00), pick tomorrow's date, time `11:00 AM`, and enter problem: *"Engine oil warning on dashboard"*.
   - Click **Confirm & Submit Booking**. A unique booking ID (e.g. `BK-2026-0008`) is generated with status `Pending`.
4. **Sign Out:** Click **Sign Out** from the customer profile.
5. **Admin Login:**
   - Sign in as `admin@autocare.com` with password `admin123`.
   - In the **Dashboard**, see your new booking in the **Recent Bookings** table.
6. **Approve Booking:**
   - Click **Review & Assign** on `BK-2026-0008`.
   - Click **Approve Booking**. The status updates to `Approved` and logs an audit update.
7. **Assign Mechanic:**
   - Click **Assign Mechanic**.
   - Select `Rajesh Kumar` (Engine & Transmission Specialist) &rarr; Click **Confirm Assignment**.
   - The booking status transitions to `Mechanic Assigned`.
8. **Sign Out:** Click **Sign Out** from the Admin top navbar.
9. **Mechanic Login:**
   - Sign in as `rajesh.kumar@autocare.com` with password `mechanic123`.
   - In the **Bay Dashboard**, see `BK-2026-0008` in your active queue.
10. **Vehicle Check-In:**
    - Click **Work on Job**.
    - Change status to `Vehicle Received`, enter remarks: *"Vehicle checked in at workshop gate. Odometer verified 35,000 km."* &rarr; Click **Save Service Update**.
11. **Perform Service:**
    - Change status to `In Service`, enter remarks: *"Hoisted on Ramp #2. Drained old 5W-30 oil. Replaced OEM oil filter cartridge."* &rarr; Click **Save Service Update**.
12. **Complete Service:**
    - Change status to `Completed`, enter remarks: *"Refilled synthetic oil, reset dashboard oil life counter, road test cleared."*, Work done summary: *"Oil flush and OEM filter installation"* &rarr; Click **Save Service Update**.
13. **Sign Out:** Click **Sign Out** from the mechanic bay.
14. **Admin Billing & Invoicing:**
    - Sign in as `admin@autocare.com` with password `admin123`.
    - Go to **Bookings** &rarr; Open `BK-2026-0008`.
    - Click **Generate Bill & Invoice**.
    - Notice that Base Service Charge (₹ 1,200.00) is prefilled.
    - Click **Add Part Row** to add:
      - Item Name: `Castrol Edge 5W-40 Synthetic Oil (4L)`, Qty: `1`, Unit Price: `₹ 2,400.00`
      - Item Name: `OEM VW Oil Filter Element`, Qty: `1`, Unit Price: `₹ 450.00`
    - Notice that Subtotal, 18% GST Tax, and Grand Total recalculate dynamically in real time on the screen!
    - Set Payment Status to `Paid` via `UPI` &rarr; Click **Generate & Save Tax Invoice**.
15. **Print Invoice:**
    - The official printable invoice `INV-2026-0003` is rendered.
    - Click **Print Invoice** to test print formatting or save as PDF.
16. **Customer Verification:**
    - Sign out and log back in as `amit.sharma@gmail.com`.
    - Go to **My Bookings** &rarr; Notice status is `Delivered` with linked invoice `INV-2026-0003`.
    - Go to **Service History** &rarr; The job is permanently archived with work details.
    - Go to **My Invoices** &rarr; View and print your official tax invoice.

---

## 🔒 Security & Best Practices

- **Zero Plaintext Passwords:** All user passwords are encrypted using Werkzeug's secure `scrypt` hashing algorithm.
- **SQL Injection Prevention:** All SQL interactions are strictly parameterized with `%s` placeholders via PyMySQL; zero dynamic SQL string concatenations.
- **Role Isolation:** HTTP endpoints are protected with `@login_required` and role-specific decorators (`@admin_required`, `@customer_required`, `@mechanic_required`).
- **Data Integrity:** Foreign keys enforce referential integrity with cascading deletes where appropriate and restrict rules on critical catalogs.
- **Input Validation:** Strict server-side verification for unique registration numbers, email syntax, phone lengths, and non-negative numeric prices.

---

## 🎓 Future Enhancements for Viva Discussion

When asked by evaluators how this system can be expanded in an industrial context:
1. **SMS / WhatsApp Notifications:** Integrating Twilio or WhatsApp Business API to dispatch automated vehicle ready alerts to customers.
2. **Payment Gateway Integration:** Adding Razorpay or Stripe for in-app credit card and UPI payments.
3. **Inventory Management Module:** Automatic stock level deduction when spare parts are added to an invoice.
4. **Customer Mobile Application:** Developing an Android/iOS companion app using Flutter interacting with Flask RESTful APIs.

---

**Developed for College Project & Academic Defense &bull; 2026**

-- =====================================================================
-- Vehicle Service Management and Billing System
-- Database Schema & Comprehensive Demo Seed Data
-- Target Database: MySQL 5.7+ / 8.0+ / MariaDB
-- =====================================================================

CREATE DATABASE IF NOT EXISTS vehicle_service_management
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE vehicle_service_management;

-- Disable foreign key checks for clean teardown/rebuild
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS bill_items;
DROP TABLE IF EXISTS bills;
DROP TABLE IF EXISTS service_updates;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS services;
DROP TABLE IF EXISTS vehicles;
DROP TABLE IF EXISTS mechanics;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS settings;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- Table: users (Core authentication for Admin, Customers, and Mechanics)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    role ENUM('admin', 'customer', 'mechanic') NOT NULL,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: customers (Profile details for customers)
-- ---------------------------------------------------------------------
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_customer_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: mechanics (Profile and specialization for mechanics)
-- ---------------------------------------------------------------------
CREATE TABLE mechanics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    specialization VARCHAR(150) NOT NULL,
    experience INT NOT NULL DEFAULT 1,
    status ENUM('Available', 'Busy', 'Inactive') DEFAULT 'Available',
    joining_date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_mechanic_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: vehicles (Registered customer vehicles)
-- ---------------------------------------------------------------------
CREATE TABLE vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    registration_number VARCHAR(30) NOT NULL UNIQUE,
    brand VARCHAR(60) NOT NULL,
    model VARCHAR(60) NOT NULL,
    vehicle_type ENUM('Car', 'Bike', 'Scooter', 'Other') NOT NULL,
    manufacturing_year INT NOT NULL,
    fuel_type ENUM('Petrol', 'Diesel', 'CNG', 'Electric', 'Hybrid') NOT NULL,
    color VARCHAR(40) NOT NULL,
    current_km INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_vehicle_reg (registration_number),
    INDEX idx_vehicle_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: services (Catalog of repair and maintenance services)
-- ---------------------------------------------------------------------
CREATE TABLE services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    description TEXT,
    base_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    estimated_duration VARCHAR(50) NOT NULL,
    status ENUM('Active', 'Inactive') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_service_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: bookings (Service booking requests and assignments)
-- ---------------------------------------------------------------------
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_number VARCHAR(30) NOT NULL UNIQUE,
    customer_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    service_id INT NOT NULL,
    mechanic_id INT NULL,
    preferred_date DATE NOT NULL,
    preferred_time VARCHAR(20) NOT NULL,
    complaint TEXT NOT NULL,
    notes TEXT,
    status ENUM(
        'Pending',
        'Approved',
        'Mechanic Assigned',
        'Vehicle Received',
        'In Service',
        'Waiting for Parts',
        'Completed',
        'Cancelled',
        'Delivered'
    ) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE RESTRICT,
    FOREIGN KEY (mechanic_id) REFERENCES mechanics(id) ON DELETE SET NULL,
    INDEX idx_booking_number (booking_number),
    INDEX idx_booking_status (status),
    INDEX idx_booking_date (preferred_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: service_updates (Audit trail / timeline of status updates)
-- ---------------------------------------------------------------------
CREATE TABLE service_updates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    remarks TEXT NOT NULL,
    updated_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_update_booking (booking_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: bills (Invoices generated for completed services)
-- ---------------------------------------------------------------------
CREATE TABLE bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(30) NOT NULL UNIQUE,
    booking_id INT NOT NULL UNIQUE,
    service_charge DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    additional_charge DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    parts_charge DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    discount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    tax DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    grand_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    payment_status ENUM('Unpaid', 'Paid', 'Partial') DEFAULT 'Unpaid',
    payment_method VARCHAR(50) DEFAULT 'Cash',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    INDEX idx_bill_invoice (invoice_number),
    INDEX idx_bill_payment_status (payment_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: bill_items (Itemized parts and labor for an invoice)
-- ---------------------------------------------------------------------
CREATE TABLE bill_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    item_name VARCHAR(150) NOT NULL,
    description VARCHAR(255),
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
    INDEX idx_item_bill (bill_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table: settings (Application and workshop configuration)
-- ---------------------------------------------------------------------
CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(50) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- SEED DATA
-- Default Passwords:
-- Admin:    admin123
-- Mechanic: mechanic123
-- Customer: customer123 (or password123)
-- (All hashed using Werkzeug scrypt format)
-- =====================================================================

-- Default Workshop Settings
INSERT INTO settings (setting_key, setting_value) VALUES
('workshop_name', 'AutoCare Pro Vehicle Workshop'),
('workshop_address', 'Plot 42, Ring Road Industrial Hub, Metro City - 400001'),
('workshop_phone', '+91 98765 43210'),
('workshop_email', 'service@autocarepro.com'),
('workshop_gstin', '27AABCA1234F1Z9'),
('default_tax_rate', '18.00'),
('currency_symbol', '₹');

-- 1 Admin, 2 Mechanics, 5 Customers
INSERT INTO users (id, name, email, password_hash, phone, role, status) VALUES
-- Admin (admin123)
(1, 'Workshop Administrator', 'admin@autocare.com', 'scrypt:32768:8:1$U7FAcCodod3QK3t2$c0d0424099d5f717867771ab774b470218ff60e95a29bd5e83b4af4fab13e45a9d08bcf31b4f60a0b8373d14232ab0c318a170f85da748f57ad5ed05629c5eef', '9822011223', 'admin', 'active'),
-- Mechanic 1 (mechanic123)
(2, 'Rajesh Kumar', 'rajesh.kumar@autocare.com', 'scrypt:32768:8:1$E4fKUB6fRPpZo9w3$7c4a50e2563b8af236b27cd25ca5b94cbb12a3d0d6f16c4d79d093bd3db4e7fd1a0472e102e31605d4879a24b1deed575457995e10dfe9da9e7b5e12964c2811', '9822022334', 'mechanic', 'active'),
-- Mechanic 2 (mechanic123)
(3, 'Vikram Singh', 'vikram.singh@autocare.com', 'scrypt:32768:8:1$E4fKUB6fRPpZo9w3$7c4a50e2563b8af236b27cd25ca5b94cbb12a3d0d6f16c4d79d093bd3db4e7fd1a0472e102e31605d4879a24b1deed575457995e10dfe9da9e7b5e12964c2811', '9822033445', 'mechanic', 'active'),
-- Customers (customer123)
(4, 'Amit Sharma', 'amit.sharma@gmail.com', 'scrypt:32768:8:1$WYrb59xN4n05NGYr$7bc0b8bcca15e6264053ba38a02f941087af8386f6add9030dcb3b77e7b5bcb47d7590db3aea49a89e9e1f09f92537ea9f4bb5310670c729ec5358ba308cd2f1', '9890111222', 'customer', 'active'),
(5, 'Priya Patel', 'priya.patel@gmail.com', 'scrypt:32768:8:1$WYrb59xN4n05NGYr$7bc0b8bcca15e6264053ba38a02f941087af8386f6add9030dcb3b77e7b5bcb47d7590db3aea49a89e9e1f09f92537ea9f4bb5310670c729ec5358ba308cd2f1', '9890222333', 'customer', 'active'),
(6, 'Rahul Verma', 'rahul.verma@gmail.com', 'scrypt:32768:8:1$WYrb59xN4n05NGYr$7bc0b8bcca15e6264053ba38a02f941087af8386f6add9030dcb3b77e7b5bcb47d7590db3aea49a89e9e1f09f92537ea9f4bb5310670c729ec5358ba308cd2f1', '9890333444', 'customer', 'active'),
(7, 'Sneha Deshmukh', 'sneha.deshmukh@gmail.com', 'scrypt:32768:8:1$WYrb59xN4n05NGYr$7bc0b8bcca15e6264053ba38a02f941087af8386f6add9030dcb3b77e7b5bcb47d7590db3aea49a89e9e1f09f92537ea9f4bb5310670c729ec5358ba308cd2f1', '9890444555', 'customer', 'active'),
(8, 'Arun Nair', 'arun.nair@gmail.com', 'scrypt:32768:8:1$WYrb59xN4n05NGYr$7bc0b8bcca15e6264053ba38a02f941087af8386f6add9030dcb3b77e7b5bcb47d7590db3aea49a89e9e1f09f92537ea9f4bb5310670c729ec5358ba308cd2f1', '9890555666', 'customer', 'active');

-- Mechanics details
INSERT INTO mechanics (id, user_id, specialization, experience, status, joining_date) VALUES
(1, 2, 'Engine Diagnostic & Transmission Overhaul', 7, 'Busy', '2022-03-15'),
(2, 3, 'Auto-Electrical, Hybrid Systems & AC Diagnostics', 5, 'Available', '2023-01-10');

-- Customers details
INSERT INTO customers (id, user_id, address) VALUES
(1, 4, 'Flat 302, Green Meadows, Senapati Bapat Road, Pune'),
(2, 5, 'Bungalow 14, Silver Crest Residency, Baner, Pune'),
(3, 6, 'Apt 101, Lakeview Heights, Viman Nagar, Pune'),
(4, 7, 'Row House 8, Orchid Villa, Kothrud, Pune'),
(5, 8, 'Flat 504, Horizon Towers, Hadapsar, Pune');

-- 7 Vehicles
INSERT INTO vehicles (id, customer_id, registration_number, brand, model, vehicle_type, manufacturing_year, fuel_type, color, current_km) VALUES
(1, 1, 'MH-12-AB-1234', 'Honda', 'City i-VTEC', 'Car', 2020, 'Petrol', 'Platinum White', 42500),
(2, 1, 'MH-12-CD-5678', 'Royal Enfield', 'Classic 350', 'Bike', 2021, 'Petrol', 'Stealth Black', 18300),
(3, 2, 'MH-14-EF-9012', 'Hyundai', 'Creta 1.5 SX', 'Car', 2022, 'Diesel', 'Polar White', 31200),
(4, 3, 'MH-02-GH-3456', 'Tata', 'Nexon EV Empowered', 'Car', 2023, 'Electric', 'Daytona Grey', 24100),
(5, 4, 'MH-12-JK-7890', 'TVS', 'Jupiter 125', 'Scooter', 2022, 'Petrol', 'Titanium Grey', 12400),
(6, 4, 'MH-12-LM-2345', 'Maruti Suzuki', 'Swift ZXi', 'Car', 2019, 'CNG', 'Fire Red', 58000),
(7, 5, 'MH-14-NP-6789', 'Toyota', 'Innova Crysta 2.4Z', 'Car', 2021, 'Diesel', 'Silver Metallic', 65000);

-- 10 Services Catalog
INSERT INTO services (id, service_name, description, base_price, estimated_duration, status) VALUES
(1, 'General Periodic Service', 'Complete 50-point inspection, engine oil check, fluid top-up, spark plugs inspection, air filter cleaning, and full wash.', 2500.00, '3 - 4 Hours', 'Active'),
(2, 'Engine Oil & Filter Replacement', 'Drain old engine oil, install genuine OEM oil filter, refill synthetic/semi-synthetic engine oil, reset service light.', 1200.00, '1 Hour', 'Active'),
(3, 'Brake Inspection & Pad Service', 'Inspection of front & rear brake discs, calipers, brake fluid moisture check, brake pad cleaning or replacement.', 1500.00, '2 Hours', 'Active'),
(4, 'Air Conditioning (AC) Servicing', 'AC cabin filter replacement, condenser cleaning, refrigerant/gas pressure check & top-up, compressor inspection.', 2200.00, '2 - 3 Hours', 'Active'),
(5, 'Computerized Wheel Alignment & Balancing', '4-wheel laser alignment, high-speed dynamic wheel balancing, tyre rotation and tread depth analysis.', 800.00, '1 Hour', 'Active'),
(6, 'Full Vehicle Diagnostic & Scanning', 'Complete OBD-II computer scanner diagnosis, error code readout, sensor check, battery and alternator health report.', 1000.00, '1.5 Hours', 'Active'),
(7, 'Battery Health Test & Replacement', 'Battery voltage & load test, terminal cleaning, anti-corrosion spray, battery replacement with warranty recording.', 500.00, '45 Mins', 'Active'),
(8, 'Clutch & Transmission Overhaul', 'Clutch plate wear analysis, pressure plate replacement, release bearing lubrication, and transmission fluid replacement.', 4500.00, '5 - 6 Hours', 'Active'),
(9, 'Suspension & Shock Absorber Tuning', 'Inspection of front struts, lower arms, stabilizer links, bush condition, and rear shock absorber dampening.', 2800.00, '3 - 4 Hours', 'Active'),
(10, 'Exterior Detailing & Ceramic Polish', 'High-pressure foam wash, paint decontamination, dual-action machine polishing, and hydrophobic ceramic sealant.', 3200.00, '4 - 5 Hours', 'Active');

-- 7 Bookings covering diverse real-world workflow statuses
INSERT INTO bookings (id, booking_number, customer_id, vehicle_id, service_id, mechanic_id, preferred_date, preferred_time, complaint, notes, status, created_at) VALUES
-- 1. Pending (New customer booking awaiting Admin approval)
(1, 'BK-2026-0001', 1, 1, 1, NULL, DATE_ADD(CURRENT_DATE, INTERVAL 2 DAY), '10:00 AM', 'Engine makes slight rattling noise on cold start. Scheduled 40,000 km general service.', 'Please inspect front brake feel as well.', 'Pending', DATE_SUB(NOW(), INTERVAL 2 HOUR)),

-- 2. Approved (Admin approved, awaiting mechanic assignment)
(2, 'BK-2026-0002', 2, 3, 4, NULL, DATE_ADD(CURRENT_DATE, INTERVAL 1 DAY), '11:30 AM', 'AC cooling is insufficient in afternoon traffic. Mild whistling sound from dashboard vents.', 'Customer requests early afternoon delivery if possible.', 'Approved', DATE_SUB(NOW(), INTERVAL 5 HOUR)),

-- 3. Mechanic Assigned (Mechanic assigned, vehicle not yet received at workshop)
(3, 'BK-2026-0003', 3, 4, 6, 2, CURRENT_DATE, '09:30 AM', 'Dashboard warning light blinking occasionally. High voltage regenerative braking diagnostic needed.', 'Electric vehicle safety precautions apply.', 'Mechanic Assigned', DATE_SUB(NOW(), INTERVAL 1 DAY)),

-- 4. In Service (Vehicle received, mechanic currently working on it)
(4, 'BK-2026-0004', 4, 6, 3, 1, CURRENT_DATE, '10:00 AM', 'Front right brake squeals when pressing brake pedal firmly. Also vibration felt on steering at 60 km/h.', 'Inspect front rotors and pad wear.', 'In Service', DATE_SUB(NOW(), INTERVAL 2 DAY)),

-- 5. Waiting for Parts (Mechanic requested OEM parts)
(5, 'BK-2026-0005', 5, 7, 8, 1, DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY), '02:00 PM', 'Clutch pedal feels spongy and gear shift from 1st to 2nd is hard.', 'Waiting for genuine clutch release bearing delivery.', 'Waiting for Parts', DATE_SUB(NOW(), INTERVAL 3 DAY)),

-- 6. Completed (Mechanic finished, ready for billing)
(6, 'BK-2026-0006', 4, 5, 2, 2, DATE_SUB(CURRENT_DATE, INTERVAL 2 DAY), '03:30 PM', 'Periodic oil change and general checkup. Scooter starting trouble after rain.', 'Cleaned spark plug and adjusted carburetor idle.', 'Completed', DATE_SUB(NOW(), INTERVAL 3 DAY)),

-- 7. Delivered (Work done, bill paid, vehicle returned to customer)
(7, 'BK-2026-0007', 1, 2, 5, 2, DATE_SUB(CURRENT_DATE, INTERVAL 5 DAY), '11:00 AM', 'Handle vibration at high speeds, wheel alignment and balancing requested.', 'Replaced left handlebar weight and balanced both wheels.', 'Delivered', DATE_SUB(NOW(), INTERVAL 6 DAY));

-- Service Updates (Lifecycle audit trail)
INSERT INTO service_updates (booking_id, status, remarks, updated_by, created_at) VALUES
-- Updates for Booking 1 (Pending)
(1, 'Pending', 'Customer submitted online booking request for General Periodic Service.', 4, DATE_SUB(NOW(), INTERVAL 2 HOUR)),

-- Updates for Booking 2 (Approved)
(2, 'Pending', 'Booking request placed by Priya Patel.', 5, DATE_SUB(NOW(), INTERVAL 6 HOUR)),
(2, 'Approved', 'Appointment slot verified and confirmed by Admin.', 1, DATE_SUB(NOW(), INTERVAL 5 HOUR)),

-- Updates for Booking 3 (Mechanic Assigned)
(3, 'Pending', 'Service request booked by Rahul Verma for Tata Nexon EV.', 6, DATE_SUB(NOW(), INTERVAL 26 HOUR)),
(3, 'Approved', 'Booking accepted by Admin.', 1, DATE_SUB(NOW(), INTERVAL 25 HOUR)),
(3, 'Mechanic Assigned', 'Assigned to Senior Auto-Electrical Specialist Vikram Singh.', 1, DATE_SUB(NOW(), INTERVAL 24 HOUR)),

-- Updates for Booking 4 (In Service)
(4, 'Pending', 'Booking created for Maruti Swift brake inspection.', 7, DATE_SUB(NOW(), INTERVAL 50 HOUR)),
(4, 'Approved', 'Booking approved for scheduled bay.', 1, DATE_SUB(NOW(), INTERVAL 48 HOUR)),
(4, 'Mechanic Assigned', 'Assigned to Mechanic Rajesh Kumar.', 1, DATE_SUB(NOW(), INTERVAL 47 HOUR)),
(4, 'Vehicle Received', 'Vehicle received at workshop gate. Odometer: 58,000 km. Inventory check completed.', 2, DATE_SUB(NOW(), INTERVAL 20 HOUR)),
(4, 'In Service', 'Vehicle hoisted on hydraulic ramp. Front caliper pistons inspected. Brake pads found worn to 2mm.', 2, DATE_SUB(NOW(), INTERVAL 4 HOUR)),

-- Updates for Booking 5 (Waiting for Parts)
(5, 'Pending', 'Booking created for Toyota Innova clutch overhaul.', 8, DATE_SUB(NOW(), INTERVAL 74 HOUR)),
(5, 'Approved', 'Approved by workshop supervisor.', 1, DATE_SUB(NOW(), INTERVAL 72 HOUR)),
(5, 'Mechanic Assigned', 'Assigned to Transmission Specialist Rajesh Kumar.', 1, DATE_SUB(NOW(), INTERVAL 71 HOUR)),
(5, 'Vehicle Received', 'Vehicle checked in. Odometer 65,000 km.', 2, DATE_SUB(NOW(), INTERVAL 48 HOUR)),
(5, 'In Service', 'Gearbox dismounted. Clutch pressure plate found heat scored.', 2, DATE_SUB(NOW(), INTERVAL 30 HOUR)),
(5, 'Waiting for Parts', 'OEM Toyota clutch kit ordered. Awaiting delivery from central distributor.', 2, DATE_SUB(NOW(), INTERVAL 12 HOUR)),

-- Updates for Booking 6 (Completed)
(6, 'Pending', 'Booking placed for TVS Jupiter service.', 7, DATE_SUB(NOW(), INTERVAL 80 HOUR)),
(6, 'Approved', 'Approved by admin.', 1, DATE_SUB(NOW(), INTERVAL 78 HOUR)),
(6, 'Mechanic Assigned', 'Assigned to Vikram Singh.', 1, DATE_SUB(NOW(), INTERVAL 75 HOUR)),
(6, 'Vehicle Received', 'Scooter handed over by customer.', 3, DATE_SUB(NOW(), INTERVAL 60 HOUR)),
(6, 'In Service', 'Engine oil flushed. Synthetic 10W-30 filled. Spark plug and air filter replaced.', 3, DATE_SUB(NOW(), INTERVAL 40 HOUR)),
(6, 'Completed', 'All service points cleared. Road test conducted successfully. Ready for billing.', 3, DATE_SUB(NOW(), INTERVAL 10 HOUR)),

-- Updates for Booking 7 (Delivered)
(7, 'Pending', 'Booking initiated for Royal Enfield Classic 350.', 4, DATE_SUB(NOW(), INTERVAL 140 HOUR)),
(7, 'Approved', 'Slot approved.', 1, DATE_SUB(NOW(), INTERVAL 135 HOUR)),
(7, 'Mechanic Assigned', 'Assigned to Vikram Singh.', 1, DATE_SUB(NOW(), INTERVAL 130 HOUR)),
(7, 'Vehicle Received', 'Motorcycle received at service reception.', 3, DATE_SUB(NOW(), INTERVAL 120 HOUR)),
(7, 'In Service', 'Front and rear wheel rim runout measured and corrected. Alignment tuned.', 3, DATE_SUB(NOW(), INTERVAL 110 HOUR)),
(7, 'Completed', 'Service finalized, wash completed.', 3, DATE_SUB(NOW(), INTERVAL 100 HOUR)),
(7, 'Delivered', 'Invoice generated and paid in full. Key handed back to Amit Sharma.', 1, DATE_SUB(NOW(), INTERVAL 90 HOUR));

-- Bills / Invoices for Bookings 6 and 7
-- Formula:
-- Subtotal = Service Charge + Additional Charge + Parts Charge
-- Grand Total = Subtotal - Discount + Tax (18% of Subtotal)

-- Bill 1: Booking 6 (Status: Completed, Unpaid)
-- Service: 1200, Additional: 150, Parts: 450 => Subtotal: 1800, Discount: 100 => 1700 + Tax 18% (306) = 2006.00
INSERT INTO bills (id, invoice_number, booking_id, service_charge, additional_charge, parts_charge, discount, tax, subtotal, grand_total, payment_status, payment_method, notes, created_at) VALUES
(1, 'INV-2026-0001', 6, 1200.00, 150.00, 450.00, 100.00, 306.00, 1800.00, 2006.00, 'Unpaid', 'Cash', 'General tune-up and filter replacement invoice.', DATE_SUB(NOW(), INTERVAL 8 HOUR));

INSERT INTO bill_items (bill_id, item_name, description, quantity, unit_price, total) VALUES
(1, 'Castrol Activ 4T 10W-30 (800ml)', 'Genuine OEM 4-Stroke Scooter Engine Oil', 1, 350.00, 350.00),
(1, 'OEM Air Filter Element', 'Replacement paper filter element for TVS Jupiter', 1, 100.00, 100.00),
(1, 'Labor: Oil Flush & General Tuning', 'Standard labor and safety inspection charge', 1, 1200.00, 1200.00),
(1, 'Spark Plug Cleaning & Gap Setting', 'Additional labor for ignition check', 1, 150.00, 150.00);

-- Bill 2: Booking 7 (Status: Delivered, Paid)
-- Service: 800, Additional: 200, Parts: 350 => Subtotal: 1350, Discount: 50 => 1300 + Tax 18% (234) = 1534.00
INSERT INTO bills (id, invoice_number, booking_id, service_charge, additional_charge, parts_charge, discount, tax, subtotal, grand_total, payment_status, payment_method, notes, created_at) VALUES
(2, 'INV-2026-0002', 7, 800.00, 200.00, 350.00, 50.00, 234.00, 1350.00, 1534.00, 'Paid', 'UPI', 'Wheel alignment and balancing completed. Paid via Google Pay.', DATE_SUB(NOW(), INTERVAL 90 HOUR));

INSERT INTO bill_items (bill_id, item_name, description, quantity, unit_price, total) VALUES
(2, 'Wheel Balancing Weights (Zinc Coated)', 'Adhesive lead-free counterweights (60g)', 1, 200.00, 200.00),
(2, 'Handlebar Damper Washer Kit', 'Vibration dampening rubber washers', 1, 150.00, 150.00),
(2, 'Computerized Laser Wheel Alignment Labor', '4-wheel sensor alignment & camber tuning', 1, 800.00, 800.00),
(2, 'Dynamic High-Speed Wheel Balancing Labor', 'Spin balancing front & rear wheels', 1, 200.00, 200.00);

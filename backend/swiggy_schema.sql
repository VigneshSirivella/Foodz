-- =========================================================
-- SWIGGY FOOD DELIVERY APP - POSTGRESQL DATABASE SCHEMA
-- Compatible with pgAdmin4 Query Tool
-- Database: foodz_db / postgres
-- =========================================================

-- Drop existing tables if they exist (Clean Setup)
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS menu_items CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS restaurants CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. USERS TABLE
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. RESTAURANTS TABLE
CREATE TABLE restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    cuisine VARCHAR(150) NOT NULL,
    rating NUMERIC(2,1) DEFAULT 4.2,
    delivery_time VARCHAR(50) DEFAULT '25-30 mins',
    cost_for_two INTEGER DEFAULT 300,
    image_url VARCHAR(255),
    is_featured BOOLEAN DEFAULT FALSE,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. CATEGORIES TABLE
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    icon VARCHAR(50),
    image_url VARCHAR(255)
);

-- 4. MENU ITEMS TABLE
CREATE TABLE menu_items (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL,
    image_url VARCHAR(255),
    is_veg BOOLEAN DEFAULT FALSE,
    is_bestseller BOOLEAN DEFAULT FALSE,
    rating NUMERIC(2,1) DEFAULT 4.5
);

-- 5. ORDERS TABLE
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(150) NOT NULL,
    restaurant_name VARCHAR(150) DEFAULT 'Foodz Central',
    delivery_address TEXT DEFAULT 'Main Street, Kadapa, AP',
    cart_items TEXT NOT NULL,
    subtotal NUMERIC(10,2) NOT NULL,
    tax NUMERIC(10,2) DEFAULT 0.00,
    delivery_fee NUMERIC(10,2) DEFAULT 30.00,
    total_price NUMERIC(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'Placed', -- 'Placed', 'Preparing', 'Out for Delivery', 'Delivered', 'Cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. REVIEWS TABLE
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(150) NOT NULL,
    restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. COMPLAINTS TABLE
CREATE TABLE complaints (
    id SERIAL PRIMARY KEY,
    complaint_id VARCHAR(50) UNIQUE NOT NULL,
    user_email VARCHAR(150) NOT NULL,
    order_id VARCHAR(50),
    category VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'Submitted',
    admin_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_menu_items_restaurant ON menu_items(restaurant_id);
CREATE INDEX idx_orders_user ON orders(user_email);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_complaints_user ON complaints(user_email);

SELECT 'Database Schema Created Successfully!' AS status;

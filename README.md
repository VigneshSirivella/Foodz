# 🛵 Swiggy Food Delivery Application & PostgreSQL (pgAdmin4) Integration

Welcome to the **Next-Level Swiggy Food Delivery Application**! This project is organized into two separate folders: **`frontend/`** and **`backend/`**.

---

## 📂 Project Architecture

```
Foodz/
│
├── 🎨 frontend/                # Frontend Web Application (Swiggy UI & Admin Portal)
│   ├── index.html              # Main Swiggy Food Delivery App & Live Tracking
│   ├── admin.html              # Swiggy Admin Management Dashboard
│   └── images/                 # Dish & Food Media Assets
│       ├── dum_biryani.jpeg
│       ├── dosa.jpeg
│       ├── pizza.jpg
│       ├── chicken_burger.jpg
│       └── ...
│
├── ⚙️ backend/                 # Backend REST API Server & PostgreSQL Connectivity
│   ├── server.py               # REST API HTTP Server (Supports PostgreSQL & SQLite)
│   ├── init_db.py              # Python Database Initialization & Auto-Seeder
│   ├── db_config.json          # PostgreSQL Connection Settings
│   ├── swiggy_schema.sql       # PostgreSQL DDL Table Creation Script for pgAdmin4
│   ├── swiggy_seed.sql         # PostgreSQL Seed Dataset for pgAdmin4
│   └── database.sqlite         # SQLite Fallback Database File
│
└── README.md                   # Project Documentation & Setup Guide
```

---

## 🚀 How to Run the Application

1. Open your terminal in the `backend/` directory:
   ```bash
   cd backend
   python3 server.py
   ```

2. Open your web browser:
   - **User App**: [http://localhost:3000/](http://localhost:3000/)
   - **Admin Dashboard**: [http://localhost:3000/admin.html](http://localhost:3000/admin.html)

---

## 🐘 Connecting PostgreSQL & Viewing Tables in pgAdmin4

### 1️⃣ Database Configuration (`backend/db_config.json`)
Modify `backend/db_config.json` with your local PostgreSQL credentials:
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "foodz_db",
  "user": "postgres",
  "password": "your_pgadmin_password"
}
```

### 2️⃣ Viewing Database Tables in pgAdmin4

1. Launch **pgAdmin4**.
2. Right-click **Servers** ➔ **Register** ➔ **Server...**
3. In the **Connection** tab, enter:
   - **Host**: `localhost`
   - **Port**: `5432`
   - **Database**: `postgres` (or `foodz_db`)
   - **Username**: `postgres`
   - **Password**: Enter your pgAdmin4 password.
4. Right-click `foodz_db` ➔ **Query Tool**.
5. Open and execute:
   - [`backend/swiggy_schema.sql`](file:///home/rgukt/Desktop/Foodz/backend/swiggy_schema.sql)
   - [`backend/swiggy_seed.sql`](file:///home/rgukt/Desktop/Foodz/backend/swiggy_seed.sql)
6. Expand `foodz_db` ➔ `Schemas` ➔ `public` ➔ `Tables` to view all 6 tables:
   - 👥 `users`
   - 🏪 `restaurants`
   - 🍕 `categories`
   - 🍲 `menu_items`
   - 📦 `orders`
   - ⭐ `reviews`

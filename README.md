# 🍔 Foodz – Online Food Ordering & Restaurant Management System

<p align="center">
  <strong>A Full-Stack Web Application for Online Food Ordering</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-HTML%20%7C%20CSS%20%7C%20JavaScript-orange" />
  <img src="https://img.shields.io/badge/Backend-Python-blue" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-336791" />
  <img src="https://img.shields.io/badge/Status-Deployment%20Ready-success" />
</p>

## 📌 Project Overview

**Foodz** is a full-stack online food ordering and restaurant management web application designed to make food ordering simple and convenient.

The application provides customers with an interface to explore food items, manage their cart, register or log in, and place food orders. It also provides an administrative dashboard to manage and monitor customer orders.

The project uses HTML, CSS, and JavaScript for the frontend, Python for backend processing, and PostgreSQL for database management.

## 🎯 Objectives

- Develop a user-friendly online food ordering platform.
- Provide secure user registration and authentication.
- Allow customers to browse food items and place orders.
- Maintain customer, menu, and order information in a database.
- Provide an admin dashboard for order management.
- Deploy the application using cloud hosting services.

## ✨ Features

### 👤 Customer Module

- User registration and login.
- Email OTP verification.
- Browse available food items.
- View food item details and prices.
- Add and manage items in the cart.
- Place food orders.
- Access customer-related information.

### 🛠️ Admin Module

- Administrative login.
- Admin dashboard.
- View and manage customer orders.
- Monitor order information.
- Manage restaurant operations through the dashboard.

### 🔐 Security Features

- Environment-based configuration for sensitive credentials.
- PostgreSQL connections with SSL support.
- CORS configuration for frontend-backend communication.
- Sensitive file access restrictions.
- Production database configuration separated from local development.

## 🧰 Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python |
| Database | PostgreSQL |
| Database Driver | psycopg2 |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |
| Database Hosting | Supabase |
| Version Control | Git, GitHub |

## 🏗️ System Architecture

```text
              CUSTOMER / ADMIN
                     |
                     v
             FRONTEND (VERCEL)
              HTML, CSS, JS
                     |
                     v
              PYTHON BACKEND
                  (RENDER)
                     |
                     v
             POSTGRESQL DATABASE
                 (SUPABASE)
```

The frontend communicates with the Python backend through API requests. The backend processes requests and interacts with the PostgreSQL database to store and retrieve application information.

## 📂 Project Structure

```text
Foodz/
│
├── frontend/
│   ├── index.html
│   ├── admin.html
│   ├── config.js
│   ├── vercel.json
│   └── images/
│
├── backend/
│   ├── server.py
│   ├── init_db.py
│   ├── requirements.txt
│   ├── swiggy_schema.sql
│   ├── swiggy_seed.sql
│   └── images/
│
├── images/
├── index.html
├── admin.html
├── server.py
├── init_db.py
├── config.js
├── requirements.txt
├── swiggy_schema.sql
├── swiggy_seed.sql
├── render.yaml
├── vercel.json
├── .env.example
├── .gitignore
├── DEPLOYMENT.md
└── README.md
```

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/VigneshSirivella/Foodz.git
cd Foodz
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file using `.env.example` as a reference.

Configure the required database and email settings.

**Important:** Never upload your actual `.env` file or credentials to GitHub.

### 4. Configure PostgreSQL Database

Create a PostgreSQL database and execute the SQL files in the following order:

1. `swiggy_schema.sql`
2. `swiggy_seed.sql`

The schema creates the required database tables, and the seed file inserts the initial application data.

### 5. Start the Backend Server

```bash
python server.py
```

Open the application using the local server address configured by the backend.

## ☁️ Cloud Deployment

Foodz is prepared for deployment using the following services:

| Service | Purpose |
|---|---|
| GitHub | Source code management |
| Vercel | Frontend hosting |
| Render | Python backend hosting |
| Supabase | PostgreSQL database hosting |

Detailed instructions are available in **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## 🖥️ Application Screenshots

Add actual screenshots of your application here.

Suggested screenshots:

- Customer home page
- Food menu page
- Shopping cart
- Login and registration pages
- Admin dashboard
- Order management page

Example:

```markdown
![Foodz Home Page](screenshots/home.png)
![Foodz Admin Dashboard](screenshots/admin.png)
```

## 🔮 Future Enhancements

- Online payment gateway integration.
- Live order tracking.
- Restaurant ratings and reviews.
- Improved order notifications.
- More advanced admin analytics.
- Mobile-responsive improvements.

## 👨‍💻 Project Information

| Detail | Information |
|---|---|
| Project Name | Foodz |
| Project Type | Full-Stack Web Application |
| Domain | Web Development |
| Frontend | HTML, CSS, JavaScript |
| Backend | Python |
| Database | PostgreSQL |

## 📜 License

This project is developed for academic and educational purposes.

---

<p align="center">
  <strong>Foodz – Making Food Ordering Simple and Convenient 🍔</strong>
</p>

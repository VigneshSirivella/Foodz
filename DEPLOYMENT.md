# Foodz Food Delivery Application — Cloud Deployment Guide

This guide provides end-to-end instructions for deploying the **Foodz** web application publicly using free-tier cloud hosting services:

- **Database**: [Supabase](https://supabase.com) (Free Managed PostgreSQL with SSL)
- **Backend API**: [Render](https://render.com) (Free Web Service, Python 3)
- **Frontend Client**: [Vercel](https://vercel.com) (Free Hobby Static Hosting)
- **Source Code**: [GitHub](https://github.com/VigneshSirivella/Foodz.git)

---

## 1. Architecture Overview

```mermaid
graph LR
    User([Browser Client]) -->|HTTPS| Vercel[Vercel Frontend\nHTML5, CSS3, JS, Images]
    Vercel -->|CORS / Edge Rewrites\n/api/*| Render[Render Python Backend\n0.0.0.0:$PORT]
    Render -->|PostgreSQL TLS/SSL\nsslmode=require| Supabase[(Supabase PostgreSQL\nDatabase)]
    Render -->|SMTP / HTTPS API| Mailer[Email Provider\nGmail SMTP / Resend]
```

---

## 2. Step 1: Database Setup on Supabase

1. Sign up or log in to [Supabase](https://supabase.com).
2. Click **New Project**:
   - **Name**: `foodz-database`
   - **Database Password**: Choose a strong password (save this securely).
   - **Region**: Choose the region closest to your users (e.g., `AWS - Singapore` or `AWS - Mumbai`).
3. Once the database is provisioned (1-2 minutes):
   - In the left sidebar, click **SQL Editor**.
   - Click **+ New query**.
   - Open [swiggy_schema.sql](swiggy_schema.sql) in your code editor, copy its entire contents, paste it into the Supabase SQL Editor, and click **RUN**.
   - Open a second query, copy the entire contents of [swiggy_seed.sql](swiggy_seed.sql), paste it, and click **RUN**.
4. Retrieve your Connection String:
   - In the left sidebar, click **Project Settings** (gear icon) ➔ **Database**.
   - Under **Connection String**, select the **URI** tab.
   - Choose **Mode: Session** (Port 5432) or **Transaction** (Port 6543).
   - The connection string looks like:
     ```text
     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
     ```
   - Replace `[YOUR-PASSWORD]` with your actual database password and ensure `sslmode=require` is present at the end.

---

## 3. Step 2: Push Source Code to GitHub

Commit and push the updated deployment files to your repository:

```bash
git add .
git commit -m "Prepare Foodz for public cloud deployment on Render, Supabase, and Vercel"
git push origin main
```

---

## 4. Step 3: Backend Deployment on Render

1. Sign up or log in to [Render](https://render.com).
2. In the Render Dashboard, click **New +** ➔ **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your GitHub repository: `VigneshSirivella/Foodz`.
4. Configure the service settings:
   - **Name**: `foodz-backend`
   - **Region**: Same or nearest region to your Supabase database.
   - **Branch**: `main`
   - **Root Directory**: Leave blank (root `.`)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
   - **Instance Type**: `Free`
5. In the **Environment Variables** section, add the following key-value pairs:

| Key | Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres...` | Your Supabase connection URI |
| `DB_SSLMODE` | `require` | Enforces SSL for Supabase |
| `ENV` | `production` | Enables production security checks |
| `PORT` | `10000` | Render default web port |
| `ALLOWED_ORIGINS` | `*` | Or your Vercel URL once deployed |
| `ALLOW_SQLITE_FALLBACK` | `false` | Prevents fallback to ephemeral SQLite |
| `SMTP_HOST` | `smtp.gmail.com` | Email SMTP host |
| `SMTP_PORT` | `587` | Email SMTP port (TLS) |
| `SMTP_EMAIL` | `your_email@gmail.com` | Gmail address for sending OTPs |
| `SMTP_PASSWORD` | `your_app_password` | 16-character Google App Password |

> **Alternative Email API (Resend)**:
> If cloud SMTP is blocked or rate-limited, create a free account on [Resend](https://resend.com) and add:
> - `RESEND_API_KEY`: `re_xxxxxxxxxxxx`
> - `EMAIL_FROM`: `Foodz <onboarding@resend.dev>`

6. Click **Deploy Web Service**.
7. Once deployed, Render will provide a public URL (e.g., `https://foodz-backend.onrender.com`).
8. Test the live backend:
   ```bash
   curl -i https://foodz-backend.onrender.com/api/db-status
   ```
   You should receive a `200 OK` JSON response indicating connected database stats!

---

## 5. Step 4: Frontend Deployment on Vercel

1. Sign up or log in to [Vercel](https://vercel.com).
2. Click **Add New...** ➔ **Project**.
3. Import your GitHub repository: `VigneshSirivella/Foodz`.
4. Configure the project:
   - **Project Name**: `foodz-app`
   - **Framework Preset**: `Other`
   - **Root Directory**: Click Edit and select `frontend` (or leave as root `.`)
   - **Build Command**: Leave blank (static)
   - **Output Directory**: Leave blank
5. Update your Render Backend URL:
   - In [config.js](config.js) / [frontend/config.js](frontend/config.js), change:
     ```javascript
     const DEFAULT_CLOUD_BACKEND = 'https://foodz-backend.onrender.com';
     ```
     to your actual Render service URL.
   - In [vercel.json](vercel.json) / [frontend/vercel.json](frontend/vercel.json), update the rewrite destination:
     ```json
     { "source": "/api/(.*)", "destination": "https://foodz-backend.onrender.com/api/$1" }
     ```
6. Click **Deploy**.
7. Vercel will build and assign your production URL (e.g., `https://foodz-app.vercel.app`).

---

## 6. Verification Checklist

- [ ] **Home Page Loads**: Open `https://foodz-app.vercel.app` in your browser. Verify categories, restaurants, and images load.
- [ ] **Admin Dashboard**: Open `https://foodz-app.vercel.app/admin` or `admin.html`. Verify statistics and orders display.
- [ ] **Customer Registration**: Sign up with a new real email. Verify non-existent domains are rejected.
- [ ] **OTP Delivery**: Receive 6-digit OTP code in your inbox.
- [ ] **OTP Verification**: Enter the code; verify account unlocks and updates `is_verified` in Supabase.
- [ ] **Food Ordering**: Add items to cart and place an order. Verify order shows up in the orders table.
- [ ] **Forgot Password**: Click "Forgot Password?", receive reset code, and update password.
- [ ] **Security Verification**: Accessing `/.env` or `/db_config.json` returns HTTP `403 Forbidden`.

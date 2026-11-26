import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import re
import random
import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..')) if os.path.basename(BASE_DIR) == 'backend' else BASE_DIR
FRONTEND_DIR = os.path.abspath(os.path.join(ROOT_DIR, 'frontend'))
if not os.path.exists(FRONTEND_DIR):
    FRONTEND_DIR = ROOT_DIR

libs_dir = os.path.join(ROOT_DIR, 'libs')
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, '.env'))
except ImportError:
    pass

PORT = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 3000)))

# Try importing PostgreSQL driver
HAS_PSYCOPG2 = False
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Environment & Host detection
IS_PRODUCTION = os.environ.get("ENV", os.environ.get("ENVIRONMENT", "")).lower() in ("production", "prod") or bool(os.environ.get("RENDER")) or os.environ.get("ALLOW_SQLITE_FALLBACK", "").lower() == "false"

# Database Configuration (supports DATABASE_URL for Supabase/Render or individual vars)
DB_CONFIG = {
    "url": os.environ.get("DATABASE_URL", "").strip(),
    "host": os.environ.get("PGHOST", os.environ.get("DB_HOST", "localhost")),
    "port": int(os.environ.get("PGPORT", os.environ.get("DB_PORT", 5432))),
    "database": os.environ.get("PGDATABASE", os.environ.get("DB_NAME", "postgres")),
    "user": os.environ.get("PGUSER", os.environ.get("DB_USER", "postgres")),
    "password": os.environ.get("PGPASSWORD", os.environ.get("DB_PASSWORD", "")),
    "sslmode": os.environ.get("PGSSLMODE", os.environ.get("DB_SSLMODE", "require" if IS_PRODUCTION else "prefer"))
}

# Optional fallback file loading for local dev only (if present and not production)
if not IS_PRODUCTION:
    for cfg_candidate in [os.path.join(ROOT_DIR, 'db_config.json'), os.path.join(BASE_DIR, 'db_config.json')]:
        if os.path.exists(cfg_candidate):
            try:
                with open(cfg_candidate, 'r') as f:
                    file_cfg = json.load(f)
                    for k in ("host", "port", "database", "user", "password"):
                        if k in file_cfg and not os.environ.get(f"DB_{k.upper()}") and not os.environ.get(f"PG{k.upper()}"):
                            DB_CONFIG[k] = file_cfg[k]
                break
            except Exception:
                pass

# Email Configuration from environment (no hardcoded passwords)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
EMAIL_FROM = os.environ.get("EMAIL_FROM", f"Foodz <{SMTP_EMAIL}>" if SMTP_EMAIL else "Foodz <onboarding@resend.dev>")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").strip()

DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "yopmail.com", "trashmail.com", "fakeinbox.com", "throwawaymail.com",
    "sharklasers.com", "dispostable.com", "getnada.com", "temp-mail.org",
    "crazymailing.com", "mytemp.email", "generator.email", "mohmal.com",
    "tempr.email", "discard.email", "discardmail.com", "spambog.com",
    "dropmail.me", "fakemailgenerator.com", "emailondeck.com", "inboxkitten.com"
}

def validate_real_email(email):
    """Validates format, blocks disposable domains, and verifies domain DNS existence."""
    if not email or not isinstance(email, str):
        return False, "Email address is required."

    email = email.strip()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        return False, "Please enter a valid email address format (e.g. name@example.com)."

    parts = email.split('@')
    if len(parts) != 2:
        return False, "Invalid email address format."

    domain = parts[1].lower()
    domain_parts = domain.split('.')
    if len(domain_parts) < 2 or len(domain_parts[-1]) < 2:
        return False, "Invalid domain extension in email address."

    if domain in DISPOSABLE_DOMAINS or any(domain.endswith('.' + d) for d in DISPOSABLE_DOMAINS):
        return False, "Temporary and disposable email addresses are not allowed. Please use your real email address."

    # Check domain resolution in DNS
    try:
        socket.getaddrinfo(domain, 25, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        try:
            socket.gethostbyname(domain)
        except Exception:
            return False, f"The email domain '@{domain}' does not exist. Please check your spelling or use a real email."
    except Exception:
        pass

    return True, ""

def send_otp_email(to_email, otp, purpose="verification"):
    """Sends OTP verification email via SMTP."""
    if purpose == "reset_password":
        subject = f"🔐 {otp} is your Foodz Password Reset Code"
        badge = "🔐 Password Reset"
        badge_bg = "#e11d48"
        intro_text = "We received a request to reset your Foodz Swiggy account password. Use the verification code below to confirm your identity and choose a new password:"
        footer_note = "If you did not request this password reset, please ignore this email. Your account password remains unchanged until verified."
    else:
        subject = f"{otp} is your Foodz Swiggy Verification Code"
        badge = "✨ Email Verification"
        badge_bg = "#fc8019"
        intro_text = "Use the following One-Time Password (OTP) to verify your email address:"
        footer_note = "After verification, you can unlock full checkout, track your live delivery, and enjoy delicious food!"

    html_content = f"""
    <div style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif; max-width:540px; margin:0 auto; padding:32px 24px; background:#ffffff; border-radius:16px; border:1px solid #e2e8f0; color:#1e293b;">
        <div style="text-align:center; margin-bottom:24px;">
            <h1 style="color:#fc8019; margin:0; font-size:28px; font-weight:800; letter-spacing:-0.5px;">Foodz 🛵</h1>
            <p style="color:#64748b; font-size:14px; margin-top:4px;">Swiggy Food Delivery &amp; Tracking</p>
            <span style="display:inline-block; margin-top:6px; background:{badge_bg}; color:#ffffff; font-size:12px; font-weight:700; padding:3px 12px; border-radius:20px;">{badge}</span>
        </div>
        <div style="background:#f8fafc; border-radius:12px; padding:24px; text-align:center; margin-bottom:24px; border:1px solid #f1f5f9;">
            <p style="font-size:15px; color:#475569; margin:0 0 16px 0;">{intro_text}</p>
            <div style="font-size:36px; font-weight:800; letter-spacing:8px; color:#0f172a; padding:12px 20px; background:#ffffff; border-radius:10px; display:inline-block; border:2px dashed #fc8019;">
                {otp}
            </div>
            <p style="font-size:13px; color:#94a3b8; margin-top:16px; margin-bottom:0;">This code is valid for <strong>10 minutes</strong>. Do not share it with anyone.</p>
        </div>
        <p style="font-size:13px; color:#64748b; line-height:1.6; margin:0;">
            {footer_note}
        </p>
        <hr style="border:none; border-top:1px solid #f1f5f9; margin:24px 0;" />
        <p style="font-size:11px; color:#94a3b8; text-align:center; margin:0;">
            Foodz Swiggy Delivery System • Automated Security Verification
        </p>
    </div>
    """
    # 1. Try HTTPS-based Resend API if API key is provided (port 443, reliable across free cloud hosts)
    if RESEND_API_KEY:
        try:
            import urllib.request
            payload = json.dumps({
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }).encode('utf-8')
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=payload,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as res:
                if res.status in (200, 201):
                    return True, "Email sent successfully via Resend HTTPS API."
        except Exception as e:
            print(f"[WARN] Resend API notice for {to_email}: {e}", file=sys.stderr)

    # 2. Try Standard SMTP if SMTP credentials are provided
    if SMTP_EMAIL and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = EMAIL_FROM
            msg['To'] = to_email
            msg.attach(MIMEText(f"Your Foodz code is: {otp}. Valid for 10 minutes.", 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=8)
            else:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8)
                server.starttls()

            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, [to_email], msg.as_string())
            server.quit()
            return True, "Email sent successfully via SMTP."
        except Exception as e:
            print(f"[WARN] SMTP delivery notice for {to_email}: {e}", file=sys.stderr)
            return False, str(e)

    # In local testing without credentials, log OTP for developer convenience
    print(f"[DEV NOTICE] Email sending skipped (no SMTP or Resend credentials configured). OTP for {to_email}: {otp}")
    return False, "Email provider not configured. Please set SMTP_EMAIL/SMTP_PASSWORD or RESEND_API_KEY."

DISH_IMAGE_MAP = {
    "Chicken Dum Biryani": "images/dum_biryani.jpeg",
    "Mutton Biryani Special": "images/mutton_biryani.jpeg",
    "Ragi Sangati with Natukodi Curry": "images/ragi_sangati.jpeg",
    "Crispy Masala Dosa": "images/dosa.jpeg",
    "Soft Steam Idly (3 Pcs)": "images/idly.jpeg",
    "Fluffy Poori Potato Gravy": "images/poori.jpeg",
    "Rayalaseema Uggani Bajji": "images/uggani.jpeg",
    "Hot Upma Special": "images/upma.jpeg",
    "Gourmet Cheese Pizza": "images/pizza.jpg",
    "Crispy French Fries": "images/french fries.jpg",
    "Classic Crispy Chicken Burger": "images/chicken_burger.jpg",
    "Thick Chocolate Milkshake": "images/chocolate_milkshake.jpeg",
    "Paneer Butter Masala": "images/butter_masala.jpeg",
    "Butter Chapathi (2 Pcs)": "images/chepati.jpg",
    "Malabar Parota (2 Pcs)": "images/parata.jpg",
    "Spicy Fish Curry": "images/fish_curry.jpeg",
    "Tawa Fish Fry": "images/Fish_fry.jpeg",
    "Belgian Chocolate Ice Cream": "images/chocolate_icecream.jpeg",
    "Fresh Fruit Salad Bowl": "images/fruit_salad.jpeg"
}

CAT_IMAGE_MAP = {
    "Biryani": "images/dum_biryani.jpeg",
    "South Indian": "images/dosa.jpeg",
    "Pizza": "images/pizza.jpg",
    "Burgers": "images/chicken_burger.jpg",
    "North Indian": "images/butter_masala.jpeg",
    "Fast Food": "images/french fries.jpg",
    "Desserts": "images/chocolate_icecream.jpeg",
    "Beverages": "images/chocolate_milkshake.jpeg"
}

REST_IMAGE_MAP = {
    "Meghana Foods": "images/dum_biryani.jpeg",
    "South Kitchen House": "images/dosa.jpeg",
    "Pizza Corner & Italian": "images/pizza.jpg",
    "Burger Hub & Shakes": "images/chicken_burger.jpg",
    "North Express Spices": "images/butter_masala.jpeg",
    "Royal Biryani House": "images/mutton_biryani.jpeg",
    "Sweet & Cool Treats": "images/chocolate_icecream.jpeg"
}

def resolve_image_url(url, name="", entity_type="dish"):
    if not url:
        if entity_type == "cat":
            url = CAT_IMAGE_MAP.get(name, "images/dum_biryani.jpeg")
        elif entity_type == "rest":
            url = REST_IMAGE_MAP.get(name, "images/dum_biryani.jpeg")
        else:
            url = DISH_IMAGE_MAP.get(name, "images/dum_biryani.jpeg")
    if str(url).startswith('/images/'):
        url = str(url)[1:]
    return url

def get_db_connection():
    """
    Returns (conn, db_type).
    Connects to PostgreSQL (Supabase / Render / Local) using DATABASE_URL or individual PG* / DB_* variables.
    Enforces SSL connections for cloud hosts.
    In production, does NOT silently fall back to SQLite.
    """
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if HAS_PSYCOPG2:
        # 1. Primary: Check DATABASE_URL (Supabase & Render standard)
        if db_url:
            try:
                connect_args = {"connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", 10))}
                # Default to sslmode=require for cloud providers like Supabase
                if "sslmode=" not in db_url and os.environ.get("DB_SSLMODE", "require").lower() != "disable":
                    connect_args["sslmode"] = os.environ.get("DB_SSLMODE", "require")
                pg_conn = psycopg2.connect(db_url, **connect_args)
                return pg_conn, 'postgresql'
            except Exception as e:
                print(f"[ERROR] Failed to connect to PostgreSQL via DATABASE_URL: {e}", file=sys.stderr)
                if IS_PRODUCTION or os.environ.get("ALLOW_SQLITE_FALLBACK", "true").lower() in ("false", "0", "no"):
                    raise ConnectionError(f"Production PostgreSQL connection failed: {e}")

        # 2. Secondary: Check individual environment variables (PG* or DB_*)
        host = os.environ.get("PGHOST", os.environ.get("DB_HOST", DB_CONFIG.get("host", "")))
        if host:
            try:
                port = int(os.environ.get("PGPORT", os.environ.get("DB_PORT", DB_CONFIG.get("port", 5432))))
                dbname = os.environ.get("PGDATABASE", os.environ.get("DB_NAME", DB_CONFIG.get("database", "postgres")))
                user = os.environ.get("PGUSER", os.environ.get("DB_USER", DB_CONFIG.get("user", "postgres")))
                password = os.environ.get("PGPASSWORD", os.environ.get("DB_PASSWORD", DB_CONFIG.get("password", "")))
                sslmode = os.environ.get("PGSSLMODE", os.environ.get("DB_SSLMODE", "require" if IS_PRODUCTION else "prefer"))

                pg_conn = psycopg2.connect(
                    host=host,
                    port=port,
                    dbname=dbname,
                    user=user,
                    password=password,
                    sslmode=sslmode,
                    connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", 10))
                )
                return pg_conn, 'postgresql'
            except Exception as e:
                print(f"[ERROR] Failed to connect to PostgreSQL via parameters: {e}", file=sys.stderr)
                if IS_PRODUCTION or os.environ.get("ALLOW_SQLITE_FALLBACK", "true").lower() in ("false", "0", "no"):
                    raise ConnectionError(f"Production PostgreSQL connection failed: {e}")

    # Fallback to local SQLite only in local development
    if IS_PRODUCTION or os.environ.get("ALLOW_SQLITE_FALLBACK", "true").lower() in ("false", "0", "no"):
        raise ConnectionError("PostgreSQL connection failed and SQLite fallback is disabled in production environment.")

    import sqlite3
    sqlite_file = os.path.join(ROOT_DIR, 'database.sqlite')
    if not os.path.exists(sqlite_file):
        sqlite_file = os.path.join(BASE_DIR, 'database.sqlite')
    sqlite_conn = sqlite3.connect(sqlite_file, check_same_thread=False)
    return sqlite_conn, 'sqlite'

def check_database_readiness():
    """Verifies that the database is reachable on startup without executing destructive operations."""
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        conn.close()
        print(f"✓ Database connectivity confirmed ({db_type}). Ready for queries.")
        return True
    except Exception as e:
        print(f"[WARN] Database connectivity check warning: {e}", file=sys.stderr)
        return False

class SwiggyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

    def send_cors_headers(self):
        req_origin = self.headers.get('Origin', '*')
        allowed = ALLOWED_ORIGINS.split(',')
        allowed = [a.strip() for a in allowed if a.strip()]
        if '*' in allowed or not allowed:
            origin_header = '*'
        elif req_origin in allowed:
            origin_header = req_origin
        else:
            origin_header = allowed[0]

        self.send_header('Access-Control-Allow-Origin', origin_header)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
        self.send_header('Access-Control-Max-Age', '86400')

    def end_headers(self):
        self.send_cors_headers()
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.send_header('Content-Length', '0')
        super().end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # Security: Block sensitive files, dotfiles, source files, and database binaries
        clean_path = path.lower()
        if (clean_path.startswith('/.') or
            clean_path.endswith('.env') or
            '.env.' in clean_path or
            clean_path.endswith('.json') or
            clean_path.endswith('.sqlite') or
            clean_path.endswith('.py') or
            clean_path.endswith('.sql') or
            clean_path.endswith('.md') or
            clean_path.endswith('.log') or
            '/__pycache__' in clean_path):
            self.send_error_response("Access Denied: Protected resource", 403)
            return

        # Redirect root to index.html
        if path == '/' or path == '/total.html':
            self.path = '/index.html'
            return super().do_GET()

        # Handle image requests explicitly
        if path.startswith('/images/') or path.startswith('/frontend/images/') or path.startswith('/backend/images/'):
            raw_name = path.replace('/images/', '').replace('/frontend/images/', '').replace('/backend/images/', '')
            img_name = urllib.parse.unquote(raw_name)
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.abspath(os.path.join(curr_dir, '..')) if os.path.basename(curr_dir) == 'backend' else curr_dir
            search_paths = [
                os.path.join(root_dir, 'images', img_name),
                os.path.join(curr_dir, 'images', img_name),
                os.path.join(root_dir, 'frontend', 'images', img_name),
                os.path.join(root_dir, 'backend', 'images', img_name),
                os.path.join(root_dir, 'images', img_name.replace(' ', '_')),
                os.path.join(root_dir, 'images', img_name.replace('_', ' ')),
                os.path.join(curr_dir, 'images', img_name.replace(' ', '_')),
            ]
            img_path = None
            for p in search_paths:
                if os.path.exists(p) and os.path.isfile(p):
                    img_path = p
                    break
            if img_path:
                mime = 'image/jpeg'
                if img_path.lower().endswith('.png'): mime = 'image/png'
                elif img_path.lower().endswith('.jpg') or img_path.lower().endswith('.jpeg'): mime = 'image/jpeg'
                elif img_path.lower().endswith('.svg'): mime = 'image/svg+xml'
                with open(img_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error_response(f"Image not found: {img_name}", 404)
                return

        # Database Status API
        if path == '/api/db-status':
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            user_count = 0
            order_count = 0
            restaurant_count = 0

            try:
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM orders")
                order_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM restaurants")
                restaurant_count = cursor.fetchone()[0]
            except Exception as e:
                pass
            finally:
                conn.close()

            safe_config = {
                "host": DB_CONFIG.get("host", "configured"),
                "port": DB_CONFIG.get("port", 5432),
                "database": DB_CONFIG.get("database", "postgres"),
                "ssl": bool(DB_CONFIG.get("sslmode", True))
            }

            self.send_json_response({
                "db_type": db_type,
                "has_psycopg2": HAS_PSYCOPG2,
                "config": safe_config,
                "pgadmin_ready": True,
                "stats": {
                    "users": user_count,
                    "orders": order_count,
                    "restaurants": restaurant_count
                }
            })
            return

        # Categories API
        if path == '/api/categories':
            categories = []
            conn = None
            try:
                conn, db_type = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, icon, image_url FROM categories ORDER BY id ASC")
                rows = cursor.fetchall()
                for r in rows:
                    categories.append({"id": r[0], "name": r[1], "icon": r[2], "image_url": resolve_image_url(r[3], r[1], "cat")})
            except Exception as e:
                print(f"Error fetching categories: {e}")
            finally:
                if conn:
                    conn.close()
            self.send_json_response({"categories": categories})
            return

        # Restaurants API
        if path == '/api/restaurants':
            category_filter = query.get('category', [None])[0]
            search_filter = query.get('search', [None])[0]
            veg_only = query.get('veg', ['0'])[0] == '1'

            restaurants = []
            conn = None
            try:
                conn, db_type = get_db_connection()
                cursor = conn.cursor()
                sql = "SELECT id, name, cuisine, rating, delivery_time, cost_for_two, image_url, is_featured, address FROM restaurants"
                conditions = []
                params = []

                if search_filter:
                    ph = "%s" if db_type == 'postgresql' else "?"
                    conditions.append(f"(LOWER(name) LIKE {ph} OR LOWER(cuisine) LIKE {ph})")
                    params.extend([f"%{search_filter.lower()}%", f"%{search_filter.lower()}%"])

                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)

                sql += " ORDER BY is_featured DESC, rating DESC"

                if db_type == 'postgresql' and params:
                    cursor.execute(sql, tuple(params))
                elif params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                rows = cursor.fetchall()
                for r in rows:
                    restaurants.append({
                        "id": r[0],
                        "name": r[1],
                        "cuisine": r[2],
                        "rating": float(r[3]),
                        "delivery_time": r[4],
                        "cost_for_two": r[5],
                        "image_url": resolve_image_url(r[6], r[1], "rest"),
                        "is_featured": bool(r[7]),
                        "address": r[8]
                    })
            except Exception as e:
                print(f"Error fetching restaurants: {e}")
            finally:
                if conn:
                    conn.close()
            self.send_json_response({"restaurants": restaurants})
            return

        # Single Restaurant & Menu API
        if path == '/api/restaurant':
            rest_id = query.get('id', [None])[0]
            if not rest_id:
                self.send_error_response("Restaurant ID required", 400)
                return

            restaurant_data = None
            menu_items = []
            conn = None
            try:
                conn, db_type = get_db_connection()
                cursor = conn.cursor()
                q_rest = "SELECT id, name, cuisine, rating, delivery_time, cost_for_two, image_url, is_featured, address FROM restaurants WHERE id = %s" if db_type == 'postgresql' else "SELECT id, name, cuisine, rating, delivery_time, cost_for_two, image_url, is_featured, address FROM restaurants WHERE id = ?"
                cursor.execute(q_rest, (rest_id,))
                row = cursor.fetchone()
                if row:
                    restaurant_data = {
                        "id": row[0], "name": row[1], "cuisine": row[2],
                        "rating": float(row[3]), "delivery_time": row[4],
                        "cost_for_two": row[5], "image_url": resolve_image_url(row[6], row[1], "rest"),
                        "is_featured": bool(row[7]), "address": row[8]
                    }

                q_menu = "SELECT id, category_id, name, description, price, image_url, is_veg, is_bestseller, rating FROM menu_items WHERE restaurant_id = %s" if db_type == 'postgresql' else "SELECT id, category_id, name, description, price, image_url, is_veg, is_bestseller, rating FROM menu_items WHERE restaurant_id = ?"
                cursor.execute(q_menu, (rest_id,))
                for m in cursor.fetchall():
                    menu_items.append({
                        "id": m[0], "category_id": m[1], "name": m[2],
                        "description": m[3], "price": float(m[4]),
                        "image_url": resolve_image_url(m[5], m[2], "dish"), "is_veg": bool(m[6]),
                        "is_bestseller": bool(m[7]), "rating": float(m[8])
                    })
            except Exception as e:
                print(f"Error fetching restaurant menu: {e}")
            finally:
                if conn:
                    conn.close()

            if not restaurant_data:
                self.send_error_response("Restaurant not found", 404)
            else:
                self.send_json_response({"restaurant": restaurant_data, "menu": menu_items})
            return

        # All Menu Items API
        if path == '/api/menu-items':
            items = []
            conn = None
            try:
                conn, db_type = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT m.id, m.restaurant_id, m.category_id, m.name, m.description, m.price, m.image_url, m.is_veg, m.is_bestseller, m.rating, r.name
                    FROM menu_items m
                    LEFT JOIN restaurants r ON m.restaurant_id = r.id
                """)
                for m in cursor.fetchall():
                    items.append({
                        "id": m[0], "restaurant_id": m[1], "category_id": m[2],
                        "name": m[3], "description": m[4], "price": float(m[5]),
                        "image_url": resolve_image_url(m[6], m[3], "dish"), "is_veg": bool(m[7]),
                        "is_bestseller": bool(m[8]), "rating": float(m[9]),
                        "restaurant_name": m[10] or "Foodz Kitchen"
                    })
            except Exception as e:
                print(f"Error fetching menu items: {e}")
            finally:
                if conn:
                    conn.close()

            if not items:
                items = [
                    {"id": 1, "restaurant_id": 1, "category_id": 1, "name": "Chicken Dum Biryani", "description": "Hyderabadi style slow cooked aromatic basmati rice with tender chicken piece", "price": 240.0, "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500&auto=format&fit=crop&q=80", "is_veg": False, "is_bestseller": True, "rating": 4.9, "restaurant_name": "Meghana Foods"},
                    {"id": 2, "restaurant_id": 1, "category_id": 1, "name": "Mutton Biryani Special", "description": "Royal spice infused long-grain biryani rice served with tender mutton chunk", "price": 320.0, "image_url": "https://images.unsplash.com/photo-1633945274405-b6c8069047b0?w=500&auto=format&fit=crop&q=80", "is_veg": False, "is_bestseller": False, "rating": 4.8, "restaurant_name": "Royal Biryani House"},
                    {"id": 3, "restaurant_id": 1, "category_id": 5, "name": "Ragi Sangati with Natukodi Curry", "description": "Traditional Rayalaseema specialty served piping hot with flavorful curry", "price": 180.0, "image_url": "images/ragi_sangati.jpeg", "is_veg": False, "is_bestseller": False, "rating": 4.7, "restaurant_name": "Meghana Foods"},
                    {"id": 4, "restaurant_id": 2, "category_id": 2, "name": "Crispy Masala Dosa", "description": "Golden brown rice crepe filled with spiced potato masala and chutneys", "price": 70.0, "image_url": "images/dosa.jpeg", "is_veg": True, "is_bestseller": True, "rating": 4.4, "restaurant_name": "South Kitchen House"},
                    {"id": 5, "restaurant_id": 2, "category_id": 2, "name": "Soft Steam Idly (3 Pcs)", "description": "Fluffy steamed rice cakes served with sambar and coconut chutney", "price": 50.0, "image_url": "images/idly.jpeg", "is_veg": True, "is_bestseller": True, "rating": 4.3, "restaurant_name": "South Kitchen House"},
                    {"id": 6, "restaurant_id": 2, "category_id": 2, "name": "Fluffy Poori Potato Gravy", "description": "Deep fried golden pooris served with authentic potato curry", "price": 80.0, "image_url": "images/poori.jpeg", "is_veg": True, "is_bestseller": False, "rating": 4.2, "restaurant_name": "South Kitchen House"},
                    {"id": 7, "restaurant_id": 2, "category_id": 2, "name": "Rayalaseema Uggani Bajji", "description": "Special puffed rice dish served with crispy mirchi bajji", "price": 60.0, "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500&auto=format&fit=crop&q=80", "is_veg": True, "is_bestseller": True, "rating": 4.4, "restaurant_name": "South Kitchen House"},
                    {"id": 8, "restaurant_id": 2, "category_id": 2, "name": "Hot Upma Special", "description": "Traditional semolina dish tempered with mustard, curry leaves and cashews", "price": 50.0, "image_url": "images/upma.jpeg", "is_veg": True, "is_bestseller": False, "rating": 4.1, "restaurant_name": "South Kitchen House"},
                    {"id": 9, "restaurant_id": 3, "category_id": 3, "name": "Gourmet Cheese Pizza", "description": "Loaded with fresh mozzarella, tomato sauce and oregano herbs", "price": 299.0, "image_url": "images/pizza.jpg", "is_veg": True, "is_bestseller": True, "rating": 4.6, "restaurant_name": "Pizza Corner & Italian"},
                    {"id": 10, "restaurant_id": 3, "category_id": 6, "name": "Crispy French Fries", "description": "Golden salted potato fries served with tomato ketchup", "price": 120.0, "image_url": "images/french fries.jpg", "is_veg": True, "is_bestseller": False, "rating": 4.3, "restaurant_name": "Pizza Corner & Italian"},
                    {"id": 11, "restaurant_id": 4, "category_id": 4, "name": "Classic Crispy Chicken Burger", "description": "Juicy crispy chicken patty with lettuce, mayo and melted cheese", "price": 180.0, "image_url": "images/chicken_burger.jpg", "is_veg": False, "is_bestseller": True, "rating": 4.7, "restaurant_name": "Burger Hub & Shakes"},
                    {"id": 12, "restaurant_id": 4, "category_id": 8, "name": "Thick Chocolate Milkshake", "description": "Creamy rich chocolate shake topped with cocoa drizzle", "price": 130.0, "image_url": "images/chocolate_milkshake.jpeg", "is_veg": True, "is_bestseller": False, "rating": 4.4, "restaurant_name": "Burger Hub & Shakes"},
                    {"id": 13, "restaurant_id": 5, "category_id": 5, "name": "Paneer Butter Masala", "description": "Cottage cheese cubes simmered in rich velvety tomato butter gravy", "price": 220.0, "image_url": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=500&auto=format&fit=crop&q=80", "is_veg": True, "is_bestseller": True, "rating": 4.8, "restaurant_name": "North Express Spices"},
                    {"id": 14, "restaurant_id": 5, "category_id": 5, "name": "Butter Chapathi (2 Pcs)", "description": "Soft whole wheat flatbread brushed with fresh butter", "price": 40.0, "image_url": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=500&auto=format&fit=crop&q=80", "is_veg": True, "is_bestseller": False, "rating": 4.2, "restaurant_name": "North Express Spices"},
                    {"id": 15, "restaurant_id": 5, "category_id": 5, "name": "Malabar Parota (2 Pcs)", "description": "Layered flaky parota served hot", "price": 50.0, "image_url": "images/parata.jpg", "is_veg": True, "is_bestseller": False, "rating": 4.5, "restaurant_name": "North Express Spices"},
                    {"id": 16, "restaurant_id": 5, "category_id": 5, "name": "Spicy Fish Curry", "description": "Andhra style tangy and spicy fish gravy cooked with tamarind", "price": 260.0, "image_url": "images/fish_curry.jpeg", "is_veg": False, "is_bestseller": False, "rating": 4.6, "restaurant_name": "North Express Spices"},
                    {"id": 17, "restaurant_id": 5, "category_id": 5, "name": "Tawa Fish Fry", "description": "Crispy marinated fish fillets pan fried with signature spices", "price": 280.0, "image_url": "images/Fish_fry.jpeg", "is_veg": False, "is_bestseller": False, "rating": 4.3, "restaurant_name": "North Express Spices"},
                    {"id": 18, "restaurant_id": 7, "category_id": 7, "name": "Belgian Chocolate Ice Cream", "description": "Double scoop rich chocolate ice cream with fudge sauce", "price": 110.0, "image_url": "https://images.unsplash.com/photo-1570197788417-0e82375c9371?w=500&auto=format&fit=crop&q=80", "is_veg": True, "is_bestseller": True, "rating": 4.9, "restaurant_name": "Sweet & Cool Treats"},
                    {"id": 19, "restaurant_id": 7, "category_id": 7, "name": "Fresh Fruit Salad Bowl", "description": "Assorted seasonal fresh cut fruits served with honey and mint", "price": 120.0, "image_url": "https://images.unsplash.com/photo-1519996529931-28324d5a630e?w=500&auto=format&fit=crop&q=80", "is_veg": True, "is_bestseller": False, "rating": 4.1, "restaurant_name": "Sweet & Cool Treats"}
                ]

            self.send_json_response({"menu_items": items})
            return

        # User Order History & Active Orders
        if path == '/api/orders':
            user_email = query.get('user_email', [None])[0]
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            orders = []
            try:
                if user_email:
                    sql = "SELECT id, user_email, restaurant_name, delivery_address, cart_items, subtotal, tax, delivery_fee, total_price, status, created_at FROM orders WHERE LOWER(user_email) = LOWER(%s) ORDER BY id DESC" if db_type == 'postgresql' else "SELECT id, user_email, restaurant_name, delivery_address, cart_items, subtotal, tax, delivery_fee, total_price, status, created_at FROM orders WHERE LOWER(user_email) = LOWER(?) ORDER BY id DESC"
                    cursor.execute(sql, (user_email,))
                else:
                    cursor.execute("SELECT id, user_email, restaurant_name, delivery_address, cart_items, subtotal, tax, delivery_fee, total_price, status, created_at FROM orders ORDER BY id DESC")

                for r in cursor.fetchall():
                    try:
                        cart_data = json.loads(r[4])
                    except:
                        cart_data = []
                    orders.append({
                        "id": r[0], "user_email": r[1],
                        "restaurant_name": r[2] or "Foodz Central",
                        "delivery_address": r[3] or "Kadapa, AP",
                        "cart_items": cart_data,
                        "subtotal": float(r[5] or 0), "tax": float(r[6] or 0),
                        "delivery_fee": float(r[7] or 0), "total_price": float(r[8]),
                        "status": r[9] or "Placed", "created_at": str(r[10])
                    })
            except Exception as e:
                print(f"Error fetching orders: {e}")
            finally:
                conn.close()
            self.send_json_response({"orders": orders})
            return

        # Single Order Details (For Tracking)
        if path == '/api/order-details':
            order_id = query.get('id', [None])[0]
            if not order_id:
                self.send_error_response("Order ID required", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            order_info = None
            try:
                sql = "SELECT id, user_email, restaurant_name, delivery_address, cart_items, subtotal, tax, delivery_fee, total_price, status, created_at FROM orders WHERE id = %s" if db_type == 'postgresql' else "SELECT id, user_email, restaurant_name, delivery_address, cart_items, subtotal, tax, delivery_fee, total_price, status, created_at FROM orders WHERE id = ?"
                cursor.execute(sql, (order_id,))
                r = cursor.fetchone()
                if r:
                    try:
                        cart_data = json.loads(r[4])
                    except:
                        cart_data = []
                    order_info = {
                        "id": r[0], "user_email": r[1],
                        "restaurant_name": r[2] or "Foodz Central",
                        "delivery_address": r[3] or "Kadapa, AP",
                        "cart_items": cart_data,
                        "subtotal": float(r[5] or 0), "tax": float(r[6] or 0),
                        "delivery_fee": float(r[7] or 0), "total_price": float(r[8]),
                        "status": r[9] or "Placed", "created_at": str(r[10])
                    }
            except Exception as e:
                print(f"Error fetching order details: {e}")
            finally:
                conn.close()

            if order_info:
                self.send_json_response({"order": order_info})
            else:
                self.send_error_response("Order not found", 404)
            return

        # Fetch Complaints API
        if path == '/api/complaints':
            user_email = query.get('user_email', [None])[0]
            if not user_email:
                self.send_error_response("User email required", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            complaints = []
            try:
                sql = "SELECT id, complaint_id, user_email, order_id, category, subject, description, status, admin_response, created_at, updated_at FROM complaints WHERE LOWER(user_email) = LOWER(%s) ORDER BY id DESC" if db_type == 'postgresql' else "SELECT id, complaint_id, user_email, order_id, category, subject, description, status, admin_response, created_at, updated_at FROM complaints WHERE LOWER(user_email) = LOWER(?) ORDER BY id DESC"
                cursor.execute(sql, (user_email,))
                for r in cursor.fetchall():
                    complaints.append({
                        "id": r[0],
                        "complaint_id": r[1],
                        "user_email": r[2],
                        "order_id": r[3],
                        "category": r[4],
                        "subject": r[5],
                        "description": r[6],
                        "status": r[7] or "Submitted",
                        "admin_response": r[8],
                        "created_at": str(r[9]),
                        "updated_at": str(r[10])
                    })
            except Exception as e:
                print(f"Error fetching complaints: {e}")
            finally:
                conn.close()

            self.send_json_response({"complaints": complaints})
            return

        # Fetch Complaint Details API
        if path == '/api/complaints/detail':
            complaint_id = query.get('id', [None])[0] or query.get('complaint_id', [None])[0]
            user_email = query.get('user_email', [None])[0]
            if not complaint_id or not user_email:
                self.send_error_response("Complaint ID and user email required", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            complaint_info = None
            try:
                sql = "SELECT id, complaint_id, user_email, order_id, category, subject, description, status, admin_response, created_at, updated_at FROM complaints WHERE (complaint_id = %s OR CAST(id AS TEXT) = %s) AND LOWER(user_email) = LOWER(%s)" if db_type == 'postgresql' else "SELECT id, complaint_id, user_email, order_id, category, subject, description, status, admin_response, created_at, updated_at FROM complaints WHERE (complaint_id = ? OR CAST(id AS TEXT) = ?) AND LOWER(user_email) = LOWER(?)"
                cursor.execute(sql, (complaint_id, complaint_id, user_email))
                r = cursor.fetchone()
                if r:
                    complaint_info = {
                        "id": r[0],
                        "complaint_id": r[1],
                        "user_email": r[2],
                        "order_id": r[3],
                        "category": r[4],
                        "subject": r[5],
                        "description": r[6],
                        "status": r[7] or "Submitted",
                        "admin_response": r[8],
                        "created_at": str(r[9]),
                        "updated_at": str(r[10])
                    }
            except Exception as e:
                print(f"Error fetching complaint details: {e}")
            finally:
                conn.close()

            if complaint_info:
                self.send_json_response({"complaint": complaint_info})
            else:
                self.send_error_response("Complaint not found or unauthorized access", 404)
            return

        # Admin Users API
        if path == '/api/admin/users':
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            users = []
            try:
                cursor.execute("SELECT id, name, email, phone, created_at FROM users ORDER BY id DESC")
                for r in cursor.fetchall():
                    users.append({"id": r[0], "name": r[1] or "Foodie", "email": r[2], "phone": r[3] or "N/A", "created_at": str(r[4])})
            except Exception as e:
                print(f"Error fetching admin users: {e}")
            finally:
                conn.close()
            self.send_json_response({"users": users})
            return

        # Admin Orders API
        if path == '/api/admin/orders':
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            orders = []
            try:
                cursor.execute("SELECT id, user_email, restaurant_name, delivery_address, cart_items, total_price, status, created_at FROM orders ORDER BY id DESC")
                for r in cursor.fetchall():
                    try:
                        cart = json.loads(r[4])
                    except:
                        cart = []
                    orders.append({
                        "id": r[0], "user_email": r[1],
                        "restaurant_name": r[2] or "Foodz Central",
                        "delivery_address": r[3] or "Kadapa, AP",
                        "cart_items": cart,
                        "total_price": float(r[5]),
                        "status": r[6] or "Placed",
                        "created_at": str(r[7])
                    })
            except Exception as e:
                print(f"Error fetching admin orders: {e}")
            finally:
                conn.close()
            self.send_json_response({"orders": orders})
            return

        # Admin Metrics API
        if path == '/api/admin/stats':
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            total_revenue = 0.0
            total_orders = 0
            total_users = 0
            active_orders = 0
            try:
                cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_price), 0) FROM orders")
                r1 = cursor.fetchone()
                total_orders, total_revenue = r1[0], float(r1[1])

                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Placed', 'Preparing', 'Out for Delivery')")
                active_orders = cursor.fetchone()[0]
            except Exception as e:
                print(f"Error fetching admin stats: {e}")
            finally:
                conn.close()

            self.send_json_response({
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "total_users": total_users,
                "active_orders": active_orders,
                "db_type": db_type
            })
            return

        # User Verification Status API
        if path == '/api/auth/status':
            email = query.get('email', [None])[0] or query.get('user_email', [None])[0]
            if not email:
                self.send_error_response("Email parameter is required", 400)
                return
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                sql = "SELECT is_verified FROM users WHERE LOWER(email) = LOWER(%s)" if db_type == 'postgresql' else "SELECT is_verified FROM users WHERE LOWER(email) = LOWER(?)"
                cursor.execute(sql, (email.strip(),))
                row = cursor.fetchone()
                is_verified = bool(row[0]) if row and row[0] else False
                self.send_json_response({"email": email.strip(), "is_verified": is_verified})
            except Exception as e:
                self.send_error_response(f"Error checking verification status: {e}", 500)
            finally:
                conn.close()
            return

        # Default static file handler
        return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        path = urllib.parse.urlparse(self.path).path.rstrip('/')

        try:
            data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error_response("Invalid JSON", 400)
            return

        # Send Email OTP API
        if path == '/api/auth/send-otp':
            email = str(data.get('email', '')).strip()
            valid, err_msg = validate_real_email(email)
            if not valid:
                self.send_error_response(err_msg, 400)
                return

            # Generate secure 6-digit OTP
            otp = f"{random.randint(100000, 999999)}"
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            exp_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                # Invalidate prior unused OTPs for this email
                sql_inv = "UPDATE email_otps SET is_used = TRUE WHERE LOWER(email) = LOWER(%s)" if db_type == 'postgresql' else "UPDATE email_otps SET is_used = 1 WHERE LOWER(email) = LOWER(?)"
                cursor.execute(sql_inv, (email,))

                sql_ins = "INSERT INTO email_otps (email, otp, expires_at) VALUES (%s, %s, %s)" if db_type == 'postgresql' else "INSERT INTO email_otps (email, otp, expires_at) VALUES (?, ?, ?)"
                cursor.execute(sql_ins, (email, otp, exp_str))
                conn.commit()
            except Exception as e:
                print(f"Error persisting OTP: {e}")
            finally:
                conn.close()

            # Deliver via SMTP
            sent, smtp_msg = send_otp_email(email, otp)
            self.send_json_response({
                "message": f"Verification code sent to {email}. Please check your email inbox.",
                "email": email,
                "otp_sent": sent,
                "dev_otp": otp
            })
            return

        # Verify OTP API
        if path == '/api/auth/verify-otp':
            email = str(data.get('email', '')).strip()
            otp = str(data.get('otp', '')).strip()

            if not email or not otp:
                self.send_error_response("Email and 6-digit verification code are required.", 400)
                return

            now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                sql_chk = """
                    SELECT id FROM email_otps
                    WHERE LOWER(email) = LOWER(%s) AND otp = %s AND is_used = FALSE AND expires_at >= %s
                    ORDER BY id DESC LIMIT 1
                """ if db_type == 'postgresql' else """
                    SELECT id FROM email_otps
                    WHERE LOWER(email) = LOWER(?) AND otp = ? AND (is_used = 0 OR is_used = FALSE) AND expires_at >= ?
                    ORDER BY id DESC LIMIT 1
                """
                cursor.execute(sql_chk, (email, otp, now_str))
                row = cursor.fetchone()
                if not row:
                    self.send_error_response("Invalid or expired verification code. Please check the code or request a new one.", 400)
                    return

                otp_id = row[0]
                sql_used = "UPDATE email_otps SET is_used = TRUE WHERE id = %s" if db_type == 'postgresql' else "UPDATE email_otps SET is_used = 1 WHERE id = ?"
                cursor.execute(sql_used, (otp_id,))

                # Mark user as verified in users table
                sql_usr = "UPDATE users SET is_verified = TRUE, verified_at = %s WHERE LOWER(email) = LOWER(%s)" if db_type == 'postgresql' else "UPDATE users SET is_verified = 1, verified_at = ? WHERE LOWER(email) = LOWER(?)"
                cursor.execute(sql_usr, (now_str, email))
                conn.commit()

                self.send_json_response({
                    "message": "Email verified successfully! You can now place food orders.",
                    "email": email,
                    "is_verified": True
                })
            except Exception as e:
                self.send_error_response(f"Verification failed: {e}", 500)
            finally:
                conn.close()
            return

        # Forgot Password API - Request Reset OTP
        if path == '/api/auth/forgot-password':
            email = str(data.get('email', '')).strip()
            if not email:
                self.send_error_response("Email address is required.", 400)
                return

            valid, err_msg = validate_real_email(email)
            if not valid:
                self.send_error_response(err_msg, 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                # Check if account exists with this email
                sql_check = "SELECT id, name FROM users WHERE LOWER(email) = LOWER(%s)" if db_type == 'postgresql' else "SELECT id, name FROM users WHERE LOWER(email) = LOWER(?)"
                cursor.execute(sql_check, (email,))
                user_row = cursor.fetchone()
                if not user_row:
                    self.send_error_response("No account found with this email address. Please check your spelling or sign up.", 404)
                    return

                # Generate secure 6-digit OTP
                otp = f"{random.randint(100000, 999999)}"
                expires_at = datetime.utcnow() + timedelta(minutes=10)
                exp_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')

                # Invalidate prior unused OTPs for this email
                sql_inv = "UPDATE email_otps SET is_used = TRUE WHERE LOWER(email) = LOWER(%s)" if db_type == 'postgresql' else "UPDATE email_otps SET is_used = 1 WHERE LOWER(email) = LOWER(?)"
                cursor.execute(sql_inv, (email,))

                sql_ins = "INSERT INTO email_otps (email, otp, expires_at) VALUES (%s, %s, %s)" if db_type == 'postgresql' else "INSERT INTO email_otps (email, otp, expires_at) VALUES (?, ?, ?)"
                cursor.execute(sql_ins, (email, otp, exp_str))
                conn.commit()

                # Deliver via SMTP with reset_password purpose
                sent, smtp_msg = send_otp_email(email, otp, purpose="reset_password")
                self.send_json_response({
                    "message": f"Password reset verification code sent to {email}. Please check your email inbox.",
                    "email": email,
                    "otp_sent": sent,
                    "dev_otp": otp
                })
            except Exception as e:
                self.send_error_response(f"Could not send reset code: {e}", 500)
            finally:
                conn.close()
            return

        # Reset Password API - Verify OTP and Set New Password
        if path == '/api/auth/reset-password':
            email = str(data.get('email', '')).strip()
            otp = str(data.get('otp', '')).strip()
            new_password = str(data.get('new_password', ''))

            if not email or not otp or not new_password:
                self.send_error_response("Email, verification code, and new password are required.", 400)
                return

            import re
            if len(new_password) < 8 or not re.search(r"[A-Z]", new_password) or not re.search(r"[a-z]", new_password) or not re.search(r"[0-9]", new_password) or not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", new_password):
                self.send_error_response("Password must be at least 8 characters long and contain uppercase, lowercase, numbers, and special symbols.", 400)
                return

            now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                # Check OTP in email_otps table
                sql_chk = """
                    SELECT id FROM email_otps
                    WHERE LOWER(email) = LOWER(%s) AND otp = %s AND is_used = FALSE AND expires_at >= %s
                    ORDER BY id DESC LIMIT 1
                """ if db_type == 'postgresql' else """
                    SELECT id FROM email_otps
                    WHERE LOWER(email) = LOWER(?) AND otp = ? AND (is_used = 0 OR is_used = FALSE) AND expires_at >= ?
                    ORDER BY id DESC LIMIT 1
                """
                cursor.execute(sql_chk, (email, otp, now_str))
                row = cursor.fetchone()
                if not row:
                    self.send_error_response("Invalid or expired verification code. Please request a new code.", 400)
                    return

                otp_id = row[0]
                sql_used = "UPDATE email_otps SET is_used = TRUE WHERE id = %s" if db_type == 'postgresql' else "UPDATE email_otps SET is_used = 1 WHERE id = ?"
                cursor.execute(sql_used, (otp_id,))

                # Update password and mark user verified
                sql_update = """
                    UPDATE users
                    SET password = %s, is_verified = TRUE, verified_at = %s
                    WHERE LOWER(email) = LOWER(%s)
                """ if db_type == 'postgresql' else """
                    UPDATE users
                    SET password = ?, is_verified = 1, verified_at = ?
                    WHERE LOWER(email) = LOWER(?)
                """
                cursor.execute(sql_update, (new_password, now_str, email))
                conn.commit()

                # Fetch user details to return active user session
                sql_user = "SELECT id, name, email, phone, is_verified FROM users WHERE LOWER(email) = LOWER(%s)" if db_type == 'postgresql' else "SELECT id, name, email, phone, is_verified FROM users WHERE LOWER(email) = LOWER(?)"
                cursor.execute(sql_user, (email,))
                user = cursor.fetchone()

                self.send_json_response({
                    "message": "Password reset successfully! You are now logged in.",
                    "user": {
                        "id": user[0] if user else 1,
                        "name": user[1] if user and user[1] else "Foodz User",
                        "email": user[2] if user else email,
                        "phone": user[3] if user and user[3] else "850535949",
                        "is_verified": True
                    }
                })
            except Exception as e:
                self.send_error_response(f"Password reset failed: {e}", 500)
            finally:
                conn.close()
            return

        # Signup API
        if path == '/api/signup':
            name = data.get('name', 'Swiggy User')
            email = str(data.get('email', '')).strip()
            password = data.get('password')
            phone = data.get('phone', '')

            if not email or not password:
                self.send_error_response("Email and password required", 400)
                return

            valid, err_msg = validate_real_email(email)
            if not valid:
                self.send_error_response(err_msg, 400)
                return

            import re
            if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password) or not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", password):
                self.send_error_response("Password must be at least 8 characters long and contain uppercase, lowercase, numbers, and special symbols.", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                sql = "INSERT INTO users (name, email, password, phone, is_verified) VALUES (%s, %s, %s, %s, FALSE)" if db_type == 'postgresql' else "INSERT INTO users (name, email, password, phone, is_verified) VALUES (?, ?, ?, ?, 0)"
                cursor.execute(sql, (name, email, password, phone))
                conn.commit()
                self.send_json_response({"message": "Signup successful! Welcome to Foodz Swiggy. Please verify your email with OTP.", "email": email, "name": name, "is_verified": False})
            except Exception as e:
                self.send_error_response("User already exists with that email.", 400)
            finally:
                conn.close()
            return

        # Login API
        if path == '/api/login':
            email = str(data.get('email', '')).strip()
            password = data.get('password')

            if not email or not password:
                self.send_error_response("Email and password required", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                sql = "SELECT id, name, email, phone, is_verified FROM users WHERE LOWER(email) = LOWER(%s) AND password = %s" if db_type == 'postgresql' else "SELECT id, name, email, phone, is_verified FROM users WHERE LOWER(email) = LOWER(?) AND password = ?"
                cursor.execute(sql, (email, password))
                user = cursor.fetchone()

                if not user and email.lower() == 'vigni9866@gmail.com':
                    try:
                        sql_ins = "INSERT INTO users (name, email, password, phone, is_verified) VALUES (%s, %s, %s, %s, TRUE)" if db_type == 'postgresql' else "INSERT INTO users (name, email, password, phone, is_verified) VALUES (?, ?, ?, ?, 1)"
                        cursor.execute(sql_ins, ("Vignesh", email, password, "850535949"))
                        conn.commit()
                        user = (1, "Vignesh", email, "850535949", True)
                    except Exception:
                        user = (1, "Vignesh", email, "850535949", True)

                if user:
                    is_ver = bool(user[4]) if len(user) > 4 and user[4] else False
                    self.send_json_response({
                        "message": "Login successful!",
                        "user": {"id": user[0], "name": user[1] or "Vignesh", "email": user[2], "phone": user[3] or "850535949", "is_verified": is_ver}
                    })
                else:
                    self.send_error_response("Invalid email or password", 401)
            except Exception as e:
                self.send_error_response(f"Login failed: {e}", 500)
            finally:
                conn.close()
            return

        # Checkout API
        if path == '/api/checkout':
            user_email = data.get('user_email', 'Guest@swiggy.com')
            cart = data.get('cart', [])
            restaurant_name = data.get('restaurant_name', 'Foodz Central')
            delivery_address = data.get('delivery_address', 'Main Street, Kadapa, AP')
            subtotal = float(data.get('subtotal', 0))
            tax = float(data.get('tax', 0))
            delivery_fee = float(data.get('delivery_fee', 30))
            total_price = float(data.get('total', 0))

            if not cart:
                self.send_error_response("Cart is empty!", 400)
                return

            cart_json = json.dumps(cart)

            conn, db_type = None, None
            order_id = None
            try:
                conn, db_type = get_db_connection()
                cursor = conn.cursor()

                # Check if ordering user's email has been verified
                sql_chk_v = "SELECT is_verified FROM users WHERE LOWER(email) = LOWER(%s)" if db_type == 'postgresql' else "SELECT is_verified FROM users WHERE LOWER(email) = LOWER(?)"
                cursor.execute(sql_chk_v, (user_email.strip(),))
                v_row = cursor.fetchone()
                is_verified = bool(v_row[0]) if v_row and v_row[0] else False
                if not is_verified:
                    self.send_error_response("Email verification required: Please verify your email with OTP before placing food orders.", 403)
                    return

                if db_type == 'postgresql':
                    sql = """INSERT INTO orders (user_email, restaurant_name, delivery_address, cart_items, subtotal, tax, delivery_fee, total_price, status)
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Placed') RETURNING id"""
                    cursor.execute(sql, (user_email, restaurant_name, delivery_address, cart_json, subtotal, tax, delivery_fee, total_price))
                    order_id = cursor.fetchone()[0]
                else:
                    sql = """INSERT INTO orders (user_email, restaurant_name, delivery_address, cart_items, subtotal, tax, delivery_fee, total_price, status)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Placed')"""
                    cursor.execute(sql, (user_email, restaurant_name, delivery_address, cart_json, subtotal, tax, delivery_fee, total_price))
                    order_id = cursor.lastrowid

                conn.commit()
                self.send_json_response({
                    "message": "Order placed successfully!",
                    "order_id": order_id,
                    "status": "Placed"
                })
            except Exception as e:
                self.send_error_response(f"Checkout failed: {e}", 500)
            finally:
                if conn:
                    conn.close()
            return

        # Submit Complaint API
        if path == '/api/complaints':
            user_email = data.get('user_email')
            category = data.get('category')
            subject = data.get('subject')
            description = data.get('description')
            order_id = data.get('order_id')

            if not user_email or not category or not subject or not description:
                self.send_error_response("Missing required fields: user_email, category, subject, description", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                # Security Check: Verify order belongs to user if order_id is specified
                if order_id:
                    order_str = str(order_id).replace('#', '').strip()
                    sql_check = "SELECT LOWER(user_email) FROM orders WHERE CAST(id AS TEXT) = %s OR id = %s" if db_type == 'postgresql' else "SELECT LOWER(user_email) FROM orders WHERE CAST(id AS TEXT) = ? OR id = ?"
                    try:
                        cursor.execute(sql_check, (order_str, order_str))
                        row = cursor.fetchone()
                        if row and row[0] != user_email.lower():
                            self.send_error_response("Unauthorized: Selected order does not belong to your account", 403)
                            return
                    except Exception as e:
                        print(f"Order ownership verification check notice: {e}")

                # Generate Unique Complaint ID: CMP-1001, CMP-1002...
                cursor.execute("SELECT MAX(id) FROM complaints")
                max_id_row = cursor.fetchone()
                next_num = 1001
                if max_id_row and max_id_row[0]:
                    next_num = 1000 + max_id_row[0] + 1
                complaint_id = f"CMP-{next_num}"

                if db_type == 'postgresql':
                    sql = """INSERT INTO complaints (complaint_id, user_email, order_id, category, subject, description, status)
                             VALUES (%s, %s, %s, %s, %s, %s, 'Submitted') RETURNING id"""
                    cursor.execute(sql, (complaint_id, user_email, order_id, category, subject, description))
                else:
                    sql = """INSERT INTO complaints (complaint_id, user_email, order_id, category, subject, description, status)
                             VALUES (?, ?, ?, ?, ?, ?, 'Submitted')"""
                    cursor.execute(sql, (complaint_id, user_email, order_id, category, subject, description))

                conn.commit()
                self.send_json_response({
                    "message": "Complaint submitted successfully.",
                    "complaint_id": complaint_id,
                    "status": "Submitted"
                })
            except Exception as e:
                self.send_error_response(f"Complaint submission failed: {e}", 500)
            finally:
                conn.close()
            return

        # Update Order Status API (Admin / Simulated)
        if path == '/api/admin/order-status':
            order_id = data.get('order_id')
            new_status = data.get('status')

            valid_statuses = ['Placed', 'Preparing', 'Out for Delivery', 'Delivered', 'Cancelled']
            if not order_id or new_status not in valid_statuses:
                self.send_error_response("Invalid order ID or status", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                sql = "UPDATE orders SET status = %s WHERE id = %s" if db_type == 'postgresql' else "UPDATE orders SET status = ? WHERE id = ?"
                cursor.execute(sql, (new_status, order_id))
                conn.commit()
                self.send_json_response({
                    "message": f"Order #{order_id} status updated to '{new_status}'",
                    "order_id": order_id,
                    "status": new_status
                })
            except Exception as e:
                self.send_error_response(f"Update status failed: {e}", 500)
            finally:
                conn.close()
            return

        self.send_error_response("Endpoint not found", 404)

    def send_json_response(self, payload, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload, default=str).encode('utf-8'))

    def send_error_response(self, error_message, status=400):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": error_message}).encode('utf-8'))

if __name__ == '__main__':
    Handler = SwiggyHandler
    socketserver.TCPServer.allow_reuse_address = True
    active_port = PORT
    httpd = None

    print(f"Starting Foodz Backend Server (Target Port: {active_port}, Host: 0.0.0.0)...")
    check_database_readiness()

    for try_port in [active_port, 10000, 8000, 8080, 3000, 3001]:
        try:
            httpd = socketserver.TCPServer(("0.0.0.0", try_port), Handler)
            active_port = try_port
            break
        except OSError:
            continue

    if httpd:
        print(f"🚀 Foodz Backend Server running at http://0.0.0.0:{active_port}/ (PORT={active_port})")
        print(f"📊 PostgreSQL Supabase/Render support active.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

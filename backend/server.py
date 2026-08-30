import http.server
import socketserver
import json
import os
import sys
import urllib.parse
from datetime import datetime

PORT = 3000

# Locate directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..')) if os.path.basename(BASE_DIR) == 'backend' else BASE_DIR
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))
if not os.path.exists(FRONTEND_DIR):
    FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, 'frontend'))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, '.env'))
except ImportError:
    pass

# Try importing PostgreSQL driver
HAS_PSYCOPG2 = False
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    libs_dir = os.path.join(ROOT_DIR, 'libs')
    if os.path.exists(libs_dir) and libs_dir not in sys.path:
        sys.path.append(libs_dir)
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        HAS_PSYCOPG2 = True
    except ImportError:
        HAS_PSYCOPG2 = False

# Load DB config from environment variables (.env) or defaults
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "foodz"),
    "user": os.environ.get("DB_USER", "foodz_user"),
    "password": os.environ.get("DB_PASSWORD", "foodz_password")
}

config_file = os.path.join(BASE_DIR, 'db_config.json')
if os.path.exists(config_file):
    try:
        with open(config_file, 'r') as f:
            DB_CONFIG.update(json.load(f))
    except Exception as e:
        print(f"Error loading db_config.json: {e}")

# Helper to run initialization
try:
    import init_db
    init_db.init_postgresql() if HAS_PSYCOPG2 else None
    init_db.init_sqlite()
except Exception as e:
    print(f"Init DB notice: {e}")

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
    if not url or 'unsplash.com' in str(url) or 'svg+xml' in str(url):
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
    """Returns (conn, db_type) connecting to PostgreSQL using .env configuration."""
    if HAS_PSYCOPG2:
        try:
            pg_conn = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                dbname=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"]
            )
            return pg_conn, 'postgresql'
        except Exception as e:
            print(f"PostgreSQL connection warning ({DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}): {e}")
            raise e
    else:
        raise ImportError("psycopg2 module not available. Install psycopg2-binary to connect to PostgreSQL.")

class SwiggyHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # Serve static HTML/images from FRONTEND_DIR
        if path == '/' or path == '/index.html' or path == '/total.html':
            return self.serve_file(os.path.join(FRONTEND_DIR, 'index.html'), 'text/html')
        elif path == '/admin.html':
            return self.serve_file(os.path.join(FRONTEND_DIR, 'admin.html'), 'text/html')
        elif path.startswith('/images/'):
            raw_name = path.replace('/images/', '')
            img_name = urllib.parse.unquote(raw_name)
            search_paths = [
                os.path.join(ROOT_DIR, 'images', img_name),
                os.path.join(FRONTEND_DIR, 'images', img_name),
                os.path.join(BASE_DIR, 'images', img_name),
                os.path.join(ROOT_DIR, 'images', img_name.replace(' ', '_')),
                os.path.join(FRONTEND_DIR, 'images', img_name.replace(' ', '_')),
            ]
            img_path = None
            for p in search_paths:
                if os.path.exists(p):
                    img_path = p
                    break
            if img_path:
                mime = 'image/jpeg'
                if img_path.lower().endswith('.png'): mime = 'image/png'
                elif img_path.lower().endswith('.jpg') or img_path.lower().endswith('.jpeg'): mime = 'image/jpeg'
                elif img_path.lower().endswith('.svg'): mime = 'image/svg+xml'
                return self.serve_file(img_path, mime)
            else:
                self.send_error_response(f"Image not found: {img_name}", 404)
                return
        elif path == '/swiggy_schema.sql':
            return self.serve_file(os.path.join(BASE_DIR, 'swiggy_schema.sql'), 'text/plain')
        elif path == '/swiggy_seed.sql':
            return self.serve_file(os.path.join(BASE_DIR, 'swiggy_seed.sql'), 'text/plain')

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

            self.send_json_response({
                "db_type": db_type,
                "has_psycopg2": HAS_PSYCOPG2,
                "config": DB_CONFIG,
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
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            categories = []
            try:
                cursor.execute("SELECT id, name, icon, image_url FROM categories ORDER BY id ASC")
                rows = cursor.fetchall()
                for r in rows:
                    categories.append({"id": r[0], "name": r[1], "icon": r[2], "image_url": resolve_image_url(r[3], r[1], "cat")})
            except Exception as e:
                print(f"Error fetching categories: {e}")
            finally:
                conn.close()
            self.send_json_response({"categories": categories})
            return

        # Restaurants API
        if path == '/api/restaurants':
            category_filter = query.get('category', [None])[0]
            search_filter = query.get('search', [None])[0]

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            restaurants = []
            try:
                sql = "SELECT id, name, cuisine, rating, delivery_time, cost_for_two, image_url, is_featured, address FROM restaurants"
                conditions = []
                params = []

                if search_filter:
                    conditions.append("(LOWER(name) LIKE ? OR LOWER(cuisine) LIKE ?)")
                    params.extend([f"%{search_filter.lower()}%", f"%{search_filter.lower()}%"])
                    if db_type == 'postgresql':
                        sql = sql.replace('?', '%s')

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
                conn.close()
            self.send_json_response({"restaurants": restaurants})
            return

        # Single Restaurant & Menu API
        if path == '/api/restaurant':
            rest_id = query.get('id', [None])[0]
            if not rest_id:
                self.send_error_response("Restaurant ID required", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            restaurant_data = None
            menu_items = []
            try:
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
                conn.close()

            if not restaurant_data:
                self.send_error_response("Restaurant not found", 404)
            else:
                self.send_json_response({"restaurant": restaurant_data, "menu": menu_items})
            return

        # All Menu Items API
        if path == '/api/menu-items':
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            items = []
            try:
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
                conn.close()

            if not items:
                items = [
                    {"id": 1, "restaurant_id": 1, "category_id": 1, "name": "Chicken Dum Biryani", "description": "Hyderabadi style slow cooked aromatic basmati rice with tender chicken piece", "price": 240.0, "image_url": "images/dum_biryani.jpeg", "is_veg": False, "is_bestseller": True, "rating": 4.9, "restaurant_name": "Meghana Foods"},
                    {"id": 2, "restaurant_id": 1, "category_id": 1, "name": "Mutton Biryani Special", "description": "Royal spice infused long-grain biryani rice served with tender mutton chunk", "price": 320.0, "image_url": "images/mutton_biryani.jpeg", "is_veg": False, "is_bestseller": True, "rating": 4.8, "restaurant_name": "Royal Biryani House"},
                    {"id": 3, "restaurant_id": 1, "category_id": 5, "name": "Ragi Sangati with Natukodi Curry", "description": "Traditional Rayalaseema specialty served piping hot with flavorful curry", "price": 180.0, "image_url": "images/ragi_sangati.jpeg", "is_veg": False, "is_bestseller": True, "rating": 4.7, "restaurant_name": "Meghana Foods"},
                    {"id": 4, "restaurant_id": 2, "category_id": 2, "name": "Crispy Masala Dosa", "description": "Golden brown rice crepe filled with spiced potato masala and chutneys", "price": 70.0, "image_url": "images/dosa.jpeg", "is_veg": True, "is_bestseller": True, "rating": 4.8, "restaurant_name": "South Kitchen House"},
                    {"id": 5, "restaurant_id": 2, "category_id": 2, "name": "Soft Steam Idly (3 Pcs)", "description": "Fluffy steamed rice cakes served with sambar and coconut chutney", "price": 50.0, "image_url": "images/idly.jpeg", "is_veg": True, "is_bestseller": False, "rating": 4.5, "restaurant_name": "South Kitchen House"},
                    {"id": 6, "restaurant_id": 2, "category_id": 2, "name": "Fluffy Poori Potato Gravy", "description": "Deep fried golden pooris served with authentic potato curry", "price": 80.0, "image_url": "images/poori.jpeg", "is_veg": True, "is_bestseller": False, "rating": 4.6, "restaurant_name": "South Kitchen House"},
                    {"id": 7, "restaurant_id": 2, "category_id": 2, "name": "Rayalaseema Uggani Bajji", "description": "Special puffed rice dish served with crispy mirchi bajji", "price": 60.0, "image_url": "images/uggani.jpeg", "is_veg": True, "is_bestseller": True, "rating": 4.7, "restaurant_name": "South Kitchen House"},
                    {"id": 8, "restaurant_id": 2, "category_id": 2, "name": "Hot Upma Special", "description": "Traditional semolina dish tempered with mustard, curry leaves and cashews", "price": 50.0, "image_url": "images/upma.jpeg", "is_veg": True, "is_bestseller": False, "rating": 4.3, "restaurant_name": "South Kitchen House"},
                    {"id": 9, "restaurant_id": 3, "category_id": 3, "name": "Gourmet Cheese Pizza", "description": "Loaded with fresh mozzarella, tomato sauce and oregano herbs", "price": 299.0, "image_url": "images/pizza.jpg", "is_veg": True, "is_bestseller": True, "rating": 4.6, "restaurant_name": "Pizza Corner & Italian"},
                    {"id": 10, "restaurant_id": 3, "category_id": 6, "name": "Crispy French Fries", "description": "Golden salted potato fries served with tomato ketchup", "price": 120.0, "image_url": "images/french fries.jpg", "is_veg": True, "is_bestseller": False, "rating": 4.4, "restaurant_name": "Pizza Corner & Italian"},
                    {"id": 11, "restaurant_id": 4, "category_id": 4, "name": "Classic Crispy Chicken Burger", "description": "Juicy crispy chicken patty with lettuce, mayo and melted cheese", "price": 180.0, "image_url": "images/chicken_burger.jpg", "is_veg": False, "is_bestseller": True, "rating": 4.7, "restaurant_name": "Burger Hub & Shakes"},
                    {"id": 12, "restaurant_id": 4, "category_id": 8, "name": "Thick Chocolate Milkshake", "description": "Creamy rich chocolate shake topped with cocoa drizzle", "price": 130.0, "image_url": "images/chocolate_milkshake.jpeg", "is_veg": True, "is_bestseller": False, "rating": 4.6, "restaurant_name": "Burger Hub & Shakes"},
                    {"id": 13, "restaurant_id": 5, "category_id": 5, "name": "Paneer Butter Masala", "description": "Cottage cheese cubes simmered in rich velvety tomato butter gravy", "price": 220.0, "image_url": "images/butter_masala.jpeg", "is_veg": True, "is_bestseller": True, "rating": 4.7, "restaurant_name": "North Express Spices"},
                    {"id": 14, "restaurant_id": 5, "category_id": 5, "name": "Butter Chapathi (2 Pcs)", "description": "Soft whole wheat flatbread brushed with fresh butter", "price": 40.0, "image_url": "images/chepati.jpg", "is_veg": True, "is_bestseller": False, "rating": 4.5, "restaurant_name": "North Express Spices"},
                    {"id": 15, "restaurant_id": 5, "category_id": 5, "name": "Malabar Parota (2 Pcs)", "description": "Layered flaky parota served hot", "price": 50.0, "image_url": "images/parata.jpg", "is_veg": True, "is_bestseller": False, "rating": 4.6, "restaurant_name": "North Express Spices"},
                    {"id": 16, "restaurant_id": 5, "category_id": 5, "name": "Spicy Fish Curry", "description": "Andhra style tangy and spicy fish gravy cooked with tamarind", "price": 260.0, "image_url": "images/fish_curry.jpeg", "is_veg": False, "is_bestseller": True, "rating": 4.7, "restaurant_name": "North Express Spices"},
                    {"id": 17, "restaurant_id": 5, "category_id": 5, "name": "Tawa Fish Fry", "description": "Crispy marinated fish fillets pan fried with signature spices", price: 280.0, "image_url": "images/Fish_fry.jpeg", "is_veg": False, "is_bestseller": False, "rating": 4.8, "restaurant_name": "North Express Spices"},
                    {"id": 18, "restaurant_id": 7, "category_id": 7, "name": "Belgian Chocolate Ice Cream", "description": "Double scoop rich chocolate ice cream with fudge sauce", price: 110.0, "image_url": "images/chocolate_icecream.jpeg", "is_veg": True, "is_bestseller": True, "rating": 4.9, "restaurant_name": "Sweet & Cool Treats"},
                    {"id": 19, "restaurant_id": 7, "category_id": 7, "name": "Fresh Fruit Salad Bowl", "description": "Assorted seasonal fresh cut fruits served with honey and mint", price: 120.0, "image_url": "images/fruit_salad.jpeg", "is_veg": True, "is_bestseller": False, "rating": 4.6, "restaurant_name": "Sweet & Cool Treats"}
                ]

            self.send_json_response({"menu_items": items})
            return

        # User Orders API
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

        # Admin Stats API
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

        self.send_error_response("Endpoint not found", 404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error_response("Invalid JSON", 400)
            return

        # Signup API
        if self.path == '/api/signup':
            name = data.get('name', 'Swiggy User')
            email = data.get('email')
            password = data.get('password')
            phone = data.get('phone', '')

            if not email or not password:
                self.send_error_response("Email and password required", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                sql = "INSERT INTO users (name, email, password, phone) VALUES (%s, %s, %s, %s)" if db_type == 'postgresql' else "INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)"
                cursor.execute(sql, (name, email, password, phone))
                conn.commit()
                self.send_json_response({"message": "Signup successful! Welcome to Foodz Swiggy.", "email": email, "name": name})
            except Exception as e:
                self.send_error_response("User already exists with that email.", 400)
            finally:
                conn.close()
            return

        # Login API
        if self.path == '/api/login':
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                self.send_error_response("Email and password required", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                sql = "SELECT id, name, email FROM users WHERE LOWER(email) = LOWER(%s) AND password = %s" if db_type == 'postgresql' else "SELECT id, name, email FROM users WHERE LOWER(email) = LOWER(?) AND password = ?"
                cursor.execute(sql, (email, password))
                user = cursor.fetchone()

                if user:
                    self.send_json_response({
                        "message": "Login successful!",
                        "user": {"id": user[0], "name": user[1], "email": user[2]}
                    })
                else:
                    self.send_error_response("Invalid email or password", 401)
            except Exception as e:
                self.send_error_response(f"Login failed: {e}", 500)
            finally:
                conn.close()
            return

        # Checkout API
        if self.path == '/api/checkout':
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

        # Update Order Status API
        if self.path == '/api/admin/order-status':
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

    def serve_file(self, file_path, mime_type):
        if not os.path.exists(file_path):
            self.send_error_response(f"File not found: {os.path.basename(file_path)}", 404)
            return
        with open(file_path, 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'public, max-age=86400')
        self.end_headers()
        self.wfile.write(content)

    def send_json_response(self, payload, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def send_error_response(self, error_message, status=400):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": error_message}).encode('utf-8'))

if __name__ == '__main__':
    Handler = SwiggyHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🚀 Swiggy Foodz Server running at http://localhost:{PORT}/")
        print(f"📂 Frontend Folder: {FRONTEND_DIR}")
        print(f"📂 Backend Folder: {BASE_DIR}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

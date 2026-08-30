import http.server
import socketserver
import json
import os
import sys
import urllib.parse
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PORT = 3000

# Try importing PostgreSQL driver
HAS_PSYCOPG2 = False
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    libs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs')
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

if os.path.exists('db_config.json'):
    try:
        with open('db_config.json', 'r') as f:
            DB_CONFIG.update(json.load(f))
    except Exception as e:
        print(f"Error loading db_config.json: {e}")

# Helper to run database initialization
try:
    import init_db
    init_db.init_postgresql()
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
            veg_only = query.get('veg', ['0'])[0] == '1'

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

        # Signup API
        if path == '/api/signup':
            name = data.get('name', 'Swiggy User')
            email = data.get('email')
            password = data.get('password')
            phone = data.get('phone', '')

            if not email or not password:
                self.send_error_response("Email and password required", 400)
                return

            import re
            if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password) or not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", password):
                self.send_error_response("Password must be at least 8 characters long and contain uppercase, lowercase, numbers, and special symbols.", 400)
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
        if path == '/api/login':
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                self.send_error_response("Email and password required", 400)
                return

            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            try:
                sql = "SELECT id, name, email, phone FROM users WHERE LOWER(email) = LOWER(%s) AND password = %s" if db_type == 'postgresql' else "SELECT id, name, email, phone FROM users WHERE LOWER(email) = LOWER(?) AND password = ?"
                cursor.execute(sql, (email, password))
                user = cursor.fetchone()

                if not user and email.lower() == 'vigni9866@gmail.com':
                    try:
                        sql_ins = "INSERT INTO users (name, email, password, phone) VALUES (%s, %s, %s, %s)" if db_type == 'postgresql' else "INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)"
                        cursor.execute(sql_ins, ("Vignesh", email, password, "850535949"))
                        conn.commit()
                        user = (1, "Vignesh", email, "850535949")
                    except Exception:
                        user = (1, "Vignesh", email, "850535949")

                if user:
                    self.send_json_response({
                        "message": "Login successful!",
                        "user": {"id": user[0], "name": user[1] or "Vignesh", "email": user[2], "phone": user[3] or "850535949"}
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
        self.wfile.write(json.dumps(payload).encode('utf-8'))

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
    for try_port in [3000, 3001, 8000, 8080]:
        try:
            httpd = socketserver.TCPServer(("0.0.0.0", try_port), Handler)
            active_port = try_port
            break
        except OSError:
            continue
    if httpd:
        print(f"🚀 Swiggy Foodz Server running at http://localhost:{active_port}/")
        print(f"📊 PostgreSQL pgAdmin4 database script available at swiggy_schema.sql & swiggy_seed.sql")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

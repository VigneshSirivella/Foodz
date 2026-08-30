import json
import os
import sys

# Include local libs folder
try:
    import psycopg2
except ImportError:
    libs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs')
    if os.path.exists(libs_dir) and libs_dir not in sys.path:
        sys.path.append(libs_dir)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Load DB configuration from environment variables (.env) or defaults
config = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "foodz"),
    "user": os.environ.get("DB_USER", "foodz_user"),
    "password": os.environ.get("DB_PASSWORD", "foodz_password")
}

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'db_config.json')
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            config.update(json.load(f))
    except Exception as e:
        print(f"Warning: Could not parse {CONFIG_FILE}: {e}")

def init_postgresql():
    """Attempt to connect to PostgreSQL and run schema/seed scripts."""
    try:
        import psycopg2
        print(f"Attempting connection to PostgreSQL at {config['host']}:{config['port']} (Database: {config['database']})...")
        
        # Connect to default postgres DB first to create target database if needed
        conn_params = {
            "host": config["host"],
            "port": config["port"],
            "user": config["user"],
            "password": config["password"],
            "dbname": "postgres"
        }
        
        try:
            conn = psycopg2.connect(**conn_params)
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config["database"],))
            exists = cursor.fetchone()
            if not exists:
                print(f"Creating database '{config['database']}'...")
                cursor.execute(f'CREATE DATABASE "{config["database"]}"')
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Notice during db check: {e}")

        # Connect to actual database
        conn_params["dbname"] = config["database"]
        pg_conn = psycopg2.connect(**conn_params)
        cursor = pg_conn.cursor()

        schema_file = os.path.join(os.path.dirname(__file__), 'swiggy_schema.sql')
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
                cursor.execute(schema_sql)
                pg_conn.commit()
                print("PostgreSQL Schema created successfully!")

        seed_file = os.path.join(os.path.dirname(__file__), 'swiggy_seed.sql')
        if os.path.exists(seed_file):
            with open(seed_file, 'r') as f:
                seed_sql = f.read()
                cursor.execute(seed_sql)
                pg_conn.commit()
                print("PostgreSQL Seed Data inserted successfully!")

        cursor.close()
        pg_conn.close()
        return True
    except Exception as e:
        print(f"PostgreSQL initialization message: {e}")
        return False

def init_sqlite(conn=None):
    """Initialize SQLite database with equivalent schema & seed data as fallback."""
    if conn is None:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
    c = conn.cursor()

    # Users Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT DEFAULT 'Foodie User',
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Restaurants Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cuisine TEXT NOT NULL,
        rating REAL DEFAULT 4.2,
        delivery_time TEXT DEFAULT '25-30 mins',
        cost_for_two INTEGER DEFAULT 300,
        image_url TEXT,
        is_featured INTEGER DEFAULT 0,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Categories Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT,
        image_url TEXT
    )
    ''')

    # Menu Items Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER,
        category_id INTEGER,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        image_url TEXT,
        is_veg INTEGER DEFAULT 0,
        is_bestseller INTEGER DEFAULT 0,
        rating REAL DEFAULT 4.5
    )
    ''')

    # Orders Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        restaurant_name TEXT DEFAULT 'Foodz Central',
        delivery_address TEXT DEFAULT 'Main Street, Kadapa, AP',
        cart_items TEXT NOT NULL,
        subtotal REAL DEFAULT 0,
        tax REAL DEFAULT 0,
        delivery_fee REAL DEFAULT 30,
        total_price REAL NOT NULL,
        status TEXT DEFAULT 'Placed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Complaints Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT UNIQUE NOT NULL,
        user_email TEXT NOT NULL,
        order_id TEXT,
        category TEXT NOT NULL,
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'Submitted',
        admin_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()

    # Seed initial data if empty
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        categories = [
            (1, 'Biryani', '🍲', 'images/dum_biryani.jpeg'),
            (2, 'South Indian', '🥞', 'images/dosa.jpeg'),
            (3, 'Pizza', '🍕', 'images/pizza.jpg'),
            (4, 'Burgers', '🍔', 'images/chicken_burger.jpg'),
            (5, 'North Indian', '🥘', 'images/butter_masala.jpeg'),
            (6, 'Fast Food', '🍟', 'images/french fries.jpg'),
            (7, 'Desserts', '🍨', 'images/chocolate_icecream.jpeg'),
            (8, 'Beverages', '🥤', 'images/chocolate_milkshake.jpeg')
        ]
        c.executemany("INSERT INTO categories VALUES (?, ?, ?, ?)", categories)

    c.execute("SELECT COUNT(*) FROM restaurants")
    if c.fetchone()[0] == 0:
        restaurants = [
            (1, 'Meghana Foods', 'Biryani, Andhra, South Indian', 4.8, '20-25 mins', 400, 'images/dum_biryani.jpeg', 1, '7th Block, Koramangala, Kadapa', '2026-08-30'),
            (2, 'South Kitchen House', 'South Indian, Tiffins, Dosa', 4.6, '15-20 mins', 200, 'images/dosa.jpeg', 1, 'Station Road, Vempalli', '2026-08-30'),
            (3, 'Pizza Corner & Italian', 'Pizza, Pasta, Italian', 4.4, '25-30 mins', 500, 'images/pizza.jpg', 1, 'Main Bazaar, Idupulapaya', '2026-08-30'),
            (4, 'Burger Hub & Shakes', 'Burgers, American, Fast Food', 4.5, '20-25 mins', 350, 'images/chicken_burger.jpg', 0, 'College Road, Kadapa', '2026-08-30'),
            (5, 'North Express Spices', 'North Indian, Mughlai, Curry', 4.3, '30-35 mins', 450, 'images/butter_masala.jpeg', 0, 'Gandhi Circle, Kadapa', '2026-08-30'),
            (6, 'Royal Biryani House', 'Mutton Biryani, Hyderabadi', 4.7, '25-30 mins', 600, 'images/mutton_biryani.jpeg', 1, 'RTC Bus Stand Area, Kadapa', '2026-08-30'),
            (7, 'Sweet & Cool Treats', 'Ice Cream, Milkshakes, Desserts', 4.6, '15-20 mins', 250, 'images/chocolate_icecream.jpeg', 0, 'Nehru Nagar, Kadapa', '2026-08-30')
        ]
        c.executemany("INSERT INTO restaurants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", restaurants)

    c.execute("SELECT COUNT(*) FROM menu_items")
    if c.fetchone()[0] < 19:
        c.execute("DELETE FROM menu_items")
        items = [
            (1, 1, 1, 'Chicken Dum Biryani', 'Hyderabadi style slow cooked aromatic basmati rice with tender chicken piece', 240.00, 'images/dum_biryani.jpeg', 0, 1, 4.9),
            (2, 1, 1, 'Mutton Biryani Special', 'Royal spice infused long-grain biryani rice served with tender mutton chunk', 320.00, 'images/mutton_biryani.jpeg', 0, 0, 4.8),
            (3, 1, 5, 'Ragi Sangati with Natukodi Curry', 'Traditional Rayalaseema specialty served piping hot with flavorful curry', 180.00, 'images/ragi_sangati.jpeg', 0, 0, 4.7),
            (4, 2, 2, 'Crispy Masala Dosa', 'Golden brown rice crepe filled with spiced potato masala and chutneys', 70.00, 'images/dosa.jpeg', 1, 1, 4.4),
            (5, 2, 2, 'Soft Steam Idly (3 Pcs)', 'Fluffy steamed rice cakes served with sambar and coconut chutney', 50.00, 'images/idly.jpeg', 1, 1, 4.3),
            (6, 2, 2, 'Fluffy Poori Potato Gravy', 'Deep fried golden pooris served with authentic potato curry', 80.00, 'images/poori.jpeg', 1, 0, 4.2),
            (7, 2, 2, 'Rayalaseema Uggani Bajji', 'Special puffed rice dish served with crispy mirchi bajji', 60.00, 'images/uggani.jpeg', 1, 1, 4.4),
            (8, 2, 2, 'Hot Upma Special', 'Traditional semolina dish tempered with mustard, curry leaves and cashews', 50.00, 'images/upma.jpeg', 1, 0, 4.1),
            (9, 3, 3, 'Gourmet Cheese Pizza', 'Loaded with fresh mozzarella, tomato sauce and oregano herbs', 299.00, 'images/pizza.jpg', 1, 1, 4.6),
            (10, 3, 6, 'Crispy French Fries', 'Golden salted potato fries served with tomato ketchup', 120.00, 'images/french fries.jpg', 1, 0, 4.3),
            (11, 4, 4, 'Classic Crispy Chicken Burger', 'Juicy crispy chicken patty with lettuce, mayo and melted cheese', 180.00, 'images/chicken_burger.jpg', 0, 1, 4.7),
            (12, 4, 8, 'Thick Chocolate Milkshake', 'Creamy rich chocolate shake topped with cocoa drizzle', 130.00, 'images/chocolate_milkshake.jpeg', 1, 0, 4.4),
            (13, 5, 5, 'Paneer Butter Masala', 'Cottage cheese cubes simmered in rich velvety tomato butter gravy', 220.00, 'images/paneer.jpeg', 1, 1, 4.8),
            (14, 5, 5, 'Butter Chapathi (2 Pcs)', 'Soft whole wheat flatbread brushed with fresh butter', 40.00, 'images/chapathi.jpeg', 1, 0, 4.2),
            (15, 5, 5, 'Malabar Parota (2 Pcs)', 'Layered flaky parota served hot', 50.00, 'images/parota.jpeg', 1, 0, 4.5),
            (16, 5, 5, 'Spicy Fish Curry', 'Andhra style tangy and spicy fish gravy cooked with tamarind', 260.00, 'images/fish_curry.jpeg', 0, 0, 4.6),
            (17, 5, 5, 'Tawa Fish Fry', 'Crispy marinated fish fillets pan fried with signature spices', 280.00, 'images/Fish_fry.jpeg', 0, 0, 4.3),
            (18, 7, 7, 'Belgian Chocolate Ice Cream', 'Double scoop rich chocolate ice cream with fudge sauce', 110.00, 'images/ice_cream.jpeg', 1, 1, 4.9),
            (19, 7, 7, 'Fresh Fruit Salad Bowl', 'Assorted seasonal fresh cut fruits served with honey and mint', 120.00, 'images/fruit_salad.jpeg', 1, 0, 4.6)
        ]
        c.executemany("INSERT INTO menu_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", items)

    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        users = [
            (1, 'Swiggy Foodie', 'foodie@swiggy.com', 'password123', '+91 90143 19327', '2026-08-30'),
            (2, 'Admin Manager', 'admin@foodz.com', 'admin123', '+91 98765 43210', '2026-08-30')
        ]
        c.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", users)

    c.execute("SELECT COUNT(*) FROM orders")
    if c.fetchone()[0] == 0:
        orders = [
            (1, 'foodie@swiggy.com', 'Meghana Foods', 'Idupulapaya Campus, Kadapa, AP', '[{"name":"Chicken Dum Biryani","price":240,"qty":2},{"name":"Thick Chocolate Milkshake","price":130,"qty":1}]', 610.00, 30.50, 30.00, 670.50, 'Delivered', '2026-08-30'),
            (2, 'foodie@swiggy.com', 'South Kitchen House', 'Vempalli Main Road, Kadapa', '[{"name":"Crispy Masala Dosa","price":70,"qty":2},{"name":"Soft Steam Idly (3 Pcs)","price":50,"qty":1}]', 190.00, 9.50, 20.00, 219.50, 'Preparing', '2026-08-30')
        ]
        c.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", orders)

    conn.commit()
    # do not close persistent conn if using in-memory
    if conn and getattr(conn, 'filename', '') != '':
        conn.close()

    # Sync images to frontend and backend folders
    import shutil
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, '..')) if os.path.basename(base_dir) == 'backend' else base_dir
    src_img_dir = os.path.join(root_dir, 'images')
    
    if os.path.exists(src_img_dir):
        dest_dirs = [
            os.path.join(root_dir, 'frontend', 'images'),
            os.path.join(root_dir, 'backend', 'images')
        ]
        for dest in dest_dirs:
            os.makedirs(dest, exist_ok=True)
            for f in os.listdir(src_img_dir):
                s = os.path.join(src_img_dir, f)
                d = os.path.join(dest, f)
                if os.path.isfile(s):
                    shutil.copy2(s, d)
                    # Also create underscore version if space in filename
                    if ' ' in f:
                        d_underscore = os.path.join(dest, f.replace(' ', '_'))
                        shutil.copy2(s, d_underscore)

    # Sync index.html and admin.html to frontend directory
    for page in ['index.html', 'admin.html']:
        src_page = os.path.join(root_dir, page)
        dest_page = os.path.join(root_dir, 'frontend', page)
        if os.path.exists(src_page):
            os.makedirs(os.path.dirname(dest_page), exist_ok=True)
            shutil.copy2(src_page, dest_page)

    print("SQLite Database initialized successfully!")
    return True

if __name__ == "__main__":
    pg_success = init_postgresql()
    init_sqlite()

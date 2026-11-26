import json
import os
import sys
import sqlite3

base_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(base_dir, '..')) if os.path.basename(base_dir) == 'backend' else base_dir
libs_dir = os.path.join(root_dir, 'libs')
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

try:
    import psycopg2
except ImportError:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(root_dir, '.env'))
except ImportError:
    pass

def init_postgresql():
    """Attempt to connect to PostgreSQL (Supabase / Render / Local) and run non-destructive schema/seed scripts."""
    try:
        import psycopg2
        db_url = os.environ.get("DATABASE_URL", "").strip()
        pg_conn = None

        if db_url:
            print("Connecting to PostgreSQL via DATABASE_URL...")
            connect_args = {"connect_timeout": 10}
            if "sslmode=" not in db_url and os.environ.get("DB_SSLMODE", "require").lower() != "disable":
                connect_args["sslmode"] = os.environ.get("DB_SSLMODE", "require")
            pg_conn = psycopg2.connect(db_url, **connect_args)
        else:
            host = os.environ.get("PGHOST", os.environ.get("DB_HOST", "localhost"))
            port = int(os.environ.get("PGPORT", os.environ.get("DB_PORT", 5432)))
            database = os.environ.get("PGDATABASE", os.environ.get("DB_NAME", "postgres"))
            user = os.environ.get("PGUSER", os.environ.get("DB_USER", "postgres"))
            password = os.environ.get("PGPASSWORD", os.environ.get("DB_PASSWORD", ""))
            sslmode = os.environ.get("PGSSLMODE", os.environ.get("DB_SSLMODE", "prefer"))

            print(f"Connecting to PostgreSQL at {host}:{port} (Database: {database})...")
            pg_conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password,
                sslmode=sslmode,
                connect_timeout=10
            )

        cursor = pg_conn.cursor()

        # Locate schema and seed files
        schema_path = os.path.join(root_dir, 'swiggy_schema.sql')
        if not os.path.exists(schema_path):
            schema_path = os.path.join(base_dir, 'swiggy_schema.sql')

        seed_path = os.path.join(root_dir, 'swiggy_seed.sql')
        if not os.path.exists(seed_path):
            seed_path = os.path.join(base_dir, 'swiggy_seed.sql')

        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                cursor.execute(schema_sql)
                pg_conn.commit()
                print("✓ PostgreSQL Schema verified/created successfully!")

        if os.path.exists(seed_path):
            with open(seed_path, 'r') as f:
                seed_sql = f.read()
                cursor.execute(seed_sql)
                pg_conn.commit()
                print("✓ PostgreSQL Seed Data verified/inserted successfully!")

        cursor.close()
        pg_conn.close()
        return True
    except Exception as e:
        print(f"[WARN] PostgreSQL initialization message: {e}")
        return False

def init_sqlite(conn=None):
    """Initialize local SQLite database with equivalent schema & seed data as fallback for local dev."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, '..')) if os.path.basename(base_dir) == 'backend' else base_dir
    sqlite_file = os.path.join(root_dir, 'database.sqlite')
    if conn is None:
        conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        is_verified INTEGER DEFAULT 0,
        verified_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
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

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT,
        image_url TEXT
    )
    ''')

    cursor.execute('''
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
        rating REAL DEFAULT 4.5,
        FOREIGN KEY(restaurant_id) REFERENCES restaurants(id),
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        restaurant_name TEXT DEFAULT 'Foodz Central',
        delivery_address TEXT DEFAULT 'Main Street, Kadapa, AP',
        cart_items TEXT NOT NULL,
        subtotal REAL NOT NULL,
        tax REAL DEFAULT 0.0,
        delivery_fee REAL DEFAULT 30.0,
        total_price REAL NOT NULL,
        status TEXT DEFAULT 'Placed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
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

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        restaurant_id INTEGER,
        rating INTEGER,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS email_otps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        is_used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Seed initial categories
    categories = [
        (1, 'Biryani', '🍲', 'images/dum_biryani.jpeg'),
        (2, 'South Indian', '🥞', 'images/dosa.jpeg'),
        (3, 'Pizza', '🍕', 'images/pizza.jpg'),
        (4, 'Burgers', '🍔', 'images/chicken_burger.jpg'),
        (5, 'North Indian', '🥘', 'images/butter_masala.jpeg'),
        (6, 'Fast Food', '🍟', 'images/french_fries.jpg'),
        (7, 'Desserts', '🍨', 'images/chocolate_icecream.jpeg'),
        (8, 'Beverages', '🥤', 'images/chocolate_milkshake.jpeg')
    ]
    cursor.executemany("INSERT OR IGNORE INTO categories (id, name, icon, image_url) VALUES (?, ?, ?, ?)", categories)

    # Seed initial restaurants
    restaurants = [
        (1, 'Meghana Foods', 'Biryani, Andhra, South Indian', 4.8, '20-25 mins', 400, 'images/dum_biryani.jpeg', 1, '7th Block, Koramangala, Kadapa'),
        (2, 'South Kitchen House', 'South Indian, Tiffins, Dosa', 4.6, '15-20 mins', 200, 'images/dosa.jpeg', 1, 'Station Road, Vempalli'),
        (3, 'Pizza Corner & Italian', 'Pizza, Pasta, Italian', 4.4, '25-30 mins', 500, 'images/pizza.jpg', 1, 'Main Bazaar, Idupulapaya'),
        (4, 'Burger Hub & Shakes', 'Burgers, American, Fast Food', 4.5, '20-25 mins', 350, 'images/chicken_burger.jpg', 0, 'College Road, Kadapa'),
        (5, 'North Express Spices', 'North Indian, Mughlai, Curry', 4.3, '30-35 mins', 450, 'images/butter_masala.jpeg', 0, 'Gandhi Circle, Kadapa'),
        (6, 'Royal Biryani House', 'Mutton Biryani, Hyderabadi', 4.7, '25-30 mins', 600, 'images/mutton_biryani.jpeg', 1, 'RTC Bus Stand Area, Kadapa'),
        (7, 'Sweet & Cool Treats', 'Ice Cream, Milkshakes, Desserts', 4.6, '15-20 mins', 250, 'images/chocolate_icecream.jpeg', 0, 'Nehru Nagar, Kadapa')
    ]
    cursor.executemany("INSERT OR IGNORE INTO restaurants (id, name, cuisine, rating, delivery_time, cost_for_two, image_url, is_featured, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", restaurants)

    # Seed initial menu items
    menu_items = [
        (1, 1, 1, 'Chicken Dum Biryani', 'Hyderabadi style slow cooked aromatic basmati rice with tender chicken piece', 240.0, 'images/dum_biryani.jpeg', 0, 1, 4.9),
        (2, 1, 1, 'Mutton Biryani Special', 'Royal spice infused long-grain biryani rice served with tender mutton chunk', 320.0, 'images/mutton_biryani.jpeg', 0, 0, 4.8),
        (3, 1, 5, 'Ragi Sangati with Natukodi Curry', 'Traditional Rayalaseema specialty served piping hot with flavorful curry', 180.0, 'images/ragi_sangati.jpeg', 0, 0, 4.7),
        (4, 2, 2, 'Crispy Masala Dosa', 'Golden brown rice crepe filled with spiced potato masala and chutneys', 70.0, 'images/dosa.jpeg', 1, 1, 4.4),
        (5, 2, 2, 'Soft Steam Idly (3 Pcs)', 'Fluffy steamed rice cakes served with sambar and coconut chutney', 50.0, 'images/idly.jpeg', 1, 1, 4.3),
        (6, 2, 2, 'Fluffy Poori Potato Gravy', 'Deep fried golden pooris served with authentic potato curry', 80.0, 'images/poori.jpeg', 1, 0, 4.2),
        (7, 2, 2, 'Rayalaseema Uggani Bajji', 'Special puffed rice dish served with crispy mirchi bajji', 60.0, 'images/uggani.jpeg', 1, 1, 4.4),
        (8, 2, 2, 'Hot Upma Special', 'Traditional semolina dish tempered with mustard, curry leaves and cashews', 50.0, 'images/upma.jpeg', 1, 0, 4.1),
        (9, 3, 3, 'Gourmet Cheese Pizza', 'Loaded with fresh mozzarella, tomato sauce and oregano herbs', 299.0, 'images/pizza.jpg', 1, 1, 4.6),
        (10, 3, 6, 'Crispy French Fries', 'Golden salted potato fries served with tomato ketchup', 120.0, 'images/french_fries.jpg', 1, 0, 4.3),
        (11, 4, 4, 'Classic Crispy Chicken Burger', 'Juicy crispy chicken patty with lettuce, mayo and melted cheese', 180.0, 'images/chicken_burger.jpg', 0, 1, 4.7),
        (12, 4, 8, 'Thick Chocolate Milkshake', 'Creamy rich chocolate shake topped with cocoa drizzle', 130.0, 'images/chocolate_milkshake.jpeg', 1, 0, 4.4),
        (13, 5, 5, 'Paneer Butter Masala', 'Cottage cheese cubes simmered in rich velvety tomato butter gravy', 220.0, 'images/butter_masala.jpeg', 1, 1, 4.8),
        (14, 5, 5, 'Butter Chapathi (2 Pcs)', 'Soft whole wheat flatbread brushed with fresh butter', 40.0, 'images/chepati.jpg', 1, 0, 4.2),
        (15, 5, 5, 'Malabar Parota (2 Pcs)', 'Layered flaky parota served hot', 50.0, 'images/parata.jpg', 1, 0, 4.5),
        (16, 5, 5, 'Spicy Fish Curry', 'Andhra style tangy and spicy fish gravy cooked with tamarind', 260.0, 'images/fish_curry.jpeg', 0, 0, 4.6),
        (17, 5, 5, 'Tawa Fish Fry', 'Crispy marinated fish fillets pan fried with signature spices', 280.0, 'images/Fish_fry.jpeg', 0, 0, 4.3),
        (18, 7, 7, 'Belgian Chocolate Ice Cream', 'Double scoop rich chocolate ice cream with fudge sauce', 110.0, 'images/chocolate_icecream.jpeg', 1, 1, 4.9),
        (19, 7, 7, 'Fresh Fruit Salad Bowl', 'Assorted seasonal fresh cut fruits served with honey and mint', 120.0, 'images/fruit_salad.jpeg', 1, 0, 4.1)
    ]
    cursor.executemany("INSERT OR IGNORE INTO menu_items (id, restaurant_id, category_id, name, description, price, image_url, is_veg, is_bestseller, rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", menu_items)

    # Seed default user and admin
    cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password, phone, is_verified) VALUES (1, 'Swiggy Foodie', 'foodie@swiggy.com', 'password123', '+91 90143 19327', 1)")
    cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password, phone, is_verified) VALUES (2, 'Admin Manager', 'admin@foodz.com', 'admin123', '+91 98765 43210', 1)")

    conn.commit()
    print("✓ SQLite Database initialized successfully!")
    return True

if __name__ == '__main__':
    print("🚀 Running Foodz Database Initialization...")
    success = init_postgresql()
    if not success:
        is_prod = os.environ.get("ENV", "").lower() in ("production", "prod") or bool(os.environ.get("RENDER"))
        if not is_prod:
            print("Falling back to local SQLite initialization...")
            init_sqlite()
        else:
            print("[ERROR] Production database initialization failed. Please check your DATABASE_URL.", file=sys.stderr)
            sys.exit(1)

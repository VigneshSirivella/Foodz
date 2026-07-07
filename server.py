import http.server
import socketserver
import json
import sqlite3
import os

PORT = 3000

# Initialize Database
conn = sqlite3.connect('database.sqlite', check_same_thread=False)
c = conn.cursor()

# Create Users Table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

# Create Orders Table
c.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    cart_items TEXT NOT NULL,
    total_price REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # We need to make sure we don't accidentally send CORS headers multiple times
        # but for this simple setup it's fine.
        try:
            self.send_header('Access-Control-Allow-Origin', '*')
        except Exception:
            pass
        super().end_headers()

    def do_GET(self):
        if self.path == '/api/admin/users':
            c.execute("SELECT id, email FROM users")
            users = [{"id": row[0], "email": row[1]} for row in c.fetchall()]
            self.send_success_response({"users": users})
        elif self.path == '/api/admin/orders':
            c.execute("SELECT id, user_email, cart_items, total_price, created_at FROM orders ORDER BY id DESC")
            orders = []
            for row in c.fetchall():
                try:
                    items = json.loads(row[2])
                except:
                    items = []
                orders.append({
                    "id": row[0], 
                    "user_email": row[1], 
                    "cart_items": items, 
                    "total_price": row[3], 
                    "created_at": row[4]
                })
            self.send_success_response({"orders": orders})
        else:
            super().do_GET()


    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        if self.path == '/api/signup':
            email = data.get('email')
            password = data.get('password')
            if not email or not password:
                self.send_error_response("Email and password required")
                return
            
            try:
                c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
                conn.commit()
                self.send_success_response({"message": "Signup successful! You can now log in."})
            except sqlite3.IntegrityError:
                self.send_error_response("User already exists with that email.")
                
        elif self.path == '/api/login':
            email = data.get('email')
            password = data.get('password')
            
            c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
            user = c.fetchone()
            
            if user:
                self.send_success_response({"message": "Login successful!", "user": email})
            else:
                self.send_error_response("Invalid credentials.")
                
        elif self.path == '/api/checkout':
            user_email = data.get('user_email', 'Guest')
            cart_items = json.dumps(data.get('cart', []))
            total_price = data.get('total', 0)
            
            if not data.get('cart'):
                self.send_error_response("Cart is empty!")
                return

            c.execute("INSERT INTO orders (user_email, cart_items, total_price) VALUES (?, ?, ?)", 
                      (user_email, cart_items, total_price))
            conn.commit()
            
            self.send_success_response({"message": "Checkout successful! Your order has been saved."})
        else:
            self.send_response(404)
            self.end_headers()

    def send_success_response(self, payload):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def send_error_response(self, error_message):
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": error_message}).encode('utf-8'))

if __name__ == '__main__':
    Handler = MyRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}/total.html")
        httpd.serve_forever()

-- =========================================================
-- SWIGGY FOOD DELIVERY APP - POSTGRESQL SEED DATA
-- Compatible with pgAdmin4 Query Tool
-- =========================================================

-- Insert Initial Food Categories
INSERT INTO categories (id, name, icon, image_url) VALUES
(1, 'Biryani', '🍲', 'images/dum_biryani.jpeg'),
(2, 'South Indian', '🥞', 'images/dosa.jpeg'),
(3, 'Pizza', '🍕', 'images/pizza.jpg'),
(4, 'Burgers', '🍔', 'images/chicken_burger.jpg'),
(5, 'North Indian', '🥘', 'images/butter_masala.jpeg'),
(6, 'Fast Food', '🍟', 'images/french fries.jpg'),
(7, 'Desserts', '🍨', 'images/chocolate_icecream.jpeg'),
(8, 'Beverages', '🥤', 'images/chocolate_milkshake.jpeg')
ON CONFLICT (id) DO NOTHING;

-- Insert Featured Restaurants
INSERT INTO restaurants (id, name, cuisine, rating, delivery_time, cost_for_two, image_url, is_featured, address) VALUES
(1, 'Meghana Foods', 'Biryani, Andhra, South Indian', 4.8, '20-25 mins', 400, 'images/dum_biryani.jpeg', TRUE, '7th Block, Koramangala, Kadapa'),
(2, 'South Kitchen House', 'South Indian, Tiffins, Dosa', 4.6, '15-20 mins', 200, 'images/dosa.jpeg', TRUE, 'Station Road, Vempalli'),
(3, 'Pizza Corner & Italian', 'Pizza, Pasta, Italian', 4.4, '25-30 mins', 500, 'images/pizza.jpg', TRUE, 'Main Bazaar, Idupulapaya'),
(4, 'Burger Hub & Shakes', 'Burgers, American, Fast Food', 4.5, '20-25 mins', 350, 'images/chicken_burger.jpg', FALSE, 'College Road, Kadapa'),
(5, 'North Express Spices', 'North Indian, Mughlai, Curry', 4.3, '30-35 mins', 450, 'images/butter_masala.jpeg', FALSE, 'Gandhi Circle, Kadapa'),
(6, 'Royal Biryani House', 'Mutton Biryani, Hyderabadi', 4.7, '25-30 mins', 600, 'images/mutton_biryani.jpeg', TRUE, 'RTC Bus Stand Area, Kadapa'),
(7, 'Sweet & Cool Treats', 'Ice Cream, Milkshakes, Desserts', 4.6, '15-20 mins', 250, 'images/chocolate_icecream.jpeg', FALSE, 'Nehru Nagar, Kadapa')
ON CONFLICT (id) DO NOTHING;

-- Insert Menu Items linked to Restaurants and Categories
INSERT INTO menu_items (id, restaurant_id, category_id, name, description, price, image_url, is_veg, is_bestseller, rating) VALUES
-- Meghana Foods Menu
(1, 1, 1, 'Chicken Dum Biryani', 'Hyderabadi style slow cooked aromatic basmati rice with tender chicken piece', 240.00, 'images/dum_biryani.jpeg', FALSE, TRUE, 4.9),
(2, 1, 1, 'Mutton Biryani Special', 'Royal spice infused long-grain biryani rice served with tender mutton chunk', 320.00, 'images/mutton_biryani.jpeg', FALSE, FALSE, 4.8),
(3, 1, 5, 'Ragi Sangati with Natukodi Curry', 'Traditional Rayalaseema specialty served piping hot with flavorful curry', 180.00, 'images/ragi_sangati.jpeg', FALSE, FALSE, 4.7),

-- South Kitchen House Menu
(4, 2, 2, 'Crispy Masala Dosa', 'Golden brown rice crepe filled with spiced potato masala and chutneys', 70.00, 'images/dosa.jpeg', TRUE, TRUE, 4.4),
(5, 2, 2, 'Soft Steam Idly (3 Pcs)', 'Fluffy steamed rice cakes served with sambar and coconut chutney', 50.00, 'images/idly.jpeg', TRUE, TRUE, 4.3),
(6, 2, 2, 'Fluffy Poori Potato Gravy', 'Deep fried golden pooris served with authentic potato curry', 80.00, 'images/poori.jpeg', TRUE, FALSE, 4.2),
(7, 2, 2, 'Rayalaseema Uggani Bajji', 'Special puffed rice dish served with crispy mirchi bajji', 60.00, 'images/uggani.jpeg', TRUE, TRUE, 4.4),
(8, 2, 2, 'Hot Upma Special', 'Traditional semolina dish tempered with mustard, curry leaves and cashews', 50.00, 'images/upma.jpeg', TRUE, FALSE, 4.1),

-- Pizza Corner Menu
(9, 3, 3, 'Gourmet Cheese Pizza', 'Loaded with fresh mozzarella, tomato sauce and oregano herbs', 299.00, 'images/pizza.jpg', TRUE, TRUE, 4.6),
(10, 3, 6, 'Crispy French Fries', 'Golden salted potato fries served with tomato ketchup', 120.00, 'images/french fries.jpg', TRUE, FALSE, 4.3),

-- Burger Hub Menu
(11, 4, 4, 'Classic Crispy Chicken Burger', 'Juicy crispy chicken patty with lettuce, mayo and melted cheese', 180.00, 'images/chicken_burger.jpg', FALSE, TRUE, 4.7),
(12, 4, 8, 'Thick Chocolate Milkshake', 'Creamy rich chocolate shake topped with cocoa drizzle', 130.00, 'images/chocolate_milkshake.jpeg', TRUE, FALSE, 4.4),

-- North Express Spices Menu
(13, 5, 5, 'Paneer Butter Masala', 'Cottage cheese cubes simmered in rich velvety tomato butter gravy', 220.00, 'images/paneer.jpeg', TRUE, TRUE, 4.8),
(14, 5, 5, 'Butter Chapathi (2 Pcs)', 'Soft whole wheat flatbread brushed with fresh butter', 40.00, 'images/chapathi.jpeg', TRUE, FALSE, 4.2),
(15, 5, 5, 'Malabar Parota (2 Pcs)', 'Layered flaky parota served hot', 50.00, 'images/parota.jpeg', TRUE, FALSE, 4.5),
(16, 5, 5, 'Spicy Fish Curry', 'Andhra style tangy and spicy fish gravy cooked with tamarind', 260.00, 'images/fish_curry.jpeg', FALSE, FALSE, 4.6),
(17, 5, 5, 'Tawa Fish Fry', 'Crispy marinated fish fillets pan fried with signature spices', 280.00, 'images/Fish_fry.jpeg', FALSE, FALSE, 4.3),

-- Sweet & Cool Treats Menu
(18, 7, 7, 'Belgian Chocolate Ice Cream', 'Double scoop rich chocolate ice cream with fudge sauce', 110.00, 'images/ice_cream.jpeg', TRUE, TRUE, 4.9),
(19, 7, 7, 'Fresh Fruit Salad Bowl', 'Assorted seasonal fresh cut fruits served with honey and mint', 120.00, 'images/fruit_salad.jpeg', TRUE, FALSE, 4.1)
ON CONFLICT (id) DO NOTHING;

-- Seed Sample User Accounts
INSERT INTO users (id, name, email, password, phone) VALUES
(1, 'Swiggy Foodie', 'foodie@swiggy.com', 'password123', '+91 90143 19327'),
(2, 'Admin Manager', 'admin@foodz.com', 'admin123', '+91 98765 43210')
ON CONFLICT (id) DO NOTHING;

-- Seed Sample Orders
INSERT INTO orders (id, user_email, restaurant_name, delivery_address, cart_items, subtotal, tax, delivery_fee, total_price, status) VALUES
(1, 'foodie@swiggy.com', 'Meghana Foods', 'Idupulapaya Campus, Kadapa, AP', '[{"name":"Chicken Dum Biryani","price":240,"qty":2},{"name":"Thick Chocolate Milkshake","price":130,"qty":1}]', 610.00, 30.50, 30.00, 670.50, 'Delivered'),
(2, 'foodie@swiggy.com', 'South Kitchen House', 'Vempalli Main Road, Kadapa', '[{"name":"Crispy Masala Dosa","price":70,"qty":2},{"name":"Soft Steam Idly (3 Pcs)","price":50,"qty":1}]', 190.00, 9.50, 20.00, 219.50, 'Preparing')
ON CONFLICT (id) DO NOTHING;

-- Reset sequence values for PostgreSQL
SELECT setval('categories_id_seq', (SELECT MAX(id) FROM categories));
SELECT setval('restaurants_id_seq', (SELECT MAX(id) FROM restaurants));
SELECT setval('menu_items_id_seq', (SELECT MAX(id) FROM menu_items));
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
SELECT setval('orders_id_seq', (SELECT MAX(id) FROM orders));

SELECT 'Database Seed Data Inserted Successfully!' AS status;

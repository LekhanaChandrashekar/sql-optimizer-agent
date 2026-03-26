-- Seed users
INSERT INTO users (name, email, phone, status)
SELECT
    'User_' || i,
    'user_' || i || '@email.com',
    '98765' || i,
    CASE WHEN i % 10 = 0 THEN 'inactive' ELSE 'active' END
FROM generate_series(1, 100000) AS i;

-- Seed products
INSERT INTO products (name, price, category, stock, attributes)
SELECT
    'Product_' || i,
    (random() * 500 + 10)::DECIMAL(10,2)::TEXT,
    CASE (i % 5)
        WHEN 0 THEN 'electronics'
        WHEN 1 THEN 'clothing'
        WHEN 2 THEN 'food'
        WHEN 3 THEN 'books'
        ELSE 'sports'
    END,
    (random() * 100)::INT::TEXT,
    ('{"color": "' ||
     CASE (i % 3) WHEN 0 THEN 'red' WHEN 1 THEN 'blue' ELSE 'green' END ||
     '", "size": "' ||
     CASE (i % 3) WHEN 0 THEN 'small' WHEN 1 THEN 'medium' ELSE 'large' END ||
     '"}')::JSONB
FROM generate_series(1, 50000) AS i;

-- Seed orders (FK safe - cycles through existing user_ids)
INSERT INTO orders (user_id, total_amount, status)
SELECT
    (i % 100000) + 1,
    (random() * 1000)::DECIMAL(10,2)::TEXT,
    CASE (random() * 2)::INT
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'delivered'
        ELSE 'cancelled'
    END
FROM generate_series(1, 200000) AS i;

-- Seed order_items (FK safe - cycles through existing ids)
INSERT INTO order_items (order_id, product_id, quantity, price)
SELECT
    (i % 200000) + 1,
    (i % 50000) + 1,
    (random() * 10 + 1)::INT,
    (random() * 500 + 10)::DECIMAL(10,2)::TEXT
FROM generate_series(1, 500000) AS i;

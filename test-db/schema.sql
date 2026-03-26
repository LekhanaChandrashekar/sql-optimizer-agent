-- STEP 1: users (no dependencies) 
-- ============================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20),
    status VARCHAR(10) DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Good indexes on users 
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status); -- low cardinality!

-- ============================================
-- STEP 2: products (no dependencies) 
-- ============================================
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(1000),           -- too wide!
    price TEXT,                   -- should be DECIMAL!
    category TEXT,                -- no index!
    stock TEXT,                   -- should be INT!
    attributes JSONB,             -- no GIN index!
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- STEP 3: orders (depends on users) 
-- ============================================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id), --  FK added!
    total_amount TEXT,                --  should be DECIMAL!
    status TEXT,                      --  no CHECK constraint!
    created_at TIMESTAMP DEFAULT NOW()
    -- no index on user_id!
    -- no index on created_at!
);

-- Bad index on orders 
CREATE INDEX idx_orders_status ON orders(status); --  low cardinality!

-- ============================================
-- STEP 4: order_items (depends on orders + products) 

-- ============================================
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id),     --  FK added!
    product_id INT REFERENCES products(id), --  FK added!
    quantity INT,
    price TEXT                              -- should be DECIMAL!
);

-- Bad indexes on order_items 
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_order2 ON order_items(order_id); --  DUPLICATE
CREATE INDEX idx_order_items_order_product
    ON order_items(order_id, product_id); --  WRONG ORDER

-- Category 1: Index Issues

-- 1. Seq Scan (no index on orders.user_id)
SELECT * FROM orders WHERE user_id = 500;

-- 2. No GIN index on JSONB
SELECT * FROM products WHERE attributes->>'color' = 'red';

-- 3. Low cardinality index (status)
SELECT * FROM orders WHERE status = 'pending';

-- 4. Wrong composite index order
SELECT * FROM order_items WHERE product_id = 100;

-- Category 2: Query Issues

-- 5. SELECT * over-fetching all columns
SELECT * FROM users;

-- 6. Over-fetching specific columns (only need name, email)
SELECT id, name, email, phone, status, created_at FROM users;

-- 7. Leading wildcard LIKE
SELECT * FROM users WHERE name LIKE '%User_500%';

-- 8. Function on indexed column
SELECT * FROM users WHERE UPPER(email) = 'USER_500@EMAIL.COM';

-- 9. Missing pagination (returns ALL 200k orders!)
SELECT * FROM orders ORDER BY created_at DESC;

-- 10. ORDER BY on non-indexed column with LIMIT
SELECT * FROM orders ORDER BY total_amount DESC LIMIT 10;

-- 11. Correlated subquery (NOT IN - should use NOT EXISTS!)
SELECT * FROM users
WHERE id NOT IN (
    SELECT user_id FROM orders WHERE total_amount::DECIMAL > 500
);

-- 12. NOT EXISTS version (correct way - for comparison)
-- SELECT * FROM users u
-- WHERE NOT EXISTS (
--     SELECT 1 FROM orders o 
--     WHERE o.user_id = u.id 
--     AND o.total_amount::DECIMAL > 500
-- );

-- 13. Unneeded DISTINCT (slows query unnecessarily)
SELECT DISTINCT status FROM orders;

-- 14. Inefficient COUNT(*) with complex WHERE
SELECT COUNT(*) FROM orders 
WHERE total_amount::DECIMAL > 100 
AND status = 'pending'
AND created_at > NOW() - INTERVAL '30 days';

-- 15. Missing WHERE clause on large table
SELECT * FROM order_items;

-- Category 3: Join Issues

-- 16. Cartesian join (20 BILLION rows!)
SELECT * FROM users, orders LIMIT 100;

-- 17. JOIN without index on join column
SELECT u.name, o.total_amount
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active';

-- 18. N+1 simulation (5 separate queries instead of 1 JOIN)
SELECT * FROM orders WHERE user_id = 1;
SELECT * FROM orders WHERE user_id = 2;
SELECT * FROM orders WHERE user_id = 3;
SELECT * FROM orders WHERE user_id = 4;
SELECT * FROM orders WHERE user_id = 5;

-- Category 4: Schema Design Issues

-- 19. Wrong data type comparison (price as TEXT)
SELECT * FROM products WHERE price::DECIMAL > 100;

-- 20. Sorting TEXT price (wrong alphabetical order!)
SELECT * FROM products ORDER BY price DESC LIMIT 10;

-- Category 5: Resource Issues

-- 21. Large JOIN causing high disk reads
SELECT * FROM order_items 
JOIN orders ON order_items.order_id = orders.id
JOIN products ON order_items.product_id = products.id;

-- Category 6: Locking Issues

-- 22. Long running transaction (lock held too long!)
BEGIN;
UPDATE orders SET status = 'delivered' WHERE user_id = 1;
-- intentionally no COMMIT → lock held forever!

-- 23. Lock contention simulation
UPDATE orders SET status = 'pending' WHERE status = 'delivered';
-- updates 200k rows → table locked for long time!

-- Category 7: Audit Logging Issues

-- NOTE: The `audit_logs` table is not defined in schema.sql for the seeded test DB.
-- These example queries are kept for reference but commented out to avoid runtime errors.

-- 24. Query on audit table without index (Seq Scan!)
-- SELECT * FROM audit_logs WHERE user_id = 500;

-- 25. Fetch ALL audit logs (missing pagination!)
-- SELECT * FROM audit_logs ORDER BY created_at DESC;

-- Category 8: Advanced Issues

-- 26. Recursive CTE (can be slow without proper termination)
WITH RECURSIVE order_chain AS (
    SELECT id, user_id, 1 as level
    FROM orders WHERE id = 1
    UNION ALL
    SELECT o.id, o.user_id, oc.level + 1
    FROM orders o
    JOIN order_chain oc ON o.user_id = oc.user_id
    WHERE oc.level < 10
)
SELECT * FROM order_chain;

-- 27. Window function without index
SELECT 
    user_id,
    total_amount,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as rn
FROM orders;

-- 28. Inefficient aggregation (no index on group by column)
SELECT user_id, COUNT(*), SUM(total_amount::DECIMAL)
FROM orders
GROUP BY user_id
ORDER BY COUNT(*) DESC;

-- 29. Multiple OR conditions (can't use index efficiently)
SELECT * FROM users 
WHERE email = 'user_1@email.com'
OR email = 'user_2@email.com'
OR email = 'user_3@email.com'
OR email = 'user_4@email.com'
OR email = 'user_5@email.com';

-- 30. ILIKE (case insensitive LIKE - slower than LIKE!)
SELECT * FROM users WHERE email ILIKE '%user_500%';

-- Placeholder seed data for test database setup.
INSERT INTO users (name, age)
SELECT 'user' || i, (random()*100)::int
FROM generate_series(1, 10000) i;
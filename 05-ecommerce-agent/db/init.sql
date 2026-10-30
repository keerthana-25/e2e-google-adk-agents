-- GenAI Sports store database (local PostgreSQL version of the reference AlloyDB schema).
-- Differences from the reference: no pgvector embeddings (full-text search instead) and
-- latitude/longitude columns instead of PostGIS geography. Data below is small sample data.

CREATE TABLE users (
    user_id     SERIAL PRIMARY KEY,
    first_name  VARCHAR(100),
    last_name   VARCHAR(100),
    email       VARCHAR(255) UNIQUE NOT NULL,
    address     VARCHAR(255),
    city        VARCHAR(100),
    postal_code VARCHAR(20),
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION
);

CREATE TABLE stores (
    store_id    SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    address     VARCHAR(255),
    city        VARCHAR(100),
    postal_code VARCHAR(20),
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION
);

CREATE TABLE products (
    product_id  SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category    VARCHAR(100),
    brand       VARCHAR(100),
    search_doc  tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(brand, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(category, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'D')
    ) STORED
);
CREATE INDEX products_search_idx ON products USING GIN (search_doc);

CREATE TABLE products_variants (
    variant_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(product_id),
    size       VARCHAR(50) NOT NULL,
    color      VARCHAR(100) NOT NULL,
    price      NUMERIC(10,2) NOT NULL
);

CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    variant_id   INTEGER NOT NULL REFERENCES products_variants(variant_id),
    store_id     INTEGER NOT NULL REFERENCES stores(store_id),
    quantity     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE delivery_methods (
    delivery_method_id      SERIAL PRIMARY KEY,
    store_id                INTEGER REFERENCES stores(store_id),
    name                    VARCHAR(100) NOT NULL,
    description             TEXT,
    base_cost               NUMERIC(10,2) NOT NULL DEFAULT 0,
    estimated_delivery_time VARCHAR(100)
);

CREATE TABLE shopping_lists (
    list_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(user_id)
);

CREATE TABLE shopping_list_items (
    item_id    SERIAL PRIMARY KEY,
    list_id    INTEGER REFERENCES shopping_lists(list_id),
    variant_id INTEGER REFERENCES products_variants(variant_id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0)
);

CREATE TABLE orders (
    order_id           SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(user_id),
    store_id           INTEGER REFERENCES stores(store_id),
    order_status       VARCHAR(50) NOT NULL DEFAULT 'pending',
    shipping_address   VARCHAR(255),
    delivery_method_id INTEGER REFERENCES delivery_methods(delivery_method_id),
    shipping_cost      NUMERIC(10,2) DEFAULT 0,
    total_amount       NUMERIC(12,2) NOT NULL,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE order_items (
    order_item_id               SERIAL PRIMARY KEY,
    order_id                    INTEGER NOT NULL REFERENCES orders(order_id),
    variant_id                  INTEGER NOT NULL REFERENCES products_variants(variant_id),
    quantity                    INTEGER NOT NULL CHECK (quantity > 0),
    price_at_purchase           NUMERIC(10,2) NOT NULL,
    product_name_at_purchase    VARCHAR(255) NOT NULL,
    variant_details_at_purchase TEXT,
    subtotal_line_item          NUMERIC(12,2) GENERATED ALWAYS AS (quantity * price_at_purchase) STORED
);

-- ---------------- sample data ----------------
INSERT INTO users (first_name, last_name, email, address, city, postal_code, latitude, longitude) VALUES
('Alex',  'Doe',   'alex@example.com',  'Calle de Alcala 100', 'Madrid', '28009', 40.4220, -3.6760),
('Maria', 'Lopez', 'maria@example.com', 'Gran Via 20',         'Madrid', '28013', 40.4200, -3.7030);

INSERT INTO stores (name, address, city, postal_code, latitude, longitude) VALUES
('GenAI Sports Retiro',   'Calle de O''Donnell 10', 'Madrid', '28009', 40.4215, -3.6790),
('GenAI Sports Sol',      'Calle del Carmen 5',     'Madrid', '28013', 40.4175, -3.7040),
('GenAI Sports Chamartin','Paseo de la Castellana 200', 'Madrid', '28046', 40.4630, -3.6890);

INSERT INTO products (name, description, category, brand) VALUES
('Stride Glide 3',  'Lightweight cushioned running shoe for daily training and long distance road running.', 'Running', 'Stridex'),
('Stride Trail X',  'Grippy trail running shoe with rock plate and waterproof upper for muddy trails.',       'Running', 'Stridex'),
('Summit Pack 50',  'Versatile 50L hiking backpack with rain cover, perfect for weekend adventures.',          'Hiking',  'PeakLine'),
('Summit Pack 70',  'Expedition 70L backpack with adjustable suspension for multi-day trips and heavy loads.', 'Hiking',  'PeakLine'),
('Court Pro Racket','Carbon tennis racket with large sweet spot for intermediate players.',                    'Tennis',  'AceCo'),
('Aqua Swim Goggles','Anti-fog swimming goggles with UV protection for pool and open water.',                  'Swimming','WaveRider'),
('Dry Fit Tee',     'Breathable quick-dry t-shirt for running and gym workouts.',                              'Apparel', 'Stridex');

INSERT INTO products_variants (product_id, size, color, price) VALUES
(1, '40', 'Black/White', 119.99), (1, '42', 'Black/White', 119.99), (1, '42', 'Blue', 119.99), (1, '44', 'Blue', 119.99),
(2, '41', 'Green', 139.99), (2, '42', 'Green', 139.99), (2, '43', 'Grey', 139.99),
(3, 'One Size', 'Red', 89.99), (3, 'One Size', 'Black', 89.99),
(4, 'One Size', 'Black', 179.99),
(5, 'Grip 2', 'White', 149.00), (5, 'Grip 3', 'White', 149.00),
(6, 'One Size', 'Clear', 24.50), (6, 'One Size', 'Smoke', 24.50),
(7, 'S', 'Black', 29.99), (7, 'M', 'Black', 29.99), (7, 'L', 'Blue', 29.99);

-- every variant in every store, with some variation in stock
INSERT INTO inventory (variant_id, store_id, quantity)
SELECT v.variant_id, s.store_id, ((v.variant_id * 7 + s.store_id * 3) % 12)
FROM products_variants v CROSS JOIN stores s;

INSERT INTO delivery_methods (store_id, name, description, base_cost, estimated_delivery_time)
SELECT store_id, m.name, m.description, m.cost, m.eta FROM stores CROSS JOIN (VALUES
  ('Standard Home Delivery', 'Delivered to your address by courier.', 4.99, '3-5 business days'),
  ('Express Delivery',       'Priority courier delivery.',            9.99, '1-2 business days'),
  ('Click & Collect',        'Pick up your order in store.',          0.00, 'Ready in 2 hours')
) AS m(name, description, cost, eta);

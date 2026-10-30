-- Tickets database for the software bug assistant (QuantumRoast coffee machine company).
-- Local PostgreSQL version of the reference schema. The reference used Cloud SQL +
-- pgvector embeddings; here search uses PostgreSQL full-text search instead so it runs
-- on a plain local Postgres.

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id     SERIAL PRIMARY KEY,
    title         VARCHAR(255) NOT NULL,
    description   TEXT,
    assignee      VARCHAR(100),
    priority      VARCHAR(50),
    status        VARCHAR(50) DEFAULT 'Open',
    creation_time TIMESTAMPTZ DEFAULT NOW(),
    updated_time  TIMESTAMPTZ DEFAULT NOW(),
    search_doc    tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
    ) STORED
);

CREATE INDEX IF NOT EXISTS tickets_search_idx ON tickets USING GIN (search_doc);

CREATE OR REPLACE FUNCTION touch_updated_time() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_time = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tickets_touch ON tickets;
CREATE TRIGGER tickets_touch BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION touch_updated_time();

INSERT INTO tickets (title, description, assignee, priority, status, creation_time) VALUES
('Login Page Freezes After Multiple Failed Attempts',
 'After 3 failed login attempts the login page stops responding and must be refreshed. No error message is shown.',
 'samuel.green@example.com', 'P0 - Critical', 'Open', NOW() - INTERVAL '10 days'),
('Dashboard Sales Widget Intermittent Data Loading Failure',
 'The Sales Overview widget sometimes shows a spinner and never loads data. Refreshing the page usually fixes it.',
 'maria.rodriguez@example.com', 'P1 - High', 'In Progress', NOW() - INTERVAL '8 days'),
('Broken Link in Footer - Privacy Policy',
 'The Privacy Policy link in the website footer returns a 404 Not Found error.',
 'david.lee@example.com', 'P3 - Low', 'Resolved', NOW() - INTERVAL '20 days'),
('UI Misalignment on Mobile Landscape View (iOS)',
 'On iOS in landscape mode, the navigation menu overlaps the main content area.',
 'maria.rodriguez@example.com', 'P2 - Medium', 'In Progress', NOW() - INTERVAL '6 days'),
('Order Confirmation Email Not Sent',
 'Customers are not receiving order confirmation emails after buying a coffee machine. SMTP logs show timeouts.',
 'samuel.green@example.com', 'P1 - High', 'Open', NOW() - INTERVAL '3 days'),
('Espresso Machine App Crashes on Brew Schedule Save',
 'The mobile companion app crashes with a null pointer exception when saving a brew schedule with no end time.',
 'priya.nair@example.com', 'P1 - High', 'Open', NOW() - INTERVAL '2 days'),
('Firmware Update Fails at 90 Percent',
 'Firmware OTA update for QuantumRoast X2 stops at 90 percent and the machine reboots into the old version.',
 'david.lee@example.com', 'P0 - Critical', 'Open', NOW() - INTERVAL '1 day'),
('Password Reset Link Expires Too Quickly',
 'Password reset links expire after 2 minutes instead of 30 minutes, so users cannot reset their password.',
 'samuel.green@example.com', 'P2 - Medium', 'Open', NOW() - INTERVAL '5 days');

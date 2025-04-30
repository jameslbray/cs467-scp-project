
-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS presence;

-- Create user_status table
CREATE TABLE
    IF NOT EXISTS presence.user_status (
        user_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        last_changed TIMESTAMP NOT NULL DEFAULT NOW (),
        CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users.users (id) -- Reference the users table in users schema
        ON DELETE CASCADE
    );

-- Create connections table
CREATE TABLE
    IF NOT EXISTS presence.connections (
        user_id TEXT NOT NULL,
        connected_user_id TEXT NOT NULL,
        connection_status TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW (),
        PRIMARY KEY (user_id, connected_user_id),
        CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users.users (id) ON DELETE CASCADE,
        CONSTRAINT fk_connected_user_id FOREIGN KEY (connected_user_id) REFERENCES users.users (id) ON DELETE CASCADE
    );

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_status_last_changed ON presence.user_status (last_changed);

CREATE INDEX IF NOT EXISTS idx_connections_status ON presence.connections (connection_status);

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA presence TO CURRENT_USER;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA presence TO CURRENT_USER;
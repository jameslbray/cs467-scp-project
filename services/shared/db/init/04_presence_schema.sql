-- Set search path for this script
SET search_path TO presence, users, public;

-- Create user_status table
CREATE TABLE IF NOT EXISTS presence.user_status (
    user_id UUID PRIMARY KEY,
    status VARCHAR(10) NOT NULL DEFAULT 'offline' CHECK (status IN ('online', 'away', 'offline')),
    last_changed TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE
);

-- Create connections table
CREATE TABLE IF NOT EXISTS presence.connections (
    user_id UUID NOT NULL,
    connected_user_id UUID NOT NULL,
    connection_status TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, connected_user_id),
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_connected_user_id FOREIGN KEY (connected_user_id) REFERENCES users.users(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_status_last_changed ON presence.user_status(last_changed);
CREATE INDEX IF NOT EXISTS idx_connections_status ON presence.connections(connection_status);

-- Grant privileges again to ensure they're set after table creation
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA presence TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA presence TO app_user;
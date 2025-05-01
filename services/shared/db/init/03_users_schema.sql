-- Set search path for this script
SET search_path TO users, public;

-- Create users table
CREATE TABLE IF NOT EXISTS users.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    profile_picture_url VARCHAR(255),
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes - IF NOT EXISTS prevents errors on recreating indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users.users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users.users(email);

-- Create blacklisted_tokens table
CREATE TABLE IF NOT EXISTS users.blacklisted_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token TEXT NOT NULL UNIQUE,
    user_id UUID REFERENCES users.users(id) ON DELETE CASCADE,
    username VARCHAR(255),
    blacklisted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_blacklisted_tokens_token ON users.blacklisted_tokens(token);

-- Grant privileges again to ensure they're set after table creation
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA users TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA users TO app_user;
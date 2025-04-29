-- Create users table
CREATE TABLE
    users (
        id SERIAL PRIMARY KEY,
        email VARCHAR UNIQUE NOT NULL,
        username VARCHAR UNIQUE NOT NULL,
        hashed_password VARCHAR NOT NULL,
        created_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            profile_picture_url VARCHAR(255),
            last_login TIMESTAMP
        WITH
            TIME ZONE
    );

-- Create indexes
CREATE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_username ON users (username);

CREATE INDEX ix_users_id ON users (id);

-- Create user_status table
CREATE TABLE
    user_status (
        user_id INTEGER PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
        status VARCHAR(10) NOT NULL DEFAULT 'offline' CHECK (status IN ('online', 'away', 'offline')),
        last_status_change TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

-- Create blacklisted_tokens table
CREATE TABLE
    blacklisted_tokens (
        id SERIAL PRIMARY KEY,
        token VARCHAR UNIQUE NOT NULL,
        user_id INTEGER REFERENCES users (id),
        username VARCHAR,
        blacklisted_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        WITH
            TIME ZONE
    );

-- Create indexes for blacklisted_tokens
CREATE INDEX ix_blacklisted_tokens_id ON blacklisted_tokens (id);

CREATE INDEX ix_blacklisted_tokens_token ON blacklisted_tokens (token);

-- Insert test user with hashed password (password is 'testpassword')
-- The hash was generated using Argon2 with the same settings as in your security.py
INSERT INTO
    users (
        email,
        username,
        hashed_password,
        profile_picture_url
    )
VALUES
    (
        'test@example.com',
        'test_user',
        '$argon2id$v=19$m=65536,t=3,p=4$GUMIQSjF+L+XslaqVSql1A$YRxMqFsROQsIl0cZjA0zZp7oUZbE7UCqqnGqRgb6c7M',
        'https://example.com/test.jpg'
    );

-- Set initial status for test user
INSERT INTO
    user_status (user_id, status)
VALUES
    (
        (
            SELECT
                id
            FROM
                users
            WHERE
                username = 'test_user'
        ),
        'offline'
    );
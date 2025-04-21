-- Drop tables if they exist (in reverse order of dependency)
-- Using IF EXISTS should prevent errors if tables don't exist yet
DROP TABLE IF EXISTS user_status;
DROP TABLE IF EXISTS users;

-- Create the Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    profile_picture_url VARCHAR(255),
    last_login TIMESTAMP
);

-- Add comment for documentation
COMMENT ON TABLE user_status IS 'Stores the user information, including username, profile picture, and last login time';

-- Create the User_Status table
CREATE TABLE user_status (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE PRIMARY KEY,
    status VARCHAR(10) CHECK (status IN ('online', 'away', 'offline')) NOT NULL DEFAULT 'offline',
    last_status_change TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comment for documentation
COMMENT ON TABLE user_status IS 'Stores the current online status of users and when it was last updated';

-- Drop the connections table if it exists
DROP TABLE IF EXISTS connections;

-- Create the connections table
CREATE TABLE connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    connected_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    connection_status VARCHAR(10) CHECK (connection_status IN ('pending', 'accepted')) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, connected_user_id) -- Prevent duplicate connections
);

-- Add comment for documentation
COMMENT ON TABLE user_status IS 'Stores the connections between users, including the status of the connection and when it was created';
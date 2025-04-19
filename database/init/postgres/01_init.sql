-- Create enum type for status values
CREATE TYPE user_status_type AS ENUM ('online', 'away', 'offline');

-- Create user_status table
CREATE TABLE user_status (
    user_id INTEGER NOT NULL,
    status user_status_type NOT NULL DEFAULT 'offline',
    last_status_change TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Add foreign key constraint
    CONSTRAINT fk_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
        
    -- Make user_id the primary key (one status per user)
    PRIMARY KEY (user_id)
);

-- Create index for faster queries when filtering by status
CREATE INDEX idx_user_status_status ON user_status(status);

-- Add comment for documentation
COMMENT ON TABLE user_status IS 'Stores the current online status of users and when it was last updated';
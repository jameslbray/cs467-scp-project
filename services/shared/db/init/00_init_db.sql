-- This handles both Docker (where database exists) and local setup (where it may not)
DO $$
BEGIN
    -- Only try to create the database if we're connected to a different one
    -- This won't run in Docker because Docker creates the database first
    IF (SELECT current_database()) <> 'sycolibre' THEN
        -- Check if database exists
        IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sycolibre') THEN
            PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE sycolibre');
        END IF;
    END IF;
EXCEPTION
    -- Silently handle errors if dblink is not available
    WHEN OTHERS THEN
        RAISE NOTICE 'Cannot create database automatically. If running locally, please create the database manually.';
END $$;

-- Create extensions - will run in both Docker and local
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "dblink";  -- Added for database creation
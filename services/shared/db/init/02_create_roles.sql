DO $$
BEGIN
    -- Create app_user role if it doesn't exist
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password';
    END IF;
END
$$;

-- Grant necessary permissions - will run in both environments
GRANT ALL PRIVILEGES ON SCHEMA users TO app_user;
GRANT ALL PRIVILEGES ON SCHEMA presence TO app_user;
ALTER ROLE app_user SET search_path TO users, presence, public;

-- This needs to run after tables are created but we'll include it here
-- It will fail silently on first run but succeed on subsequent runs
DO $$
BEGIN
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA users TO app_user;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA presence TO app_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA users TO app_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA presence TO app_user;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not grant privileges on all objects yet. Will try again after they are created.';
END $$;
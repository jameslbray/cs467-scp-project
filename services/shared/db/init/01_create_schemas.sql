-- Try to connect to sycolibre database if we're not already connected to it
DO $$
BEGIN
    IF (SELECT current_database()) <> 'sycolibre' THEN
        -- This only works locally; in Docker we're already connected
        PERFORM dblink_connect('dbname=sycolibre');
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Already connected to the correct database or connection failed.';
END $$;

-- Create application schemas
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS presence;

-- Grant usage to public for referencing 
GRANT USAGE ON SCHEMA users TO PUBLIC;
GRANT USAGE ON SCHEMA presence TO PUBLIC;
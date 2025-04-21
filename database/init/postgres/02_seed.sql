-- Insert example records into the Users table
INSERT INTO users (username, created_at, updated_at, profile_picture_url, last_login)
VALUES 
    ('michael_shaffer', '2025-01-15 08:30:00', '2025-01-15 08:30:00', './assets/default_profile.png', '2025-04-19 14:25:00'),
    ('james_bray', '2025-01-16 10:15:00', '2025-01-16 10:15:00', './assets/default_profile.png', '2025-04-20 09:15:00'),
    ('charles_holz', '2025-01-17 14:45:00', '2025-01-17 14:45:00', './assets/default_profile.png', '2025-04-18 18:30:00'),
    ('nicholas_laustrup', '2025-01-18 12:20:00', '2025-01-18 12:20:00', './assets/default_profile.png', '2025-04-19 20:45:00');


-- Insert records into the User_Status table
INSERT INTO user_status (user_id, status, last_status_change)
VALUES 
    (1, 'online', '2025-04-19 14:25:00'),
    (2, 'online', '2025-04-20 09:15:00'),
    (3, 'away', '2025-04-18 19:45:00'),
    (4, 'offline', '2025-04-19 21:30:00');

-- Insert sample connection records
-- Assuming we're using the four users we created earlier
INSERT INTO connections (user_id, connected_user_id, connection_status, created_at)
VALUES 
    -- Michael and James are connected
    (1, 2, 'accepted', '2025-02-15 10:30:00'),
    
    -- Michael and Charles are connected
    (1, 3, 'accepted', '2025-02-16 14:20:00'),
    
    -- Michael and Nicholas have a pending connection (Michael sent request)
    (1, 4, 'pending', '2025-04-18 09:45:00'),
    
    -- James and Charles are connected
    (2, 3, 'accepted', '2025-03-10 16:15:00'),
    
    -- James and Nicholas are connected
    (2, 4, 'accepted', '2025-03-12 11:30:00'),
    
    -- Charles sent a pending connection request to Nicholas
    (3, 4, 'pending', '2025-04-19 15:20:00');
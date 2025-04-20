-- Insert example records into the Users table
INSERT INTO users (username, created_at, updated_at, profile_picture_url, last_login)
VALUES 
    ('michael_shaffer', '2025-01-15 08:30:00', '2025-01-15 08:30:00', 'https://sycolibre.com/profiles/michael.jpg', '2025-04-19 14:25:00'),
    ('james_bray', '2025-01-16 10:15:00', '2025-01-16 10:15:00', 'https://sycolibre.com/profiles/james.jpg', '2025-04-20 09:15:00'),
    ('charles_holz', '2025-01-17 14:45:00', '2025-01-17 14:45:00', 'https://sycolibre.com/profiles/charles.jpg', '2025-04-18 18:30:00'),
    ('nicholas_laustrup', '2025-01-18 12:20:00', '2025-01-18 12:20:00', 'https://sycolibre.com/profiles/nicholas.jpg', '2025-04-19 20:45:00');


-- Insert records into the User_Status table
INSERT INTO user_status (user_id, status, last_status_change)
VALUES 
    (1, 'online', '2025-04-19 14:25:00'),
    (2, 'online', '2025-04-20 09:15:00'),
    (3, 'away', '2025-04-18 19:45:00'),
    (4, 'offline', '2025-04-19 21:30:00');
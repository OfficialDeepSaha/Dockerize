-- Insert test roles if they don't exist
INSERT INTO user_onboarding_roles (name, description)
VALUES 
    ('s2 admin', 'S2 Administrator'),
    ('railway admin', 'Railway Administrator'),
    ('war room user', 'User responsible for handling complaints in war room')
ON CONFLICT DO NOTHING;

-- Get role IDs
DO $$
DECLARE
    s2_admin_id INTEGER;
    railway_admin_id INTEGER;
    war_room_id INTEGER;
BEGIN
    SELECT id INTO s2_admin_id FROM user_onboarding_roles WHERE name = 's2 admin';
    SELECT id INTO railway_admin_id FROM user_onboarding_roles WHERE name = 'railway admin';
    SELECT id INTO war_room_id FROM user_onboarding_roles WHERE name = 'war room user';

    -- Insert test users
    -- S2 Admin
    INSERT INTO user_onboarding_user (username, email, full_name, mobile_number, user_type_id)
    VALUES ('s2admin', 'deepsaha01896@gmail.com', 'S2 Admin User', '9876543210', s2_admin_id);

    -- Railway Admin
    INSERT INTO user_onboarding_user (username, email, full_name, mobile_number, user_type_id)
    VALUES ('railadmin', 'hiremeasadeveloper@gmail.com', 'Railway Admin User', '9876543211', railway_admin_id);

    -- War Room Users with different depots
    INSERT INTO user_onboarding_user (username, email, full_name, mobile_number, user_type_id, depot, train_number)
    VALUES 
        ('warroom1', 'warroom1@example.com', 'War Room User 1', '9876543212', war_room_id, 'NDLS', '12345'),
        ('warroom2', 'warroom2@example.com', 'War Room User 2', '9876543213', war_room_id, 'NDLS', '12346'),
        ('warroom3', 'warroom3@example.com', 'War Room User 3', '9876543214', war_room_id, 'HWH', '12347');
END $$;

-- Insert train access for war room users
DO $$
DECLARE
    user_id INTEGER;
BEGIN
    -- For user with train number 12345
    SELECT id INTO user_id FROM user_onboarding_user WHERE username = 'warroom1';
    INSERT INTO trains_trainaccess (user_id, train_details)
    VALUES (user_id, '{"trains": ["12345", "12346"]}');

    -- For user with train number 12346
    SELECT id INTO user_id FROM user_onboarding_user WHERE username = 'warroom2';
    INSERT INTO trains_trainaccess (user_id, train_details)
    VALUES (user_id, '{"trains": ["12346", "12347"]}');

    -- For user with train number 12347
    SELECT id INTO user_id FROM user_onboarding_user WHERE username = 'warroom3';
    INSERT INTO trains_trainaccess (user_id, train_details)
    VALUES (user_id, '{"trains": ["12347", "12348"]}');
END $$;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables
CREATE TABLE IF NOT EXISTS rail_sathi_complain (
    complain_id SERIAL PRIMARY KEY,
    pnr_number VARCHAR(20),
    is_pnr_validated VARCHAR(20) DEFAULT 'not-attempted',
    name VARCHAR(255),
    mobile_number VARCHAR(15),
    complain_type VARCHAR(50),
    complain_description TEXT,
    complain_date DATE,
    complain_status VARCHAR(20) DEFAULT 'pending',
    train_id INTEGER,
    train_number VARCHAR(10),
    train_name VARCHAR(255),
    train_no INTEGER,
    train_depot VARCHAR(255),
    coach VARCHAR(10),
    berth_no INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS rail_sathi_complain_media (
    id SERIAL PRIMARY KEY,
    complain_id INTEGER REFERENCES rail_sathi_complain(complain_id) ON DELETE CASCADE,
    media_type VARCHAR(50),
    media_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

-- Create trains_traindetails table
CREATE TABLE IF NOT EXISTS trains_traindetails (
    id SERIAL PRIMARY KEY,
    train_no INTEGER,
    train_name VARCHAR(255),
    "Depot" VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user onboarding tables
CREATE TABLE IF NOT EXISTS user_onboarding_roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Now this will work:
INSERT INTO user_onboarding_roles (name, description)
VALUES ('war room user', 'User responsible for handling complaints in war room')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS user_onboarding_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(255),
    mobile_number VARCHAR(15),
    user_type_id INTEGER REFERENCES user_onboarding_roles(id),
    depot VARCHAR(100),
    train_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default role
INSERT INTO user_onboarding_roles (name, description)
VALUES ('war room user', 'User responsible for handling complaints in war room')
ON CONFLICT (name) DO NOTHING;

-- Create trains_trainaccess table
CREATE TABLE IF NOT EXISTS trains_trainaccess (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_onboarding_user(id) ON DELETE CASCADE,
    train_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_complain_mobile ON rail_sathi_complain(mobile_number);
CREATE INDEX IF NOT EXISTS idx_complain_date ON rail_sathi_complain(complain_date);
CREATE INDEX IF NOT EXISTS idx_complain_status ON rail_sathi_complain(complain_status);
CREATE INDEX IF NOT EXISTS idx_media_complain_id ON rail_sathi_complain_media(complain_id);
CREATE INDEX IF NOT EXISTS idx_train_no ON trains_traindetails(train_no);
CREATE INDEX IF NOT EXISTS idx_user_role ON user_onboarding_user(user_type_id);
CREATE INDEX IF NOT EXISTS idx_user_depot ON user_onboarding_user(depot);
CREATE INDEX IF NOT EXISTS idx_user_train ON user_onboarding_user(train_number);
CREATE INDEX IF NOT EXISTS idx_trainaccess_user ON trains_trainaccess(user_id);

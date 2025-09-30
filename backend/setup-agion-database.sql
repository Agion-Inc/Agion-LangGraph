-- BP-Chat Database Setup Script for Agion PostgreSQL
-- Run this script on your existing Agion PostgreSQL server

-- Create the database (run as admin user)
CREATE DATABASE bpchat_db;

-- Create a dedicated user for BP-Chat
CREATE USER bpchat_user WITH ENCRYPTED PASSWORD 'CHANGE_ME_TO_SECURE_PASSWORD';

-- Grant all privileges on the database to the user
GRANT ALL PRIVILEGES ON DATABASE bpchat_db TO bpchat_user;

-- Connect to the new database
\c bpchat_db;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- For encryption functions (optional)

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO bpchat_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bpchat_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bpchat_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO bpchat_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO bpchat_user;

-- Create a read-only user for monitoring/analytics (optional)
CREATE USER bpchat_readonly WITH ENCRYPTED PASSWORD 'CHANGE_ME_TO_READONLY_PASSWORD';
GRANT CONNECT ON DATABASE bpchat_db TO bpchat_readonly;
GRANT USAGE ON SCHEMA public TO bpchat_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bpchat_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bpchat_readonly;

-- Verify the setup
\du bpchat_user
\du bpchat_readonly

-- Show database info
\l bpchat_db

-- Connection test query
SELECT 
    current_database() as database,
    current_user as user,
    version() as postgres_version,
    pg_database_size(current_database()) as database_size;

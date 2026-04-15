-- TamilScholar Pro – PostgreSQL Initialization
-- Create application database
CREATE DATABASE tamilscholar;

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for full-text search
-- (Tables created by SQLAlchemy on startup)

#!/bin/bash
# .env.sh - Bash-compatible environment variables

# Environment
export ENV="development"
export DEBUG="True"
export LOG_LEVEL="info"

# Database (PostgreSQL)
export PG_USER="sahdude"
export PG_PASSWORD="CS467"
export PG_HOST="209.46.124.94"
export PG_DATABASE="postgres"
export PG_PORT="5432"
export DATABASE_URL="postgresql://sahdude:CS467@209.46.124.94:5432/postgres"

# JWT Auth
export JWT_SECRET_KEY="vJtHdzrVdmwOqkKXEoZ3iCNhOUl9een1Kvaq+SFHmrs"
export JWT_ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES="60"

# CORS - properly quoted for JSON
export CORS_ORIGINS='["http://localhost:3000"]'

# Constructed URLs
export RABBITMQ_URL="amqp://guest:guest@localhost:5672"
export USERS_QUEUE="users_tasks"

# Presence Service Database Configuration
export PRESENCE_POSTGRES_USER="sahdude"
export PRESENCE_POSTGRES_PASSWORD="CS467"
export PRESENCE_POSTGRES_HOST="209.46.124.94"
export PRESENCE_POSTGRES_PORT="5432"
export PRESENCE_POSTGRES_DB="postgres"
export PRESENCE_DATABASE_URL="postgresql://sahdude:CS467@209.46.124.94:5432/postgres"

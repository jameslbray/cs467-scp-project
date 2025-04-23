# User Service

This service handles user registration and authentication using FastAPI and PostgreSQL.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

## Setup

1. Create a PostgreSQL database:
```sql
CREATE DATABASE users_db;
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

5. Update the `.env` file with your PostgreSQL credentials and other settings.

6. Run the application:
```bash
uvicorn app.main:app --reload
```

The service will be available at `http://localhost:8000`

## API Endpoints

- `POST /register` - Register a new user
- `POST /token` - Login and get access token
- `GET /users/me` - Get current user information

## Database Schema

The service uses PostgreSQL with the following main tables:

- `users` - Stores user information
  - id (Primary Key)
  - email (Unique)
  - username (Unique)
  - hashed_password
  - created_at
  - updated_at

## Security

- Passwords are hashed using bcrypt
- JWT tokens are used for authentication
- All sensitive data is stored securely in PostgreSQL 
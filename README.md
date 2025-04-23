# SCP Project Microservices Architecture

This repository contains a collection of microservices that power the SCP Project application. The architecture is designed around separate services that communicate with each other to provide a scalable and maintainable system.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Service Management](#service-management)
   - [Using Direct Execution](#using-direct-execution)
   - [Using Supervisor](#using-supervisor)
5. [Development Workflow](#development-workflow)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

## Architecture Overview

The application is divided into the following microservices:

| Service | Port | Description |
|---------|------|-------------|
| socket-io | 8000 | WebSocket service that handles real-time communication |
| chat | 8001 | Chat service that manages messaging between users |
| auth | 8002 | Authentication service that handles user login/registration |
| notifications | 8003 | Notifications service that manages user notifications |
| presence | 8004 | Presence service that tracks user online status |
| users | 8005 | User management service that handles user profiles |

Each service is implemented as a FastAPI application that communicates with other services through HTTP/WebSocket APIs.

## Prerequisites

- Python 3.9+
- Virtual environment (venv)
- Gunicorn
- Uvicorn
- Supervisor (optional, for production)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/cs467-scp-project.git
   cd cs467-scp-project
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install additional dependencies for production:
   ```bash
   pip install gunicorn supervisor
   ```

## Service Management

The project includes a service management script (`manage_services.sh`) that provides a convenient way to start, stop, and check the status of all services.

### Using Direct Execution

This mode runs each service directly without using Supervisor.

```bash
# Show available commands
./manage_services.sh

# Start all services
./manage_services.sh --direct start-all

# Start a specific service
./manage_services.sh --direct start socket-io

# Check status of all services
./manage_services.sh --direct status

# Stop a specific service
./manage_services.sh --direct stop chat

# Stop all services
./manage_services.sh --direct stop-all
```

### Using Supervisor

Supervisor provides process management for production environments.

```bash
# Start all services with supervisor
./manage_services.sh --supervisor start-all

# Check status
./manage_services.sh --supervisor status

# Stop all services
./manage_services.sh --supervisor stop-all
```

To start supervisor manually:

```bash
supervisord -c supervisor/supervisord.conf
```

To control services with supervisorctl:

```bash
supervisorctl -c supervisor/supervisord.conf status
supervisorctl -c supervisor/supervisord.conf start socket-io
supervisorctl -c supervisor/supervisord.conf stop chat
supervisorctl -c supervisor/supervisord.conf restart presence
supervisorctl -c supervisor/supervisord.conf start scp-project:*  # All services
```

## Development Workflow

During development, you can run each service individually:

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Start a specific service with hot-reloading:
   ```bash
   cd services/chat
   uvicorn app.main:app --reload --port 8001
   ```

3. For testing API endpoints, each service provides a Swagger UI at `/docs`:
   - http://localhost:8001/docs (Chat service)
   - http://localhost:8002/docs (Auth service)
   - etc.

## Production Deployment

For production deployment, consider the following:

1. Set up appropriate environment variables for each service
2. Configure proper logging
3. Use Supervisor for process management
4. Set up a reverse proxy (Nginx/Apache) in front of the services
5. Configure SSL/TLS for secure communication

### Sample Nginx Configuration

```nginx
# Socket.IO Service
server {
    listen 80;
    server_name socket.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}

# API Gateway for other services
server {
    listen 80;
    server_name api.example.com;

    # Auth Service
    location /auth/ {
        proxy_pass http://localhost:8002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Chat Service
    location /chat/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Add other services as needed
}
```

### Docker Deployment

For containerized deployment, consider using Docker Compose:

1. Create a Dockerfile for each service
2. Set up a docker-compose.yml file
3. Configure networking between containers
4. Set up data persistence for databases

## Troubleshooting

### Common Issues

#### Service won't start

- Check if the port is already in use:
  ```bash
  lsof -i :<port>
  ```

- Verify virtual environment is activated:
  ```bash
  which python  # Should point to your venv
  ```

- Check service logs:
  ```bash
  cat logs/<service-name>.log
  ```

#### Supervisor issues

- Check supervisor logs:
  ```bash
  cat logs/supervisord.log
  ```

- Restart supervisor:
  ```bash
  supervisorctl -c supervisor/supervisord.conf shutdown
  supervisord -c supervisor/supervisord.conf
  ```

#### Import errors

If you encounter import errors like `ModuleNotFoundError`, ensure:
- The PYTHONPATH includes the project root
- All `__init__.py` files are in place
- Your imports use the correct module structure

### Service-Specific Issues

#### Socket.IO Service

- WebSocket connections require specific proxy settings if behind Nginx/Apache
- Only use 1 worker process for WebSocket service

#### Database Connectivity

- Verify MongoDB/PostgreSQL connection strings
- Check database service is running
- Ensure database credentials are correct

### Getting More Help

- Check service logs in the `logs/` directory
- Review FastAPI documentation at https://fastapi.tiangolo.com/
- For supervisor issues, see https://supervisord.org/

# SycoLibre: Open-Source Synchronous Communication Platform

## 📝 Project Overview

SycoLibre is an open-source web-based synchronous communication platform similar to Slack/Discord, designed to be customizable for organizations, groups, and individuals. This platform addresses limitations in existing solutions by providing:

- A reliable and efficient open-source communication alternative
- Customizable features that can be adapted to specific needs
- Transparency in how user data is processed
- A balance between simplicity and robust functionality

## ✨ Key Features

- **Real-time Communication**: Send and receive messages instantly
- **User Authentication**: Register, login, and logout securely
- **Direct Messaging**: Private communication between users
- **Notification System**: Alerts for new messages and mentions
- **Member List**: View available users for communication
- **Status Indicators**: See who's online, away, or offline
- **Emoji Support**: Express yourself beyond plain text

## 🏗️ Project Architecture
```
sycolibre/
│
├── client/                 # React frontend
│   ├── public/             # Static assets
│   ├── src/                # React components and logic
│   │   ├── components/     # UI components
│   │   ├── contexts/       # React contexts
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   └── App.jsx         # Main application
│   ├── package.json        # Dependencies and scripts
│   └── vite.config.js      # Vite configuration
│
├── services/               # Backend services
│   ├── chat/               # Chat service with integrated socket server
│   │   ├── app/            # Application package
│   │   │   ├── core/       # Core components
│   │   │   │   ├── socket_service.py  # Socket.IO server implementation
│   │   │   │   └── config.py         # Configuration 
│   │   │   ├── db/         # Database models and connections
│   │   │   └── main.py     # Application entry point
│   │   └── tests/          # Test suite
│   └── presence/           # User presence service
│
├── fastapi-backend/        # Python FastAPI backend
│   ├── app/                # Application package
│   │   ├── main.py         # FastAPI application
│   │   ├── routes/         # API endpoints
│   │   ├── models/         # Data models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment variables template
│
├── .gitignore              # Git ignore file
├── README.md               # This file
└── docker-compose.yml      # Container configuration
```

## 🚀 Getting Started

### Prerequisites

- Node.js (v16+)
- Python 3.8+
- MongoDB
- PostgreSQL
- RabbitMQ

### Setup Instructions

#### 1. Clone the repository

```bash
git clone https://github.com/jameslbray/cs467-scp-project.git
cd sycolibre
```

#### 2. Setup the Frontend

```bash
cd client
npm install
npm run dev
```
#### 3. Setup the Chat Service (with integrated Socket.IO Server)

```bash
cd services/chat
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 3001
```

#### 4. Setup the FastAPI Backend

```bash
cd fastapi-backend
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 5. Database Configuration

MongoDB Connection:

`mongodb://username:password@host:27017/scp-db`

You can use MongoDB Compass for connecting to the database.

PostgreSQL Setup:

__Install PostgreSQL adapter for Node.js__

`npm install pg`

Configure your PostgreSQL connection in the appropriate configuration files.


## 💻 Technology Stack
- **Frontend:** React, Vite, Redux Toolkit, ChakraUI
- **Backend:** FastAPI, Python, Socket.io
- **Databases:** PostgreSQL (relational data), MongoDB (messages)
- **Message Queue:** RabbitMQ
- **Authentication:** JWT, OAuth 2.0

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request after our initial project is complete, turned in, and a grade has been issued.

## 📄 License

This project is licensed under the AGPL3.0 License - see the LICENSE file for details.
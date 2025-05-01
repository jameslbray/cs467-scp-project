# SCP Project Microservices Architecture

This repository contains a collection of microservices that power the SCP Project application. The architecture is designed around separate services that communicate with each other to provide a scalable and maintainable system.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Service Management](#service-management)
   - [Using run_service.sh](#using-run_service.sh)
5. [Development Workflow](#development-workflow)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

## Architecture Overview

The application is divided into the following microservices:

- **PostgreSQL Database**: Central data storage with separate schemas for different services
- **RabbitMQ**: Message broker for inter-service communication and event-driven architecture
- **Socket.IO Server**: Real-time WebSocket communication with clients
- **User Service**: Handles authentication, registration, and user profile management
- **Presence Service**: Tracks user online status and availability
- **Chat Service**: Manages message delivery and storage
- **Notifications Service**: Processes and delivers system notifications
- **Frontend**: React-based client application

Each service is implemented as a FastAPI application that communicates with other services through HTTP/WebSocket APIs.

## Prerequisites

- Python 3.12+
- Virtual environment (venv)
- Gunicorn
- Uvicorn
- Supervisor (optional, for production)
- Docker
- Docker Compose

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/cs467-scp-project.git
   cd cs467-scp-project
   ```
2. Create a `.env` file with the following variables:
  ```
  ENV=development
  DEBUG=True
  LOG_LEVEL=INFO
  JWT_SECRET_KEY=3a11374cd633b1d251e5c4cc40c81e81d43357f1b6d6e0f96f94c33a4cc0439d
  JWT_ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=60
  CORS_ORIGINS=["http://localhost:5173"]
  
  USERS_QUEUE=users_tasks
  
  POSTGRES_DB=sycolibre
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=postgres
  POSTGRES_HOST=postgres_db
  POSTGRES_PORT=5432
  DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/sycolibre
  
  RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
  RABBITMQ_HOST=localhost
  RABBITMQ_PORT=5672
  RABBITMQ_USER=guest
  RABBITMQ_PASSWORD=guest
  RABBITMQ_VHOST=/
  
  SOCKET_IO_PORT=8000
  USERS_PORT=8001
  NOTIFICATIONS_PORT=8002
  PRESENCE_PORT=8003
  CHAT_PORT=8004
  FRONTEND_PORT=5173
  ```

3. Start the services:
  ```
  docker-compose up -d
      ```


## Using docker-compose

Docker compose also allows you to run individual services. Just specify the name of the service(s) you want to run.
```
docker-compose up -d notifications
docker-compose up -d presence chat socket_io
docker-compose up -d frontend
```

## Production Deployment

For production deployment, consider the following:

1. Set up appropriate environment variables for each service
2. Configure proper logging
3. Configure SSL/TLS for secure communication


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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request after our initial project is complete, turned in, and a grade has been issued.

## License

This project is licensed under the AGPL3.0 License - see the LICENSE file for details.
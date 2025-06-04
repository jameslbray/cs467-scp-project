# SycoLibre Microservices Architecture

This repository contains a set of microservices powering SycoLibre. Each service is isolated, communicates via HTTP/WebSocket APIs and RabbitMQ, and is orchestrated using Docker Compose for easy local development and deployment.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Microservices Overview](#microservices-overview)
3. [Prerequisites](#prerequisites)
4. [Setup & Installation](#setup--installation)
5. [Service Management](#service-management)
6. [Development Workflow](#development-workflow)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)
9. [Contributing](#contributing)
10. [License](#license)

---

## Project Structure

```shell
cs467-scp-project/
  frontend/           # React client app
  services/
    chat/             # Chat microservice (FastAPI)
    connections/      # Connection management
    db_init/          # DB initialization scripts/utilities
    notifications/    # Notifications microservice (FastAPI)
    presence/         # Presence microservice (FastAPI)
    rabbitmq/         # RabbitMQ configuration
    shared/           # Shared utilities
    socket_io/        # Real-time WebSocket server (FastAPI + Socket.IO)
    users/            # User management microservice (FastAPI)_
  tests/              # End-to-end and integration tests
  docker-compose.yml  # Multi-service orchestration
  .env                # Environment variables
  requirements.txt    # Python dependencies
  ...
```

---

## Microservices Overview

- **PostgreSQL**: Central database, with schemas for each service.
- **RabbitMQ**: Message broker for inter-service communication.
- **Socket.IO**: Real-time WebSocket server for client communication.
- **User Service**: Authentication, registration, and user profiles.
- **Presence Service**: Tracks user online/offline status.
- **Chat Service**: Message delivery and storage.
- **Notifications Service**: System notification delivery.
- **Frontend**: React-based client application.

All backend services are implemented with FastAPI and communicate via HTTP, WebSocket, and RabbitMQ.

---

## Prerequisites

- Docker & Docker Compose
- (For local development outside Docker) Python 3.12+, Node.js 18+, npm

---

## Setup & Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/cs467-scp-project.git
   cd cs467-scp-project
   ```

2. **Configure environment variables:**
   - Create `.env` file at the root of the project, then copy the contents of `.env.example` to it.

   ```bash
   cp .env.example .env
   ```

   - Fill in the values for the environment variables with your own values.

3. **Install Node Modules:**

   ```bash
   cd frontend
   npm install
   ```

4. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

5. **Build all services:**

   ```bash
   docker compose build
   ```

---

## Service Management

- **Start all services:**

  ```bash
  docker compose up -d
  ```

- **Start specific service(s):**

  ```bash
  docker compose up -d users notifications
  ```

- **Stop all services:**

  ```bash
  docker compose down
  ```

- **View logs:**

  ```bash
  docker compose logs -f <service-name>
  ```

- **Rebuild a service:**

  ```bash
  docker compose build <service-name>
  docker compose up -d <service-name>
  ```

---

## Development Workflow

- **Backend:**
  Each microservice is a FastAPI app in `services/<service>/app/`.
  For local development, you can run a service outside Docker by activating a Python venv and using Uvicorn.

- **Frontend:**
  The React app is in `frontend/`.
  For local development:

  ```bash
  cd frontend
  npm install
  npm run dev
  ```

## Production Deployment

- Set production-ready environment variables in `.env`.
- Configure logging and monitoring.
- Use a production-grade WSGI server (e.g., Gunicorn) for FastAPI services.
- Set up SSL/TLS termination (e.g., via Nginx or a cloud provider).
- Scale services as needed using Docker Compose or Kubernetes.

---

## Troubleshooting

- **Service won't start:**
  - Check if the port is in use: `lsof -i :<port>`
  - Check logs: `docker-compose logs <service-name>`
  - Ensure `.env` is correctly configured.
  - Remove node_modules and run `npm install` again.

- **Database issues:**
  - Ensure PostgreSQL is running and accessible.
  - Verify credentials and connection strings.

- **Import errors (Python):**
  - Ensure all `__init__.py` files exist.
  - Use absolute imports based on the service's root.

- **WebSocket issues:**
  - If behind a proxy, ensure correct WebSocket forwarding.
  - Use a single worker for the Socket.IO service.

---

## Contributing

Contributions are welcome after the initial project submission and grading. Please open a pull request with a clear description of your changes.

---

## License

This project is licensed under the AGPL-3.0 License. See the [LICENSE](LICENSE) file for details.

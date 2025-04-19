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
├── socket-server/          # Socket.IO Node.js server
│   ├── index.js            # Server entry point
│   ├── handlers/           # Socket event handlers
│   ├── services/           # Business logic
│   └── package.json        # Dependencies and scripts
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

#### 3. Setup the Socket.IO Server

```bash
cd socket-server
npm install
npm run dev
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
- **Backend:** FastAPI, Node.js, Socket.io
- **Databases:** PostgreSQL (relational data), MongoDB (messages)
- **Message Queue:** RabbitMQ
- **Authentication:** JWT, OAuth 2.0

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request after our initial project is complete, turned in, and a grade has been issued.

## 📄 License

This project is licensed under the AGPL3.0 License - see the LICENSE file for details.
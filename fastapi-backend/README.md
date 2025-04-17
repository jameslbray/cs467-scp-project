# FastAPI with Socket.IO Integration

This project demonstrates how to integrate Socket.IO with FastAPI using python-socketio and python-engineio.

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn
- python-socketio
- python-engineio

## Installation

1. Install the required packages:

```bash
pip install fastapi uvicorn python-socketio python-engineio
```

## Running the Application

1. Start the server:

```bash
python main.py
```

2. Open the `client_test.html` file in your browser, or serve it using a simple HTTP server:

```bash
python -m http.server 8080
```

Then navigate to `http://localhost:8080/client_test.html`

## Testing the Application

1. The FastAPI endpoints can be accessed at:
   - http://localhost:8000/ - Main endpoint
   - http://localhost:8000/health - Health check endpoint
   - http://localhost:8000/docs - Swagger documentation

2. The Socket.IO connection can be tested using the provided client test HTML file.

## Notes

- The Socket.IO server is configured to accept connections from any origin with `cors_allowed_origins='*'`. In production, you should restrict this to specific origins.
- This example uses the ASGI mode of Socket.IO which is compatible with FastAPI.


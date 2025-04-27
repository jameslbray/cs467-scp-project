# Socket.IO Service

This service provides a centralized Socket.IO server for real-time communication between services in the application.

## Features

- Centralized Socket.IO server for all services
- Standardized event schema for service-to-service communication
- Service connector for easy integration with other services
- Support for rooms, broadcasting, and direct messaging
- HTTP API fallback for services that can't connect directly

## Architecture

The Socket.IO service consists of the following components:

1. **Socket.IO Server**: The main server that handles WebSocket connections and events
2. **Event Schema**: Standardized event types and payload structures
3. **Service Connector**: Client library for services to connect to the Socket.IO server
4. **HTTP API**: REST API for services that can't connect directly via WebSocket

## Getting Started

### Running the Service

```bash
# Start the Socket.IO service
./run_server.sh
```

### Environment Variables

- `SOCKET_IO_PORT`: Port to run the Socket.IO server on (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

## Using the Service Connector

The Service Connector provides a simple way for other services to connect to the Socket.IO service.

### Example: Chat Service

```python
from services.socket_io.app.core.service_connector import ServiceConnector
from services.socket_io.app.core.event_schema import EventType, Event

# Initialize the connector
connector = ServiceConnector("chat", "http://localhost:8000")
await connector.initialize()

# Register event handlers
async def handle_message(event: Event):
    print(f"Received message: {event['content']}")

connector.on_event(EventType.CHAT_MESSAGE, handle_message)

# Send a message
await connector.emit_to_user(
    "user123",
    EventType.CHAT_MESSAGE,
    sender_id="user456",
    recipient_id="user123",
    message_id="msg789",
    content="Hello, world!"
)

# Shutdown the connector
await connector.shutdown()
```

## Event Schema

Events follow a standardized schema:

```python
{
    "type": "event:type",  # e.g., "chat:message"
    "timestamp": 1234567890.123,
    "source": "service_name",
    # Event-specific data
    "user_id": "user123",
    "data": {...}
}
```

### Standard Event Types

- `user:connected`: User connected to the system
- `user:disconnected`: User disconnected from the system
- `user:status_changed`: User status changed
- `chat:message`: Chat message sent
- `chat:typing`: User typing status
- `chat:read`: Message read receipt
- `presence:update`: User presence update
- `presence:query`: Query user presence
- `notification`: System notification
- `system:error`: System error
- `system:info`: System information

## HTTP API

The Socket.IO service also provides a REST API for services that can't connect directly via WebSocket.

### Endpoints

- `POST /api/emit_to_client`: Emit an event to a specific client
- `POST /api/broadcast`: Broadcast an event to all clients
- `POST /api/join_room`: Join a room
- `POST /api/leave_room`: Leave a room
- `POST /api/emit_to_room`: Emit an event to all clients in a room
- `GET /api/rooms`: Get all rooms and their clients

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 
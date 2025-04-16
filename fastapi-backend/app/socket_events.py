def register_socketio_events(sio):
    @sio.event
    async def connect(sid, environ):
        print(f"Client connected: {sid}")

    @sio.event
    async def disconnect(sid):
        print(f"Client disconnected: {sid}")

    @sio.event
    async def message(sid, data):
        print(f"Received message from {sid}: {data}")
        await sio.emit('response', {'data': 'Message received!'}, to=sid)

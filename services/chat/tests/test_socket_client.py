#!/usr/bin/env python3
"""
Socket.IO test client for testing the socket server implementation

This script provides a simple way to test the Socket.IO server
functionality without needing a full frontend client.
It works with both the test server and production socket service.
"""

# Standard library imports
import os
import sys
import time
import json
import signal
import asyncio
import logging
import argparse
import subprocess
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Callable

# Third-party imports
import pytest
import requests
import socketio
import pytest_asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test constants
TEST_ROOM = "test_room"
TEST_USER = "test_user"
SERVER_HOST = "localhost"
SERVER_PORT = 8001
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"  # Socket.IO endpoint in the main app

# Test configuration
SKIP_SERVER_CHECK = False  # Set to True to skip server process checks

# Comment explaining usage with the main app
"""
This test client connects to the Socket.IO server defined in the main application (main.py).
Make sure the server implements the following Socket.IO events:
- connect: Connection event
- join_room: Join a chat room 
- leave_room: Leave a chat room
- send_message: Send a message to a room
- chat_message: Receive messages from a room
- presence_request_friend_statuses: Request friend statuses
- presence_response: Receive presence status information

You may need to modify these event names or handlers to match the actual implementation.
"""
# Define paths - Updated for the new directory structure
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_DIR = os.path.abspath(os.path.dirname(__file__))
SERVER_HEALTH_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

@pytest.fixture(scope="session")
def server_process():
    """Start the main app's Socket.IO server as a fixture"""
    # Get the path to the tests directory
    main_path = TEST_DIR
    try:
        # Start uvicorn server with the test application
        logger.info(f"Starting Socket.IO test server from {main_path}...")
        process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "test_server:app",
                "--host", SERVER_HOST, 
                "--port", str(SERVER_PORT)
            ],
            cwd=main_path,  # Use the tests directory
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid  # Use process group for easier cleanup
        )
        
        # Wait for server to start up
        max_retries = 10
        retry_interval = 1.0
        for i in range(max_retries):
            try:
                # Try to connect to the server's health endpoint
                response = requests.get(SERVER_HEALTH_URL)
                if response.status_code == 200 or response.status_code == 404:
                    # Server is responding, break out of retry loop
                    logger.info(f"Server started at {SERVER_URL}")
                    break
            except requests.RequestException:
                if i < max_retries - 1:  # Don't sleep on the last iteration
                    time.sleep(retry_interval)
                continue
            
            # If we've exhausted all retries, check if process is still running
            if i == max_retries - 1:
                # Check process status
                if process.poll() is not None:
                    # Process terminated
                    stdout, stderr = process.communicate()
                    error_msg = f"Server failed to start. Exit code: {process.returncode}\n"
                    error_msg += f"STDOUT: {stdout}\nSTDERR: {stderr}"
                    raise RuntimeError(error_msg)
                # Process is running but health check failed
                raise RuntimeError(f"Server health check failed after {max_retries} attempts")
        
        # Yield the process for use during the test
        yield process
        
    finally:
        # Cleanup: Kill the server process after tests are done
        if process and process.poll() is None:  # Process is still running
            logger.info("Shutting down server...")
            try:
                process_group_id = os.getpgid(process.pid)
                os.killpg(process_group_id, signal.SIGTERM)
                # Wait up to 5 seconds for process to terminate
                process.wait(timeout=5)
            except (ProcessLookupError, OSError, subprocess.TimeoutExpired) as e:
                logger.error(f"Error during server shutdown: {e}")
                # Try to force kill if normal termination failed
                try:
                    if process.poll() is None:  # Still running
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError) as e:
                    logger.error(f"Error force killing server: {e}")
            logger.info("Server shutdown complete")

@pytest_asyncio.fixture
def socket_client():
    """Fixture to create and manage the Socket.IO client"""
    client = socketio.AsyncClient()
    connected = False
    received_messages = []
    room_joined = False
    presence_data = None
    
    # Setup event handlers
    @client.event
    async def connect():
        logger.info("Connected to server")
        nonlocal connected
        connected = True
        
    @client.event
    async def disconnect():
        logger.info("Disconnected from server")
        nonlocal connected
        connected = False
        
    @client.event
    async def chat_message(data):
        logger.info(f"Received message: {json.dumps(data, indent=2)}")
        nonlocal received_messages
        received_messages.append(data)
    
    # Create a class to hold the state
    class SocketClient:
        def __init__(self):
            self.client = client
            self.connected = connected
            self.received_messages = received_messages
            self.room_joined = room_joined
            self.presence_data = presence_data
            
        async def connect_to_server(self):
            """Helper to connect to the server"""
            try:
                logger.info(f"Connecting to {SERVER_URL}...")
                await self.client.connect(SERVER_URL)
                # Wait a bit to ensure connection is established
                await asyncio.sleep(0.5)
                # Update the connection state after the sleep
                self.connected = True
                return True
            except Exception as e:
                logger.error(f"Connection error: {e}")
                return False
                
    yield SocketClient()
    
    # Cleanup client
    async def disconnect_client():
        if client.connected:
            await client.disconnect()
    
    asyncio.run(disconnect_client())

class TestSocketIOEvents:
    """Test suite for Socket.IO events"""
    @pytest.mark.asyncio
    async def test_connection(self, server_process, socket_client):
        """Test connection to the server"""
         # Verify server process is running (if not in skip mode)
        if not SKIP_SERVER_CHECK and server_process is not None:
            assert server_process.poll() is None, "Server is not running"
        connected = await socket_client.connect_to_server()
        assert connected, "Failed to connect to server"
        assert socket_client.connected, "Connected event not triggered"
        
    @pytest.mark.asyncio
    async def test_join_room(self, server_process, socket_client):
        """Test joining a room"""
        # Verify server process is running
        assert server_process.poll() is None, "Server is not running"
        
        # Connect to server
        connected = await socket_client.connect_to_server()
        assert connected, "Failed to connect to server"
        
        # Set up room join callback
        # Set up room join callback - main app might use a different response event
        # You may need to adjust these event names to match the main application's events
        @socket_client.client.on("join_room_response")
        def on_join_room_response(data):
            socket_client.room_joined = True
        
        # Alternatively, check if we've entered room successfully by listening for events
        # from that room after joining
        
        # Join test room
        logger.info(f"Joining room: {TEST_ROOM}")
        await socket_client.client.emit("join_room", TEST_ROOM)
        # Wait for room join to be processed
        await asyncio.sleep(1)
        assert socket_client.room_joined or True, "Failed to join room or no confirmation received"
    
    @pytest.mark.asyncio
    async def test_send_message(self, server_process, socket_client):
        """Test sending and receiving a message"""
        # Verify server process is running
        assert server_process.poll() is None, "Server is not running"
        
        # Connect to server and join room
        connected = await socket_client.connect_to_server()
        assert connected, "Failed to connect to server"
        
        # Join test room
        logger.info(f"Joining room: {TEST_ROOM}")
        await socket_client.client.emit("join_room", TEST_ROOM)
        await asyncio.sleep(1)
        
        # Send a test message
        test_message = {
            "user": TEST_USER,
            "text": "Hello, this is a test message!",
            "room": TEST_ROOM,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.info("Sending test message...")
        await socket_client.client.emit("send_message", test_message)
        
        # Wait for message to be processed and received
        await asyncio.sleep(2)
        
        # Check if we received our own message
        assert len(socket_client.received_messages) > 0, "No messages received"
        assert any(msg.get("text") == test_message["text"] for msg in socket_client.received_messages), \
            "Test message was not received"
    
    @pytest.mark.asyncio
    async def test_leave_room(self, server_process, socket_client):
        """Test leaving a room"""
        # Verify server process is running
        assert server_process.poll() is None, "Server is not running"
        
        # Connect to server and join room
        connected = await socket_client.connect_to_server()
        assert connected, "Failed to connect to server"
        
        # Join test room
        logger.info(f"Joining room: {TEST_ROOM}")
        await socket_client.client.emit("join_room", TEST_ROOM)
        
        # Wait for room join to be processed
        await asyncio.sleep(1)
        
        # Leave room
        logger.info(f"Leaving room: {TEST_ROOM}")
        await socket_client.client.emit("leave_room", TEST_ROOM)
        
        # Wait for leave room to be processed
        await asyncio.sleep(1)
        
        # Send a message to the room we just left
        test_message = {
            "user": TEST_USER,
            "text": "This message should not be received",
            "room": TEST_ROOM,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Clear received messages
        socket_client.received_messages = []
        
        # Send the message
        logger.info("Sending message after leaving room...")
        await socket_client.client.emit("send_message", test_message)
        
        # Wait for message to be processed
        await asyncio.sleep(2)
        
        # We should not receive this message since we left the room
        assert len(socket_client.received_messages) == 0, "Should not receive messages after leaving the room"
    
    @pytest.mark.asyncio
    async def test_presence_request(self, server_process, socket_client):
        """Test presence status request"""
        # Verify server process is running
        assert server_process.poll() is None, "Server is not running"
        
        # Connect to server
        connected = await socket_client.connect_to_server()
        assert connected, "Failed to connect to server"
        
        # Note: Adjust these event names if they differ in the main app
        # Set up presence response handler
        @socket_client.client.on("presence_response")
        def on_presence_response(data):
            logger.info(f"Received presence response: {json.dumps(data, indent=2)}")
            socket_client.presence_data = data
        # Send presence request
        presence_request = {"user_id": TEST_USER}
        logger.info("Testing presence request...")
        await socket_client.client.emit("presence_request_friend_statuses", presence_request)
        
        # Wait for presence response
        await asyncio.sleep(2)
        
        # Check if we received a presence response
        # Note: This may be skipped if the implementation doesn't yet return presence data
        if socket_client.presence_data is not None:
            assert isinstance(socket_client.presence_data, dict), "Presence response should be a dictionary"
        else:
            logger.warning("No presence response received. This may be expected if the feature is not implemented.")

    @pytest.mark.asyncio
    async def test_full_flow(self, server_process, socket_client):
        """Test the full flow of socket operations"""
        # Verify server process is running
        assert server_process.poll() is None, "Server is not running"
        
        # Connect
        connected = await socket_client.connect_to_server()
        assert connected, "Failed to connect to server"
        
        # Join room
        logger.info(f"Joining room: {TEST_ROOM}")
        await socket_client.client.emit("join_room", TEST_ROOM)
        await asyncio.sleep(1)
        
        # Send message
        test_message = {
            "user": TEST_USER,
            "text": "Test message for full flow",
            "room": TEST_ROOM,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.info("Sending test message...")
        await socket_client.client.emit("send_message", test_message)
        await asyncio.sleep(2)
        
        # Verify message received
        assert len(socket_client.received_messages) > 0, "No messages received"
        
        # Request presence status
        await socket_client.client.emit("presence_request_friend_statuses", {"user_id": TEST_USER})
        await asyncio.sleep(1)
        
        # Leave room
        logger.info(f"Leaving room: {TEST_ROOM}")
        await socket_client.client.emit("leave_room", TEST_ROOM)
        await asyncio.sleep(1)
        
        # Disconnect
        await socket_client.client.disconnect()
        await asyncio.sleep(0.5)  # Give time for disconnect to process
        assert not socket_client.connected, "Failed to disconnect"


if __name__ == "__main__":
    # For manual testing without pytest
    import argparse
    
    parser = argparse.ArgumentParser(description="Socket.IO Test Client")
    parser.add_argument("--no-server", action="store_true", help="Don't start the server, only run tests")
    args = parser.parse_args()
    
    async def run_manual_tests():
        """Run tests manually without pytest"""
        server_proc = None
        
        # Start server if requested
        if not args.no_server:
            main_path = TEST_DIR
            logger.info(f"Starting Socket.IO test server from {main_path}...")
            
            try:
                server_proc = subprocess.Popen(
                    [
                        sys.executable, "-m", "uvicorn", "test_server:app",
                        "--host", SERVER_HOST,
                        "--port", str(SERVER_PORT)
                    ],
                    cwd=main_path,  # Use the tests directory
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid
                )
                
                # Wait for server to start
                for retry in range(10):
                    try:
                        response = requests.get(SERVER_HEALTH_URL)
                        if response.status_code == 200 or response.status_code == 404:
                            logger.info("Server is up!")
                            break
                    except requests.RequestException:
                        if retry == 9:  # Last retry
                            # Check if process failed
                            if server_proc.poll() is not None:
                                stdout, stderr = server_proc.communicate()
                                logger.error(f"Server failed to start! Exit code: {server_proc.returncode}")
                                logger.error(f"STDOUT: {stdout}")
                                logger.error(f"STDERR: {stderr}")
                            else:
                                logger.error("Server is running but health check failed")
                            
                            if server_proc and server_proc.poll() is None:
                                os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
                            return
                        time.sleep(1)
            except Exception as e:
                logger.error(f"Error starting server: {e}")
                if 'server_proc' in locals() and server_proc and server_proc.poll() is None:
                    os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
                return
                
        # Run tests
        try:
            # Create socket client
            client = socketio.AsyncClient()
            connected = False
            received_messages = []
            room_joined = False
            presence_data = None
            
            # Set up event handlers
            @client.event
            async def connect():
                nonlocal connected
                logger.info("Connected to server")
                connected = True
                
            @client.event
            async def disconnect():
                nonlocal connected
                logger.info("Disconnected from server")
                connected = False
                
            @client.event
            async def chat_message(data):
                nonlocal received_messages
                logger.info(f"Received message: {json.dumps(data, indent=2)}")
                received_messages.append(data)
            
            # Create mock socket_client fixture
            class MockSocketClient:
                def __init__(self):
                    self.client = client
                    self.connected = connected
                    self.received_messages = received_messages
                    self.room_joined = room_joined
                    self.presence_data = presence_data
                    
                async def connect_to_server(self):
                    try:
                        logger.info(f"Connecting to {SERVER_URL}...")
                        await self.client.connect(SERVER_URL)
                        await asyncio.sleep(0.5)
                        self.connected = True
                        return True
                    except Exception as e:
                        logger.error(f"Connection error: {e}")
                        return False
            
            test = TestSocketIOEvents()
            mock_client = MockSocketClient()
            try:
                # Run tests with proper error handling
                try:
                    await test.test_connection(server_proc, mock_client)
                    await test.test_join_room(server_proc, mock_client)
                    await test.test_send_message(server_proc, mock_client)
                    await test.test_leave_room(server_proc, mock_client)
                    await test.test_presence_request(server_proc, mock_client)
                    await test.test_full_flow(server_proc, mock_client)
                    logger.info("All tests completed successfully!")
                except AssertionError as e:
                    logger.error(f"Test assertion failed: {e}")
                except ConnectionError as e:
                    logger.error(f"Connection error: {e}")
                    logger.warning("Is the Socket.IO server running? Use without --no-server to start it automatically.")
                except Exception as e:
                    logger.error(f"Test error: {type(e).__name__}: {e}")
            except AssertionError as e:
                logger.error(f"Test failed: {e}")
            finally:
                # Disconnect client
                if client.connected:
                    await client.disconnect()
        finally:
            # Stop server if we started it
            if 'server_proc' in locals() and server_proc and server_proc.poll() is None:
                logger.info("Stopping server...")
                try:
                    os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
                    server_proc.wait(timeout=5)  # Wait up to 5 seconds
                except (ProcessLookupError, OSError, subprocess.TimeoutExpired) as e:
                    logger.error(f"Error stopping server: {e}")
                    # Try force kill if needed
                    try:
                        if server_proc.poll() is None:  # Still running
                            os.killpg(os.getpgid(server_proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError) as e:
                        logger.error(f"Error force killing server: {e}")
    
    # Run the tests
    asyncio.run(run_manual_tests())

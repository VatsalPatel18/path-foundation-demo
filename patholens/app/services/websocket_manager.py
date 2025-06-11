from fastapi import WebSocket
from typing import Dict, List

class WebSocketManager:
    def __init__(self):
        # A dictionary to hold active connections, keyed by session_id
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accepts a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str):
        """Closes a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"WebSocket disconnected for session: {session_id}")

    async def send_json(self, message: dict, session_id: str):
        """Sends a JSON message to a specific client."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

    async def broadcast_json(self, message: dict):
        """Sends a JSON message to all connected clients."""
        for session_id, connection in self.active_connections.items():
            await connection.send_json(message)

# Create a single instance to be used throughout the application
websocket_manager = WebSocketManager()

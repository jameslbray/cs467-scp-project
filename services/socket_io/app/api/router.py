"""
API router module for handling routing to microservices.
"""

import logging
import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

# Configure logging
logger = logging.getLogger(__name__)

# Service registry - maps service names to their URLs
SERVICE_REGISTRY = {
    "users": "http://users:8001",
    "chat": "http://chat:8001",
    "notifications": "http://notifications:8004",
    "presence": "http://presence:8000",
}


class ServiceRouter:
    """Handles routing of API requests to appropriate microservices."""

    def __init__(self):
        """Initialize the API router."""
        self.router = APIRouter()
        self.client = httpx.AsyncClient()
        self._setup_routes()

    def _setup_routes(self):
        """Set up API routes."""
        @self.router.api_route(
            "/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        async def route_request(request: Request, path: str):
            """Route the request to the appropriate microservice."""
            # Extract service name from path (e.g., /api/users/... -> users)
            service_name = path.split("/")[0]

            if service_name not in SERVICE_REGISTRY:
                return Response(
                    content=f"Service {service_name} not found",
                    status_code=404
                )

            # Get the target service URL
            target_url = SERVICE_REGISTRY[service_name]

            # Construct the full target URL
            full_url = f"{target_url}/{path}"

            # Get the request body
            body = await request.body()

            # Forward the request
            try:
                response = await self.client.request(
                    method=request.method,
                    url=full_url,
                    headers=dict(request.headers),
                    content=body,
                    follow_redirects=True
                )

                # Return the response
                return StreamingResponse(
                    response.aiter_raw(),
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except Exception as e:
                logger.error(
                    f"Error routing request to {service_name}: {str(e)}")
                return Response(
                    content=f"Error routing request to {service_name}",
                    status_code=500
                )

    async def shutdown(self):
        """Cleanup resources."""
        await self.client.aclose()

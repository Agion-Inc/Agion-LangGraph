"""
Rate Limiting Middleware for Agent-Chat
Protects API endpoints from abuse
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Tuple


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent API abuse"""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        
        # Track requests by IP
        self.minute_requests: Dict[str, list] = defaultdict(list)
        self.hour_requests: Dict[str, list] = defaultdict(list)
        
        # Start cleanup task
        asyncio.create_task(self.cleanup_old_requests())
    
    async def cleanup_old_requests(self):
        """Cleanup old request records periodically"""
        while True:
            await asyncio.sleep(60)  # Run every minute
            now = datetime.now()
            
            # Cleanup minute requests
            for ip in list(self.minute_requests.keys()):
                self.minute_requests[ip] = [
                    req_time for req_time in self.minute_requests[ip]
                    if now - req_time < timedelta(minutes=1)
                ]
                if not self.minute_requests[ip]:
                    del self.minute_requests[ip]
            
            # Cleanup hour requests
            for ip in list(self.hour_requests.keys()):
                self.hour_requests[ip] = [
                    req_time for req_time in self.hour_requests[ip]
                    if now - req_time < timedelta(hours=1)
                ]
                if not self.hour_requests[ip]:
                    del self.hour_requests[ip]
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limits and process request"""
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/api/v1/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        client_ip = self.get_client_ip(request)
        now = datetime.now()
        
        # Check minute rate limit
        minute_ago = now - timedelta(minutes=1)
        self.minute_requests[client_ip] = [
            req_time for req_time in self.minute_requests[client_ip]
            if req_time > minute_ago
        ]
        
        if len(self.minute_requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Too many requests per minute.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Check hourly rate limit
        hour_ago = now - timedelta(hours=1)
        self.hour_requests[client_ip] = [
            req_time for req_time in self.hour_requests[client_ip]
            if req_time > hour_ago
        ]
        
        if len(self.hour_requests[client_ip]) >= self.requests_per_hour:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Too many requests per hour.",
                    "retry_after": 3600
                },
                headers={"Retry-After": "3600"}
            )
        
        # Check burst limit (requests in last 10 seconds)
        ten_seconds_ago = now - timedelta(seconds=10)
        recent_requests = [
            req_time for req_time in self.minute_requests[client_ip]
            if req_time > ten_seconds_ago
        ]
        
        if len(recent_requests) >= self.burst_size:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Too many requests in a short time.",
                    "retry_after": 10
                },
                headers={"Retry-After": "10"}
            )
        
        # Record this request
        self.minute_requests[client_ip].append(now)
        self.hour_requests[client_ip].append(now)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            self.requests_per_minute - len(self.minute_requests[client_ip])
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            self.requests_per_hour - len(self.hour_requests[client_ip])
        )
        
        return response

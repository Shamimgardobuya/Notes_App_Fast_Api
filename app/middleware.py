import logging
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

logger  = logging.getLogger("request_logger")
    
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request:Request, call_next):
        start_time = time.time()
        #loggin request details
        logger.info(f"Request: {request.method} {request.url} from {request.client.host}")
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(f"Response: {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:4f}s")
        
        return response

 
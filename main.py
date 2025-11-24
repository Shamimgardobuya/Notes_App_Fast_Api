from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import notes
from app.middleware import LoggingMiddleware
from app.config.logging import setup_logger
from app.config.database import  redis_client
from fastapi_limiter import FastAPILimiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup...")
    
    # Logging initialized once at startup
    setup_logger()  
    
    # Initialize redis for rate limiting
    await FastAPILimiter.init(redis_client)
    print("✅ Rate limiter initialized")

    yield

    print("Application shutdown...")
    await redis_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(notes.router, prefix="/api/v1/notes")
app.add_middleware(LoggingMiddleware)

# main.py

from fastapi import FastAPI
import uvicorn
from app.database import engine, Base
from contextlib import asynccontextmanager
from app.routes.authRoutes import authRoute
from app.routes.fileRoutes import file_router
import logging

logger = logging.getLogger(__name__)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database created successfully")
    except Exception as e:
        logger.error(f"Error initializing DB: {str(e)}")
        raise

async def close_db():
    try:
        await engine.dispose()
        print("Database disposed successfully")
    except Exception as e:
        logger.error(f"Error closing DB: {str(e)}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(lifespan=lifespan)
app.include_router(authRoute)
app.include_router(file_router)

@app.get("/")
def root():
    return {"message": "backend is online"}

def main():
    uvicorn.run("app.main:app", host="localhost", port=8000, reload=True)

if __name__ == "__main__":
    main()

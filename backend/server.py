from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import os
import logging
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from db import db, client
import auth
import routers

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("matchipy")

app = FastAPI(title="Matchipy API")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Matchipy API", "status": "ok"}


api_router.include_router(auth.router)
api_router.include_router(routers.router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000"),
                   "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    await db.cvs.create_index("user_id")
    await db.jobs.create_index("user_id")
    await db.sessions.create_index("user_id")
    await db.applications.create_index("user_id")
    await auth.seed_admin()
    logger.info("Matchipy startup complete")


@app.on_event("shutdown")
async def shutdown():
    client.close()

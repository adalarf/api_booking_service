from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from auth.utils import clean_revoked_tokens
from auth.router import router as auth_router
from user_profile.router import router as profile_router
from events.router import router as events_router
from database import async_session_maker


app = FastAPI()

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(events_router)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin",
                   "Authorization"],
)

app.mount("/media", StaticFiles(directory="media"), name="media")


@app.on_event("startup")
async def on_startup():
    async with async_session_maker() as db:
        await clean_revoked_tokens(db)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.auth.utils import clean_revoked_tokens
from src.auth.router import router as auth_router
from src.user_profile.router import router as profile_router
from src.events.utils import schedule_jobs
from src.events.router import router as events_router
from src.teams.router import router as teams_router
from src.database import async_session_maker
from fastapi.openapi.utils import get_openapi
import uvicorn


app = FastAPI()

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(events_router)
app.include_router(teams_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your API",
        version="1.0.0",
        description="API for event management",
        routes=app.routes,
    )
    
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"Bearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT", "HEAD"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin",
                   "Authorization", "Content-Length"],
)

# app.mount("/media", StaticFiles(directory="media"), name="media")


@app.on_event("startup")
async def on_startup():
    async with async_session_maker() as db:
        await clean_revoked_tokens(db)
    
    await schedule_jobs()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

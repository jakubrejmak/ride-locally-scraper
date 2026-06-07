import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ride_locally.api.routes.auth import router as auth
from ride_locally.api.routes.targets import router as targets
from ride_locally.config import config

app = FastAPI()
app.include_router(auth)
app.include_router(targets)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.API_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def main() -> None:
    uvicorn.run(
        "ride_locally.api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.API_RELOAD,
    )


if __name__ == "__main__":
    main()

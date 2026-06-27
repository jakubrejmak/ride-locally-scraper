import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from ride_locally.api.routes.auth import router as auth
from ride_locally.api.routes.list_dirs import (
    router as list_scripts_directory,
)
from ride_locally.api.routes.targets import router as targets
from ride_locally.config import config

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(auth)
app.include_router(targets)
app.include_router(list_scripts_directory)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


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

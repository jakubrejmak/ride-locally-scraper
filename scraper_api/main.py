import uvicorn
from fastapi import FastAPI
from routes.auth import router as auth
from routes.targets import router as targets

from conf import config

app = FastAPI()
app.include_router(auth)
app.include_router(targets)


def main() -> None:
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.API_RELOAD,
    )


if __name__ == "__main__":
    main()

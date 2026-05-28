import uvicorn
from fastapi import FastAPI
from routes.targets import router as targets

app = FastAPI()
app.include_router(targets)


def main() -> None:
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()

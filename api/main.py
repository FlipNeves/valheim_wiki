import uvicorn
from fastapi import FastAPI
from api.endpoints import router
from core import config

app = FastAPI(title="Scrappy Wiki RAG API", version="2.0.0")

config.ensure_dirs()

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

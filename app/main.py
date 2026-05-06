from fastapi import FastAPI
from app.routes.owner_manual import router as owner_manual_router

app = FastAPI()

app.include_router(owner_manual_router)

@app.get("/")
def health():
    return {"status": "running"}
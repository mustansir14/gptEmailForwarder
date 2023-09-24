from fastapi import FastAPI, Request, HTTPException
from db import update_or_create_config, get_config_from_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"])


@app.get("/")
async def get_config():
    config = get_config_from_db()
    if not config:
        raise HTTPException(status_code=404, detail="No config found")
    return config.config_json


@app.post("/")
async def update_config(request: Request):
    try:
        config_json = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Bad Request")
    if config_json == {}:
        raise HTTPException(status_code=400, detail="Bad Request")
    update_or_create_config(config_json)
    return {"status": "ok"}

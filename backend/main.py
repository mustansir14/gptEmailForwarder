from fastapi import FastAPI, Request
from db import update_or_create_config

app = FastAPI()


@app.post("/")
async def update_config(request: Request):
    try:
        config_json = await request.json()
    except:
        return
    if config_json == {}:
        return
    update_or_create_config(config_json)
    return {"status": "ok"}

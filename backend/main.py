from fastapi import FastAPI, Request, HTTPException
from db import update_or_create_config

app = FastAPI()


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

from typing import Union
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def read_root():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Welcome"}
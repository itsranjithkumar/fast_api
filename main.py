from fastapi import FastAPI, BackgroundTasks
import httpx
import asyncio

app = FastAPI()

# Function to call the '/' endpoint
async def call_root_endpoint():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://fast-api-10yx.onrender.com/")
        print(response.json())  # Prints the response to the console

# Background job to call the root endpoint every 10 minutes
async def background_task():
    while True:
        await call_root_endpoint()
        await asyncio.sleep(600)  # 600 seconds = 10 minutes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_task())  # Start background task on app startup

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

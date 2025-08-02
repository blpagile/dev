from fastapi.testclient import TestClient
from fastapi import FastAPI
import inspect
import httpx

app = FastAPI()
client = TestClient(app)

print(inspect.signature(httpx.Client.__init__))


app = FastAPI() 

@app.get("/")
def read_root():
    return {"Hello": "World"}

client = TestClient(app)
print(client.get("/").json())

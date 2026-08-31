from fastapi import FastAPI

app = FastAPI(title="Fenato Business Automation API")

@app.get("/")
def root():
    return {"status": "running"}
from fastapi import FastAPI

app = FastAPI(title="Microservice", version="1.0.0")

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "healthy"}

@app.get("/")
def root():
    return {"message": "Service is running on DevForge"}

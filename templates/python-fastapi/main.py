from fastapi import FastAPI

app = FastAPI(title="{{APPLICATION_NAME}}", version="{{VERSION}}")

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "{{APPLICATION_NAME}}"}

@app.get("/")
def root():
    return {"message": "Service {{APPLICATION_NAME}} is running on DevForge"}

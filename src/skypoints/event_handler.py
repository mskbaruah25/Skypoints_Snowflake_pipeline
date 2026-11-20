"""HTTP receiver scaffold. Never acknowledges an unimplemented ingestion action."""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="SkyPoints notification receiver", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str | bool]:
    """Report process liveness separately from unfinished ingestion readiness."""
    return {"status": "scaffold", "ready_for_ingestion": False}


@app.post("/events/minio")
def minio_event() -> None:
    raise HTTPException(status_code=503, detail="Notification ingestion is not implemented yet.")

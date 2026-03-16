from fastapi import FastAPI

import app.models  # noqa: F401
from app.core.logging import configure_logging
from app.core.exceptions import register_exception_handlers
from app.database import Base, engine
from app.routes.document_routes import router as document_router


configure_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Legal Document Manager",
    version="1.0.0",
    description="Backend service for legal document versioning, diffing, and notifications.",
)

register_exception_handlers(app)
app.include_router(document_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

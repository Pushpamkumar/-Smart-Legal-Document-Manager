from fastapi import FastAPI

import app.models  # noqa: F401
from app.core.logging import configure_logging
from app.core.exceptions import register_exception_handlers
from app.database import Base, engine
from app.routes.document_routes import router as document_router


configure_logging()


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    application = FastAPI(
        title="Smart Legal Document Manager",
        version="1.0.0",
        description="Backend service for legal document versioning, diffing, and notifications.",
    )

    register_exception_handlers(application)
    application.include_router(document_router)

    @application.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()

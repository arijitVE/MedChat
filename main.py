from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Import all models so SQLAlchemy Base.metadata is populated before create_all
from shared.db.models import case, extraction, user  # noqa: F401
from shared.db.session import init_db

# Auto-create tables on startup (dev convenience — use Alembic for prod migrations)
init_db()

from product.api.auth_routes import router as auth_router
from product.api.case_routes import router as case_router
from product.api.user_routes import router as user_router

app = FastAPI(
    title="DocuMed-AI API",
    description="AI-powered Medical Documentation System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(case_router)
app.include_router(user_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

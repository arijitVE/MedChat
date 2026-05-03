from pathlib import Path
import sys

from fastapi import FastAPI


PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from pipeline_a.api.routes import router as pipeline_a_router
from pipeline_b.api.doctor_routes import router as doctor_router
from pipeline_b.api.patient_routes import router as patient_router


app = FastAPI(
    title="HDMIS API",
    description="Healthcare Document Management & Intelligence System",
    version="0.1.0",
)

app.include_router(pipeline_a_router)
app.include_router(doctor_router)
app.include_router(patient_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

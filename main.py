from dotenv import load_dotenv
load_dotenv()

import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "/Users/arijitkarmakar/Desktop/vision-key.json"
)

from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from pipeline_a.api.routes import router as pipeline_a_router
from pipeline_b.api.doctor_routes import router as doctor_router
from pipeline_b.api.patient_routes import router as patient_router
from product.api.auth_routes import router as auth_router
from product.api.admin_routes import router as product_admin_router
from product.api.doctor_routes import router as product_doctor_router
from product.api.patient_routes import router as product_patient_router


app = FastAPI(
    title="HDMIS API",
    description="Healthcare Document Management & Intelligence System",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_a_router)
app.include_router(auth_router)
app.include_router(product_admin_router)
app.include_router(product_doctor_router)
app.include_router(product_patient_router)
app.include_router(doctor_router)
app.include_router(patient_router)

app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")


@app.get("/health")
def health_check():
    return {"status": "ok"}

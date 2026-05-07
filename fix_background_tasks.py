"""
Run this to verify your upload_service.py is using FastAPI BackgroundTasks
and NOT Celery. If it uses Celery and you don't have Redis running,
every upload will fail silently.
"""
import os

upload_service_path = "product/services/upload_service.py"
if not os.path.exists(upload_service_path):
    print("❌ upload_service.py not found")
    exit(1)

src = open(upload_service_path).read()

if "celery" in src.lower():
    print("❌ CELERY FOUND — uploads will fail without Redis")
    print("   Tell your agent: Replace Celery with FastAPI BackgroundTasks")
elif "BackgroundTasks" in src or "background_tasks" in src:
    print("✅ BackgroundTasks in use — uploads will work")
elif "asyncio" in src:
    print("✅ asyncio in use — uploads will work")
else:
    print("⚠️  Cannot determine async strategy — check upload_service.py manually")
    
# Also check if on_pipeline_a_complete is defined
if "on_pipeline_a_complete" in src:
    print("✅ on_pipeline_a_complete hook defined")
else:
    print("❌ on_pipeline_a_complete not found — lifecycle_status will never update after Pipeline A")

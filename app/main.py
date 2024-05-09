from uuid import UUID
from pathlib import Path

from datetime import datetime
from celery.result import AsyncResult
from fastapi import FastAPI, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.worker import predict_image

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

TEMP_FOLDER = Path("tmp")
PHOTO_CONTENT_TYPES = ["image/png", "image/jpeg"]


@app.post("/check_photo", status_code=201)
@limiter.limit("5/minute")
def check_photo(request: Request, image: UploadFile):
    if image.content_type not in PHOTO_CONTENT_TYPES or image.content_type is None:
        return Response(status_code=422)

    image_path = save_file(image, image.content_type)
    task = predict_image.delay(str(image_path))
    return JSONResponse({"task_id": task.id})


def save_file(image: UploadFile, content_type: str) -> Path:
    filename = image.filename or generate_name(content_type)
    image_path = TEMP_FOLDER / filename
    with open(image_path, "wb") as f:
        f.write(image.file.read())
    return image_path


def generate_name(content_type: str):
    extension = content_type.split("/")[1]
    return f"{UUID()}.{extension}"


@app.get("/check_photo/{task_id}")
@limiter.limit("5/minute")
def get_photo(request: Request, task_id: str):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result,
    }
    return JSONResponse(result)


@app.get("/model_status")
def check_model_status():
    try:
        sample_image_path = "tests/assets/test.jpg"
        predict = predict_image.delay(sample_image_path).get()
        return {
            "model_status": "OK",
            "last_checked": datetime.now().isoformat(),
            "prediction": predict,
        }
    except Exception as e:
        return {
            "model_status": "Error",
            "error_message": str(e),
            "last_checked": datetime.now().isoformat(),
        }


@app.get("/ping")
def pong():
    return {"ping": "pong"}

from pathlib import Path
from uuid import UUID

from celery.result import AsyncResult
from fastapi import FastAPI, Response, UploadFile
from fastapi.responses import JSONResponse

from app.worker import create_task

app = FastAPI()

TEMP_FOLDER = Path("tmp")
PHOTO_CONTENT_TYPES = ["image/png", "image/jpeg"]


@app.post("/check_photo", status_code=201)
def check_photo(image: UploadFile):
    if image.content_type not in PHOTO_CONTENT_TYPES or image.content_type is None:
        return Response(status_code=422)

    image_path = save_file(image, image.content_type)
    task = create_task.delay(str(image_path))
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
def get_photo(task_id: str):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result,
    }
    return JSONResponse(result)


@app.get("/ping")
def pong():
    return {"ping": "pong"}

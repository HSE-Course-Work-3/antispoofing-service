from pathlib import Path
from uuid import UUID
from datetime import datetime

from celery.result import AsyncResult
from fastapi import FastAPI, Response, UploadFile
from fastapi.responses import JSONResponse

from app.worker import create_task, predict_image
from app.neural_network import get_prediction

app = FastAPI()

TEMP_FOLDER = Path("tmp")
PHOTO_CONTENT_TYPES = ["image/png", "image/jpeg"]


@app.post("/check_photo", status_code=201)
def check_photo(image: UploadFile):
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
def get_photo(task_id: str):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result,
    }
    return JSONResponse(result)


# @app.get("/model_status")
# def check_model_status():
#     try:
#         sample_image_path = "tests/assets/test.jpg"
#         predict = get_prediction(str(sample_image_path), model)
#         return {"model_status": "OK", "last_checked": datetime.now().isoformat(), "prediction": predict}
#     except Exception as e:
#         return {"model_status": "Error", "error_message": str(e), "last_checked": datetime.now().isoformat()}


@app.get("/ping")
def pong():
    return {"ping": "pong"}

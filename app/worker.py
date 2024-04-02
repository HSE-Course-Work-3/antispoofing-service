import os
import time

from celery import Celery
from celery.utils.time import random

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

celery = Celery(__name__, broker=BROKER_URL, backend=RESULT_BACKEND)


@celery.task(name="create_task")
def create_task(image_path: str):
    prediction = predict(image_path)
    os.remove(image_path)
    return prediction, image_path


def predict(image: str) -> dict[str, float]:
    time.sleep(2)
    return {
        "param1": random.random(),
        "param2": random.random(),
        "param3": random.random(),
        "param4": random.random(),
    }

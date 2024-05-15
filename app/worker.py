import logging
import os
from dataclasses import dataclass
from typing import Literal

import requests
import torch
from albumentations import CenterCrop, Compose, Normalize, PadIfNeeded
from albumentations.pytorch.transforms import ToTensorV2
from celery import Celery, Task
from datasouls_antispoof.class_mapping import class_mapping
from iglovikov_helper_functions.utils.image_utils import load_rgb

from app.neural_network import create_model, get_prediction

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

celery = Celery(__name__, broker=BROKER_URL, backend=RESULT_BACKEND)


@dataclass
class BotUserInfo:
    bot_token: str
    user_id: int
    reply_message: int
    image_path: str


class PredictTask(Task):
    """
    Abstraction of Celery's Task class to support loading ML model.
    """

    abstract = True

    def __init__(self):
        super().__init__()
        self.model_efficient_net = None
        self.model_resnet = None

    def __call__(self, *args, **kwargs):
        """
        Load model on first call (i.e. first task processed)
        Avoids the need to load model on each task request
        """
        if not self.model_efficient_net:
            logging.info("Loading Efficient Model...")
            self.model_efficient_net = load_model("tf_efficientnet_b3_ns")
            logging.info("Model Efficient loaded")

        if not self.model_resnet:
            logging.info("Loading Resnet Model...")
            self.model_resnet = load_model("swsl_resnext50_32x4d")
            logging.info("Model Resnet loaded")

        return self.run(*args, **kwargs)

    def predict(
        self,
        image_path: str,
        model_name: Literal["efficient_net", "resnet"] = "efficient_net",
    ):
        match model_name:
            case "efficient_net":
                model = self.model_efficient_net
            case "resnet":
                model = self.model_resnet
            case _:
                raise Exception("No such model with name", model_name)

        return get_prediction(image_path, model)


def load_model(model_name: str):
    nn_model = create_model(model_name)
    nn_model = nn_model.eval()
    return nn_model


@celery.task(
    ignore_result=False,
    bind=True,
    base=PredictTask,
)
def predict_image(
    self: PredictTask,
    image_path: str,
    selected_model: Literal["efficient_net", "resnet"] = "efficient_net",
):
    """
    Essentially the run method of PredictTask
    """
    prediction = self.predict(image_path, selected_model)
    os.remove(image_path)
    return prediction


@celery.task(
    ignore_result=False,
    bind=True,
    base=PredictTask,
)
def predict_image_for_bot(
    self: PredictTask,
    bot_token: str,
    user_id: int,
    reply_message: int,
    image_path: str,
    selected_model: Literal["efficient_net", "resnet"] = "efficient_net",
):
    """
    Essentially the run method of PredictTask
    """
    prediction = self.predict(image_path, selected_model)
    os.remove(image_path)

    prediction_result = f"Результат: {prediction}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={user_id}&text={prediction_result}&reply_to_message_id={reply_message}"
    requests.get(url)


def predict(image: str, model) -> dict[str, float]:
    return get_prediction(image, model)

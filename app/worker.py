import os
import importlib
import logging
from celery import Task

from celery import Celery
from app.neural_network import get_prediction
from datasouls_antispoof.pre_trained_models import create_model

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

celery = Celery(__name__, broker=BROKER_URL, backend=RESULT_BACKEND)


def load_model():
    nn_model = create_model("tf_efficientnet_b3_ns")
    nn_model = nn_model.eval()
    return nn_model


model = load_model()


@celery.task(name="create_task")
def create_task(image_path: str):
    prediction = predict(image_path)
    os.remove(image_path)
    return prediction, image_path


def predict(image: str) -> dict[str, float]:
    return get_prediction(image, model)


class PredictTask(Task):
    """
    Abstraction of Celery's Task class to support loading ML model.
    """
    abstract = True

    def __init__(self):
        super().__init__()
        self.model = None

    def __call__(self, *args, **kwargs):
        """
        Load model on first call (i.e. first task processed)
        Avoids the need to load model on each task request
        """
        if not self.model:
            logging.info('Loading Model...')
            self.model = load_model()
            logging.info('Model loaded')
        return self.run(*args, **kwargs)


@celery.task(ignore_result=False,
             bind=True,
             base=PredictTask,
             name='{}.{}'.format(__name__, 'Churn'))
def predict_image(self, data):
    """
    Essentially the run method of PredictTask
    """
    return get_prediction(data, self.model)

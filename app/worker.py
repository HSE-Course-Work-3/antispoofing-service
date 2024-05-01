import os
import logging

from celery import Celery, Task

from app.neural_network import create_model, get_prediction

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

celery = Celery(__name__, broker=BROKER_URL, backend=RESULT_BACKEND)


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
            logging.info("Loading Model...")
            self.model = load_model("tf_efficientnet_b3_ns")
            logging.info("Model loaded")
        return self.run(*args, **kwargs)


def load_model(model_name: str):
    nn_model = create_model(model_name)
    nn_model = nn_model.eval()
    return nn_model


@celery.task(
    ignore_result=False,
    bind=True,
    base=PredictTask,
    name="{}.{}".format(__name__, "Churn"),
)
def predict_image(self, image_path):
    """
    Essentially the run method of PredictTask
    """
    prediction = get_prediction(image_path, self.model)
    os.remove(image_path)
    return prediction


def predict(image: str, model) -> dict[str, float]:
    return get_prediction(image, model)

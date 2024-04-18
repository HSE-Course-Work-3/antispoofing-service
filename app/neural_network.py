from typing import Optional

import torch
from albumentations import CenterCrop, Compose, Normalize, PadIfNeeded
from albumentations.pytorch.transforms import ToTensorV2
from datasouls_antispoof.class_mapping import class_mapping
from iglovikov_helper_functions.dl.pytorch.utils import rename_layers
from iglovikov_helper_functions.utils.image_utils import load_rgb
from timm import create_model as timm_create_model
from torch import nn

from app.paths import EFFICENT_NET_PATH

MODEL_WEIGHTS = {"tf_efficientnet_b3_ns": EFFICENT_NET_PATH}


def create_model(model_name: str, activation: Optional[str] = "softmax"):
    model = timm_create_model(model_name, pretrained=False, num_classes=4)

    state_dict = torch.load(
        MODEL_WEIGHTS[model_name], map_location=torch.device("cpu")
    )["state_dict"]
    state_dict = rename_layers(state_dict, {"model.": ""})
    model.load_state_dict(state_dict)

    if activation == "softmax":
        return nn.Sequential(model, nn.Softmax(dim=1))
    return model


def get_prediction(image_path, model):
    image = load_rgb(image_path)

    transform = Compose(
        [
            PadIfNeeded(min_height=400, min_width=400),
            CenterCrop(height=400, width=400),
            Normalize(),
            ToTensorV2(),
        ]
    )
    transformed_image = transform(image=image)["image"]

    with torch.no_grad():
        prediction = model(torch.unsqueeze(transformed_image, 0))[0].numpy()

    class_names = list(class_mapping.keys())

    result = {
        class_name: float(pred) for class_name, pred in zip(class_names, prediction)
    }
    return result

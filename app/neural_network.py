import torch
from albumentations.pytorch.transforms import ToTensorV2
from datasouls_antispoof.class_mapping import class_mapping
from iglovikov_helper_functions.utils.image_utils import load_rgb
from albumentations import Compose, PadIfNeeded, Normalize, CenterCrop


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

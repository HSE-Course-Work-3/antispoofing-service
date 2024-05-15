from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WEIGHTS_PATH = PROJECT_ROOT / "weights"

EFFICENT_NET_PATH = WEIGHTS_PATH / "2020-12-02_efficientnet_b3.pth"
RESNET_PATH = WEIGHTS_PATH / "2020-11-30b_resnext50_32x4d.pth"

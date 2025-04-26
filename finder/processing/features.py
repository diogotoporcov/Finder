from typing import Self
import numpy as np
import torch
from PIL import Image
from torchvision.models import resnet50, ResNet50_Weights
from torchvision import transforms


class FeaturesExtractor:
    _PROCESSOR: Self | None = None

    def __new__(cls, *args, **kwargs):
        if cls._PROCESSOR is None:
            cls._PROCESSOR = super().__new__(cls)

        return cls._PROCESSOR

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V1).to(self._device).eval()
            self._transform = transforms.Compose([
                transforms.Resize((256, 256)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

    def extract_features(self, image: Image.Image) -> np.ndarray:
        tensor = self._transform(image).unsqueeze(0).to(self._device)
        with torch.no_grad():
            return self._model(tensor).flatten().cpu().numpy()


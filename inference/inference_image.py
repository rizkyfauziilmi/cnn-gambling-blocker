import io
from types.result import PredictionResult

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms


class GamblingImageClassifier(nn.Module):
    def __init__(self, model_type: str = "efficientnet"):
        super().__init__()
        # Tidak perlu download weights imagenet lagi, cukup model kosong
        model_type = model_type.lower()
        model_factory = self._get_model_factory(model_type)
        self.model = model_factory(weights=None)
        in_features = self._get_classifier_in_features(self.model)
        self.model.classifier = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, 1),  # Output 1 logit untuk Binary
        )

    @staticmethod
    def _get_model_factory(model_type: str):
        if model_type in ("efficientnet", "efficientnet_b0"):
            return models.efficientnet_b0
        if model_type in ("mobilenet", "mobilenet_v3_small"):
            return models.mobilenet_v3_small
        raise ValueError(f"Model type '{model_type}' tidak didukung")

    @staticmethod
    def _get_classifier_in_features(model: nn.Module) -> int:
        classifier = getattr(model, "classifier", None)
        if classifier is None:
            raise ValueError("Model tidak memiliki classifier yang dikenali")
        if isinstance(classifier, nn.Sequential):
            last_linear = next((m for m in reversed(classifier) if isinstance(m, nn.Linear)), None)
            if last_linear is not None:
                return last_linear.in_features
            raise ValueError("Classifier sequential tidak memiliki layer Linear")
        if isinstance(classifier, nn.Linear):
            return classifier.in_features
        raise ValueError("Classifier tidak dikenali")

    def forward(self, x):
        return self.model(x)


class ImagePredictor:
    def __init__(self, model_path: str, model_type: str = "efficientnet", device: torch.device | None = None):
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = GamblingImageClassifier(model_type=model_type)

        # Load model weights
        state_dict = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])

    def predict(self, image_input: str | bytes | Image.Image, threshold: float = 0.5) -> PredictionResult:
        try:
            # jika berupa path string maka buka file
            if isinstance(image_input, str):
                img = Image.open(image_input).convert("RGB")
            # jika berupa bytes atau bytearray maka buka dari memory
            elif isinstance(image_input, (bytes, bytearray)):
                img = Image.open(io.BytesIO(image_input)).convert("RGB")
            # jika sudah berupa PIL Image, pastikan dalam mode RGB
            elif isinstance(image_input, Image.Image):
                img = image_input.convert("RGB")
            else:
                raise ValueError("Format input tidak didukung")

            img_tensor = self.transform(img).unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.model(img_tensor)
                probability = torch.sigmoid(output).item()

            is_gambling = probability > threshold

            return PredictionResult(label="JUDI" if is_gambling else "BUKAN JUDI", confidence=round(probability * 100, 2), is_gambling=is_gambling, status="success")

        except Exception as e:
            return PredictionResult(label="UNKNOWN", confidence=0.0, is_gambling=False, status="error", message=str(e))

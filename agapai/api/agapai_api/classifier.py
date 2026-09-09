import math
from pathlib import Path
from typing import Dict, Union
import re
import joblib

BASE_DIR = Path(__file__).resolve().parent
MODEL_FILEPATH = BASE_DIR / "models" / "agapai_linearsvc_model.pkl"

if not MODEL_FILEPATH.exists():
    MODEL_FILEPATH = BASE_DIR / "agapai_linearsvc_model.pkl"


def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return

    text = text.lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return " ".join(text.split())


class VictimVolunteerClassifier:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if MODEL_FILEPATH.exists():
            try:
                loaded_object = joblib.load(MODEL_FILEPATH)
                if hasattr(loaded_object, "predict"):
                    self.model = loaded_object
            except Exception as error:
                print(f"Warning: Failed to load model file: {error}")

    def classify(self, live_text: str) -> Dict[str, Union[str, float, bool]]:
        cleaned = preprocess_text(live_text)

        predicted_label = None
        confidence = 0.0

        if self.model is not None:
            predicted_label = str(self.model.predict([cleaned])[0])

            if hasattr(self.model, "decision_function"):
                score = float(self.model.decision_function([cleaned])[0])
                confidence = round(1 / (1 + math.exp(-abs(score))), 2)

        return {
            "text": live_text,
            "cleaned_text": cleaned,
            "category": predicted_label or "Unclassified",
            "classifier_type": predicted_label or "Unclassified",
            "classifier_score": confidence,
            "is_disaster_related": predicted_label is not None,
        }


_classifier_instance = VictimVolunteerClassifier()

def classify_post(text: str) -> Dict[str, Union[str, float, bool]]:
    return _classifier_instance.classify(text)

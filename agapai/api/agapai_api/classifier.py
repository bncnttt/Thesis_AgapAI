import math
import re
from pathlib import Path
from typing import Dict, Union
import joblib

BASE_DIR = Path(__file__).resolve().parent
MODEL_FILEPATH = BASE_DIR / "models" / "agapai_linearsvc_model.pkl"

if not MODEL_FILEPATH.exists():
    MODEL_FILEPATH = BASE_DIR / "agapai_linearsvc_model.pkl"

RECRUITMENT_PHRASES = [
    "volunteers needed",
    "volunteer needed",
    "need volunteer",
    "need volunteers",
    "need helpers",
    "looking for volunteers",
    "looking for more volunteers",  
    "if willing to donate",
]

VICTIM_PHRASES = [
    "trapped",
    "na trap",
    "natrap",
    "roof",
    "bubong",
    "rescue",
    "tulong po",
    "hingi ng tulong",
    "help",
    "need help",
    "need help po",
    "cebuneedshelp",
    "sos",
    "sos cebu",
    "please rescue",
    "palihog rescue",
    "kailangan ng rescue",
    "send food",
    "send water",
    "naubusan",
    "pls help",
    "pls help us",
    "kailangan marefill",
    "kailangan i-refill",
    "hindi kami makaalis",
    "urgent needs",
    "need power banks",
]

VOLUNTEER_PHRASES = [
    "relief operations",
    "flood response team",
    "volunteer group",
    "volunteers",
    "volunteer",
    "para tumulong",
    "gustong tumulong",
    "free charging",
    "charging station kami",
    "may available",
    "boats available",
    "may generator",
    "may bangka kami",
    "mayroon kaming",
    "pupunta kami sa",
    "mamimigay kami",
    "magmimigay kami",
    "distributing free",
    "for donation",
    "open 24 hours for evacuees",
]

FLOOD_HAZARD_PHRASES = [
    "water continues to rise",
    "water reached",
    "water hazard",
    "mataas ang baha",
    "baha na",
    "landslide",
    "brownout",
]

def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return 

    text = text.lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text) 
    text = re.sub(r"@\w+", "", text)  
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)  
    return " ".join(text.split())  


def contains_any(text: str, phrases: list) -> bool:
    return any(phrase in text for phrase in phrases)

def apply_wsd(text: str) -> str:
    if not text:
        return

    text_lower = text.lower()
    tags = []

    has_victim_intent = contains_any(text_lower, VICTIM_PHRASES) or (
        "kailangan" in text_lower and not contains_any(text_lower, ["volunteers needed", "looking for volunteers"])
    )

    is_volunteer_call = contains_any(text_lower, RECRUITMENT_PHRASES) or contains_any(text_lower, VOLUNTEER_PHRASES)

    if has_victim_intent:
        tags.append("wsd_resource_request")
        if not is_volunteer_call and any(w in text_lower for w in ["rescue", "trapped", "sos", "tulong po"]):
            tags.append("wsd_distress_urgent")

    if contains_any(text_lower, FLOOD_HAZARD_PHRASES):
        tags.append("wsd_flood_hazard")

    if is_volunteer_call and not ("kailangan ng tubig" in text_lower or "kailangan ng pagkain" in text_lower):
        tags.append("wsd_resource_offer")
        tags.append("wsd_relief_service")

    if tags:
        return text + " " + " ".join(tags)
    return text


def apply_directional_override(post_text: str, wsd_text: str, predicted_label: str) -> str:
    text_lower = post_text.lower()

    if contains_any(text_lower, RECRUITMENT_PHRASES):
        return "Volunteer"

    if contains_any(text_lower, VICTIM_PHRASES):
        return "Victim"

    if "wsd_resource_offer" in wsd_text and "wsd_resource_request" in wsd_text:
        if "volunteers" in text_lower or "relief" in text_lower:
            return "Volunteer"

    if "wsd_distress_urgent" in wsd_text:
        return "Victim"

    if "wsd_resource_offer" in wsd_text or "wsd_relief_service" in wsd_text:
        return "Volunteer"

    return predicted_label

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
        wsd_augmented = apply_wsd(cleaned)

        raw_pred = "Victim"
        confidence = 0.75

        if self.model is not None:
            raw_pred = str(self.model.predict([wsd_augmented])[0])

            if hasattr(self.model, "decision_function"):
                score = float(self.model.decision_function([wsd_augmented])[0])
                confidence = round(1 / (1 + math.exp(-abs(score))), 2)

        final_label = apply_directional_override(live_text, wsd_augmented, raw_pred)

        valid_labels = ["Victim", "Volunteer", "Victim Request", "Volunteer Offer"]
        is_related = final_label in valid_labels

        return {
            "text": live_text,
            "cleaned_text": cleaned,
            "wsd_augmented_text": wsd_augmented,
            "category": final_label,
            "classifier_type": final_label,
            "classifier_score": confidence,
            "is_disaster_related": is_related,
        }


_classifier_instance = VictimVolunteerClassifier()

def classify_post(text: str) -> Dict[str, Union[str, float, bool]]:
    return _classifier_instance.classify(text)
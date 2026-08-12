import calamancy

_nlp = calamancy.load("tl_calamancy_md-0.1.0")


def extract_entities(text):
    """Labels: PER (person), ORG (organization), LOC (location)."""
    if not text:
        return []

    doc = _nlp(text)
    return [
        {
            "text": ent.text,
            "label": ent.label_,
            "start_char": ent.start_char,
            "end_char": ent.end_char,
        }
        for ent in doc.ents
    ]


def get_location_entities(text):
    return [e for e in extract_entities(text) if e["label"] == "LOC"]
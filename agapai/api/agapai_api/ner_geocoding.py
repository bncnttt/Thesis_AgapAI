import psgc
from agapai_api.ner_landmarks import lookup_landmark

CEBU_PROVINCE_NAME = "Cebu"


def clean_location_text(text):
    import re
    cleaned = re.sub(r'^(brgy\.?|barangay)\s*', '', text.strip(), flags=re.IGNORECASE)
    return cleaned.strip(" ,.")


def geocode_location(location_text, municipality_hint=None):
    if not location_text:
        return None

    cleaned = clean_location_text(location_text)

    landmark_match = lookup_landmark(cleaned.lower())
    if landmark_match:
        return {**landmark_match, "matched_name": location_text}

    results = psgc.search(cleaned, n=1000, threshold=85.0)
    cebu_matches = [
        r for r in results
        if len(r.place.breadcrumb) >= 2 and r.place.breadcrumb[1] == CEBU_PROVINCE_NAME
    ]

    if not cebu_matches:
        return None

    if municipality_hint:
        hint = municipality_hint.strip().lower()
        narrowed = [r for r in cebu_matches if hint in " ".join(r.place.breadcrumb).lower()]
        if narrowed:
            cebu_matches = narrowed

    if len(cebu_matches) == 1:
        place = cebu_matches[0].place
        return {
            "latitude": place.coordinate.latitude,
            "longitude": place.coordinate.longitude,
            "matched_name": place.name,
            "breadcrumb": place.breadcrumb,
            "source": getattr(place, "coordinate_source", "psgc_search"),
        }

    return {
        "ambiguous": True,
        "candidate_count": len(cebu_matches),
        "candidates": [m.place.breadcrumb for m in cebu_matches],
        "source": "psgc_ambiguous",
    }
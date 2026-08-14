import psgc
from agapai_api.ner_landmarks import lookup_landmark

CEBU_PROVINCE_NAME = "Cebu"

# Cebu City, Mandaue, and Lapu-Lapu are administratively "Independent
# Cities" in PSGC's own hierarchy -- their breadcrumb's second entry is
# their own name, not "Cebu". Without this, they'd be silently excluded
# from our scope entirely, despite being core Cebu cities.
CEBU_INDEPENDENT_CITY_PARENTS = {
    "City of Cebu (Independent City)",
    "City of Mandaue (Independent City)",
    "City of Lapu-Lapu (Independent City)",
}


def clean_location_text(text):
    import re
    cleaned = re.sub(r'^(brgy\.?|barangay)\s*', '', text.strip(), flags=re.IGNORECASE)
    return cleaned.strip(" ,.")


def _is_in_cebu_scope(breadcrumb):
    if len(breadcrumb) < 2:
        return False
    parent = breadcrumb[1]
    return parent == CEBU_PROVINCE_NAME or parent in CEBU_INDEPENDENT_CITY_PARENTS


def _search_cebu(query, level_filter=None):
    results = psgc.search(query, n=1000, threshold=85.0)
    matches = [r for r in results if _is_in_cebu_scope(r.place.breadcrumb)]
    if level_filter:
        matches = [r for r in matches if r.level in level_filter]
    return matches


def _to_result(place, source_label="psgc_search"):
    return {
        "latitude": place.coordinate.latitude,
        "longitude": place.coordinate.longitude,
        "matched_name": place.name,
        "breadcrumb": place.breadcrumb,
        "psgc_code": getattr(place, "psgc_code", None),
        "source": getattr(place, "coordinate_source", source_label),
    }


def geocode_location(location_text, municipality_hint=None):
    """
    Resolves NER-extracted location text to coordinates, restricted to
    Cebu province plus its three independent cities.
    """
    if not location_text:
        return None

    cleaned = clean_location_text(location_text)

    landmark_match = lookup_landmark(cleaned.lower())
    if landmark_match:
        return {**landmark_match, "matched_name": location_text}

    cebu_matches = _search_cebu(cleaned)
    narrowed = []
    if municipality_hint:
        hint = municipality_hint.strip().lower()
        narrowed = [r for r in cebu_matches if hint in " ".join(r.place.breadcrumb).lower()]
        if narrowed:
            cebu_matches = narrowed

    # SPECIAL CASE: "cebu" alone is too generic -- it's both the province
    # name AND coincidentally matches "City of Cebu". If the raw text
    # didn't actually overlap with the hint (narrowed came up empty), trust
    # the hint's own city-level match instead of this coincidental match.
    if cleaned.lower() == "cebu" and not narrowed and municipality_hint:
        hint_matches = _search_cebu(municipality_hint, level_filter=("city", "municipality"))
        hint_exact = [
            r for r in hint_matches
            if r.place.name.lower().endswith(municipality_hint.strip().lower())
        ]
        if len(hint_exact) == 1:
            return _to_result(hint_exact[0].place)

    # If the search text itself IS a city/municipality name, prefer an
    # exact match at that level -- prevents a plain municipality name from
    # being falsely flagged "ambiguous" just because its own barangays
    # also fuzzy-match the same text.
    if len(cebu_matches) > 1:
        city_level_exact = [
            r for r in cebu_matches
            if r.level in ("city", "municipality") and r.place.name.lower().endswith(cleaned.lower())
        ]
        if len(city_level_exact) == 1:
            cebu_matches = city_level_exact

    if not cebu_matches:
        return None

    if len(cebu_matches) == 1:
        result = _to_result(cebu_matches[0].place)
        if len(result["breadcrumb"]) <= 2 and municipality_hint:
            hint_matches = _search_cebu(municipality_hint, level_filter=("city", "municipality"))
            if len(hint_matches) == 1:
                return _to_result(hint_matches[0].place)
        return result

    return {
        "ambiguous": True,
        "candidate_count": len(cebu_matches),
        "candidates": [m.place.breadcrumb for m in cebu_matches],
        "source": "psgc_ambiguous",
    }
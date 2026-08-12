from agapai_api.geography import CEBU_MUNICIPALITIES_CITIES

GENERIC_LOCATION_WORDS = {"brgy", "brgy.", "barangay", "sitio", "purok", "cebu", "philippines"}


def select_best_location_entity(entity_texts):
    """
    calamanCy sometimes splits 'Brgy. San Roque, Cebu' into 3 separate
    entities instead of one merged span. This picks the most useful one:
    drops generic administrative words, then drops municipality/city names
    (since those are redundant with the separately-detected hint and would
    cause geocoding to resolve at the wrong, too-broad level).
    """
    if not entity_texts:
        return None

    step1 = [t for t in entity_texts if t.strip().lower().rstrip(".,") not in GENERIC_LOCATION_WORDS]
    if not step1:
        step1 = entity_texts

    step2 = [t for t in step1 if t.strip().lower() not in CEBU_MUNICIPALITIES_CITIES]
    final_candidates = step2 if step2 else step1

    final_candidates.sort(key=len, reverse=True)
    return final_candidates[0]
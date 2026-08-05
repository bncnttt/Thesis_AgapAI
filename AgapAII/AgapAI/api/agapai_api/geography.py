import re

CEBU_EXPLICIT_MARKERS = {
    "cebu", "cebu city", "cebu province", "province of cebu", "metro cebu",
    "sugbo", "sugbuanon", "central visayas", "region vii", "region 7",
}

PHILIPPINE_CONTEXT_MARKERS = {
    "philippines", "philippine", "pilipinas", "visayas",
}

CEBU_LOCALITY_MARKERS = {
    "alcantara", "alcoy", "alegria", "aloguinsan", "argao", "asturias",
    "badian", "balamban", "bantayan", "barili", "bogo", "boljoon", "borbon",
    "carcar", "carmen", "catmon", "cebu city", "compostela", "consolacion",
    "cordova", "daanbantayan", "dalaguete", "danao", "dumanjug", "ginatilan",
    "lapu-lapu", "lapu lapu", "liloan", "madridejos", "malabuyoc", "mandaue",
    "medellin", "minglanilla", "moalboal", "naga", "oslob", "pilar", "pinamungajan",
    "poro", "ronda", "samboan", "san fernando", "san francisco", "san remegio",
    "santa fe", "santander", "sibonga", "sogod", "tabogon", "tabuelan", "talisay",
    "toledo", "tuburan", "tudela",
}

CEBU_LANDMARK_MARKERS = {
    "ayala center cebu", "basilica del santo nino", "carbon market", "cebu it park",
    "cebu provincial capitol", "colon street", "fort san pedro", "mactan", "mactan island",
    "mactan-cebu", "magellan's cross", "magellans cross", "sm seaside", "sm city cebu",
    "south road properties", "srp", "taoist temple", "tops lookout",
}

CEBU_CONTEXT_MARKERS = CEBU_EXPLICIT_MARKERS | CEBU_LOCALITY_MARKERS | CEBU_LANDMARK_MARKERS
CEBU_SECONDARY_MARKERS = CEBU_EXPLICIT_MARKERS | CEBU_LANDMARK_MARKERS | PHILIPPINE_CONTEXT_MARKERS
AMBIGUOUS_CEBU_LOCALITIES = {
    "asturias", "carmen", "compostela", "cordova", "danao", "medellin", "naga",
    "pilar", "san fernando", "san francisco", "santa fe", "sogod", "talisay",
    "toledo", "tuburan",
}


def load_cebu_geographic_registry():
    cebu_location_markers = {
        "cebu", "cebu province", "province of cebu", "cebu city", "metro cebu",
        "sugbo", "sugbuanon", "central visayas", "region vii", "region 7",
        "brgy", "barangay", "sitio", "purok", "kalye", "street", "st", "bayan",
        "bldg", "provincial", "city", "poblacion",
    }

    registry = cebu_location_markers | CEBU_LOCALITY_MARKERS | CEBU_LANDMARK_MARKERS
    print(f"SUCCESS: Indexed {len(registry)} Cebu Province location markers only.")
    return registry


CEBU_GEOGRAPHIC_REGISTRY = load_cebu_geographic_registry()


def contains_phrase(text, phrase):
    escaped = re.escape(phrase).replace(r'\ ', r'[\s.-]+')
    return re.search(r'\b' + escaped + r'\b', text, flags=re.IGNORECASE) is not None


def find_matching_phrases(text, phrases):
    return sorted({phrase.title() for phrase in phrases if contains_phrase(text, phrase)})


def has_cebu_context(text):
    """
    Accepts a post only when a location mention is contextually tied to Cebu, Philippines.
    Shared names like Naga, Carmen, Compostela, or San Fernando must have a secondary
    Cebu/Philippines/landmark marker nearby in the same post.
    """
    if not text:
        return False, []

    explicit_matches = find_matching_phrases(text, CEBU_EXPLICIT_MARKERS)
    landmark_matches = find_matching_phrases(text, CEBU_LANDMARK_MARKERS)
    locality_matches = find_matching_phrases(text, CEBU_LOCALITY_MARKERS)
    secondary_matches = find_matching_phrases(text, CEBU_SECONDARY_MARKERS)
    ambiguous_matches = find_matching_phrases(text, AMBIGUOUS_CEBU_LOCALITIES)

    if explicit_matches or landmark_matches:
        return True, sorted(set(explicit_matches + landmark_matches + locality_matches))

    if locality_matches and secondary_matches and not ambiguous_matches:
        return True, sorted(set(locality_matches + secondary_matches))

    if locality_matches and len(locality_matches) >= 2:
        return True, locality_matches

    return False, locality_matches


def extract_location_name(text):
    """
    Scans the text for Philippine locations and context markers,
    capturing the full address phrase such as 'Purok 2, Colon' or 'Brgy. Malanday'.
    """
    context_pattern = r'\b(purok|brgy|barangay|sitio|kalye|street|st|bayan|poblacion)\b\s*\d*[\s,.-]*[A-Z][a-zA-Z0-9]*'
    match = re.search(context_pattern, text, flags=re.IGNORECASE)
    if match:
        return match.group(0).title()

    words = re.findall(r'\b\w+\b', text.lower())
    for word in words:
        if word in CEBU_GEOGRAPHIC_REGISTRY:
            return word.capitalize()

    return None

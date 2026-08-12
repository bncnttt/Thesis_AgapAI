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
    "poro", "ronda", "samboan", "san antonio", "san fernando", "san francisco",
    "san isidro", "san jose", "san miguel", "san nicolas", "san remegio",
    "san roque", "san vicente", "santa fe", "santander", "sibonga", "sogod",
    "tabogon", "tabuelan", "talisay", "toledo", "tuburan", "tudela",
}

CEBU_LANDMARK_MARKERS = {
    "ayala center cebu", "basilica del santo nino", "carbon market", "cebu it park",
    "cebu provincial capitol", "colon street", "fort san pedro", "mactan", "mactan island",
    "mactan-cebu", "magellan's cross", "magellans cross", "sm seaside", "sm city cebu",
    "south road properties", "srp", "taoist temple", "tops lookout", "IT PARK", "SM City Cebu", "SM Seaside City Cebu", "Cebu IT Park", "Cebu Provincial Capitol",
}

CEBU_CONTEXT_MARKERS = CEBU_EXPLICIT_MARKERS | CEBU_LOCALITY_MARKERS | CEBU_LANDMARK_MARKERS
CEBU_SECONDARY_MARKERS = CEBU_EXPLICIT_MARKERS | CEBU_LANDMARK_MARKERS | PHILIPPINE_CONTEXT_MARKERS
AMBIGUOUS_CEBU_LOCALITIES = {
    "asturias", "carmen", "compostela", "cordova", "danao", "medellin", "naga",
    "pilar", "san fernando", "san francisco", "santa fe", "sogod", "talisay",
    "toledo", "tuburan", "san roque", "san miguel", "san isidro", "san antonio", "san vicente", "san nicolas", "san jose"
}


def load_cebu_geographic_registry():
    cebu_location_markers = {
        "cebu", "cebu province", "province of cebu", "cebu city", "metro cebu",
        "sugbo", "sugbuanon", "central visayas", "region vii", "region 7",
        "brgy", "barangay", "sitio", "purok", "kalye", "street", "st", "bayan",
        "bldg", "provincial", "poblacion",
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


def format_location_name(phrase):
    if phrase.lower() in {"lapu-lapu", "lapu lapu"}:
        return "Lapu-Lapu"
    return phrase.title()


def find_ordered_matching_phrases(text, phrases):
    matches = []
    for phrase in phrases:
        escaped = re.escape(phrase).replace(r'\ ', r'[\s.-]+')
        match = re.search(r'\b' + escaped + r'\b', text, flags=re.IGNORECASE)
        if match:
            matches.append((match.start(), -len(phrase), format_location_name(phrase)))
    return [match_text for _start, _length, match_text in sorted(matches)]


def format_context_location(value):
    cleaned_value = re.sub(r'\s+', ' ', value.strip())
    cleaned_value = re.sub(r'\s+(cebu city|cebu)$', '', cleaned_value, flags=re.IGNORECASE)
    cleaned_value = re.sub(r'^(brgy)\.?\s*[,.-]?\s*', 'Brgy. ', cleaned_value, flags=re.IGNORECASE)
    cleaned_value = re.sub(r'^(barangay)\s*[,.-]?\s*', 'Barangay ', cleaned_value, flags=re.IGNORECASE)
    return cleaned_value.title().replace("Brgy.", "Brgy.")


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
    context_pattern = r'\b(purok|brgy|barangay|sitio|kalye|street|st|bayan|poblacion)\b\.?\s*[,.-]?\s*(?:\d+\s*)?[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*){0,2}'
    match = re.search(context_pattern, text, flags=re.IGNORECASE)
    if match:
        context_location = format_context_location(match.group(0))
        locality_matches = find_ordered_matching_phrases(text, CEBU_LOCALITY_MARKERS - {"cebu city"})
        if "Poblacion" in context_location and locality_matches:
            return locality_matches[0]
        return context_location

    specific_localities = CEBU_LOCALITY_MARKERS - {"cebu city"}
    locality_matches = find_ordered_matching_phrases(text, specific_localities)
    if locality_matches:
        return locality_matches[0]

    landmark_matches = find_ordered_matching_phrases(text, CEBU_LANDMARK_MARKERS)
    if landmark_matches:
        return landmark_matches[0]

    phrase_matches = find_ordered_matching_phrases(text, CEBU_GEOGRAPHIC_REGISTRY)
    if phrase_matches:
        return phrase_matches[0]

    words = re.findall(r'\b\w+\b', text.lower())
    for word in words:
        if word in CEBU_GEOGRAPHIC_REGISTRY:
            return word.capitalize()

    return None


CEBU_MUNICIPALITIES_CITIES = {
    "alcantara", "alcoy", "alegria", "aloguinsan", "argao", "asturias", "badian",
    "balamban", "bantayan", "barili", "boljoon", "borbon", "carmen", "catmon",
    "compostela", "consolacion", "cordova", "daanbantayan", "dalaguete",
    "dumanjug", "ginatilan", "liloan", "madridejos", "malabuyoc", "medellin",
    "minglanilla", "moalboal", "oslob", "pilar", "pinamungajan", "poro",
    "ronda", "samboan", "san fernando", "san francisco", "san remigio",
    "santa fe", "santander", "sibonga", "sogod", "tabogon", "tabuelan",
    "tuburan", "tudela",
    "cebu city", "mandaue", "lapu-lapu", "talisay", "toledo", "carcar",
    "naga", "danao", "bogo",
}

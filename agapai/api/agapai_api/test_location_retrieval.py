from agapai_api.ner_extraction import get_location_entities
from agapai_api.ner_geocoding import geocode_location
from agapai_api.ner_entity_selection import select_best_location_entity
from agapai_api.geography import CEBU_LOCALITY_MARKERS


def find_municipality_hint(text):
    lowered = text.lower()
    for name in CEBU_LOCALITY_MARKERS:
        if name in lowered:
            return name
    return None


test_posts = [
    "tulong mataas ang baha dito sa talisay city, cebu at 11pm. need help kailangan namin ng tubig at damit.",
    "Donation drive para sa mga naapektuhan ng sunog malapit sa Ayala Center Cebu. Tumatanggap kami ng cash at goods simula 7:00 AM.",
    "may mga senior citizens dito na need ng medicines asap. One of them needs maintenance medicine for hypertension, pero hindi makalabas dahil baha ang daan. 📍 Brgy. San Roque, Cebu pls help us contact anyone doing relief operations nearby. @RedCrossPH @LGU",
    "Relief operations headed to Brgy. Poblacion, Compostela, Cebu. May dalang pagkain, tubig, baby diapers, at hygiene kits.",
    "Nasa Brgy. Poblacion, Compostela, Cebu kami. Kailangan ng tubig, canned goods, at baby diapers. Salamat po.",
    "brownout since yesterday and our phones are almost dead. We're at a temporary evacuation area near IT Park Cebu. Need power banks or kahit charging station lang po so we can contact family. #WalangKuryente #Brownout #CebuNeedsHelp",
]

for i, post in enumerate(test_posts, 1):
    print(f"\n--- Post {i} ---")
    locations = get_location_entities(post)
    entity_texts = [loc["text"] for loc in locations]
    hint = find_municipality_hint(post)
    best_entity = select_best_location_entity(entity_texts)

    print(f"NER found: {entity_texts}")
    print(f"Selected entity: {best_entity}")
    print(f"Municipality hint detected: {hint}")
    print(f"Geocode result: {geocode_location(best_entity, hint)}")
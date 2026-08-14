from agapai_api.ner_extraction import get_location_entities
from agapai_api.ner_entity_selection import rank_location_entity_candidates
from agapai_api.ner_geocoding import geocode_location
from agapai_api.ner_temporal import resolve_post_datetime
from agapai_api.geography import CEBU_LOCALITY_MARKERS

# Simulated post metadata for temporal fallback cases -- in the real
# pipeline, this comes from the actual post_document["created_at"]
# that Lopez's code already saves on every real post.
FAKE_CREATED_AT = "2026-08-11T08:00:00Z"
FAKE_READABLE = "Tuesday, August 11, 2026, 4:00:00 PM PHT"


def find_municipality_hint(text):
    lowered = text.lower()
    for name in CEBU_LOCALITY_MARKERS:
        if name in lowered:
            return name
    return None


# Ground truth, confirmed through manual verification during development.
# location_expected: "resolved" / "ambiguous" / "known_limitation"
# temporal_expected: "extracted_from_text" / "post_metadata_fallback"
TEST_CASES = [
    {
        "post": "tulong mataas ang baha dito sa talisay city, cebu at 11pm. need help kailangan namin ng tubig at damit.",
        "location_expected": "resolved",
        "location_expected_name": "City of Talisay",
        "temporal_expected": "extracted_from_text",
        "temporal_phrase": "11pm",
    },
    {
        "post": "Donation drive para sa mga naapektuhan ng sunog malapit sa Ayala Center Cebu. Tumatanggap kami ng cash at goods simula 7:00 AM.",
        "location_expected": "resolved",
        "location_expected_name": "Ayala Center Cebu",
        "temporal_expected": "extracted_from_text",
        "temporal_phrase": "7:00 AM",
    },
    {
        "post": "may mga senior citizens dito na need ng medicines asap. One of them needs maintenance medicine for hypertension, pero hindi makalabas dahil baha ang daan. 📍 Brgy. San Roque, Cebu pls help us contact anyone doing relief operations nearby. @RedCrossPH @LGU",
        "location_expected": "ambiguous",
        "location_note": "No municipality named in text; 'San Roque' exists in 4 Cebu towns.",
        "temporal_expected": "post_metadata_fallback",
    },
    {
        "post": "Relief operations headed to Brgy. Poblacion, Compostela, Cebu. May dalang pagkain, tubig, baby diapers, at hygiene kits.",
        "location_expected": "resolved",
        "location_expected_name": "Poblacion",
        "location_expected_breadcrumb_contains": "Compostela",
        "temporal_expected": "post_metadata_fallback",
    },
    {
        "post": "Nasa Brgy. Poblacion, Compostela, Cebu kami. Kailangan ng tubig, canned goods, at baby diapers. Salamat po.",
        "location_expected": "resolved",
        "location_expected_name": "Poblacion",
        "location_expected_breadcrumb_contains": "Compostela",
        "temporal_expected": "post_metadata_fallback",
    },
    {
        "post": "brownout since yesterday and our phones are almost dead. We're at a temporary evacuation area near IT Park Cebu. Need power banks or kahit charging station lang po so we can contact family. #WalangKuryente #Brownout #CebuNeedsHelp",
        "location_expected": "resolved",
        "location_expected_name": "IT Park Cebu",
        "temporal_expected": "extracted_from_text",
        "temporal_phrase": "since yesterday",
    },
    {
        "post": "Pwede tumulong? May bangka kami para sa mga stranded sa Cordova papuntang Lapu-Lapu. Nandito na kami as of 2:00 PM.",
        "location_expected": "resolved",
        "location_expected_name": "Cordova",
        "temporal_expected": "extracted_from_text",
        "temporal_phrase": "2:00 PM",
    },
]


def check_location(case):
    post = case["post"]
    expected = case["location_expected"]

    locations = get_location_entities(post)
    location_texts = [e["text"] for e in locations]
    hint = find_municipality_hint(post)
    candidates = rank_location_entity_candidates(location_texts) if location_texts else []
    best_entity = None
    result = None
    for candidate in candidates:
        candidate_result = geocode_location(candidate, hint)
        if candidate_result is not None:
            best_entity = candidate
            result = candidate_result
            break

    print(f"  NER found: {location_texts}")
    print(f"  Geocode result: {result}")

    if expected == "known_limitation":
        print(f"  LOCATION: KNOWN LIMITATION (not scored) -- {case.get('location_note', '')}")
        return "skipped"

    if expected == "ambiguous":
        if result and result.get("ambiguous"):
            print("  LOCATION: PASS (correctly flagged ambiguous)")
            return "pass"
        print("  LOCATION: FAIL (should have been ambiguous)")
        return "fail"

    if expected == "resolved":
        ok = result is not None and not result.get("ambiguous", False)
        if ok and "location_expected_name" in case:
            ok = ok and result.get("matched_name") == case["location_expected_name"]
        if ok and "location_expected_breadcrumb_contains" in case:
            ok = ok and case["location_expected_breadcrumb_contains"] in result.get("breadcrumb", [])
        print(f"  LOCATION: {'PASS' if ok else 'FAIL'}")
        return "pass" if ok else "fail"

    return "fail"


def check_temporal(case):
    post = case["post"]
    expected = case["temporal_expected"]

    result = resolve_post_datetime(post, FAKE_CREATED_AT, FAKE_READABLE)
    print(f"  Temporal result: {result}")

    ok = result["source"] == expected

    if ok and expected == "extracted_from_text":
        phrases_found = [e["raw_phrase"] for e in result["expressions"]]
        ok = case["temporal_phrase"] in phrases_found

    if ok and expected == "post_metadata_fallback":
        ok = result.get("fallback_datetime") == FAKE_CREATED_AT

    print(f"  TEMPORAL: {'PASS' if ok else 'FAIL'}")
    return "pass" if ok else "fail"


def run_tests():
    location_pass = location_fail = location_skipped = 0
    temporal_pass = temporal_fail = 0

    for i, case in enumerate(TEST_CASES, 1):
        print(f"\n=== Post {i} ===")
        print(f"Text: {case['post'][:80]}...")

        loc_result = check_location(case)
        if loc_result == "pass":
            location_pass += 1
        elif loc_result == "fail":
            location_fail += 1
        else:
            location_skipped += 1

        temp_result = check_temporal(case)
        if temp_result == "pass":
            temporal_pass += 1
        else:
            temporal_fail += 1

    loc_total = location_pass + location_fail
    loc_accuracy = (location_pass / loc_total * 100) if loc_total else 0
    temp_total = temporal_pass + temporal_fail
    temp_accuracy = (temporal_pass / temp_total * 100) if temp_total else 0

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Location retrieval:  {location_pass}/{loc_total} passed ({loc_accuracy:.1f}%) "
          f"-- {location_skipped} known limitation(s) excluded from scoring")
    print(f"Temporal retrieval:  {temporal_pass}/{temp_total} passed ({temp_accuracy:.1f}%)")


if __name__ == "__main__":
    run_tests()
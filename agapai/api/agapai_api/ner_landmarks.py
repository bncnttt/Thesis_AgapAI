# Manually looked-up coordinates for named landmarks that don't exist
# as official PSGC barangays/municipalities. Extend this list as needed.
CEBU_LANDMARKS = {
    "ayala center cebu": {"latitude": 10.3181, "longitude": 123.9057},
    "sm city cebu": {"latitude": 10.3111, "longitude": 123.9160},
    "sm seaside city cebu": {"latitude": 10.2843, "longitude": 123.8724},
    "cebu it park": {"latitude": 10.3298, "longitude": 123.9058},
    "it park cebu": {"latitude": 10.3298, "longitude": 123.9058},
    "fort san pedro": {"latitude": 10.2925, "longitude": 123.9058},
    "magellan's cross": {"latitude": 10.2934, "longitude": 123.9018},
    "basilica del santo nino": {"latitude": 10.2933, "longitude": 123.9016},
    "carbon market": {"latitude": 10.2937, "longitude": 123.9012},
    "colon street": {"latitude": 10.2950, "longitude": 123.9020},
    "cebu provincial capitol": {"latitude": 10.3157, "longitude": 123.8917},
    "mactan-cebu": {"latitude": 10.3075, "longitude": 123.9789},
    "mactan island": {"latitude": 10.3103, "longitude": 123.9494},
    "south road properties": {"latitude": 10.2775, "longitude": 123.8886},
    "tops lookout": {"latitude": 10.3625, "longitude": 123.8814},
    "taoist temple": {"latitude": 10.3421, "longitude": 123.9082},
}


def lookup_landmark(location_text):
    key = location_text.strip().lower()
    if key in CEBU_LANDMARKS:
        return {**CEBU_LANDMARKS[key], "source": "landmark_table"}
    return None
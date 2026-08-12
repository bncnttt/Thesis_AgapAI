from agapai_api.ner_temporal import resolve_post_datetime

# NOTE: these created_at/readable values are SIMULATED for this standalone
# test only, since these 6 posts are plain strings, not real Mongo documents.
# In the real pipeline (ner_routes.py), these come from the actual
# post_document["created_at"] / ["time_created_readable"] that Lopez's
# Bluesky retrieval already saves -- nothing fake reaches the real app.
test_posts = [
    ("tulong mataas ang baha dito sa talisay city, cebu at 11pm. need help kailangan namin ng tubig at damit.", "2026-08-11T22:00:00Z", "Tuesday, August 11, 2026, 10:00:00 PM PHT"),
    ("Donation drive para sa mga naapektuhan ng sunog malapit sa Ayala Center Cebu. Tumatanggap kami ng cash at goods simula 7:00 AM.", "2026-08-11T07:05:00Z", "Tuesday, August 11, 2026, 3:05:00 PM PHT"),
    ("may mga senior citizens dito na need ng medicines asap.", "2026-08-10T14:32:00Z", "Monday, August 10, 2026, 10:32:00 PM PHT"),
    ("Relief operations headed to Brgy. Poblacion, Compostela, Cebu.", "2026-08-10T09:00:00Z", "Monday, August 10, 2026, 5:00:00 PM PHT"),
    ("Nasa Brgy. Poblacion, Compostela, Cebu kami.", "2026-08-10T09:10:00Z", "Monday, August 10, 2026, 5:10:00 PM PHT"),
    ("brownout since yesterday and our phones are almost dead.", "2026-08-11T08:00:00Z", "Tuesday, August 11, 2026, 4:00:00 PM PHT"),
]

for i, (post, created_at, readable) in enumerate(test_posts, 1):
    print(f"\n--- Post {i} ---")
    print(resolve_post_datetime(post, created_at, readable))
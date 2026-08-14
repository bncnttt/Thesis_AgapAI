from fastapi import APIRouter, HTTPException

from agapai_api.clients import posts_col, mongo_connected
from agapai_api.ner_extraction import extract_entities, get_location_entities
from agapai_api.ner_entity_selection import rank_location_entity_candidates
from agapai_api.ner_geocoding import geocode_location
from agapai_api.ner_temporal import resolve_post_datetime
from agapai_api.geography import CEBU_LOCALITY_MARKERS

router = APIRouter()


def find_municipality_hint(text):
    """Scans the raw post text for a mentioned Cebu city/municipality name."""
    lowered = text.lower()
    for name in CEBU_LOCALITY_MARKERS:
        if name in lowered:
            return name
    return None


def process_post_for_ner(post_document):
    """
    Runs the full Stage 2 pipeline on one post: NER extraction, entity
    selection, geocoding, and temporal resolution. Returns a dict ready
    to be saved back into the post's MongoDB document.
    """
    text = post_document.get("text", "")

    all_entities = extract_entities(text)
    location_entities = get_location_entities(text)
    location_texts = [e["text"] for e in location_entities]

    persons = [e["text"] for e in all_entities if e["label"] == "PER"]
    organizations = [e["text"] for e in all_entities if e["label"] == "ORG"]

    municipality_hint = find_municipality_hint(text)
    candidates = rank_location_entity_candidates(location_texts) if location_texts else []

    best_location_text = None
    coordinates = None
    for candidate in candidates:
        result = geocode_location(candidate, municipality_hint)
        if result is not None:
            best_location_text = candidate
            coordinates = result
            break  # stop at the first candidate that actually resolves

    datetime_result = resolve_post_datetime(
        text,
        post_created_at=post_document.get("created_at"),
        post_time_created_readable=post_document.get("time_created_readable"),
    )

    return {
        "ner_all_entities": all_entities,
        "ner_persons": persons if persons else None,
        "ner_organizations": organizations if organizations else None,
        "ner_locations": location_texts if location_texts else None,
        "ner_selected_location_text": best_location_text,
        "ner_municipality_hint": municipality_hint,
        "ner_coordinates": coordinates,
        "ner_datetime": datetime_result,
        "ner_processed": True,
    }


def format_for_display(value):
    """Dashboard rule: any empty/missing NER field shows as 'None/NA' instead of blank."""
    if value is None or value == [] or value == {}:
        return "None/NA"
    return value


@router.post("/ner/process-all")
def process_all_unprocessed_posts():
    """
    Runs the NER pipeline on every post not yet processed. Meant to be
    called automatically by the frontend right after Lopez's Bluesky
    retrieval finishes -- not something the end user triggers manually.
    """
    if not mongo_connected or posts_col is None:
        raise HTTPException(status_code=503, detail="MongoDB is not connected.")

    unprocessed = posts_col.find({"ner_processed": {"$ne": True}})
    updated_count = 0

    for post in unprocessed:
        ner_result = process_post_for_ner(post)
        posts_col.update_one({"_id": post["_id"]}, {"$set": ner_result})
        updated_count += 1

    return {"status": "success", "posts_processed": updated_count}


@router.get("/ner/table-data")
def get_ner_table_data():
    """
    Powers the 'NER Info' dashboard table. Includes both the resolved
    values AND the raw library outputs (calamanCy entities, PSGC geocode
    result) so the dashboard can show each library's contribution separately.
    """
    if not mongo_connected or posts_col is None:
        raise HTTPException(status_code=503, detail="MongoDB is not connected.")

    posts = posts_col.find({"ner_processed": True})
    rows = []
    for post in posts:
        rows.append({
            "_id": str(post["_id"]),
            "text": post.get("text"),
            "author_handle": post.get("author_handle"),
            "posted_by": post.get("posted_by"),
            "raw_locations_found": post.get("ner_locations"),
            "ner_all_entities": post.get("ner_all_entities"),
            "ner_selected_location_text": post.get("ner_selected_location_text"),
            "ner_municipality_hint": post.get("ner_municipality_hint"),
            "ner_coordinates": post.get("ner_coordinates"),
            "ner_datetime": post.get("ner_datetime"),
            "ner_persons": post.get("ner_persons"),
            "ner_organizations": post.get("ner_organizations"),
        })

    return {"status": "success", "rows": rows}


@router.get("/ner/map-data")
def get_map_ready_posts():
    """Returns only posts with resolved (non-ambiguous) coordinates, for pin placement."""
    if not mongo_connected or posts_col is None:
        raise HTTPException(status_code=503, detail="MongoDB is not connected.")

    posts = posts_col.find({
        "ner_coordinates.latitude": {"$exists": True},
    })
    result = []
    for post in posts:
        post["_id"] = str(post["_id"])
        result.append(post)
    return {"status": "success", "posts": result}


@router.get("/ner/details/{post_id}")
def get_ner_details(post_id: str):
    """Full NER breakdown for one post -- powers the 'show NER process' button/panel."""
    if not mongo_connected or posts_col is None:
        raise HTTPException(status_code=503, detail="MongoDB is not connected.")

    post = posts_col.find_one({"_id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    post["_id"] = str(post["_id"])
    return {"status": "success", "post": post}
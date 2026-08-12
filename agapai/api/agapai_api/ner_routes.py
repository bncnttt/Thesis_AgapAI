from fastapi import APIRouter, HTTPException

from agapai_api.clients import posts_col, mongo_connected
from agapai_api.ner_extraction import extract_entities, get_location_entities
from agapai_api.ner_entity_selection import select_best_location_entity
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
    best_location_text = select_best_location_entity(location_texts) if location_texts else None
    coordinates = geocode_location(best_location_text, municipality_hint) if best_location_text else None

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
    Powers the 'NER Info' dashboard table: every processed post, with
    empty entity categories shown as 'None/NA' rather than blank.
    """
    if not mongo_connected or posts_col is None:
        raise HTTPException(status_code=503, detail="MongoDB is not connected.")

    posts = posts_col.find({"ner_processed": True})
    rows = []
    for post in posts:
        datetime_info = post.get("ner_datetime") or {}
        if datetime_info.get("source") == "extracted_from_text":
            display_datetime = datetime_info["expressions"]
        else:
            display_datetime = datetime_info.get("fallback_readable")

        coords = post.get("ner_coordinates")
        if coords and coords.get("ambiguous"):
            display_location = f"Ambiguous ({coords['candidate_count']} possible matches)"
        elif coords:
            display_location = coords.get("matched_name")
        else:
            display_location = None

        rows.append({
            "_id": str(post["_id"]),
            "text": post.get("text"),
            "posted_by": post.get("posted_by"),
            "location": format_for_display(display_location),
            "datetime": format_for_display(display_datetime),
            "persons": format_for_display(post.get("ner_persons")),
            "organizations": format_for_display(post.get("ner_organizations")),
            "raw_locations_found": format_for_display(post.get("ner_locations")),
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
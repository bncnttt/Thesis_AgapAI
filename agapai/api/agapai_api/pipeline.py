"""
Stack B: local translation + strict disaster/intent classification for
Cebu posts. No hosted LLM API (Gemini or otherwise) is used anywhere in
this module -- translation and classification both run entirely on this
machine via NLLB-200 and BART-MNLI.

This replaces two prior implementations, fixing what actually broke each
one:

1. The original local NLLB-200 + BART-MNLI stack (agapai_api/disaster_nlp.py)
   corrupted Philippine place names during translation (e.g. "Talisay" ->
   "Taraiza") because NLLB is a narrow translation model with no concept
   of "this token is a place name, don't touch it"; and BART-MNLI's
   standard (single-label) zero-shot mode always ranks *some* label
   highest across whatever candidates it's given, so non-disaster content
   (crime news, waterfall photos) got shoved into a disaster label.
2. A later Gemini-based version fixed both by using a general LLM's world
   knowledge, but requires a hosted API key.

This version fixes the SAME two failure modes locally, without any LLM,
using two targeted techniques instead of "a smarter model":

- Entity masking: every known Cebu place name (geography.py's dynamic
  PSGC registry) is replaced with a placeholder BEFORE translation and
  restored verbatim AFTER, so NLLB never even sees the actual place name
  and cannot corrupt it -- this is deterministic, not "hoping the model
  gets it right."
- Independent-threshold zero-shot classification (multi_label=True):
  each candidate label is scored on its own entailment probability
  instead of being forced into a single ranked choice, so "none of the 5
  disaster types fit" and "no active help ask/offer" are real, reachable
  outcomes -- this is what actually fixes the forced-choice bug, not the
  choice of classifier model itself.
"""
import re

from agapai_api.bluesky import resolve_parent_post_texts
from agapai_api.clients import db, mongo_connected
from agapai_api.geography import strip_dateline
from agapai_api.local_models import (
    classify_with_threshold,
    detect_source_language_code,
    is_confidently_foreign_language,
    mask_cebu_locations,
    restore_locations,
    translate_text,
)

DISASTER_TYPES = ["flood", "earthquake", "typhoon", "fire", "landslide"]
INTENT_LABELS = ["NEEDING_HELP", "WILLING_TO_HELP", "NONE"]

DISASTER_TYPE_THRESHOLD = 0.5
INTENT_THRESHOLD = 0.5

# Natural-language phrasing of each intent, scored independently against
# the post text. Not a hardcoded disaster/dialect vocabulary -- these are
# the classifier's candidate hypotheses, evaluated via entailment, not
# via keyword matching.
INTENT_CANDIDATE_PHRASES = {
    "NEEDING_HELP": "a request for urgent rescue, food, water, shelter, or medical aid",
    "WILLING_TO_HELP": "an offer of relief supplies, shelter, transport, or volunteering",
}

# A small, fixed set of major Philippine regions/provinces outside Cebu
# Province -- a geographic constant (comparable to the 5 fixed disaster
# type seeds), not an open-ended disaster-keyword or dialect vocabulary.
# Used only to help distinguish "Cebu is the disaster victim" from "Cebu
# is sending aid elsewhere"; testing showed neither a pure-semantic check
# nor a generic capitalized-word heuristic could reliably make this call
# alone with this size of local model.
OUTSIDE_CEBU_REGIONS = ["mindanao", "luzon", "manila", "bohol", "leyte", "samar"]

# This hypothesis is this pipeline's equivalent of an LLM system-prompt
# instruction: "Only flag as true if a city/municipality within Cebu
# Province is the direct victim of the disaster. Exclude posts where Cebu
# is merely sending aid to outside regions." There is no LLM prompt here
# to update directly -- this phrasing plays that role for the zero-shot
# classifier instead.
OUTGOING_AID_HYPOTHESIS = (
    "Cebu residents or officials are sending or coordinating disaster "
    "relief aid for another place, rather than responding to a disaster "
    "happening inside Cebu itself"
)
OUTGOING_AID_THRESHOLD = 0.5

# A second, independently-worded hypothesis used to corroborate a
# disaster_type match. BART-MNLI's per-label entailment score can cross
# DISASTER_TYPE_THRESHOLD on short, low-information text from surface-level
# word association alone -- verified case: "BOGO for Mitch & Lindsay" (a
# buy-one-get-one promo, unrelated to the real Cebu town of Bogo) scored
# landslide=0.51, just over threshold, with no actual disaster content
# anywhere in the text. Requiring a second, differently-phrased hypothesis
# to also pass closes that gap the same way is_outgoing_aid_post() already
# requires two independent signals above.
#
# Wording matters here: an earlier version phrased as "an actual ongoing
# disaster or emergency SITUATION" scored relief/volunteer-coordination
# posts (e.g. "Volunteers coordinating with rescue teams near Brgy. Bitoon,
# Dumanjug, Cebu due to landslide") too low (0.12-0.63, inconsistently
# straddling the threshold) because such posts describe the RESPONSE to a
# disaster rather than the event itself -- even though these are exactly
# the actionable WILLING_TO_HELP/NEEDING_HELP posts this pipeline exists to
# surface. Rephrasing to explicitly include "victims, or efforts to help
# those affected" fixes this: verified scores of 0.82-0.97 across genuine
# disaster reports AND relief/volunteer-coordination posts alike, against
# 0.01-0.22 for the BOGO false positives -- a wide, consistent margin on
# both sides of the shared 0.5 threshold.
DISASTER_EVENT_HYPOTHESIS = (
    "this text is about a real disaster event, its victims, or efforts to "
    "help those affected by it"
)
DISASTER_EVENT_THRESHOLD = 0.5


def mentions_outside_cebu_region(text):
    lowered = text.lower()
    return any(
        re.search(r'\b' + re.escape(region) + r'\b', lowered)
        for region in OUTSIDE_CEBU_REGIONS
    )


def is_outgoing_aid_post(text):
    """
    True only when BOTH signals agree: the post names a major region
    outside Cebu Province, AND the text semantically reads as Cebu
    sending/coordinating aid elsewhere rather than describing a disaster
    inside Cebu. Requiring both avoids the false positives/negatives
    either signal produced alone during testing (e.g. a genuine local
    Cebu flood-relief post getting rejected just for using "relief"
    language, or ordinary capitalized words being mistaken for places).
    """
    if not mentions_outside_cebu_region(text):
        return False

    _label, score = classify_with_threshold(text, [OUTGOING_AID_HYPOTHESIS], 0.0)
    return score >= OUTGOING_AID_THRESHOLD


def evaluate_post(raw_text, parent_text=None):
    """
    Runs one post through Stack B, entirely locally: mask known Cebu place
    names, translate to English (only if not already English), restore the
    place names verbatim, then classify disaster type and help intent via
    independent-threshold zero-shot classification.

    parent_text: thread-stitching context. If this post is a reply, pass
    the parent post's text so a fragment like "It's completely underwater!"
    is classified together with what it's actually replying to.
    """
    if not raw_text or not raw_text.strip():
        return {
            "is_disaster": False,
            "disaster_type": "none",
            "intent": "NONE",
            "translated_text_en": raw_text or "",
            "extracted_locations": [],
        }

    raw_text = strip_dateline(raw_text)

    if is_confidently_foreign_language(raw_text):
        print(
            "[AGAPAI LOG] Rejected: confidently detected as a language "
            "unrelated to the Philippines -- out of scope."
        )
        return {
            "is_disaster": False,
            "disaster_type": "none",
            "intent": "NONE",
            "translated_text_en": raw_text,
            "extracted_locations": [],
        }

    masked_text, placeholder_map = mask_cebu_locations(raw_text)
    source_lang = detect_source_language_code(raw_text)
    translated_masked = translate_text(masked_text, source_lang, "eng_Latn")
    translated_text_en = restore_locations(translated_masked, placeholder_map)

    extracted_locations = sorted(set(placeholder_map.values()))

    # Classify on the translation AND the original text together, not the
    # translation alone: NLLB can drop or garble content on code-switched
    # posts (verified case: it dropped an English sentence that was
    # already mixed into the post). The original text still carries that
    # signal even when translation partially fails, since BART-MNLI can
    # read English/loanwords mixed into it directly. Only append raw_text
    # when translation actually changed something -- literally duplicating
    # identical text (when the source was already English) was found to
    # roughly triple BART-MNLI's entailment scores from repetition alone,
    # a real false-positive risk on borderline content.
    classification_input = translated_text_en
    if raw_text.strip().lower() != translated_text_en.strip().lower():
        classification_input = f"{translated_text_en} {raw_text}"

    has_parent_context = bool(parent_text and parent_text.strip())
    if has_parent_context:
        classification_input = f"{parent_text} {classification_input}"

    disaster_type, _disaster_score = classify_with_threshold(
        classification_input, DISASTER_TYPES, DISASTER_TYPE_THRESHOLD
    )
    is_disaster = disaster_type is not None

    if is_disaster:
        event_label, _event_score = classify_with_threshold(
            classification_input, [DISASTER_EVENT_HYPOTHESIS], DISASTER_EVENT_THRESHOLD
        )
        if event_label is None:
            print(
                "[AGAPAI LOG] Discarded: a specific disaster-type label matched, "
                "but a second, independently-worded check found no actual "
                "disaster/emergency being described -- likely a short-text "
                "classifier false positive or homonym false positive."
            )
            is_disaster = False
            disaster_type = None

    if is_disaster and is_outgoing_aid_post(classification_input):
        print(
            "[AGAPAI LOG] Discarded as outgoing aid: Cebu is sending relief "
            "to an outside region, not the disaster victim."
        )
        is_disaster = False
        disaster_type = None

    intent = "NONE"
    if is_disaster:
        intent_phrase, _intent_score = classify_with_threshold(
            classification_input, list(INTENT_CANDIDATE_PHRASES.values()), INTENT_THRESHOLD
        )
        if intent_phrase is not None:
            phrase_to_label = {phrase: label for label, phrase in INTENT_CANDIDATE_PHRASES.items()}
            intent = phrase_to_label[intent_phrase]

    return {
        "is_disaster": is_disaster,
        "disaster_type": disaster_type if is_disaster else "none",
        "intent": intent,
        "translated_text_en": translated_text_en,
        "extracted_locations": extracted_locations,
    }


def is_actionable(evaluation):
    """
    The strict save gate: only genuinely actionable disaster posts reach
    'processed_disasters'. Posts with intent "NONE" are never saved there,
    even if is_disaster is true.
    """
    return (
        evaluation["is_disaster"] is True
        and evaluation["disaster_type"] != "none"
        and evaluation["intent"] != "NONE"
    )


def process_raw_posts_into_disasters(limit=None):
    """
    Reads UNPROCESSED posts from MongoDB 'raw_posts' (deduped by URI: a
    post already marked "stack_b_evaluated" is skipped entirely, whether
    it was previously saved or filtered out), evaluates each with Stack
    B, and saves ONLY actionable posts (is_disaster, a real disaster_type,
    and a non-NONE intent) into 'processed_disasters', upserted by URI so
    'processed_disasters' contains 100% actionable posts with no
    duplicates. Re-running this after a prior run only evaluates posts
    that arrived since -- the expensive translate+classify step never
    reruns on a post it's already seen.
    """
    if not mongo_connected or db is None:
        raise RuntimeError("MongoDB is not connected.")

    raw_posts_col = db["raw_posts"]
    processed_col = db["processed_disasters"]

    skipped_already_processed = raw_posts_col.count_documents({"stack_b_evaluated": True})
    print(
        f"[AGAPAI LOG] Skipped {skipped_already_processed} already-evaluated raw "
        "posts (deduped by URI before classification)."
    )

    cursor = raw_posts_col.find({"stack_b_evaluated": {"$ne": True}})
    if limit is not None and limit >= 0:
        cursor = cursor.limit(limit)
    raw_posts = list(cursor)

    # Thread stitching: batch-resolve every needed parent post up front
    # (one Bluesky API call per 25 unique parents) instead of one call per
    # reply, which would be far slower across a whole raw_posts batch.
    parent_uris = [post.get("reply_parent_uri") for post in raw_posts if post.get("reply_parent_uri")]
    parent_texts = resolve_parent_post_texts(parent_uris) if parent_uris else {}

    evaluated_count = 0
    saved_count = 0
    filtered_count = 0

    for raw_post in raw_posts:
        post_id = raw_post.get("uri") or str(raw_post.get("_id"))
        print(f"[AGAPAI LOG] Evaluating raw post ID: {post_id}...")

        raw_text = raw_post.get("text", "")
        parent_text = parent_texts.get(raw_post.get("reply_parent_uri"))

        try:
            evaluation = evaluate_post(raw_text, parent_text=parent_text)
        except Exception as evaluation_error:
            print(f"[AGAPAI LOG] Status: Skipped ({evaluation_error})")
            continue

        evaluated_count += 1
        raw_posts_col.update_one(
            {"_id": raw_post["_id"]}, {"$set": {"stack_b_evaluated": True}}
        )

        print(
            f"[AGAPAI LOG] Output -> Type: {evaluation['disaster_type']} | "
            f"Intent: {evaluation['intent']} | Valid: {evaluation['is_disaster']}"
        )

        if is_actionable(evaluation):
            processed_document = {
                "uri": post_id,
                "author_did": raw_post.get("author_did"),
                "author_handle": raw_post.get("author_handle"),
                "text": raw_text,
                "translated_text_en": evaluation["translated_text_en"],
                "is_disaster": evaluation["is_disaster"],
                "disaster_type": evaluation["disaster_type"],
                "intent": evaluation["intent"],
                "extracted_locations": evaluation["extracted_locations"],
                "reply_parent_uri": raw_post.get("reply_parent_uri"),
                "used_thread_context": parent_text is not None,
                "created_at": raw_post.get("created_at"),
                "date_range_start": raw_post.get("date_range_start"),
                "date_range_end": raw_post.get("date_range_end"),
            }
            processed_col.update_one({"uri": post_id}, {"$set": processed_document}, upsert=True)
            saved_count += 1
            print("[AGAPAI LOG] Status: Saved to 'processed_disasters'")
        else:
            filtered_count += 1
            reason = (
                "Non-Disaster"
                if not evaluation["is_disaster"] or evaluation["disaster_type"] == "none"
                else "Intent: NONE"
            )
            print(f"[AGAPAI LOG] Status: Filtered out ({reason})")

    return {
        "raw_posts_evaluated": evaluated_count,
        "saved_to_processed_disasters": saved_count,
        "filtered_out": filtered_count,
        "skipped_already_processed": skipped_already_processed,
    }

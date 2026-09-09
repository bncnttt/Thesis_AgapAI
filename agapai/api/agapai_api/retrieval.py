"""
Dual-condition Cebu disaster post retrieval and filtering.

A fetched post is only persisted into MongoDB 'raw_posts' if it satisfies
BOTH conditions:

  1. Contains Cebu location context      (geography.has_cebu_context)
  2. Contains >= 1 dynamically generated  (corpus.get_multilingual_disaster_terms)
     multilingual term for one of the 5
     target disasters

Everything that fails either condition -- general Cebu news, crime/police
reports, out-of-scope events -- is discarded. Both conditions are
evaluated dynamically at runtime: no disaster keyword list, dialect
translation, or place-name lookup array is hardcoded in this file.
"""
from agapai_api.bluesky import (
    format_bluesky_date_bound,
    get_attr,
    get_author_bio_text,
    get_recent_post_texts,
    get_reply_parent_uri,
    resolve_incremental_since,
    search_bluesky_posts,
)
from agapai_api.clients import db, mongo_connected
from agapai_api.corpus import get_dialect_only_disaster_terms, get_multilingual_disaster_terms
from agapai_api.geography import (
    PSGC_CEBU_BARANGAYS,
    format_location_name,
    get_cebu_location_search_terms,
    has_cebu_context,
)


def cascade_check_cebu_relevance(post_text, author_did=None, author_handle=None):
    """
    3-level cascade for confirming Cebu relevance, cheapest check first --
    each level only runs if the prior one fails, to minimize Bluesky API
    usage:

      Level 1: the post's own text               (has_cebu_context)
      Level 2: the author's profile bio           (has_cebu_context on bio)
      Level 3: the author's 5 most recent posts   (has_cebu_context on any)

    Exists for posts that name a genuine, specific Cebu place (e.g. a
    barangay) but never say the word "Cebu" itself -- e.g. "may landslide
    sa Pangdan, city of naga" contains two real PSGC locality names
    (Pangdan, Naga) and IS accepted by has_cebu_context on its own text,
    but a post with only one non-distinctive locality clue, or none at
    all, needs the author's bio/timeline as a fallback signal instead of
    being dropped outright.

    Returns (is_relevant, matched_at_level, matches) where
    matched_at_level is one of "post_text", "author_bio",
    "author_recent_posts", or None.
    """
    is_relevant, matches = has_cebu_context(post_text)
    if is_relevant:
        return True, "post_text", matches

    actor = author_did or author_handle
    if not actor:
        return False, None, []

    bio_text = get_author_bio_text(actor)
    is_relevant, matches = has_cebu_context(bio_text)
    if is_relevant:
        return True, "author_bio", matches

    for recent_text in get_recent_post_texts(actor, limit=5):
        is_relevant, matches = has_cebu_context(recent_text)
        if is_relevant:
            return True, "author_recent_posts", matches

    return False, None, []


def post_matches_dual_condition(post_text, disaster_terms):
    """
    Valid Post = [Contains Cebu Location] AND [Contains >= 1 dynamic term
    for the 5 target disasters].

    Disaster-term matching uses substring containment rather than strict
    word-boundary matching: Tagalog/Cebuano verbs are built by attaching
    affixes directly onto a root (nag-, gi-, mi-, pag-...), so a
    dynamically generated root term like "baha" needs to match inside
    "nagbaha" or "gibaha" too, not just as a standalone word.
    """
    if not post_text:
        return False, False

    is_cebu_post, _ = has_cebu_context(post_text)

    lowered_text = post_text.lower()
    has_disaster_term = any(
        term in lowered_text for term in disaster_terms if len(term) >= 3
    )

    return is_cebu_post, has_disaster_term


def retrieve_and_filter_cebu_disaster_posts(
    start_date,
    end_date,
    max_posts=-1,
    location_terms=None,
    disaster_terms=None,
):
    """
    Retrieves Cebu posts via dynamic PSGC location-anchored search, then
    applies the strict dual-condition filter before persisting matching
    posts to MongoDB 'raw_posts' (upserted by URI).
    """
    if not mongo_connected or db is None:
        raise RuntimeError("MongoDB is not connected.")

    location_terms = location_terms if location_terms is not None else get_cebu_location_search_terms()

    if disaster_terms is None:
        disaster_terms = get_multilingual_disaster_terms()
        print("[AGAPAI LOG] Dynamically generated disaster dialect terms via selected model.")

    since_value = format_bluesky_date_bound(start_date)
    until_value = format_bluesky_date_bound(end_date, end_of_day=True)

    raw_posts_col = db["raw_posts"]

    # Dedup against what's already saved, fetched once up front so each
    # candidate post is a cheap in-memory lookup instead of a per-post DB
    # round trip.
    existing_uris = set(raw_posts_col.distinct("uri"))
    skipped_already_saved = 0

    # True incremental retrieval: ask Bluesky only for what's newer than
    # the latest post we've already saved to raw_posts, instead of
    # re-fetching the full requested range every run. Falls back to the
    # originally requested since_value when raw_posts is empty (first run).
    bluesky_since_value = resolve_incremental_since(raw_posts_col, fallback_since=since_value)
    used_incremental_fetch = bluesky_since_value != since_value
    print(
        f"[AGAPAI LOG] {'Incremental' if used_incremental_fetch else 'Full historical'} "
        f"fetch: querying Bluesky since {bluesky_since_value}."
    )

    total_fetched = 0
    matched_count = 0
    discarded_count = 0
    seen_uris = set()

    for search_query in location_terms:
        try:
            search_results = search_bluesky_posts(
                search_query, max_posts, since=bluesky_since_value, until=until_value
            )
        except RuntimeError as search_error:
            print(f"[AGAPAI LOG] WARNING: search failed for '{search_query}': {search_error}")
            continue

        for post_view in search_results:
            post_uri = get_attr(post_view, "uri")
            if not post_uri or post_uri in seen_uris:
                continue

            if post_uri in existing_uris:
                seen_uris.add(post_uri)
                skipped_already_saved += 1
                continue
            seen_uris.add(post_uri)
            total_fetched += 1

            record = get_attr(post_view, "record")
            post_text = get_attr(record, "text", "") if record else get_attr(post_view, "text", "")

            is_cebu_post, has_disaster_term = post_matches_dual_condition(post_text, disaster_terms)

            if not (is_cebu_post and has_disaster_term):
                discarded_count += 1
                continue

            matched_count += 1
            author = get_attr(post_view, "author")
            raw_post_document = {
                "uri": post_uri,
                "author_did": get_attr(author, "did"),
                "author_handle": get_attr(author, "handle"),
                "text": post_text,
                "reply_parent_uri": get_reply_parent_uri(post_view),
                "created_at": get_attr(record, "created_at") if record else None,
                "retrieval_source": "dual_condition_cebu_disaster_filter",
                "date_range_start": start_date,
                "date_range_end": end_date,
            }
            raw_posts_col.update_one({"uri": post_uri}, {"$set": raw_post_document}, upsert=True)

    print(f"[AGAPAI LOG] Total Cebu posts fetched: {total_fetched}")
    print(f"[AGAPAI LOG] Posts matching 5 target disasters: {matched_count}")
    print(f"[AGAPAI LOG] Discarded non-disaster / out-of-scope posts: {discarded_count}")
    print(f"[AGAPAI LOG] Skipped {skipped_already_saved} already-saved posts (deduped by URI).")

    return {
        "total_fetched": total_fetched,
        "matched": matched_count,
        "discarded": discarded_count,
        "skipped_already_saved": skipped_already_saved,
        "bluesky_since_value": bluesky_since_value,
        "used_incremental_fetch": used_incremental_fetch,
    }


def retrieve_and_cascade_filter_disaster_posts(
    start_date,
    end_date,
    max_posts=-1,
    disaster_terms=None,
    include_barangays=False,
):
    """
    Complements retrieve_and_filter_cebu_disaster_posts(): that function
    anchors every search query with a Cebu place name + the literal word
    "Cebu", so it structurally cannot find a genuine post like "may
    landslide sa Pangdan, city of naga" that names a real Cebu barangay
    and municipality but never says "Cebu" at all.

    This searches Bluesky using ONLY the dynamically generated
    multilingual disaster terms (no location anchor whatsoever), then
    confirms Cebu relevance per-candidate via the 3-level cascade
    (cascade_check_cebu_relevance) instead of requiring "Cebu" in the
    post text.

    The actual Bluesky search queries use ONLY the Tagalog/Cebuano dialect
    subset of the corpus, never the English WordNet-expanded terms: a
    bare English disaster word (e.g. "blaze", "fire") is also common,
    unrelated global vocabulary, so searching it with no location anchor
    at all pulled in large volumes of irrelevant global content (verified
    case: a UK "New Forest wildfire" post surfaced from a bare "blaze"
    search). The full multilingual set (English + dialect) is still used
    for the has_disaster_term content check below, since that's just
    matching against a candidate's own already-fetched text, not sent to
    Bluesky's search API. Terms shorter than 4 characters are excluded
    from search queries -- with no location anchor at all, a very short
    root term would still return an unusably large volume of content.
    """
    if not mongo_connected or db is None:
        raise RuntimeError("MongoDB is not connected.")

    if disaster_terms is None:
        disaster_terms = get_multilingual_disaster_terms()
        print("[AGAPAI LOG] Dynamically generated disaster dialect terms via selected model.")

    search_source_terms = get_dialect_only_disaster_terms()

    since_value = format_bluesky_date_bound(start_date)
    until_value = format_bluesky_date_bound(end_date, end_of_day=True)

    raw_posts_col = db["raw_posts"]
    existing_uris = set(raw_posts_col.distinct("uri"))
    skipped_already_saved = 0

    bluesky_since_value = resolve_incremental_since(raw_posts_col, fallback_since=since_value)
    used_incremental_fetch = bluesky_since_value != since_value
    print(
        f"[AGAPAI LOG] {'Incremental' if used_incremental_fetch else 'Full historical'} "
        f"cascade fetch: querying Bluesky since {bluesky_since_value}."
    )

    total_fetched = 0
    matched_count = 0
    discarded_count = 0
    seen_uris = set()

    search_terms = sorted({term for term in search_source_terms if len(term) >= 4})

    if include_barangays:
        # Bare (unanchored) barangay names, e.g. "Tabunok", "Pangdan": no
        # location term at all requires the literal word "Cebu" (the
        # anchored search in geography.py) or a specific disaster-term
        # match in Bluesky's own search index (which does exact-token
        # matching, not stemming -- confirmed live: searching "sunog"
        # never matches a post that only says "nasunog"). A barangay name
        # is, unlike a generic disaster word, inherently distinctive
        # enough to search bare with low noise (verified live: "Tabunok"
        # and "Pangdan" returned 8 and 3 total global results
        # respectively, each including the target post) -- Cebu relevance
        # is still confirmed downstream by the cascade, same as every
        # other candidate here.
        barangay_terms = {format_location_name(name) for name in PSGC_CEBU_BARANGAYS}
        search_terms = sorted(set(search_terms) | barangay_terms)

    for search_query in search_terms:
        try:
            search_results = search_bluesky_posts(
                search_query, max_posts, since=bluesky_since_value, until=until_value
            )
        except RuntimeError as search_error:
            print(f"[AGAPAI LOG] WARNING: search failed for '{search_query}': {search_error}")
            continue

        for post_view in search_results:
            post_uri = get_attr(post_view, "uri")
            if not post_uri or post_uri in seen_uris:
                continue
            if post_uri in existing_uris:
                seen_uris.add(post_uri)
                skipped_already_saved += 1
                continue
            seen_uris.add(post_uri)
            total_fetched += 1

            record = get_attr(post_view, "record")
            post_text = get_attr(record, "text", "") if record else get_attr(post_view, "text", "")
            author = get_attr(post_view, "author")
            author_did = get_attr(author, "did")
            author_handle = get_attr(author, "handle")

            is_cebu_relevant, _matched_level, _matches = cascade_check_cebu_relevance(
                post_text, author_did=author_did, author_handle=author_handle
            )
            lowered_text = (post_text or "").lower()
            has_disaster_term = any(
                term in lowered_text for term in disaster_terms if len(term) >= 3
            )

            if not (is_cebu_relevant and has_disaster_term):
                discarded_count += 1
                continue

            matched_count += 1
            raw_post_document = {
                "uri": post_uri,
                "author_did": author_did,
                "author_handle": author_handle,
                "text": post_text,
                "reply_parent_uri": get_reply_parent_uri(post_view),
                "created_at": get_attr(record, "created_at") if record else None,
                "retrieval_source": "cascade_disaster_term_filter",
                "date_range_start": start_date,
                "date_range_end": end_date,
            }
            raw_posts_col.update_one({"uri": post_uri}, {"$set": raw_post_document}, upsert=True)

    print(f"[AGAPAI LOG] Cascade search: total fetched {total_fetched}")
    print(f"[AGAPAI LOG] Cascade search: matched {matched_count}")
    print(f"[AGAPAI LOG] Cascade search: discarded {discarded_count}")
    print(f"[AGAPAI LOG] Cascade search: skipped {skipped_already_saved} already-saved posts.")

    return {
        "total_fetched": total_fetched,
        "matched": matched_count,
        "discarded": discarded_count,
        "skipped_already_saved": skipped_already_saved,
        "bluesky_since_value": bluesky_since_value,
        "used_incremental_fetch": used_incremental_fetch,
    }

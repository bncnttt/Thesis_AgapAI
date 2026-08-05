from datetime import datetime, timedelta, timezone
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
import pymongo

from agapai_api.bluesky import (
    build_disaster_search_queries,
    collect_graph_members_with_fallback,
    get_attr,
    search_keyword_posts,
)
from agapai_api.clients import client, mongo_connected, posts_col, users_col
from agapai_api.geography import extract_location_name, has_cebu_context
from agapai_api.keywords import DISASTER_KEYWORDS

router = APIRouter()


def parse_bluesky_datetime(value):
    if not value:
        return None

    clean_value = value.replace("Z", "+00:00")
    if "." in clean_value:
        base_part, nano_part = clean_value.split(".", 1)
        timezone_part = "+00:00" if "+" in nano_part or "-" in nano_part else ""
        clean_value = f"{base_part}.{nano_part[:3]}{timezone_part}"

    parsed = datetime.fromisoformat(clean_value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_date_filter(value, end_of_day=False):
    supported_formats = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%B %d %Y",
        "%b %d %Y",
    )

    cleaned_value = value.strip()
    parsed = None

    try:
        parsed = datetime.fromisoformat(cleaned_value)
    except ValueError:
        for date_format in supported_formats:
            try:
                parsed = datetime.strptime(cleaned_value, date_format)
                break
            except ValueError:
                continue

    if parsed is None:
        raise HTTPException(
            status_code=422,
            detail="Invalid date format. Use YYYY-MM-DD, MM/DD/YYYY, or Month DD YYYY.",
        )

    if parsed.tzinfo is None:
        if end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999000)
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def trim_list(value, graph_limit):
    if not isinstance(value, list):
        return value
    if graph_limit < 0:
        return value
    return value[:graph_limit]


def apply_graph_limit(document, graph_limit):
    if graph_limit < 0:
        return document

    for key in ("followers", "following", "mutual_ties"):
        if key in document:
            document[key] = trim_list(document[key], graph_limit)

    social_graph = document.get("social_graph")
    if isinstance(social_graph, dict):
        for key in ("followers", "following", "mutual_ties"):
            if key in social_graph:
                social_graph[key] = trim_list(social_graph[key], graph_limit)

    return document


def get_saved_disaster_data(
    posts_query=None,
    users_query=None,
    search_limit=-1,
    graph_limit=10,
    date_filter_applied_since=None,
    date_filter_applied_until=None,
):
    posts_query = posts_query or {}
    users_query = users_query or {}

    post_cursor = posts_col.find(posts_query).sort("created_at", -1)
    user_cursor = users_col.find(users_query).sort("fetched_at", -1)
    if search_limit >= 0:
        post_cursor = post_cursor.limit(search_limit)
        user_cursor = user_cursor.limit(search_limit)

    posts = []
    for document in post_cursor:
        document["_id"] = str(document["_id"])
        document = apply_graph_limit(document, graph_limit)
        posts.append(document)

    users = []
    for document in user_cursor:
        document["_id"] = str(document["_id"])
        document = apply_graph_limit(document, graph_limit)
        users.append(document)

    return {
        "status": "success",
        "source": "mongodb",
        "database_preview": {
            "date_filter_applied_since": date_filter_applied_since,
            "date_filter_applied_until": date_filter_applied_until,
            "search_limit": search_limit,
            "graph_limit": graph_limit,
            "posts_returned": len(posts),
            "users_returned": len(users),
        },
        "posts_total": len(posts),
        "users_total": len(users),
        "posts_collection": posts,
        "users_collection": users,
    }


@router.get("/disaster-alerts")
def get_disaster_posts(
    start: Optional[str] = None,
    end: Optional[str] = None,
    search_limit: int = -1,
    graph_limit: int = 10,
    force_refresh: bool = False,
):
    try:
        if not mongo_connected or posts_col is None or users_col is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB is not connected. Start MongoDB on localhost:27017 and restart the API.",
            )

        if not start and not end and not force_refresh:
            return get_saved_disaster_data(
                search_limit=search_limit,
                graph_limit=graph_limit,
            )

        if (start and not end) or (end and not start):
            raise HTTPException(
                status_code=422,
                detail="Both start and end query parameters are required.",
            )

        if start and end:
            since_dt_utc = parse_date_filter(start)
            until_dt_utc = parse_date_filter(end, end_of_day=True)
        else:
            # No explicit date range but a live refresh was requested (e.g. the
            # dashboard's "Load Data" button): default to the last 24 hours.
            until_dt_utc = datetime.now(timezone.utc)
            since_dt_utc = until_dt_utc - timedelta(hours=24)

        if since_dt_utc > until_dt_utc:
            raise HTTPException(
                status_code=422,
                detail="start date must be earlier than or equal to end date.",
            )

        since_value = since_dt_utc.isoformat(timespec="seconds").replace("+00:00", "Z")
        until_value = until_dt_utc.isoformat(timespec="seconds").replace("+00:00", "Z")

        if not force_refresh:
            saved_result = get_saved_disaster_data(
                posts_query={
                    "created_at": {
                        "$gte": since_value,
                        "$lte": until_value,
                    }
                },
                users_query={
                    "fetched_at": {
                        "$gte": since_value,
                        "$lte": until_value,
                    }
                },
                search_limit=search_limit,
                graph_limit=graph_limit,
                date_filter_applied_since=since_value,
                date_filter_applied_until=until_value,
            )

            if saved_result["posts_total"] > 0 or saved_result["users_total"] > 0:
                return saved_result

        posts_collection = []
        users_collection = []
        seen_users = set()
        seen_posts = set()
        graph_cache = {}
        disaster_texts = []

        inserted_posts_count = 0
        inserted_users_count = 0
        skipped_outside_date_window = 0

        for keyword in DISASTER_KEYWORDS:
            for search_query in build_disaster_search_queries(keyword):
                for post_view in search_keyword_posts(
                    search_query,
                    search_limit,
                    since=since_value,
                    until=until_value,
                ):
                    post_uri = get_attr(post_view, "uri")
                    if post_uri in seen_posts:
                        continue

                    record = get_attr(post_view, "record")
                    post_text = get_attr(record, "text", "")

                    if not record or not post_text:
                        continue

                    keyword_found = None
                    for kw in DISASTER_KEYWORDS:
                        if re.search(r"\b" + re.escape(kw) + r"\b", post_text.lower()):
                            keyword_found = kw
                            break

                    if not keyword_found:
                        continue

                    is_cebu_post, _cebu_matches = has_cebu_context(post_text)
                    if not is_cebu_post:
                        continue

                    seen_posts.add(post_uri)

                    author = get_attr(post_view, "author")
                    author_did = get_attr(author, "did")
                    author_handle = get_attr(author, "handle")
                    display_name = get_attr(author, "display_name", author_handle)
                    created_at_raw = get_attr(record, "created_at")

                    try:
                        created_dt_utc = parse_bluesky_datetime(created_at_raw)
                        if (
                            not created_dt_utc
                            or created_dt_utc < since_dt_utc
                            or created_dt_utc > until_dt_utc
                        ):
                            skipped_outside_date_window += 1
                            continue

                        collected_dt_utc = datetime.now(timezone.utc)

                        pht_tz = timezone(timedelta(hours=8))
                        created_dt_local = created_dt_utc.astimezone(pht_tz)
                        collected_dt_local = collected_dt_utc.astimezone(pht_tz)

                        t_created = created_dt_local.strftime("%A, %B %d, %Y, %I:%M:%S %p PHT")
                        t_collected = collected_dt_local.strftime("%A, %B %d, %Y, %I:%M:%S %p PHT")

                        time_created_readable_value = t_created.replace(", 0", ", ")
                        time_collected_readable_value = t_collected.replace(", 0", ", ")

                        created_at_value = created_dt_utc.isoformat().replace("+00:00", "Z")
                        collected_at_value = collected_dt_utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")
                    except Exception:
                        time_created_readable_value = "Unknown Date/Time"
                        time_collected_readable_value = "Unknown Date/Time"
                        created_at_value = created_at_raw
                        collected_at_value = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

                    detected_location = extract_location_name(post_text)
                    reply_count = get_attr(post_view, "reply_count", 0)
                    repost_count = get_attr(post_view, "repost_count", 0)
                    like_count = get_attr(post_view, "like_count", 0)

                    official_follower_count = 0
                    official_following_count = 0

                    if author_did in graph_cache:
                        graph_data = graph_cache[author_did]
                    else:
                        followers_list = []
                        following_list = []
                        mutual_ties = []

                        try:
                            actor_profile = client.app.bsky.actor.get_profile(params={"actor": author_did})
                            official_follower_count = int(get_attr(actor_profile, "followers_count", 0))
                            official_following_count = int(get_attr(actor_profile, "follows_count", 0))
                        except Exception:
                            pass

                        graph_member_limit = None if graph_limit < 0 else max(0, min(graph_limit, 500))

                        if graph_member_limit is None or graph_member_limit > 0:
                            try:
                                following_list = collect_graph_members_with_fallback(
                                    client.app.bsky.graph.get_follows,
                                    author_did,
                                    author_handle,
                                    "follows",
                                    graph_member_limit,
                                )
                            except Exception:
                                pass

                            try:
                                followers_list = collect_graph_members_with_fallback(
                                    client.app.bsky.graph.get_followers,
                                    author_did,
                                    author_handle,
                                    "followers",
                                    graph_member_limit,
                                )
                            except Exception:
                                pass

                        if following_list and followers_list:
                            follower_set = set(followers_list)
                            following_set = set(following_list)
                            mutual_ties = sorted(follower_set.intersection(following_set))

                        graph_data = {
                            "follower_count": official_follower_count,
                            "following_count": official_following_count,
                            "followers": followers_list,
                            "following": following_list,
                            "mutual_ties": mutual_ties,
                        }
                        graph_cache[author_did] = graph_data

                    followers_list = graph_data["followers"]
                    following_list = graph_data["following"]
                    mutual_ties = graph_data["mutual_ties"]

                    post_document = {
                        "_id": post_uri,
                        "author_did": author_did,
                        "author_handle": author_handle,
                        "posted_by": display_name,
                        "text": post_text,
                        "disaster_post_text": post_text,
                        "retrieval_source": "search_posts",
                        "search_query": search_query,
                        "created_at": created_at_value,
                        "time_created_readable": time_created_readable_value,
                        "collected_at": collected_at_value,
                        "time_collected_readable": time_collected_readable_value,
                        "keyword_matched": [keyword_found],
                        "reply_count": reply_count,
                        "repost_count": repost_count,
                        "like_count": like_count,
                        "has_location_clue": True if detected_location else False,
                        "location_name": detected_location if detected_location else "Unspecified Location",
                        "processed": False,
                        "social_graph": {
                            "follower_count": len(followers_list) if followers_list else 0,
                            "following_count": len(following_list) if following_list else 0,
                            "followers": followers_list,
                            "following": following_list,
                            "mutual_ties": mutual_ties,
                        },
                    }
                    posts_collection.append(post_document)
                    disaster_texts.append(
                        {
                            "author_did": author_did,
                            "author_handle": author_handle,
                            "posted_by": display_name,
                            "text": post_text,
                            "keyword_matched": keyword_found,
                            "location_name": detected_location if detected_location else "Unspecified Location",
                            "retrieval_source": "search_posts",
                            "search_query": search_query,
                            "created_at": created_at_value,
                            "time_created_readable": time_created_readable_value,
                        }
                    )

                    try:
                        posts_col.insert_one(post_document)
                        inserted_posts_count += 1
                    except pymongo.errors.DuplicateKeyError:
                        pass

                    if author_did not in seen_users:
                        user_document = {
                            "_id": author_did,
                            "handle": author_handle,
                            "display_name": display_name,
                            "follower_count": len(followers_list) if followers_list else 0,
                            "following_count": len(following_list) if following_list else 0,
                            "mutual_tie_count": len(mutual_ties) if mutual_ties else 0,
                            "followers": followers_list,
                            "following": following_list,
                            "mutual_ties": mutual_ties,
                            "fetched_at": collected_at_value,
                        }
                        users_collection.append(user_document)
                        seen_users.add(author_did)

                        try:
                            users_col.insert_one(user_document)
                            inserted_users_count += 1
                        except pymongo.errors.DuplicateKeyError:
                            pass

        return {
            "status": "success",
            "source": "bluesky_collection",
            "database_preview": {
                "date_filter_applied_since": since_value,
                "date_filter_applied_until": until_value,
                "date_filter_start": start,
                "date_filter_end": end,
                "search_limit": search_limit,
                "graph_limit": graph_limit,
                "search_queries_per_keyword": 1,
                "disaster_texts_retrieved": len(disaster_texts),
                "posts_collected_this_cycle": len(posts_collection),
                "users_collected_this_cycle": len(users_collection),
                "newly_saved_to_mongodb_posts": inserted_posts_count,
                "newly_saved_to_mongodb_users": inserted_users_count,
                "skipped_outside_date_window": skipped_outside_date_window,
            },
            "disaster_texts": disaster_texts,
            "posts_collection": posts_collection,
            "users_collection": users_collection,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"API Processing Error Trace: {str(e)}")

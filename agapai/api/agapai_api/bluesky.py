from agapai_api.clients import client
from agapai_api.config import DEFAULT_GRAPH_MEMBER_LIMIT, GRAPH_PAGE_LIMIT, SEARCH_POSTS_PAGE_LIMIT


def get_attr(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def search_keyword_posts(keyword, max_posts, since=None, until=None):
    posts = []
    cursor = None
    while True:
        remaining = None if max_posts is None or max_posts < 0 else max_posts - len(posts)
        if remaining is not None and remaining <= 0:
            break

        try:
            params = {
                "q": keyword,
                "limit": SEARCH_POSTS_PAGE_LIMIT if remaining is None else min(SEARCH_POSTS_PAGE_LIMIT, remaining),
            }
            if since:
                params["since"] = since
            if until:
                params["until"] = until
            if cursor:
                params["cursor"] = cursor

            response = client.app.bsky.feed.search_posts(params=params)
        except Exception as search_err:
            error_message = repr(search_err)
            print(f"Search API Call failure for '{keyword}': {error_message}")
            raise RuntimeError(
                f"Bluesky search failed for keyword '{keyword}': {error_message}"
            ) from search_err

        page_posts = get_attr(response, 'posts', []) or []
        if not page_posts:
            break

        posts.extend(page_posts)
        cursor = get_attr(response, 'cursor')
        if not cursor:
            break

    return posts


def build_disaster_search_queries(keyword):
    return [keyword]


def collect_graph_members(fetch_method, actor, collection_name, max_members=DEFAULT_GRAPH_MEMBER_LIMIT):
    members = []
    cursor = None
    while True:
        try:
            response = fetch_method(
                params={"actor": actor, "limit": GRAPH_PAGE_LIMIT, "cursor": cursor}
            )
            page_members = get_attr(response, collection_name, []) or []
            for member in page_members:
                member_did = get_attr(member, 'did')
                member_handle = get_attr(member, 'handle')
                if member_did:
                    members.append(member_did)
                elif member_handle:
                    members.append(member_handle)
                if max_members is not None and max_members > 0 and len(members) >= max_members:
                    return members
            cursor = get_attr(response, 'cursor')
            if not cursor or not page_members:
                break
        except Exception:
            break
    return members


def collect_graph_members_with_fallback(fetch_method, actor_did, actor_handle, collection_name, max_members):
    members = []
    seen_members = set()
    seen_actors = set()
    actors_to_try = [actor_did, actor_handle]
    for actor in actors_to_try:
        if not actor or actor in seen_actors:
            continue
        seen_actors.add(actor)
        actor_members = collect_graph_members(fetch_method, actor, collection_name, max_members)
        for member in actor_members:
            if member not in seen_members:
                members.append(member)
                seen_members.add(member)
            if max_members is not None and max_members > 0 and len(members) >= max_members:
                return members
    return members

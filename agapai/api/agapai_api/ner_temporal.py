import re
import dateparser
from datetime import datetime

# Common ways disaster posts mention time, in English/Tagalog.
# Order matters slightly -- more specific phrases first, so "since yesterday"
# gets captured whole rather than matched only on "yesterday".
RELATIVE_TIME_PATTERNS = [
    r"\bsince yesterday\b",
    r"\bkanina\b", r"\bkagabi\b", r"\bngayong umaga\b", r"\bngayong gabi\b",
    r"\bngayon\b", r"\bbukas\b", r"\bkahapon\b",
    r"\bearlier today\b", r"\byesterday\b", r"\btonight\b",
    r"\bthis morning\b", r"\bright now\b", r"\bjust now\b",
]

# Explicit date/time formats, e.g. "11pm", "Aug 10", "7:00 AM".
EXPLICIT_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?|"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{1,2}(,?\s*\d{4})?|"
    r"\d{1,2}(:\d{2})?\s*(am|pm))\b",
    re.IGNORECASE,
)


def _dedupe_overlapping(phrases):
    """
    Drops any phrase fully contained inside a longer already-found phrase
    (e.g. drops standalone 'yesterday' once 'since yesterday' is already found).
    """
    unique = []
    for phrase in sorted(set(phrases), key=len, reverse=True):
        if not any(phrase.lower() in longer.lower() for longer in unique):
            unique.append(phrase)
    return unique


def extract_temporal_expressions(text, post_created_at=None):
    """
    Finds date/time phrases the AUTHOR wrote in the post text -- not the
    post's created_at metadata.

    post_created_at: the post's actual Bluesky creation datetime (a Python
    datetime object). If given, relative phrases like 'yesterday' or
    'kagabi' are resolved relative to WHEN THE POST WAS WRITTEN, not
    whenever this function happens to run. Without it, results would be
    wrong for any post processed more than a few hours after it was posted.

    dateparser has weak Tagalog support, so Tagalog relative phrases are
    matched by pattern only and left unnormalized (normalized_datetime =
    None) when dateparser can't resolve them.
    """
    if not text:
        return []

    found_phrases = []
    for pattern in RELATIVE_TIME_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found_phrases.append(match.group(0))
    for match in EXPLICIT_DATE_PATTERN.finditer(text):
        found_phrases.append(match.group(0))

    found_phrases = _dedupe_overlapping(found_phrases)

    settings = {"RELATIVE_BASE": post_created_at} if post_created_at else None

    results = []
    for phrase in found_phrases:
        # dateparser doesn't understand filler words like "since" attached
        # to a relative phrase -- strip them for parsing, but keep the
        # original wording in raw_phrase for display purposes.
        parseable_phrase = re.sub(r"^since\s+", "", phrase, flags=re.IGNORECASE)
        parsed = dateparser.parse(parseable_phrase, languages=["en"], settings=settings)
        results.append({
            "raw_phrase": phrase,
            "normalized_datetime": parsed.isoformat() if parsed else None,
        })
    return results


def resolve_post_datetime(text, post_created_at=None, post_time_created_readable=None):
    """
    text: the post's raw text
    post_created_at: real Bluesky created_at string (ISO format, e.g. from
        Lopez's post_document["created_at"]) -- used both as the anchor for
        relative phrases AND as the fallback display value
    post_time_created_readable: real Bluesky readable string, e.g.
        post_document["time_created_readable"]

    Returns one of two shapes:

    Author stated a time in the text:
        {
            "source": "extracted_from_text",
            "expressions": [{"raw_phrase": ..., "normalized_datetime": ...}, ...],
            "extracted_datetime": None,
        }

    Author did NOT state a time -- falls back to the post's real
    Bluesky timestamp instead of showing nothing:
        {
            "source": "post_metadata_fallback",
            "expressions": None,
            "extracted_datetime": None,
            "fallback_datetime": post_created_at,
            "fallback_readable": post_time_created_readable,
        }
    """
    parsed_created_at = None
    if post_created_at:
        try:
            parsed_created_at = datetime.fromisoformat(post_created_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            parsed_created_at = None

    expressions = extract_temporal_expressions(text, post_created_at=parsed_created_at)

    if expressions:
        return {
            "source": "extracted_from_text",
            "expressions": expressions,
            "extracted_datetime": None,
        }

    return {
        "source": "post_metadata_fallback",
        "expressions": None,
        "extracted_datetime": None,
        "fallback_datetime": post_created_at,
        "fallback_readable": post_time_created_readable,
    }
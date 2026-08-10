import os

import pymongo
from atproto import Client

from agapai_api.config import BLUESKY_HANDLE, BLUESKY_PASSWORD

client = Client()
mongo_client = None
db = None
posts_col = None
users_col = None
mongo_connected = False
bluesky_authenticated = False
bluesky_auth_error = None


def authenticate_bluesky():
    global bluesky_authenticated, bluesky_auth_error

    try:
        if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
            raise RuntimeError("BLUESKY_HANDLE and BLUESKY_PASSWORD must be set.")

        print(f"Attempting API login for {BLUESKY_HANDLE}...")
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        bluesky_authenticated = True
        bluesky_auth_error = None
        print("Login successful! Network connectivity verified.")
        return True
    except Exception as e:
        bluesky_authenticated = False
        bluesky_auth_error = repr(e)
        print(f"CRITICAL WARNING: Could not authenticate with Bluesky: {bluesky_auth_error}")
        return False


def is_bluesky_authenticated():
    return bluesky_authenticated


def get_bluesky_auth_error():
    return bluesky_auth_error

try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
    db = mongo_client["AgapAI_Database_Final"]
    mongo_client.admin.command("ping")

    existing_collections = db.list_collection_names()
    if "posts" not in existing_collections:
        db.create_collection("posts")
    if "users" not in existing_collections:
        db.create_collection("users")

    posts_col = db["posts"]
    users_col = db["users"]
    mongo_connected = True
    print("STATUS: Connected to MongoDB database AgapAI_Database_Final with posts and users collections.")
except Exception as e:
    print(f"CRITICAL WARNING: MongoDB Connection Failed: {e}")

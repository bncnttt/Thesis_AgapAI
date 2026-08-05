import os

import pymongo
from atproto import Client

client = Client()
mongo_client = None
db = None
posts_col = None
users_col = None
mongo_connected = False

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

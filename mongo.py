from pymongo import MongoClient
import os

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))

client = MongoClient(MONGO_HOST, MONGO_PORT)
db = client['charity']
likes_collection = db['comment_likes']
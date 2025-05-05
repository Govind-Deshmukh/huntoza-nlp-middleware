from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client.get_database()
users_collection = db.users
plans_collection = db.plans

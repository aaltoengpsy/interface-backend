import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
db_collection_name = os.getenv('DATABASE_NAME')

def connect():
    client = MongoClient(db_url)
    return client[db_collection_name]

def insert(item, collection):
    try:
        if entry_exists(item['_id'], collection) == False:
            collection.insert_one(item)
            return True
        return False
    except Exception as e:
        return False
    
def entry_exists(pid, collection):
    try:
        if collection.count_documents({'_id': pid}, limit = 1) == 0:
            return False
        return True
    except Exception as e:
        return True
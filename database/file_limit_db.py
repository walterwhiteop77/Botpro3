"""
File Limit Database
-------------------
Ported from Auto-Filter-Bot-SiliconBotz (database/extra_db.py) into
DreamxBotz. Tracks a per-user daily file download counter which is
reset once a day by plugins.__init__.reset_file_limits_daily.
"""

from pymongo import MongoClient
from info import DATABASE_URI, DATABASE_NAME


class FileLimitDatabase:
    def __init__(self, uri: str, db_name: str):
        client = MongoClient(uri)
        mydb = client[db_name]
        self.file_limit_collection = mydb["file_limits"]

    # ---------- read ----------
    def get_file_limit(self, user_id: int) -> int:
        user = self.file_limit_collection.find_one({"user_id": user_id})
        return user.get("file_count", 0) if user else 0

    def get_all_file_limits(self) -> list:
        return list(self.file_limit_collection.find({}))

    # ---------- write ----------
    def increment_file_limit(self, user_id: int):
        self.file_limit_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"file_count": 1}},
            upsert=True,
        )

    def reset_file_limit(self, user_id: int):
        self.file_limit_collection.update_one(
            {"user_id": user_id},
            {"$set": {"file_count": 0}},
            upsert=True,
        )

    def reset_all_file_limits(self):
        self.file_limit_collection.update_many({}, {"$set": {"file_count": 0}})


filelimitdb = FileLimitDatabase(DATABASE_URI, DATABASE_NAME)

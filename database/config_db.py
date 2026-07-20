from motor.motor_asyncio import AsyncIOMotorClient
from info import DATABASE_URI
from datetime import datetime


class Database:
    def __init__(self, uri, db_name):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.col = self.db.user
        self.config_col = self.db.configuration

    async def update_top_messages(self, user_id, message_text):
        user = await self.col.find_one({"user_id": user_id, "messages.text": message_text})

        if not user:
            await self.col.update_one(
                {"user_id": user_id},
                {"$push": {"messages": {"text": message_text, "count": 1}}},
                upsert=True
            )
        else:
            await self.col.update_one(
                {"user_id": user_id, "messages.text": message_text},
                {"$inc": {"messages.$.count": 1}}
            )

    async def get_top_messages(self, limit=30):
        pipeline = [
            {"$unwind": "$messages"},
            {"$group": {"_id": "$messages.text", "count": {"$sum": "$messages.count"}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        results = await self.col.aggregate(pipeline).to_list(limit)
        return [result['_id'] for result in results]

    async def delete_all_messages(self):
        await self.col.delete_many({})

    # ---------- Advertisement (Set Ads feature) ----------
    def _create_configuration_data(self, advertisement=None):
        return {"advertisement": advertisement}

    async def _ensure_config(self):
        config = await self.config_col.find_one({})
        if not config:
            await self.config_col.insert_one(self._create_configuration_data())
            config = await self.config_col.find_one({})
        return config

    async def update_advirtisment(self, ads_string=None, ads_name=None,
                                  expiry=None, impression=None, ads_link=None):
        config = await self._ensure_config()
        advertisement = config.get("advertisement") or {}
        advertisement["ads_string"] = ads_string
        advertisement["ads_name"] = ads_name
        advertisement["expiry"] = expiry
        advertisement["impression_count"] = impression
        advertisement["ads_link"] = ads_link
        await self.config_col.update_one(
            {}, {"$set": {"advertisement": advertisement}}, upsert=True
        )

    async def update_advirtisment_impression(self, impression=None):
        await self.config_col.update_one(
            {}, {"$set": {"advertisement.impression_count": impression}}, upsert=True
        )

    async def get_advirtisment(self):
        config = await self._ensure_config()
        advertisement = config.get("advertisement")
        if advertisement:
            return (
                advertisement.get("ads_string"),
                advertisement.get("ads_name"),
                advertisement.get("impression_count"),
            )
        return None, None, None

    async def get_ads_link(self):
        config = await self._ensure_config()
        advertisement = config.get("advertisement") or {}
        return advertisement.get("ads_link")

    async def clear_advertisement(self):
        await self.config_col.update_one(
            {}, {"$set": {"advertisement": None}}, upsert=True
        )

    async def reset_advertisement_if_expired(self):
        config = await self.config_col.find_one({})
        if not config:
            return
        advertisement = config.get("advertisement")
        if not advertisement:
            return
        impression_count = advertisement.get("impression_count")
        expiry = advertisement.get("expiry")
        if impression_count == 0 or (expiry and datetime.now() > expiry):
            await self.clear_advertisement()


mdb = Database(DATABASE_URI, "admin_database")

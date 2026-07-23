"""
File Limit Database
-------------------
Tracks per-user daily file download counters, and supports per-group
overrides so a group owner/admin can configure their own file limit
independent of the global config.

Counts are stored per (user_id, group_id) pair so a user's quota is
group-specific. group_id = 0 is used when no originating group is
available (e.g. legacy rows / direct PM starts).

Group overrides live in a separate collection ``file_limit_groups``:
    { group_id: int, enabled: bool, limit: int }
If no doc exists for a group, the bot falls back to the global
``IS_FILE_LIMIT`` / ``FILES_LIMIT`` from ``info.py``.
"""

from pymongo import MongoClient
from info import DATABASE_URI, DATABASE_NAME, IS_FILE_LIMIT, FILES_LIMIT


class FileLimitDatabase:
    def __init__(self, uri: str, db_name: str):
        client = MongoClient(uri)
        mydb = client[db_name]
        self.file_limit_collection = mydb["file_limits"]
        self.group_cfg_collection = mydb["file_limit_groups"]

    # ---------- per-user counters (group-scoped) ----------
    def get_file_limit(self, user_id: int, group_id: int = 0) -> int:
        doc = self.file_limit_collection.find_one(
            {"user_id": user_id, "group_id": int(group_id)}
        )
        if doc:
            return doc.get("file_count", 0)
        # Backward compat: legacy rows only had user_id (no group_id) and
        # correspond to group_id == 0.
        if int(group_id) == 0:
            legacy = self.file_limit_collection.find_one(
                {"user_id": user_id, "group_id": {"$exists": False}}
            )
            if legacy:
                return legacy.get("file_count", 0)
        return 0

    def get_all_file_limits(self) -> list:
        return list(self.file_limit_collection.find({}))

    def increment_file_limit(self, user_id: int, group_id: int = 0):
        self.file_limit_collection.update_one(
            {"user_id": user_id, "group_id": int(group_id)},
            {"$inc": {"file_count": 1}},
            upsert=True,
        )

    def reset_file_limit(self, user_id: int, group_id: int = None):
        if group_id is None:
            # reset the user across every group
            self.file_limit_collection.update_many(
                {"user_id": user_id}, {"$set": {"file_count": 0}}
            )
        else:
            self.file_limit_collection.update_one(
                {"user_id": user_id, "group_id": int(group_id)},
                {"$set": {"file_count": 0}},
                upsert=True,
            )

    def reset_all_file_limits(self, group_id: int = None):
        if group_id is None:
            self.file_limit_collection.update_many({}, {"$set": {"file_count": 0}})
        else:
            self.file_limit_collection.update_many(
                {"group_id": int(group_id)}, {"$set": {"file_count": 0}}
            )

    # ---------- per-group config overrides ----------
    def get_group_config(self, group_id: int) -> dict:
        """Return the raw override doc for a group, or {} if none."""
        doc = self.group_cfg_collection.find_one({"group_id": int(group_id)})
        return doc or {}

    def set_group_config(self, group_id: int, enabled: bool = None, limit: int = None, action: str = None):
        update = {}
        if enabled is not None:
            update["enabled"] = bool(enabled)
        if limit is not None:
            update["limit"] = int(limit)
        if action is not None:
            act = str(action).strip().lower()
            if act not in ("redirect", "verify"):
                act = "redirect"
            update["action"] = act
        if not update:
            return
        self.group_cfg_collection.update_one(
            {"group_id": int(group_id)},
            {"$set": update},
            upsert=True,
        )

    def clear_group_config(self, group_id: int):
        """Remove the group's override so it inherits the global config again."""
        self.group_cfg_collection.delete_one({"group_id": int(group_id)})

    def get_effective_limit(self, group_id: int) -> tuple:
        """
        Resolve the effective (enabled, limit) for a group.
        Group override wins; otherwise fall back to global config.
        Returns (enabled: bool, limit: int).
        """
        cfg = self.get_group_config(int(group_id)) if group_id else {}
        enabled = cfg.get("enabled", IS_FILE_LIMIT)
        limit = int(cfg.get("limit", FILES_LIMIT))
        return bool(enabled), int(limit)

    def get_effective_action(self, group_id: int) -> str:
        """
        Over-limit action for a group. Group override wins; otherwise
        defaults to 'redirect'. Values: 'redirect' | 'verify'.
        """
        cfg = self.get_group_config(int(group_id)) if group_id else {}
        action = str(cfg.get("action", "redirect")).lower()
        return action if action in ("redirect", "verify") else "redirect"


filelimitdb = FileLimitDatabase(DATABASE_URI, DATABASE_NAME)

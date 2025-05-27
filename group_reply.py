import json
import random
import logging
from datetime import datetime, timezone
from pathlib import Path

import botpy
from botpy.ext.cog_yaml import read
from botpy.message import GroupMessage

# Constants
CONFIG_PATH = Path(__file__).parent / "config.yaml"
DATA_FILE = Path(__file__).parent / "bread.json"
COOLDOWN_SECONDS = 5400  # 1.5 hours
WEEKEND_DAYS = {5, 6}  # Saturday, Sunday

# Configure logging
logger = logging.get_logger(__name__)

class BreadBot(botpy.Client):
    """
    A Bot for buying, robbing, and ranking virtual breads within a group chat.
    """
    def __init__(self, appid: str, secret: str, *, intents: botpy.Intents):
        super().__init__(appid=appid, secret=secret, intents=intents)
        self.config = read(CONFIG_PATH)
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Load user data from JSON file, handling missing or invalid files."""
        if not DATA_FILE.exists():
            return {}
        try:
            content = DATA_FILE.read_text(encoding="utf-8")
            return json.loads(content) if content.strip() else {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load data file: %s", exc)
            return {}

    def _save_data(self) -> None:
        """Persist user data to JSON file with pretty formatting."""
        try:
            DATA_FILE.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            logger.error("Failed to save data file: %s", exc)

    async def on_ready(self):
        logger.info("Bot %s is ready.", self.robot.name)

    async def on_group_at_message_create(self, message: GroupMessage):
        command, *args = message.content.strip().split()
        handlers = {
            "/买面包": self._handle_buy,
            "/抢面包": self._handle_rob,
            "/排行榜": self._handle_rank,
        }
        handler = handlers.get(command)
        if handler:
            await handler(message, *args)

    async def _handle_buy(self, message: GroupMessage, *args):
        user_id = message.author.member_openid
        now_ts = datetime.now(timezone.utc).timestamp()

        # Register new user with nickname
        if user_id not in self.data:
            if not args:
                return await self._reply(
                    message,
                    "首次购买请使用：/买面包 <昵称> （昵称最长8字符，不含空格）"
                )
            nickname = args[0]
            if " " in nickname or len(nickname) > 8:
                return await self._reply(message, "无效的昵称，长度不超过8且不含空格。")
            if any(u["id"] == nickname for u in self.data.values()):
                return await self._reply(message, f"昵称‘{nickname}’已被使用。")
            self.data[user_id] = {
                "id": nickname,
                "number": 0,
                "last_claim": 0,
                "last_rob": 0,
            }

        user_data = self.data[user_id]
        elapsed = now_ts - user_data["last_claim"]

        # Buying only allowed on weekends after cooldown
        if elapsed >= COOLDOWN_SECONDS and datetime.now().weekday() in WEEKEND_DAYS:
            breads = random.randint(1, 3)
            user_data["number"] += breads
            user_data["last_claim"] = now_ts
            self._save_data()
            await self._reply(
                message,
                f"成功购买 {breads} 个面包，当前拥有 {user_data['number']} 个。"
            )
        else:
            remaining = max(0, COOLDOWN_SECONDS - int(elapsed))
            await self._reply(
                message,
                f"购买冷却中，还需等待 {remaining} 秒。"
            )

    async def _handle_rob(self, message: GroupMessage, *args):
        user_id = message.author.member_openid
        now_ts = datetime.now(timezone.utc).timestamp()

        if user_id not in self.data:
            return await self._reply(message, "请先购买面包后再尝试抢夺。")
        if not args:
            return await self._reply(message, "命令格式：/抢面包 <目标昵称>")

        target = args[0]
        target_data = next((u for u in self.data.values() if u["id"] == target), None)
        if not target_data:
            return await self._reply(message, f"未找到用户 {target}。")

        elapsed = now_ts - self.data[user_id]["last_rob"]
        if elapsed < COOLDOWN_SECONDS:
            remaining = COOLDOWN_SECONDS - int(elapsed)
            return await self._reply(
                message,
                f"抢夺冷却中，还需等待 {remaining} 秒。"
            )

        amount = random.randint(1, 3)
        if target_data["number"] <= 0:
            return await self._reply(message, f"目标 {target} 没有面包可抢。")

        success = random.random() < 0.85
        if success:
            stolen = min(amount, target_data["number"])
            target_data["number"] -= stolen
            self.data[user_id]["number"] += stolen
            self.data[user_id]["last_rob"] = now_ts
            self._save_data()
            await self._reply(
                message,
                f"抢到 {stolen} 个面包，当前拥有 {self.data[user_id]['number']} 个，\n对方剩余 {target_data['number']} 个。"
            )
        else:
            await self._reply(message, f"抢夺失败，被 {target} 抵抗。")

    async def _handle_rank(self, message: GroupMessage, *args):
        ranks = sorted(self.data.values(), key=lambda x: x["number"], reverse=True)
        if not ranks:
            return await self._reply(message, "暂无数据。")
        lines = [f"{i+1}. {u['id']} — {u['number']} 个" for i, u in enumerate(ranks)]
        await self._reply(message, "\n".join(lines))

    async def _reply(self, message: GroupMessage, content: str):
        """Helper to send a text reply in the group chat."""
        return await message._api.post_group_message(
            group_openid=message.group_openid,
            msg_type=0,
            msg_id=message.id,
            content=content
        )

def main():
    intents = botpy.Intents(public_messages=True)
    config = read(CONFIG_PATH)
    client = BreadBot(
        appid=config["appid"],
        secret=config["secret"],
        intents=intents,
    )
    client.run()

if __name__ == "__main__":
    main()

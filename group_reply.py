import asyncio
import os
import json
from datetime import datetime
import random

import botpy
from botpy import logging
from botpy.ext.cog_yaml import read
from botpy.message import GroupMessage, Message

test_config = read(os.path.join(os.path.dirname(__file__), "config.yaml"))

_log = logging.get_logger()

# {<"userid">: {"id": <"id">", number": 1, "last_claim": 1, "last_rob" = 1}}

bread = "bread.json"


class MyClient(botpy.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Open the file for reading and appending
        with open(bread, 'r') as file:
            try:
                # Check if the file is empty before attempting to load JSON data
                file.seek(0)
                if file.read(1):
                    file.seek(0)
                    self.data = json.load(file)
                else:
                    self.data = {}
            except json.JSONDecodeError:
                # Handle the case where the file is not valid JSON
                self.data = {}

    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")

    async def on_group_at_message_create(self, message: GroupMessage):
        now = datetime.now()
        user = message.author.member_openid
        content = message.content.strip().split()
        if len(content) == 0:
            return
        if content[0] == "/买面包":
            if not (user in self.data):
                if len(content) < 2:
                    messageResult = await message._api.post_group_message(
                        group_openid=message.group_openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=f"\n第一次买面包需要附上昵称: /买面包 <id> (id 不能有空格)"
                    )
                    return
                if isinstance(content[1], str):
                    if not any(user_data.get('id') == content[1] for user_data in self.data.values()):
                        if len(content[1]) <=8:
                            self.data[user] = {"id": content[1], "number": 0, 'last_claim': 0, "last_rob": 0}
                        else:
                            messageResult = await message._api.post_group_message(
                                group_openid=message.group_openid,
                                msg_type=0,
                                msg_id=message.id,
                                content=f"id长度应小于8"
                            )
                    else:
                        messageResult = await message._api.post_group_message(
                            group_openid=message.group_openid,
                            msg_type=0,
                            msg_id=message.id,
                            content=f"id已被占用"
                        )
                else:
                    messageResult = await message._api.post_group_message(
                        group_openid=message.group_openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=f"格式错误：/买面包 <id> (id 不能有空格)"
                    )

            if user in self.data:
                if (now.weekday() == 5 or now.weekday() == 6) and (
                        (now.timestamp() - self.data[user]["last_claim"]) > 36000):
                    number_obtained = random.randint(1, 3)
                    self.data[user]["number"] += number_obtained
                    self.data[user]["last_claim"] = now.timestamp()
                    with open(bread, 'w') as file:
                        json.dump(self.data, file)
                        file.flush()

                    messageResult = await message._api.post_group_message(
                        group_openid=message.group_openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=f"\n买了{number_obtained}个面包\n当前拥有{self.data[user]['number']}个面包"
                    )
                else:
                    messageResult = await message._api.post_group_message(
                        group_openid=message.group_openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=f"现在还不能买面包哦~"
                    )
        elif content[0] == "/抢面包":
            if now.timestamp() - self.data[user]["last_rob"] < 5400:
                messageResult = await message._api.post_group_message(
                    group_openid=message.group_openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=f"现在还不能抢面包哦"
                )
                return
            if len(content) >= 2:
                if any(user_data.get('id') == content[1] for user_data in self.data.values()):
                    robbed = random.randint(1, 3)
                    for user_data in self.data.values():
                        if user_data.get('id') == content[1]:
                            if user_data['number'] - robbed > 0:
                                if random.random() < 0.85:
                                    user_data['number'] -= robbed
                                    self.data[user]['number'] += robbed
                                    self.data[user]['last_rob'] = now.timestamp()
                                    with open(bread, 'w') as file:
                                        json.dump(self.data, file)
                                        file.flush()

                                    messageResult = await message._api.post_group_message(
                                        group_openid=message.group_openid,
                                        msg_type=0,
                                        msg_id=message.id,
                                        content=f"\n抢了{robbed}个面包\n当前拥有{self.data[user]['number']}个面包\n{content[1]}还剩{user_data['number']}个面包"
                                    )

                                else:
                                    messageResult = await message._api.post_group_message(
                                        group_openid=message.group_openid,
                                        msg_type=0,
                                        msg_id=message.id,
                                        content=f"\n没抢到面包，被{content[1]}揍了一顿"
                                    )
                            else:
                                messageResult = await message._api.post_group_message(
                                    group_openid=message.group_openid,
                                    msg_type=0,
                                    msg_id=message.id,
                                    content=f"\n{content[1]}太穷了，抢抢别人吧qaq"
                                )
                else:
                    messageResult = await message._api.post_group_message(
                        group_openid=message.group_openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=f"未找到用户{content[1]}"
                    )
            else:
                messageResult = await message._api.post_group_message(
                    group_openid=message.group_openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=f"格式错误: /抢面包 <id>"
                )
        elif content[0] == '/排行榜':
            bread_rank = dict(sorted(self.data.items(), key=lambda item: item[1]['number'], reverse=True))
            output = "\n"
            for key, value in bread_rank.items():
                output += f"{value['id']}: {value['number']}\n"
            messageResult = await message._api.post_group_message(
                group_openid=message.group_openid,
                msg_type=0,
                msg_id=message.id,
                content=f"{output}"
            )

            # _log.info(messageResult)
            # print(f"author:{message.author} \n content:{message.content} \n id:{message.id} "
            #       f"\n group_openid:{message.group_openid} \n event_id:{message.event_id}"
            #       f"attachment: {message.attachments}\n mentions:{message.mentions}"
            #       f"\n reference: {message.message_reference} \n seq: {message.msg_seq}")
            # print(messageResult)


if __name__ == "__main__":
    intents = botpy.Intents(public_messages=True)
    client = MyClient(intents=intents)
    client.run(appid=test_config["appid"], secret=test_config["secret"])

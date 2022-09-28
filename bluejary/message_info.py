from inspect import ismethod
from json import JSONDecoder, JSONEncoder
from discord import Message, TextChannel, NotFound
from typing import Union


class MessageInfo:
    message_id: int
    message_channel: int
    _message_message: Message

    board_id: int
    board_channel: int
    _board_message: Message

    def set_message(self, message: Message):
        self.message_id = message.id
        self.message_channel = message.channel.id
        self._message_message = message
        return self

    def set_board_message(self, board_message: Message):
        if not board_message or not isinstance(board_message, Message):
            self.board_id = None
            self.board_channel = None
            self._board_message = None
            return self

        self.board_id = board_message.id
        self.board_channel = board_message.channel.id
        self._board_message = board_message
        return self

    async def get_message(self, bot, fetch=False) -> Union[Message, None]:
        try:
            channel: TextChannel = await bot.fetch_channel(self.message_channel)
            self._message_message = await channel.fetch_message(self.message_id)
        except NotFound:
            return None
        return self._message_message

    async def get_board_message(self, bot, fetch=False) -> Union[Message, None]:
        try:
            channel: TextChannel = await bot.bot.fetch_channel(self.board_channel)
            self._board_message = await channel.fetch_message(self.board_id)
        except NotFound:
            return None
        return self._board_message

    def to_json(self) -> str:
        ret = {}
        for k in dir(self):
            if k.startswith("_"):
                continue
            v = getattr(self, k)
            if ismethod(v):
                continue
            ret[k] = v
        return JSONEncoder().encode(ret)

    @classmethod
    def from_json(cls, json):
        inf = MessageInfo()
        ret: dict = JSONDecoder().decode(json)
        for k in ret.keys():
            setattr(inf, k, ret[k])
        return inf

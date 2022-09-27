import asyncio
from datetime import datetime
import logging
from typing import Union
from redbot.core import commands, Config, checks
from discord import Message, RawReactionActionEvent, RawReactionClearEvent, RawReactionClearEmojiEvent, Embed
from .message_info import MessageInfo

log = logging.getLogger("red.bluejary")


class BluejaryBot(commands.Cog):
    im_doing_shit = False
    old_updates = {}

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 3257141233294, force_registration=True)

        def_cfg = {
            "id_emoji": None,
            "id_board": None,
            "board_count": None,
            "board_map": None,
        }

        self.config.register_guild(**def_cfg)

    @commands.group()
    @checks.admin()
    async def bluejary(self, context):
        pass

    @bluejary.command()
    async def id_emoji(self, ctx: commands.Context, value):
        cfg = self.config.guild(ctx.guild)
        try:
            await cfg.id_emoji.set(int(value))
            await ctx.send("Updated value")
        except Exception:
            await ctx.send("Failed to update value, check your syntax")

    @bluejary.command()
    async def id_board(self, ctx: commands.Context, value):
        cfg = self.config.guild(ctx.guild)
        try:
            await cfg.id_board.set(int(value))
            await ctx.send("Updated value")
        except Exception:
            await ctx.send("Failed to update value, check your syntax")

    @bluejary.command()
    async def board_count(self, ctx: commands.Context, value):
        cfg = self.config.guild(ctx.guild)
        try:
            await cfg.board_count.set(int(value))
            await ctx.send("Updated value")
        except Exception:
            await ctx.send("Failed to update value, check your syntax")

    async def set_board_message(self, message: Message, board_message: Message):
        cfg = self.config.guild(message)
        map = await cfg.board_map()
        if not map:
            map = {}
        inf: MessageInfo = map.get(message.id, None)
        if not inf:
            inf = MessageInfo().set_message(message).set_board_message(board_message)
        else:
            inf.set_board_message(board_message)
        map[message.id] = inf.to_json()
        await cfg.board_map.set(map)

    async def get_board_message(self, message: Message) -> Union[Message, None]:
        cfg = self.config.guild(message)
        map = await cfg.board_map()
        if not map:
            map = {}
        inf: MessageInfo = map.get(message.id, None)
        if not inf:
            return None
        return await inf.get_board_message(self)

    async def count_emoji(self, message: Message):
        emoji = await self.config.guild(message.guild).id_emoji()
        if not emoji:
            return 0

        board = await self.get_board_message(message)

        checking = list()
        checking.extend(message.reactions)
        if board:
            checking.extend(board.reactions)
        counts = []

        for reaction in checking:
            if not reaction.custom_emoji:
                continue
            if reaction.emoji.id != emoji:
                continue
            for user in await reaction.users().flatten():
                counts.append(user.id)
        counts = set(counts)
        return len(counts)

    async def update_message(self, message: Message = None, message_id=None, message_channel=None):
        if message.id in self.old_updates:
            last_update: datetime = self.old_updates[message.id]
            utcnow = datetime.utcnow()
            delta = last_update - utcnow
            if delta.total_seconds < 2:
                return
            self.old_updates[message.id] = utcnow

        while self.im_doing_shit is False:
            await asyncio.sleep(0.25)
        self.im_doing_shit = True

        if message_id:
            message = await (await self.bot.fetch_channel(message_channel)).fetch_message(message_id)

        cfg = self.config.guild(message.guild)
        board_channel = await cfg.id_board()
        count_target = await cfg.board_count()

        if not count_target or not board_channel:
            self.im_doing_shit = False
            return

        if message.channel.id == board_channel:
            self.im_doing_shit = False
            return

        emoji_count = await self.count_emoji(message)
        boarded = (emoji_count >= count_target)
        board_msg = await self.get_board_message(message)

        if not boarded and board_msg:
            await board_msg.delete()
            self.im_doing_shit = False
            return

        if not board_channel:
            self.im_doing_shit = False
            return

        if not board_msg:
            board_msg = await (await self.bot.fetch_channel(board_channel)).send("caching context")
            await self.set_board_message(message, board_msg)
            await asyncio.sleep(0.5)

        try:
            await self.update_board_message(message, board_msg, emoji_count)
        except Exception:
            pass
        self.im_doing_shit = False

    async def update_board_message(self, message: Message, board_message: Message, emojis):
        emoji = await message.guild.fetch_emoji(await self.config.guild(message.guild).id_emoji())
        emoji_str = f"{emojis} - <:{emoji.name}:{emoji.id}>\n\n"
        embie = Embed(type="rich", description=(emoji_str + message.clean_content()), timestamp=message.created_at)
        embie.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
        embie.set_footer(f"<#{message.channel.id}> | <a href='{message.jump_url}'>Jump To</a>")
        if len(message.attachments):
            embie.url = message.attachments[0].url
        await board_message.edit(content=None, embed=embie)

    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        await self.update_message(message_id=payload.message_id, message_channel=payload.channel_id)

    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        await self.update_message(message_id=payload.message_id, message_channel=payload.channel_id)

    @commands.Cog.listener("on_raw_reaction_clear")
    async def on_raw_reaction_clear(self, payload: RawReactionClearEvent):
        await self.update_message(message_id=payload.message_id, message_channel=payload.channel_id)

    @commands.Cog.listener("on_raw_reaction_clear_emoji")
    async def on_raw_reaction_clear_emoji(self, payload: RawReactionClearEmojiEvent):
        await self.update_message(message_id=payload.message_id, message_channel=payload.channel_id)

    @commands.Cog.listener("on_message")
    async def on_message(self, message: Message):
        if not message.guild or message.author.bot:
            return
        emoji = await message.guild.fetch_emoji(await self.config.guild(message.guild).id_emoji())
        if emoji.name in message.content:
            await message.add_reaction(emoji)

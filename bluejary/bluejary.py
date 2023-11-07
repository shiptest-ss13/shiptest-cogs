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
            "id_emoji_tail": None,
            "id_emoji_stuff": None,
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
    async def id_emoji_tail(self, ctx: commands.Context, value):
        cfg = self.config.guild(ctx.guild)
        try:
            await cfg.id_emoji_tail.set(int(value))
            await ctx.send("Updated value")
        except Exception:
            await ctx.send("Failed to update value, check your syntax")

    @bluejary.command()
    async def id_emoji_stuff(self, ctx: commands.Context, value):
        cfg = self.config.guild(ctx.guild)
        try:
            await cfg.id_emoji_stuff.set(int(value))
            await ctx.send("Updated value")
        except Exception:
            await ctx.send("Failed to update value, check your syntax")

    @commands.Cog.listener("on_message")
    async def on_message(self, message: Message):
        if not message.guild or message.author.bot:
            return
        if "tail" in message.content.lower():
            emoji2 = await message.guild.fetch_emoji(await self.config.guild(message.guild).id_emoji_tail())
            await message.add_reaction(emoji2)
        if "m stuff" in message.content.lower():
            emoji3 = await message.guild.fetch_emoji(await self.config.guild(message.guild).id_emoji_stuff())
            await message.add_reaction(emoji3)
        emoji = await message.guild.fetch_emoji(await self.config.guild(message.guild).id_emoji())
        if emoji.name in message.content:
            await message.add_reaction(emoji)

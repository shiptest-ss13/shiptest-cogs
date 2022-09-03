from datetime import datetime
import logging
from redbot.core import commands, Config, checks
from discord import Message, RawReactionActionEvent, TextChannel, AllowedMentions, Embed, Reaction

log = logging.getLogger("red.bluejary")


class BluejaryBot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 3257141233194, force_registration=True)

        def_cfg = {
            "emoji_id": None,
            "board_id": None,
            "board_req": None,
            "board_map": None,
            "message_map": None,
            "ignored": None,
        }

        self.config.register_guild(**def_cfg)

    @commands.group()
    @commands.guild_only()
    @checks.admin()
    async def bluejary(self, ctx: commands.Context):
        pass

    @bluejary.command()
    async def ignore_channel(self, ctx: commands.Context, channel_id=None):
        await self.assert_defaults(ctx.guild)
        ignored: list = await self.config.guild(ctx.guild).ignored()
        if channel_id is None:
            resp = "Ignored Channels:\n```\n"
            for channel in ignored:
                channel_ins: TextChannel = self.bot.fetch_channel(channel)
                resp += f"{channel_ins.name}\n"
            resp += "```\n"
            await ctx.send(resp)
        elif channel_id in ignored:
            ignored.remove(channel_id)
            await ctx.send("No longer ignoring that channel")
        else:
            ignored.append(channel_id)
            await ctx.send("Now ignoring that channel")

    @bluejary.command()
    async def set_board(self, ctx: commands.Context, channel_id):
        await self.assert_defaults(ctx.guild)
        current = await self.config.guild(ctx.guild).board_id()
        if current == channel_id:
            await ctx.send("That is already the board!")
            return
        board = await self.bot.get_channel(channel_id)
        if board is None:
            await ctx.send("Couldnt find that channel, is it the ID of the channel?")
            return
        await self.config.guild(ctx.guild).board_id.set(channel_id)
        await ctx.send("Updated the board!")

    @bluejary.command()
    async def set_emoji(self, ctx: commands.Context, emoji_id):
        await self.assert_defaults(ctx.guild)
        current = await self.config.guild(ctx.guild).emoji_id()
        if current == emoji_id:
            await ctx.send("That is already the emoji!")
            return
        board = await ctx.guild.fetch_emoji(emoji_id)
        if board is None:
            await ctx.send("Couldnt find that emoji, is it the ID?")
            return
        await self.config.guild(ctx.guild).emoji_id.set(emoji_id)
        await ctx.send("Updated the board!")

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not message.content:
            return
        if not isinstance(message.content, str):
            return
        if "bluejary" not in message.content.lower():
            return
        if message.author.bot:
            return
        if not message.guild:
            return
        await message.add_reaction(await message.guild.fetch_emoji(await self.config.guild(message.guild).emoji_id()))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        await self.update(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        await self.update(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionActionEvent):
        await self.update(payload)

    async def assert_defaults(self, guild):
        cfg = self.config.guild(guild)
        if await cfg.emoji_id() is None:
            await cfg.emoji_id.set(979343052411920384)
        if await cfg.board_req() is None:
            await cfg.board_req.set(5)
        if await cfg.board_map() is None:
            await cfg.board_map.set({})
        if await cfg.board_id() is None:
            await cfg.board_id.set(1014906614815404144)
        if await cfg.message_map() is None:
            await cfg.message_map.set({})
        if await cfg.ignored() is None:
            await cfg.ignored.set([])

    async def update(self, event: RawReactionActionEvent):
        if not event.guild_id:
            return
        guild = await self.bot.fetch_guild(event.guild_id)
        await self.assert_defaults(guild)
        config = self.config.guild(guild)

        ignored: list = await config.ignored()
        if event.channel_id in ignored:
            return

        board_id = await config.board_id()
        if not board_id:
            return
        board: TextChannel = await self.bot.fetch_channel(board_id)
        if board is None:
            return

        message_map: dict = await config.message_map()
        board_map: dict = await config.board_map()
        message: Message = None
        board_message: Message = None
        if event.channel_id == board_id:
            log.info("board reaction")
            m_id = board_map[str(event.message_id)]
            c_id = message_map[str(m_id)]["channel"]
            message = await (await self.bot.fetch_channel(c_id)).fetch_message(m_id)
            log.info(f"message id {message.id}")
            board_message = await board.fetch_message(event.message_id)
            log.info(f"board id {board_message.id}")
        else:
            message = await (await self.bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)
            try:
                board_message = await board.fetch_message(message_map[str(message.id)]["board"])
            except KeyError:
                pass

        tallying = list()
        if message.reactions is not None:
            tallying = tallying + message.reactions
            log.info(f"added message reactions: {len(message.reactions)}")
        if board_message is not None and board_message.reactions is not None:
            log.info(f"added board reactions: {len(board_message.reactions)}")
            tallying = tallying + board_message.reactions

        counted = list()
        emoji_id = await config.emoji_id()
        emoji = await guild.fetch_emoji(emoji_id)
        for react in tallying:
            react: Reaction
            if not react.custom_emoji or isinstance(react.emoji, str):
                continue
            if react.emoji.id != emoji_id:
                continue
            for reactee in await react.users().flatten():
                counted.append(reactee.id)
        total = len(set(counted))
        should_board = (total >= await config.board_req())

        if should_board:
            if not board_message:
                board_message = await board.send("caching")
                board_map[str(board_message.id)] = message.id
                message_map[str(message.id)] = {"board": board_message.id, "channel": message.channel.id}
            embed: Embed = Embed(type="rich", timestamp=datetime.utcnow(), description=message.content, title=message.author.display_name).set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
            await board_message.edit(content=f"{total} <:{emoji.name}:{emoji.id}>s", allowed_mentions=AllowedMentions.none(), embed=embed)
        elif board_message is not None:
            board_map.pop(str(board_message.id))
            message_map.pop(str(message.id))
            await board_message.delete()
        await config.board_map.set(board_map)
        await config.message_map.set(message_map)

from datetime import datetime
from redbot.core import commands, Config
from discord import Message, RawReactionActionEvent, TextChannel, AllowedMentions, Embed


class BluejaryBot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 3257141233194, force_registration=True)

        def_cfg = {
            "emoji_id": None,
            "board_id": None,
            "board_req": None,
            "board_map": None,
        }

        self.config.register_guild(**def_cfg)

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

    async def update(self, event: RawReactionActionEvent):
        if not event.guild_id:
            return
        guild = await self.bot.fetch_guild(event.guild_id)
        await self.assert_defaults(guild)
        config = self.config.guild(guild)

        board_id = await config.board_id()
        if not board_id:
            return
        board: TextChannel = await self.bot.fetch_channel(board_id)
        if board is None:
            return

        if event.channel_id == board_id:
            return

        channel = await self.bot.fetch_channel(event.channel_id)
        message: Message = await channel.fetch_message(event.message_id)
        emoji_id = await config.emoji_id()
        total = 0
        for react in message.reactions:
            if react.emoji.id != emoji_id:
                continue
            total = react.count
            break
        should_board = (total >= await config.board_req())
        board_map: dict = await config.board_map()

        board_key = str(message.id)
        board_message: Message = None
        if board_key in board_map.keys():
            board_message = await board.fetch_message(board_map[board_key])

        if should_board:
            if not board_message:
                board_message = await board.send("caching")
                board_map[board_key] = board_message.id
            embed: Embed = Embed(type="rich", timestamp=datetime.utcnow(), description=message.content, title=message.author.display_name).set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
            await board_message.edit(content=f"{total} :bluejary:s", allowed_mentions=AllowedMentions.none(), embed=embed)
        elif board_message is not None:
            await board_message.delete()
            board_map.pop(board_key)
        await config.board_map.set(board_map)

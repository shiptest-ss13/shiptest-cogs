from redbot.core import commands, Config
from discord import Message


class BluejaryBot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 3257141233194, force_registration=True)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if "bluejary" not in message.content:
            return
        if message.author.bot:
            return
        if not message.guild:
            return
        emoji = await message.guild.fetch_emoji(1014879985149956126)
        await message.add_reaction(emoji)

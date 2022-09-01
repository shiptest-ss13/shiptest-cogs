from redbot.core import commands
from discord import Message


class BluejaryBot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if "bluejary" not in message.content:
            return
        if message.author.bot:
            return
        await message.add_reaction(":bluejary:")

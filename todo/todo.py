#Standard Imports
import asyncio
import logging
from typing import Union
import time

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import pagify, box, humanize_list, warning
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

__version__ = "0.1"
__author__ = "Mark Suckerberg"

log = logging.getLogger("red.ToDoCog")

BaseCog = getattr(commands, "Cog", object)

class ToDoCog(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257733194, force_registration=True)

        default_guild = {
            "guild_tasks": []
        }

        self.config.register_guild(**default_guild)
        self.loop = asyncio.get_event_loop()
    
    @commands.group()
    async def addtodo(self, ctx):
        """
        Adds a todo item to a specific todo list
        """
        pass

    @commands.guild_only()
    @addtodo.command()
    async def server(self, ctx, task: str):
        """
        Adds a todo item to the server-specific todo list.
        """
        author = ctx.message.author

        todo_item = {
            "TASK_USER_NAME": author.name,
            "TASK_TIMESTAMP": int(time.time()),
            "TASK_USER_ID": author.id,
            "TASK_INFO": task,
            "TASK_COMPLETED": False
        }

        async with self.config.guild.guild_tasks() as current_tasks:
            current_tasks.append(todo_item)
        try:
            await ctx.message.add_reaction("✅")
        except discord.errors.NotFound:
            pass

    @commands.group()
    async def listtodo(self, ctx):
        pass

    @listtodo.command()
    async def server(self, ctx):
        tasks = await self.config.guild.guild_tasks()
        formatted_tasks = []
        for task in tasks:
            formatted_tasks += (
                "["
                "✅" if task['TASK_COMPLETED'] else "❎"
                " - "
                f"{task['TASK_INFO']} ({task['TASK_USER_NAME']} <t:{task['TASK_TIMESTAMP']}>)"
                "]\n"
            )

        temp_embeds = []
        embeds = []
        for ban in pagify(bans_list, ["["]):
            embed = discord.Embed(description=box(ban, lang="asciidoc"), color=0x2b74ab)
            temp_embeds.append(embed)
        max_i = len(temp_embeds)
        i = 1
        for embed in temp_embeds:
            embed.set_author(name=f"Todo list for guild: | total items: {total}")
            embed.set_footer(text=f"Page {i}/{max_i}")
            embeds.append(embed)
            i += 1
        await menu(ctx, embeds, DEFAULT_CONTROLS)

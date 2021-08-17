#Standard Imports
import asyncio
import time

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import pagify, box, humanize_list
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

__version__ = "0.1"
__author__ = "Mark Suckerberg"

class ToDoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257733194, force_registration=True)

        default_guild = {
            "guild_tasks": {}
        }

        self.config.register_guild(**default_guild)
    
    #@commands.guild_only()
    #@commands.group()
    #async def addtodo(self, ctx):
    #    """
    #    Adds a todo item to a specific todo list
    #    """
    #    pass

    @commands.command()
    async def addtodo(self, ctx, task: str):
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

        async with self.config.guild(ctx.guild).guild_tasks() as current_tasks:
            current_tasks[task] = todo_item
        try:
            await ctx.message.add_reaction("✅")
        except discord.errors.NotFound:
            pass

    #@commands.group()
    #async def listtodo(self, ctx):
    #    pass

    @commands.command()
    async def completetask(self, ctx, task: str):
        async with self.config.guild(ctx.guild).guild_tasks() as current_tasks:
            current_tasks[task]["TASK_COMPLETED"] = not current_tasks[task]["TASK_COMPLETED"]


    @commands.command()
    async def listtodo(self, ctx):
        tasks = await self.config.guild(ctx.guild).guild_tasks()
        formatted_tasks = ""
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
        for ban in pagify(formatted_tasks, ["["]):
            embed = discord.Embed(description=ban, color=0x2b74ab)
            temp_embeds.append(embed)
        max_i = len(temp_embeds)
        i = 1
        for embed in temp_embeds:
            embed.set_author(name=f"Todo list for guild: | total items: {max_i}")
            embed.set_footer(text=f"Page {i}/{max_i}")
            embeds.append(embed)
            i += 1
        await menu(ctx, embeds, DEFAULT_CONTROLS)

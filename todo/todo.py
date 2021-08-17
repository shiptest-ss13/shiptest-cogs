#Standard Imports
import asyncio
import time

#Discord Imports
import discord
import random

#Redbot Imports
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import pagify, box, humanize_list
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

__version__ = "0.1"
__author__ = "Mark Suckerberg"

class ToDoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3252246194, force_registration=True)

        default_guild = {
            "guild_tasks": {}
        }

        self.config.register_guild(**default_guild)
    
    @commands.group()
    async def todo(self, ctx):
        """
        Adds a todo item to a specific todo list
        """
        pass

    @todo.command()
    async def add(self, ctx, *args):
        """
        Adds a todo item to the server-specific todo list.
        """
        task = " ".join(args)
        author = ctx.message.author
        

        todo_item = {
            "TASK_USER_NAME": author.name,
            "TASK_TIMESTAMP": int(time.time()),
            "TASK_USER_ID": author.id,
            "TASK_INFO": task,
            "TASK_COMPLETED": False
        }

        async with self.config.guild(ctx.guild).guild_tasks() as current_tasks:
            if task in current_tasks:
                ctx.send("Cannot add duplicate tasks.")
                pass
            current_tasks[task] = todo_item
        try:
            await ctx.message.add_reaction("✅")
        except discord.errors.NotFound:
            pass

    @todo.command()
    async def complete(self, ctx, *args):
        """
        Marks a todo item completed.
        """
        task = " ".join(args)
        async with self.config.guild(ctx.guild).guild_tasks() as current_tasks:
            if task in current_tasks:
                current_tasks[task]["TASK_COMPLETED"] = not current_tasks[task]["TASK_COMPLETED"]
                try:
                    await ctx.message.add_reaction("✅")
                except discord.errors.NotFound:
                    pass
            else:
                ctx.send("Task " + task + " not found.")
                pass

    @todo.command()
    async def list(self, ctx):
        tasks = await self.config.guild(ctx.guild).guild_tasks()
        formatted_tasks = ""
        for task_name in tasks:
            task = tasks[task_name]
            formatted_tasks += "\n["
            formatted_tasks += "✅" if task['TASK_COMPLETED'] else "❎"
            formatted_tasks += (
                " - "
                f"{task['TASK_INFO']} ({task['TASK_USER_NAME']} <t:{task['TASK_TIMESTAMP']}>)"
                "]\n"
            )

        temp_embeds = []
        embeds = []
        for ban in pagify(formatted_tasks, ["\n["]):
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

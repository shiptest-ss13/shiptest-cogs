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
        self.config = Config.get_conf(self, 3265224694, force_registration=True)

        default_guild = {
            "guild_tasks": []
        }

        default_user = {
            "user_tasks": []
        }

        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
    
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
            current_tasks.append(todo_item)
        try:
            await ctx.message.add_reaction("✅")
        except discord.errors.NotFound:
            pass

    @todo.command()
    async def complete(self, ctx, target:int):
        """
        Marks a todo item completed.
        """
        async with self.config.guild(ctx.guild).guild_tasks() as current_tasks:
            if (target > len(current_tasks) or target < 0):
                ctx.send("Task " + target + " not found.")
                pass
            current_tasks[target]["TASK_COMPLETED"] = not current_tasks[target]["TASK_COMPLETED"]
            try:
                await ctx.message.add_reaction("✅")
            except discord.errors.NotFound:
                pass

    @todo.command()
    async def random(self, ctx):
        """
        Selects a task at random!
        """
        async with self.config.guild(ctx.guild).guild_tasks() as tasks:
            random_num = random.randrange(0, len(tasks))
            selected_task = tasks[random_num]
            ctx.send(f"The randomly selected task is... {selected_task['TASK_INFO']}!")

    @todo.command()
    async def list(self, ctx):
        """
        Shows a list of all current to-do tasks.
        """
        async with self.config.guild(ctx.guild).guild_tasks() as tasks:
            if(len(tasks) < 1):
                ctx.send("No tasks found!")
                pass
            formatted_tasks = ""
            for task_index in range(0 , len(tasks)):
                task = tasks[task_index]
                formatted_tasks += f"\n[{task_index} - "
                formatted_tasks += "✅" if task['TASK_COMPLETED'] else "❎"
                formatted_tasks += (
                    f" {task['TASK_INFO']} ({task['TASK_USER_NAME']} <t:{task['TASK_TIMESTAMP']}>)"
                    "]"
                )

            temp_embeds = []
            embeds = []
            for ban in pagify(formatted_tasks, ["\n["]):
                embed = discord.Embed(description=ban, color=0x2b74ab)
                temp_embeds.append(embed)
            max_i = len(temp_embeds)
            i = 1
            for embed in temp_embeds:
                embed.set_author(name=f"Todo list for {ctx.guild.name}: | Total tasks: {len(tasks)}")
                embed.set_footer(text=f"Page {i}/{max_i}")
                embeds.append(embed)
                i += 1
            await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.group()
    async def usertodo(self, ctx):
        """
        Adds a todo item to a specific todo list
        """
        pass

    @usertodo.command()
    async def add(self, ctx, *args):
        """
        Adds a todo item to the server-specific todo list.
        """
        task = " ".join(args)
        todo_item = {
            "TASK_TIMESTAMP": int(time.time()),
            "TASK_INFO": task,
            "TASK_COMPLETED": False
        }

        async with self.config.user(ctx.message.author).user_tasks() as current_tasks:
            if task in current_tasks:
                ctx.send("Cannot add duplicate tasks.")
                pass
            current_tasks.append(todo_item)
        try:
            await ctx.message.add_reaction("✅")
        except discord.errors.NotFound:
            pass

    @usertodo.command()
    async def complete(self, ctx, target:int):
        """
        Marks a todo item completed.
        """
        async with self.config.user(ctx.message.author).user_tasks() as current_tasks:
            if (target > len(current_tasks) or target < 0):
                ctx.send("Task " + target + " not found.")
                pass
            current_tasks[target]["TASK_COMPLETED"] = not current_tasks[target]["TASK_COMPLETED"]
            try:
                await ctx.message.add_reaction("✅")
            except discord.errors.NotFound:
                pass

    @usertodo.command()
    async def random(self, ctx):
        """
        Selects a task at random!
        """
        async with self.config.user(ctx.message.author).user_tasks() as tasks:
            random_num = random.randrange(0, len(tasks))
            selected_task = tasks[random_num]
            ctx.send(f"The randomly selected task is... {selected_task['TASK_INFO']}!")

    @usertodo.command()
    async def list(self, ctx):
        """
        Shows a list of all the user's current to-do tasks.
        """
        async with self.config.user(ctx.message.author).user_tasks() as tasks:
            if(len(tasks) < 1):
                ctx.send("No tasks found!")
                pass
            formatted_tasks = ""
            for task_index in range(0 , len(tasks)):
                task = tasks[task_index]
                formatted_tasks += f"\n[{task_index} - "
                formatted_tasks += "✅" if task['TASK_COMPLETED'] else "❎"
                formatted_tasks += (
                    f" {task['TASK_INFO']} <t:{task['TASK_TIMESTAMP']}>)"
                    "]"
                )

            temp_embeds = []
            embeds = []
            for ban in pagify(formatted_tasks, ["\n["]):
                embed = discord.Embed(description=ban, color=0x2b74ab)
                temp_embeds.append(embed)
            max_i = len(temp_embeds)
            i = 1
            for embed in temp_embeds:
                embed.set_author(name=f"Todo list for {ctx.message.author}: | Total tasks: {len(tasks)}")
                embed.set_footer(text=f"Page {i}/{max_i}")
                embeds.append(embed)
                i += 1
            await menu(ctx, embeds, DEFAULT_CONTROLS)

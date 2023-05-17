#Standard Imports
import asyncio
import logging
from typing import Union

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, app_commands
from redbot.core.utils.chat_formatting import pagify, box, humanize_list, warning
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

__version__ = "1.0.0"
__author__ = "Mark Suckerberg"

BaseCog = getattr(commands, "Cog", object)

class GithubPRRetriever(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257823194, force_registration=True)

        default_guild = {
            "repo": "https://github.com/shiptest-ss13/shiptest"
        }
        self.config.register_guild(**default_guild)
    
    @commands.hybrid_command()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def setrepo(self, ctx, new_repo = ""):
        """
        Sets or displays the current repo to add PR requests to. 
        """
        if(new_repo):
            try:
                await self.config.guild(ctx.guild).repo.set(new_repo)
                await ctx.send(f"Target repo set to: `{new_repo}`")
            except (ValueError, KeyError, AttributeError):
                await ctx.send("There was an error setting the target repo. Please check your entry and try again!")
        else:
            url = await self.config.guild(ctx.guild).repo()
            await ctx.send(f"The target repo is currently set to: `{url}`")

    @commands.hybrid_command()
    @commands.guild_only()
    async def gh(self, ctx, *, pr: int):
        """
        Retrieves a specific PR from the github.
        """
        repo = await self.config.guild(ctx.guild).repo()
        if repo:
            url = f"{repo}/issues/{pr}"
            await ctx.send(url)
        else:
            await ctx.send("No repo has been set for this server. Please use `setrepo` to set one.")

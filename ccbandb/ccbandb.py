#Standard Imports
import asyncio
import logging
import requests
from typing import Union

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import pagify, box, humanize_list, warning
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

#Util Imports
from .util import key_to_ckey

__version__ = "0.1"
__author__ = "Mark Suckerberg"

log = logging.getLogger("red.SS13CCBanDB")

BaseCog = getattr(commands, "Cog", object)

class CCBanDB(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257143194, force_registration=True)

        default_guild = {
            "bandb": "https://centcom.melonmesa.com/ban/search"
        }

        self.config.register_guild(**default_guild)
        self.loop = asyncio.get_event_loop()
    

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def bandb(self, ctx, ban_db = ""):
        """
        Sets or displays the current global ban API. (Defaults to the Centcom ban DB found here: <https://centcom.melonmesa.com/ban/search>)
        """
        if(ban_db):
            try:
                await self.config.guild(ctx.guild).bandb.set(ban_db)
                await ctx.send(f"Global ban database set to: `{ban_db}`")
            except (ValueError, KeyError, AttributeError):
                await ctx.send("There was an error setting the global ban database. Please check your entry and try again!")
        else:
            dburl = await self.config.guild(ctx.guild).bandb()
            await ctx.send(f"The global ban databse is currently set to: `{self.config.guild(ctx.guild).bandb()}`")

    @checks.mod_or_permissions(administrator=True)
    @commands.command()
    async def cclookup(self, ctx, *, ckey: str):
        """
        Gets the ban results from the configured global ban database
        """
        ckey = key_to_ckey(ckey)

        message = await ctx.send("Retrieving bans...")

        try:
            dburl = await self.config.guild(ctx.guild).bandb()
            request = requests.get(f"{dburl}/{ckey}")
            rows = request.json()
            if(not rows):
                embed=discord.Embed(description=f"No notes found for: {str(ckey).title()}", color=0xf1d592)
                return await message.edit(content=None,embed=embed)
            # Parse the data into individual fields within an embeded message in Discord for ease of viewing
            notes = ""
            total = 0
            temp_embeds = []
            embeds = []
            for row in rows:
                total += 1
                expiration = "Permanent"
                if('expires' in row):
                    expiration = row['expires']
                notes += f"\n[Server: {row['sourceName']} ({row['sourceRoleplayLevel']}) - Expires: {expiration}]\n[{row['bannedOn']} | {row['type']} by {row['bannedBy']}]\n{row['reason']}"
            for note in pagify(notes):
                embed = discord.Embed(description=box(note, lang="asciidoc"), color=0xf1d592)
                temp_embeds.append(embed)
            max_i = len(temp_embeds)
            i = 1
            for embed in temp_embeds:
                embed.set_author(name=f"Bans for {str(ckey).title()} | Total bans: {total}")
                embed.set_footer(text=f"Page {i}/{max_i} | All times are respective server time")
                embeds.append(embed)
                i += 1
            await message.delete()
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        
        except requests.exceptions.Timeout as err:
            embed=discord.Embed(title=f"Error looking up bans for: {ckey}", description=f"{format(err)}", color=0xff0000)
            await message.edit(content=None,embed=embed)

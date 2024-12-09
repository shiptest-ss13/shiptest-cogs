import requests
from typing import Optional
from random import randint

import discord

from redbot.core import commands, checks, Config, app_commands

__version__ = "1.0.0"
__author__ = "MarkSuckerberg"


class Birds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=675261474420236490, force_registration=True
        )

        default_guild = {
            "api_key": "",
        }

        self.config.register_guild(**default_guild)

        self.random_total = 361

    @app_commands.guild_only()
    @app_commands.command(
        name="birdset", description="Set the API key for the birds cog."
    )
    @checks.admin_or_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def birdset(self, interaction: discord.Interaction, api_key: str):
        """
        Set your API key for the Birds API.
        """
        await self.config.guild(interaction.guild).api_key.set(api_key)
        await interaction.response.send_message("API key set!", ephemeral=True)

    @commands.guild_only()
    @commands.cooldown(2, 10)
    @commands.hybrid_command()
    async def bird(self, ctx, bird_name: Optional[str]):
        """
        Get information about a bird.
        """
        api_key = await self.config.guild(ctx.guild).api_key()
        if not api_key:
            return await ctx.send(
                "API key not set. Please contact an admin to set this."
            )

        url = f"https://nuthatch.lastelm.software/v2/birds?pageSize=1"
        headers = {"api-key": api_key}

        if bird_name:
            url += f"&name={bird_name}&sciName={bird_name}&order={bird_name}&family={bird_name}&operator=OR"
        else:
            url += f"&hasImg=true&page={randint(1, self.random_total)}"

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return await ctx.send("An error occurred. Please try again later.")

        data = response.json()

        if not bird_name:
            self.random_total = int(data["total"])

        if len(data["entities"]) == 0:
            return await ctx.send("No birds found.")

        entity = data["entities"][0]

        embed = discord.Embed(
            title=entity["name"],
            color=0x2B74AB,
        )

        embed.add_field(name="Scientific Name", value=entity["sciName"], inline=True)
        embed.add_field(name="Order", value=entity["order"], inline=True)
        embed.add_field(name="Family", value=entity["family"], inline=True)
        embed.add_field(name="Conservation Status", value=entity["status"], inline=True)
        embed.add_field(name="Regions", value=", ".join(entity["region"]), inline=True)

        imageCount = len(entity["images"])
        if imageCount > 0:
            embed.set_image(url=entity["images"][randint(0, imageCount - 1)]["url"])

        await ctx.send(embed=embed)

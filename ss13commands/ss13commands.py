#Standard Imports
import asyncio
import ipaddress
import struct
import select
import socket
import urllib.parse
import html.parser as htmlparser
import time
import textwrap
from datetime import datetime
import logging

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils
import json

__version__ = "1.2.2"
__author__ = "Mark Suckerberg"

log = logging.getLogger("red.SS13Commands")

class SS13Commands(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.config = Config.get_conf(self, 3257193194, force_registration=True)

        default_global = {
            "server": None,
            "game_port": None,
            "server_url": "byond://127.0.0.1:7777", 
            "comms_key": "default_pwd",
            "ooc_notice_channel": None,
            "ooc_toggle": True,
        }

        self.config.register_global(**default_global)

    @commands.guild_only()
    @commands.group()
    @checks.admin_or_permissions(administrator=True)
    async def setss13(self, ctx):
        """
        Configuration group for the SS13 status command
        """
        pass
    
    @setss13.command(aliases=['host'])
    async def server(self, ctx, host: str):
        """
        Sets the server IP used for status checks
        """
        try:
            await self.config.server.set(host)
            await ctx.send(f"Server set to: `{host}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the host! Please check your entry and try again.")
    
    @setss13.command()
    async def port(self, ctx, port: int):
        """
        Sets the port used for the status checks
        """
        try:
            if 1024 <= port <= 65535: # We don't want to allow reserved ports to be set
                await self.config.game_port.set(port)
                await ctx.send(f"Host port set to: `{port}`")
            else:
                await ctx.send(f"`{port}` is not a valid port!")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your port. Please check to ensure you're attempting to use a port from 1024 to 65535")

    @setss13.command()
    async def commskey(self, ctx, key: str):
        """
        Set the communications key for the server
        """
        try:
            await self.config.comms_key.set(key) #Used to verify incoming game data
            await ctx.send("Comms key set.")
            try:
                await ctx.message.delete()
            except(discord.DiscordException):
                await ctx.send("I do not have the required permissions to delete messages. You may wish to edit/remove your comms key manually.")
        
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your communications key. Please check your entry and try again.")

    @setss13.command()
    async def toggleooc(self, ctx, toggle:bool = None):
        """
        OOC relay toggle

        With this enabled, OOC will be relayed to the connected SS13 server with the [P]ooc command.
        """

        if toggle is None:
            toggle = await self.config.ooc_toggle()
            toggle = not toggle

        try:
            await self.config.ooc_toggle.set(toggle)
            if toggle is True:
                await ctx.send(f"I will now relay OOC to the SS13 server.")
                await self.topic_query_server(querystr="ooc_send", sender=ctx.author.display_name, params={"message": "The discord OOC relay has been enabled.", "sender": "Administrator"})
            else:
                await ctx.send("I will no longer relay OOC to the SS13 server.")
                await self.topic_query_server(querystr="ooc_send", sender=ctx.author.display_name, params={"message": "The discord OOC relay has been disabled.", "sender": "Administrator"})
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem toggling the OOC relay. Please try again or contact a coder.")

    @setss13.command()
    async def oocchannel(self, ctx, text_channel: discord.TextChannel = None):
        """
        Set the text channel for ooc reporting.
        
        Use without providing a channel to reset this to None.
        """
        try:
            if text_channel is not None:
                await self.config.ooc_notice_channel.set(text_channel.id)
                await ctx.send(f"OOC will be sent to: {text_channel.mention}")
            else:
                await self.config.ooc_notice_channel.set(None)
                await ctx.send("I will no longer send OOC messages.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the notification channel. Please check your entry and try again.")

    @setss13.command()
    async def current(self, ctx):
        """
        Lists the current settings
        """
        settings = await self.config.all()
        embed=discord.Embed(title="__Current Settings:__")
        
        for k, v in settings.items():
            if k == 'comms_key': #We don't want to actively display the comms key
                embed.add_field(name=f"{k}:", value="`redacted`", inline=False)
            else:
                embed.add_field(name=f"{k}:", value=v, inline=False)
        
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    async def ooc(self, ctx, *args):
        """
        Sends a message to the linked SS13 server's OOC chat.
        """
        if(await self.config.ooc_toggle()):
            message = " ".join(args)
            message = message.strip("@")
            data = await self.topic_query_server(querystr="ooc_send", sender=ctx.author.display_name, params={"message": message})
            if(data):
                await ctx.send(data)
        else:
            await ctx.send("The Discord OOC relay has been disabled.")


    @commands.guild_only()
    @commands.command()
    @commands.cooldown(1, 10)
    async def manifest(self, ctx):
        """
        Displays the current crew manifest of the linked SS13 server.
        """
        string = await self.topic_query_server(querystr="manifest", sender=ctx.author.display_name)

        data = urllib.parse.parse_qs(string)

        if(data):
            embed=discord.Embed(title="__Crew Manifest:__", color=0x26eaea)
            for department in data:
                entries = [i for i in data[department]]
                embed.add_field(name=f"{department}",value=f'\n'.join(map(str,entries)),inline=False)
        else:
            embed=discord.Embed(title="__Crew Manifest:__", description="No crewmembers found!", color=0x26eaea)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    @checks.admin_or_permissions(administrator=True)
    async def ccannounce(self, ctx, message:str, sender="Central Command"):
        """
        Sends a specified announcement to the linked SS13 server.
        """
        await self.topic_query_server(querystr="Comms_Console=nothing", sender=ctx.author.display_name, params={"message": message, "message_sender": sender})

    @commands.guild_only()
    @commands.command()
    @checks.admin_or_permissions(administrator=True)
    async def ahelp(self, ctx, target:str, msg:str):
        """
        Sends an adminhelp to the specified CKEY.
        """
        await self.topic_query_server(querystr=f"adminmsg={target}", sender=ctx.author.display_name, params={"msg": msg})

    @commands.guild_only()
    @commands.command()
    @checks.admin_or_permissions(administrator=True)
    async def namecheck(self, ctx, target:str):
        """
        Checks the specified CKEY or player name for information.
        """
        info = await self.topic_query_server(querystr=f"namecheck={target}")
        if(info):
            #TODO: Split recieved data into different embed fields
            await ctx.send(embed=discord.Embed(title=f"Results for {target}:", description=f"{info}"))

    @commands.guild_only()
    @commands.command()
    @checks.admin_or_permissions(administrator=True)
    async def restart_server(self, ctx, hard = False):
        """
        Restarts the linked SS13 server if there are no admins online.
        """
        info = await self.topic_query_server(querystr=f"restart", sender=ctx.author.display_name, params={"hard": int(hard)})
        await ctx.send("Restarting...")
        if(info):
            await ctx.send(info)

    @commands.guild_only()
    @commands.command()
    async def kek(self, ctx):
        """
        Kek.
        """
        await ctx.send("kek")

    @commands.guild_only()
    @commands.command()
    async def join(self, ctx):
        """
        Sends an embedded join link to the server.
        """
        server = await self.config.server()
        port = await self.config.game_port()
        embed = discord.embed(title="__Join:__", description=f"<byond://{server}:{port}>")
        await ctx.send(embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if(message.channel.id == await self.config.ooc_notice_channel()):
            if((message.author == self.bot.user) and (message.content.startswith("**OOC:**")) or (message.content == "The Discord OOC relay has been disabled.")):
                return
            if(await self.config.ooc_toggle()):
                data = await self.topic_query_server(querystr="ooc_send", sender=message.author.display_name, params={"message": message.content})
                if(data):
                    await message.channel.send(data)
            else:
                replymsg = await message.channel.send("The Discord OOC relay has been disabled.")
                await replymsg.delete(2)
        if(message.author == self.bot.user):
            return
        if(message.content.lower().endswith("when")):
            await message.channel.send("When you code it.")
        elif(message.content.lower().startswith("marg")):
            await message.channel.send("marg")

    async def topic_query_server(self, querystr="status", sender="Discord", params=None, needskey=True): #I could combine this with the previous def but I'm too scared to mess with it; credit to Aurora for most of this code
        """
        Queries the server for information
        """

        server = await self.config.server()
        port = await self.config.game_port()

        message = {}
        message["sender"] = sender
        message["source"] = "Discord"

        if(params):
            message.update(params)

        if(await self.config.comms_key() and needskey): #Little risky but mnehhh
            message["key"] = await self.config.comms_key()

        message = json.dumps(message, separators=("&", "=")) #This is just how SS13 (at least /tg/) seperates attributes

        message = message.replace("{", "")
        message = message.replace("}", "")
        message = message.replace("\"", "")

        message = f"?{querystr}&{message}"

        log.info(f"Querying gameserver with message: {message}")

        reader, writer = await asyncio.open_connection(server, port)            
        query = b"\x00\x83"
        query += struct.pack('>H', len(message) + 6)
        query += b"\x00\x00\x00\x00\x00"
        query += message.encode()
        query += b"\x00" #Creates a packet for byond according to TG's standard

        writer.write(query)

        data = b''
        while True:
            buffer = await reader.read(1024)
            data += buffer
            if len(buffer) < 1024:
                break

        writer.close()

        size_bytes = struct.unpack(">H", data[2:4])
        size = size_bytes[0] - 1

        index = 5
        index_end = index + size
        string = data[5:index_end].decode("utf-8")
        string = string.replace("\x00", "")

        log.info(f"Got Answer from Gameserver: {string}")
        return string


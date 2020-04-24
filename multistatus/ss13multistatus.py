#Standard Imports
import asyncio
import struct
import select
import socket
import urllib.parse
import html.parser as htmlparser
import time
import textwrap
from datetime import datetime
import logging
import mysql.connector
import ipaddress
import re
from typing import Union

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

__version__ = "0.0.3"
__author__ = "MarkSuckerberg with Crossedfall's code"


BaseCog = getattr(commands, "Cog", object)

class SS13MultiStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257143194, force_registration=True)

        default_guild = { 
            "offline_message": "Currently offline",    
            "timeout": 10,       
            "mysql_table": "multistatus",
            "mysql_host": "127.0.0.1",
            "mysql_port": 3306,
            "mysql_user": "user",
            "mysql_password": "password",
            "mysql_db": "multistatus"
        }

        self.config.register_guild(**default_guild)


    @commands.guild_only()
    @commands.group()
    @checks.admin_or_permissions(administrator=True)
    async def setmultistatus(self,ctx): 
        """
        SS13 MySQL database settings
        """
        pass
    
    @setmultistatus.command()
    @checks.is_owner()
    async def host(self, ctx, db_host: str):
        """
        Sets the MySQL host, defaults to localhost (127.0.0.1)
        """
        try:
            await self.config.guild(ctx.guild).mysql_host.set(db_host)
            await ctx.send(f"Database host set to: `{db_host}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the database's ip/hostname. Please check your entry and try again!")
    
    @setmultistatus.command()
    @checks.is_owner()
    async def port(self, ctx, db_port: int):
        """
        Sets the MySQL port, defaults to 3306
        """
        try:
            if 1024 <= db_port <= 65535: # We don't want to allow reserved ports to be set
                await self.config.guild(ctx.guild).mysql_port.set(db_port)
                await ctx.send(f"Database port set to: `{db_port}`")
            else:
                await ctx.send(f"{db_port} is not a valid port!")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your port. Please check to ensure you're attempting to use a port from 1024 to 65535") 
    
    @setmultistatus.command(aliases=['name', 'user'])
    @checks.is_owner()
    async def username(self,ctx,user: str):
        """
        Sets the user that will be used with the MySQL database. Defaults to User

        It's recommended to ensure that this user cannot write to the database 
        """
        try:
            await self.config.guild(ctx.guild).mysql_user.set(user)
            await ctx.send(f"User set to: `{user}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the username for your database.")
    
    @setmultistatus.command()
    @checks.is_owner()
    async def password(self,ctx,passwd: str):
        """
        Sets the password for connecting to the database

        This will be stored locally, it is recommended to ensure that your user cannot write to the database
        """
        try:
            await self.config.guild(ctx.guild).mysql_password.set(passwd)
            await ctx.send("Your password has been set.")
            try:
                await ctx.message.delete()
            except(discord.DiscordException):
                await ctx.send("I do not have the required permissions to delete messages, please remove/edit the password manually.")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the password for your database.")

    @setmultistatus.command(aliases=["db"])
    @checks.is_owner()
    async def database(self,ctx,db: str):
        """
        Sets the database to login to, defaults to multistatus
        """
        try:
            await self.config.guild(ctx.guild).mysql_db.set(db)
            await ctx.send(f"Database set to: `{db}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send ("There was a problem setting your notes database.")

    @setmultistatus.command()
    @checks.is_owner()
    async def table(self, ctx, table: str = None):
        """
        Sets the database table to use
        """
        try:
            await self.config.guild(ctx.guild).mysql_table.set(table)
            await ctx.send(f"Database table set to: `{table}`")
        
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your database table")

    @setmultistatus.command()
    @checks.is_owner()
    async def offline(self, ctx, *, msg: str):
        """
        Set a custom message for whenever a server is offline.
        """ 
        try:
            await self.config.offline_message.set(msg)
            await ctx.send(f"Offline message set to: `{msg}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your custom offline message. Please check your entry and try again.")
        
    @setmultistatus.command()
    async def timeout(self, ctx, seconds: int):
        """
        Sets the timeout duration for status checks
        """
        try:
            await self.config.timeout.set(seconds)
            await ctx.send(f"Timeout duration set to: `{seconds} seconds`")
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the timeout duration. Please check your input and try again.")


    @setmultistatus.command()
    async def current(self,ctx):
        """
        Gets the current settings for the notes database
        """
        settings = await self.config.guild(ctx.guild).all()
        embed=discord.Embed(title="__Current settings:__")
        for k, v in settings.items():
            if k != "admin_ckey":
                if k != "mysql_password": # Ensures that the database password is not sent
                    if v == "":
                        v = None
                    embed.add_field(name=f"{k}:",value=v,inline=False)
                else:
                    embed.add_field(name=f"{k}:",value="`redacted`",inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def addserver(self, ctx, name: str, ip: str, port: int, embedurl: str):
        """
        Adds a checkable server to the database.
        """ 
        table = await self.config.guild(ctx.guild).mysql_table()

        try:
            query = f"INSERT INTO `{table}` (`name`, `ip`, `port`, `embedurl`) VALUES ('{name}', '{ip}', '{port}', '{embedurl})'"
            await self.query_database(ctx, query)
            await ctx.send(f"{name.title()} added.")
        except:
            raise

    @commands.command()
    async def removeserver(self, ctx, name: str):
        """
        Removes a server from the database.
        """
        table = await self.config.guild(ctx.guild).mysql_table()        
        try:
            query = f"DELETE FROM `{table}` WHERE  `name`='{name}'"
            await self.query_database(ctx, query)
            await ctx.send(f"{name.title()} deleted.")
        except:
            raise

    @commands.command()
    async def listservers(self, ctx, searchterm = "%"):
        """
        Gets the complete list of servers from the database, allowing you to specify which server If there's less than 10 
        """

        table = await self.config.guild(ctx.guild).mysql_table()

        query = f"SELECT name, ip, port, embedurl, propername FROM {table} WHERE name OR propername LIKE \"%{searchterm}%\""
        message = await ctx.send("Getting servers...")

        try:
            rows = await self.query_database(ctx, query)
            if not rows:
                embed=discord.Embed(description=f"No servers found!", color=0xf1d592)
                return await message.edit(content=None,embed=embed)
            # Parse the data into individual fields within an embeded message in Discord for ease of viewing
            notes = ""
            embed=discord.Embed(title=f"Server list:", color=0xf1d592)
            for row in rows:
                if((len(rows) < 10) | (searchterm == "%%%")): #if you REALLY need to see the population of ALL servers. (NOT A GOOD IDEA)
                    try:
                        playercount = await self.clean_check_players(ctx, row['ip'], row['port'])
                    except:
                        playercount = "N/A"
                    embed.add_field(name=f'{row["propername"]} | ({row["name"]}) - {playercount} Players',value=f"IP: {row['ip']}:{row['port']} Embed: {row['embedurl']}")
                else:
                    embed.add_field(name=f'{row["propername"]} | ({row["name"]})',value=f"{row['embedurl']}")
            await message.edit(content=None,embed=embed)

        except mysql.connector.Error as err:
            embed=discord.Embed(title=f"Error looking up servers!", description=f"{format(err)}", color=0xff0000)
            await message.edit(content=None,embed=embed)
        
        except ModuleNotFoundError:
            await message.edit(content="`mysql-connector` requirement not found! Please install this requirement using `pip install mysql-connector`.")
    

    async def server_search(self, ctx, name = None) -> dict:
        """
        Runs a database query to check for the server's IP, port, and such.
        """
        table = await self.config.guild(ctx.guild).mysql_table()

        try:
            query = f"SELECT ip, port, embedurl FROM {table} WHERE name='{name}'"
            query = await self.query_database(ctx, query)


            results = {}
            try:
                query = query[0] # Checks to see if a player was found, if the list is empty nothing was found so we return the empty dict.
            except IndexError:
                return results

            return query

        except:
            raise
        
    @commands.command()
    @commands.cooldown(1, 5)
    async def check(self, ctx, server: str):
        """
        Gets the status and round details for a specified server
        """
        async with ctx.typing():
            serv_info = await self.server_search(ctx, name=server)
        port = serv_info['port']
        msg = await self.config.guild(ctx.guild).offline_message()
        server_url = serv_info['embedurl']
        server_ip = serv_info['ip']
        try:
            cleanip = socket.gethostbyname(server_ip)
            data = await self.query_server(ctx, cleanip, port)
        except TypeError:
            await ctx.send(f"Failed to get the server's status. Check that you have fully configured this cog using `{ctx.prefix}setmultistatus`.")
            return 

        if not data: #Server is not responding, send the offline message
            embed=discord.Embed(title="__Server Status:__", description=f"{msg}", color=0xff0000)
            await ctx.send(embed=embed)

        else:
            #Reported time is in seconds, we need to convert that to be easily understood
            duration = int(*data['round_duration'])
            duration = time.strftime('%H:%M', time.gmtime(duration))
            #Players also includes the number of admins, so we need to do some quick math
            players = (int(*data['players']) - int(*data['admins'])) 
            #Format long map names
            mapname = str.title(*data['map_name'])
            mapname = '\n'.join(textwrap.wrap(mapname,25))

            #Might make the embed configurable at a later date

            embed=discord.Embed(title=f"{server.title()}'s status:", color=0x26eaea)
            embed.add_field(name="Map", value=mapname, inline=True)
            embed.add_field(name="Security Level", value=str.title(*data['security_level']), inline=True)
            if  "shuttle_mode" in data:
                if ("docked" or "call") not in data['shuttle_mode']:
                    embed.add_field(name="Shuttle Status", value=str.title(*data['shuttle_mode']), inline=True)
                else:
                    embed.add_field(name="Shuttle Timer", value=time.strftime('%M:%S', time.gmtime(int(*data['shuttle_timer']))), inline=True)
            else:
                embed.add_field(name="Shuttle Status", value="Refueling", inline=True)
            embed.add_field(name="Players", value=players, inline=True)
            embed.add_field(name="Admins", value=int(*data['admins']), inline=True)
            embed.add_field(name="Round Duration", value=duration, inline=True)
            embed.add_field(name="Server Link:", value=f"{server_url}", inline=False)

            try:
                await self.statusmsg.delete()
                self.statusmsg = await ctx.send(embed=embed)
            except(discord.DiscordException, AttributeError):
                self.statusmsg = await ctx.send(embed=embed)

    async def clean_check_players(self, ctx, game_server:str, game_port:int) -> dict:
        cleanip = socket.gethostbyname(game_server)
        data = await self.query_server(ctx, cleanip, game_port)
        return int(*data['players'])

    async def query_server(self, ctx, game_server:str, game_port:int, querystr="?status" ) -> dict:
        """
        Queries the server for information
        """
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 

        try:
            query = b"\x00\x83" + struct.pack('>H', len(querystr) + 6) + b"\x00\x00\x00\x00\x00" + querystr.encode() + b"\x00" #Creates a packet for byond according to TG's standard
            conn.settimeout(await self.config.guild(ctx.guild).timeout()) #Byond is slow, timeout set relatively high to account for any latency
            conn.connect((game_server, game_port)) 

            conn.sendall(query)

            data = conn.recv(4096) #Minimum number should be 4096, anything less will lose data

            parsed_data = urllib.parse.parse_qs(data[5:-1].decode())

            return parsed_data
            """
            +----------------+--------+
            | Reported Items | Return |
            +----------------+--------+
            | Version        | str    |
            | mode           | str    |
            | respawn        | int    |
            | enter          | int    |
            | vote           | int    |
            | ai             | int    |
            | host           | str    |
            | active_players | int    |
            | players        | int    |
            | revision       | str    |
            | revision_date  | date   |
            | admins         | int    |
            | gamestate      | int    |
            | map_name       | str    |
            | security_level | str    |
            | round_duration | int    |
            | shuttle_mode   | str    |
            | shuttle_timer  | str    |
            +----------------+--------+
            """ #pylint: disable=unreachable
            
        except (ConnectionRefusedError, socket.gaierror, socket.timeout):
            return None #Server is likely offline

        finally:
            conn.close()

    async def query_database(self, ctx, query: str):
        # Database options loaded from the config
        db = await self.config.guild(ctx.guild).mysql_db()
        db_host = socket.gethostbyname(await self.config.guild(ctx.guild).mysql_host())
        db_port = await self.config.guild(ctx.guild).mysql_port()
        db_user = await self.config.guild(ctx.guild).mysql_user()
        db_pass = await self.config.guild(ctx.guild).mysql_password()

        cursor = None # Since the cursor/conn variables can't actually be closed if the connection isn't properly established we set a None type here
        conn = None # ^

        try:
            # Establish a connection with the database and pull the relevant data
            conn = mysql.connector.connect(host=db_host,port=db_port,database=db,user=db_user,password=db_pass, connect_timeout=5)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()

            return rows
        
        except:
            raise 

        finally:
            if cursor is not None:
                cursor.close()  
            if conn is not None:
                conn.close()

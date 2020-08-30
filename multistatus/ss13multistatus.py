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
import aiomysql
import mysql.connector
import ipaddress
import re
from typing import Union
import logging

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

__version__ = "0.0.3"
__author__ = "MarkSuckerberg with Crossedfall's code"

log = logging.getLogger("red.SS13MultiStatus")

BaseCog = getattr(commands, "Cog", object)

class SS13MultiStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257143194, force_registration=True)

        default_global = {
            "cache_toggle": True,
            "timeout": 10,
            "retries": 1,
            "offline_message": "Currently offline",    
            "mysql_table": "multistatus",
            "mysql_host": "127.0.0.1",
            "mysql_port": 3306,
            "mysql_user": "user",
            "mysql_password": "password",
            "mysql_db": "multistatus"
        }

        self.config.register_global(**default_global)
        self.svr_chk_task = self.bot.loop.create_task(self.player_cache_loop())



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
            await self.config.mysql_host.set(db_host)
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
                await self.config.mysql_port.set(db_port)
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
            await self.config.mysql_user.set(user)
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
            await self.config.mysql_password.set(passwd)
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
            await self.config.mysql_db.set(db)
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
            await self.config.mysql_table.set(table)
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
            await ctx.send(f"Timeout duration set to: `{seconds}` seconds`")
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the timeout duration. Please check your input and try again.")

    @setmultistatus.command()
    async def retries(self, ctx, attempts: int):
        """
        Sets the amount of retries done for information. Defaults to one retry.
        """
        try:
            await self.config.retries.set(attempts)
            await ctx.send(f"Amount of retries set to: `{attempts}` retries`")
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the retry amount. Please check your input and try again.")


    @setmultistatus.command()
    async def current(self,ctx):
        """
        Gets the current settings for the notes database
        """
        settings = await self.config.all()
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

    @setmultistatus.command()
    async def addserver(self, ctx, name: str, ip: str):
        """
        Adds a checkable server to the database.
        """ 
        try:
            if("byond://" in ip): #Check input to see if it's a BYOND URL or an IP address.
                embedurl = f"<{ip}>"
                byondip = ip[8:len(ip)] #Trims byond:// from IP
                port = int((ip.split(":"))[2]) #This is horrible code, yes, I know. It works, though!
            else:
                embedurl = f"<byond://{ip}>"
                byondip = (ip.split(":"))[0]
                port = int((ip.split(":"))[1]) #this too
        except (TypeError, IndexError):
            await ctx.send(f"{ip} is not a valid IP address! Please use either the raw IP (not the web redirect, and make sure it includes the port) or the byond URL!")
            return

        byondip = (byondip.split(":"))[0] #trims the port off the IP

        table = await self.config.mysql_table()
        query = f"INSERT INTO {table} (name, ip, port, embedurl, propername) VALUES ('{name}', '{byondip}', {port}, '{embedurl}', '{name.title()}')"
        try:
            info = await self.modify_database(query)
            result = await self.query_database(f"SELECT * FROM {table} where name=\"{name}\"")
            if not result:
                await ctx.send(f"{name.title()} could not be added. Query: {query} | Result: {info}")
            else:    
                await ctx.send(f"{name.title()} added.")
        except:
            raise

    @setmultistatus.command()        
    async def removeserver(self, ctx, name: str):
        """
        Removes a server from the database.
        """
        table = await self.config.mysql_table()       
        query = f"DELETE FROM {table} WHERE  name=\"{name}\""
        try:
            info = await self.modify_database(query)
            result = await self.query_database(f"SELECT * FROM {table} where name=\"{name}\"")            
            if result:
                await ctx.send(f"{name.title()} could not be removed. Query: {query} | Result: {info}")
            else:    
                await ctx.send(f"{name.title()} removed.")
        except:
            raise

    @setmultistatus.command()
    async def refresh(self, ctx):
        """
        Reloads the current pop cache manually.
        """
        message = await ctx.send("Reloading cache...")
        try:
            await self.player_cache_loop()
            await message.edit(content="Cache reloaded successfully.")
        except:
            await message.edit(content="Cache reload failed!")
            raise


    async def server_search(self, ctx, name = None) -> dict:
        """
        Runs a database query to check for the server's IP, port, and such.
        """
        table = await self.config.mysql_table()

        try:
            query = f"SELECT * FROM {table} WHERE name OR propername LIKE \"%{name}%\" ORDER BY `cachedpop` DESC"
            query = await self.query_database(query)


            results = {}
            try:
                query = query[0] # Checks to see if a player was found, if the list is empty nothing was found so we return the empty dict.
            except IndexError:
                return results

            return query

        except:
            raise
        
    @commands.command(aliases=['serverlist'])
    async def listservers(self, ctx, name = "%"):
        """
        Gets the complete list of servers from the database, allowing you to specify which server. If there's less than 10, it shows playercounts and additional details.
        """

        table = await self.config.mysql_table()

        query = f"SELECT * FROM {table} WHERE name OR propername LIKE \"%{name}%\" ORDER BY `cachedpop` DESC"
        message = await ctx.send("Getting servers...")

        try:
            rows = await self.query_database(query)
            if not rows:
                embed=discord.Embed(description=f"No servers found!", color=0xf1d592)
                return await message.edit(content=None,embed=embed)
            # Parse the data into individual fields within an embeded message in Discord for ease of viewing
            embed=discord.Embed(title=f"Server list:", color=0xf1d592)
            for row in rows:
                if((len(rows) <= 10) | (name == "%%%")): #if you REALLY need to see the population of ALL servers. (NOT A GOOD IDEA) nevermind, it's all cached now so it's all good
                    embed.add_field(name=f'{row["propername"]} | ({row["name"]}) - {row["cachedpop"]} Players',value=f"IP: {row['ip']}:{row['port']} Embed: {row['embedurl']}", inline = False)
                else:
                    embed.add_field(name=f'{row["propername"]} | ({row["name"]}) - {row["cachedpop"]} Players',value=f"{row['embedurl']}", inline = False)
            embed.set_footer(text="Accuracy not guaranteed.")
            await message.edit(content=None,embed=embed)        
        except mysql.connector.Error as err:
            embed=discord.Embed(title=f"Error looking up servers!", description=f"{format(err)}", color=0xff0000)
            await message.edit(content=None,embed=embed)
        
        except ModuleNotFoundError:
            await message.edit(content="`mysql-connector` requirement not found! Please install this requirement using `pip install mysql-connector`.")
    

    @commands.command(aliases=['status'])  
    async def check(self, ctx, server: str):
        """
        Gets the status and round details for a specified server
        """
        table = await self.config.mysql_table()
        async with ctx.typing():
            serv_info = await self.server_search(ctx, name=server)
        if not serv_info:
            await ctx.send("Server not found!")
            return

        port = serv_info['port']
        msg = await self.config.offline_message()
        server_url = serv_info['embedurl']
        server_ip = serv_info['ip']
        col = discord.Color(value=int(serv_info['color'], 16))

        try:
            cleanip = socket.gethostbyname(server_ip)
            data = await self.query_server(cleanip, port)
        except:
            await ctx.send(f"Failed to get the server's status. Check that you have fully configured this cog using `{ctx.prefix}setmultistatus`.")
            raise

        if not data: #Server is not responding, send the offline message
            embed=discord.Embed(title="__Server Status:__", description=f"{msg}", color=0xff0000)
            await ctx.send(embed=embed)
        else:
            try:
                await self.modify_database(f"UPDATE `{table}` SET `cachedpop`='{data['players'][0]}' WHERE `name`='{serv_info['name']}'") #Might as well cache it since we got it
                #Reported time is in seconds, we need to convert that to be easily understood
                if("round_duration" in data):
                    duration = int(*data['round_duration'])
                else:
                    duration = int(*data['roundduration'])    
                duration = time.strftime('%H:%M', time.gmtime(duration))
                #Format long map names
                mapname = str.title(*data['map_name'])
                mapname = '\n'.join(textwrap.wrap(mapname,25))

                #Might make the embed configurable at a later date

                embed=discord.Embed(title=f"{serv_info['propername']}'s status:", color=col)
                embed.add_field(name="Map", value=mapname, inline=True)
                embed.add_field(name="Security Level", value=str.title(*data['security_level']), inline=True)
                if("shuttle_mode" in data):
                    if ("docked" or "call") not in data['shuttle_mode']:
                        embed.add_field(name="Shuttle Status", value=str.title(*data['shuttle_mode']), inline=True)
                    else:
                        embed.add_field(name="Shuttle Timer", value=time.strftime('%M:%S', time.gmtime(int(*data['shuttle_timer']))), inline=True)
                else:
                    embed.add_field(name="Shuttle Status", value="Refueling", inline=True)
                if("popcap" in data):
                    embed.add_field(name="Players", value=f"{data['players'][0]}/{data['popcap'][0]}" , inline=True)
                else:
                    embed.add_field(name="Players", value=data['players'][0], inline=True)
                embed.add_field(name="Admins", value=data['admins'][0], inline=True)
                embed.add_field(name="Round Duration", value=duration, inline=True)
                embed.add_field(name="Server Link:", value=f"{server_url}", inline=False)

            except: #That failed, let's send a baby version of it
                embed=discord.Embed(title=f"{serv_info['propername']}'s status:", color=col)
                embed.add_field(name="Players", value=data['players'][0], inline=True)
                embed.add_field(name="Mode", value=str(data['mode']).split("'")[1], inline=True)

                if("map_name" in data): #TG
                    embed.add_field(name="Map", value=str.title(*data['map_name']), inline=True)
                elif("map" in data): #Bay/Goon
                    embed.add_field(name="Map", value=str.title(*data['map']), inline=True)

                if("round_duration" in data): #TG
                    embed.add_field(name="Round Duration", value=str(*data['round_duration']), inline=True)
                elif("roundduration" in data): #Bay
                    embed.add_field(name="Round Duration", value=str(*data['roundduration']), inline=True)
                elif("elapsed" in data): #Goon
                    embed.add_field(name="Round Duration", value=time.strftime('%H:%M', time.gmtime(int(*data['elapsed']))), inline=True)



                embed.add_field(name="Server Link:", value=f"{server_url}", inline=False)
                embed.set_footer(text="Limited information available.")

            try:
                await self.statusmsg.delete()
                self.statusmsg = await ctx.send(embed=embed)
            except(discord.DiscordException, AttributeError):
                self.statusmsg = await ctx.send(embed=embed)                

    @commands.command()  
    async def devcheck(self, ctx, server: str):
        """
        Gets the code status for a specified server
        """
        table = await self.config.mysql_table()
        async with ctx.typing():
            serv_info = await self.server_search(ctx, name=server)
        if not serv_info:
            await ctx.send("Server not found!")
            return

        port = serv_info['port']
        msg = await self.config.offline_message()
        server_url = serv_info['embedurl']
        server_ip = serv_info['ip']
        col = discord.Color(value=int(serv_info['color'], 16))

        try:
            cleanip = socket.gethostbyname(server_ip)
            data = await self.query_server(cleanip, port)
        except:
            await ctx.send(f"Failed to get the server's status. Check that you have fully configured this cog using `{ctx.prefix}setmultistatus`.")
            raise

        if not data: #Server is not responding, send the offline message
            embed=discord.Embed(title="__Server Status:__", description=f"{msg}", color=0xff0000)
            await ctx.send(embed=embed)
        else:
            embed=discord.Embed(title=f"{serv_info['propername']}'s dev stats:", color=col)
            
            if("version" in data): #TG
                embed.add_field(name="Version", value=str(*data['version']), inline=True)

            if("popcap" in data):
                if(("soft_popcap" in data) & ("hard_popcap" in data)):
                    embed.add_field(name="Popcap", value=f"{int(*data['soft_popcap'])}/{int(*data['hard_popcap'])}/{int(*data['popcap'])}", inline=True)
                else:
                    embed.add_field(name="Popcap", value=int(*data['popcap']), inline=True)

            if("host" in data):
                embed.add_field(name="Hosted by", value=str(*data['host']))

            if("time_dilation_current" in data):
                embed.add_field(name="Current Time Dilation", value=f"{float(*data['time_dilation_current'])}%", inline=True)

            if("time_dilation_avg" in data):
                embed.add_field(name="Average Time Dilation", value=f"{float(*data['time_dilation_avg_slow'])}% /{float(*data['time_dilation_avg'])}% /{float(*data['time_dilation_avg_fast'])}%", inline=False)

            await ctx.send(embed=embed)

    @setmultistatus.command()
    async def getattribs(self, ctx, server:str, info = None):
        """
        Gets the public players in a server.
        """
        async with ctx.typing():
            serv_info = await self.server_search(ctx, name=server)
        if not serv_info:
            await ctx.send("Server not found!")
            return

        port = serv_info['port']
        msg = await self.config.offline_message()
        server_url = serv_info['embedurl']
        server_ip = serv_info['ip']
        col = discord.Color(value=int(serv_info['color'], 16))

        try:
            cleanip = socket.gethostbyname(server_ip)
            data = await self.query_server(cleanip, port)
        except:
            await ctx.send(f"Failed to get the server's status. Check that you have fully configured this cog using `{ctx.prefix}setmultistatus`.")
            raise        

        if(info):
            await ctx.send(data[f'{info}'])
        else:
            attribs = []

            if data:
                for row in data:
                    attribs.append(row)
                await ctx.send(attribs)    


    @commands.command()
    async def players(self, ctx, server:str, raw = False):
        """
        Gets the players from most servers.
        """
        async with ctx.typing():
            serv_info = await self.server_search(ctx, name=server)
        if not serv_info:
            await ctx.send("Server not found!")
            return

        port = serv_info['port']
        server_ip = socket.gethostbyname(serv_info['ip'])
        col = discord.Color(value=int(serv_info['color'], 16))

        players = []
        data = await self.query_server(server_ip, port)
        if data:
            for row, ckey in data.items():
                if(row == "players"): #So that the player value isn't added
                    continue
                if((not row.find("player")) | (not row.find("client"))): #Don't ask me why there's a not, but this checks for player rows
                    players.append(str(*data[row]))


    #                playername = (str(ckey).split("'"))[1] #Splits the return value (['name']) into three parts, and takes the part with just the name
    #                players.append(playername)

        if((not len(players)) & (int(data['players'][0]) > 0)): #If there's no player info, and there's more than 0 players on
            try:
                data = await self.query_server(server_ip, port, "?whoIs")
                players = [i for i in data['players']]
            except KeyError:
                embed = discord.Embed(title=f"__Current Players__ (0): ", description="Command not supported by this server.", color=col)

        if(not raw):
            if(not len(players)): #If neither worked, send this embed instead
                embed = discord.Embed(title=f"__Current Players__ (0): ", description="No players currently online or server does not support this command.", color=col)
            else: #If one DID work, then put the players list into an embed
                embed = discord.Embed(title=f"__Current Players__ ({len(players)}): ", description=f'\n'.join(map(str,players)), color=col)

            await ctx.send(embed=embed)
        else:
            await ctx.send(players)
            return players    


    async def clean_check_players(self, game_server:str, game_port:int) -> int:
        cleanip = socket.gethostbyname(game_server)
        data = await self.query_server(cleanip, game_port)
        return data['players'][0]

    async def query_server(self, game_server:str, game_port:int, querystr="?status", attempt = 0) -> dict:
        """
        Queries the server for information
        """
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 

        try:
            query = b"\x00\x83" + struct.pack('>H', len(querystr) + 6) + b"\x00\x00\x00\x00\x00" + querystr.encode() + b"\x00" #Creates a packet for byond according to TG's standard
            conn.settimeout(await self.config.timeout()) #Byond is slow, timeout set relatively high to account for any latency
            conn.connect((game_server, game_port)) 

            conn.sendall(query)

            data = conn.recv(6144) #Minimum number should be 4096, anything less will lose data

            parsed_data = urllib.parse.parse_qs(data[5:-1].decode())

            return parsed_data
            """
            +----------------+--------+ - NOT ACCURATE FOR ALL SERVERS!!!
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

        except:
            max_attempts = await self.config.retries()
            if(attempt <= max_attempts): #Attempt to reconnect
                return await self.query_server(game_server, game_port, querystr, attempt + 1)
            else:
                return None

        finally:
            conn.close()

    async def query_database(self, query: str):
        # Database options loaded from the config
        db = await self.config.mysql_db()
        db_host = socket.gethostbyname(await self.config.mysql_host())
        db_port = await self.config.mysql_port()
        db_user = await self.config.mysql_user()
        db_pass = await self.config.mysql_password()

        pool = None # Since the pool variables can't actually be closed if the connection isn't properly established we set a None type here

        try:
            # Establish a connection with the database and pull the relevant data
            pool = await aiomysql.create_pool(host=db_host,port=db_port,db=db,user=db_user,password=db_pass, connect_timeout=5)
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query)
                    rows = cur.fetchall()
                    return rows.result()
            
        except:
            raise 

        finally:
            if pool is not None:
                pool.close()
                await pool.wait_closed()

    async def modify_database(self, query: str):
        # Database options loaded from the config
        db = await self.config.mysql_db()
        db_host = socket.gethostbyname(await self.config.mysql_host())
        db_port = await self.config.mysql_port()
        db_user = await self.config.mysql_user()
        db_pass = await self.config.mysql_password()

        pool = None # Since the pool variables can't actually be closed if the connection isn't properly established we set a None type here

        try:
            # Establish a connection with the database and pull the relevant data
            pool = await aiomysql.create_pool(host=db_host,port=db_port,db=db,user=db_user,password=db_pass, connect_timeout=5)
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    info = await cur.execute(query)
                    await conn.commit()
                    return info
            
        except:
            raise 

        finally:
            if pool is not None:
                pool.close()
                await pool.wait_closed()


    async def player_cache_loop(self):
        table = await self.config.mysql_table()        
        check_time = 100
        now = datetime.utcnow()
        toggle = await self.config.cache_toggle()

        while self == self.bot.get_cog("SS13MultiStatus"):
            log.debug("Starting server checks")            

            if(toggle is False):
                pass
            else:
                query = f"SELECT name, ip, port FROM {table}"            
                rows = await self.query_database(query)
                for row in rows:
                    cache_pop = await self.clean_check_players(row['ip'], row['port'])
                    cache_query = f"UPDATE `{table}` SET `cachedpop`='{cache_pop}' WHERE `name`='{row['name']}'"
                    await self.modify_database(cache_query)

            now = datetime.utcnow()
            next_check = datetime.utcfromtimestamp(now.timestamp() + check_time)
            log.debug("Done. Next check at {}".format(next_check.strftime("%Y-%m-%d %H:%M:%S")))            
            await asyncio.sleep(check_time)                    
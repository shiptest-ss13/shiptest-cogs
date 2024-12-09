from .ss13multistatus import SS13MultiStatus

async def setup(bot):
    bot.add_cog(SS13MultiStatus(bot))
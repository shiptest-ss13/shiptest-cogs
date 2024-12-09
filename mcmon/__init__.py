from .mcmon import MCMon


async def setup(bot):
    bot.add_cog(MCMon(bot))

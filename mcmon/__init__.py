from .mcmon import MCMon


async def setup(bot):
    await bot.add_cog(MCMon(bot))

from .ss13multistatus import SS13MultiStatus

async def setup(bot):
    await bot.add_cog(SS13MultiStatus(bot))
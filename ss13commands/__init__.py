from .ss13commands import SS13Commands

async def setup(bot):
    await bot.add_cog(SS13Commands(bot))
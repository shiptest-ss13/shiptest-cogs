from .fsctime import FSCTime

async def setup(bot):
    await bot.add_cog(FSCTime(bot))

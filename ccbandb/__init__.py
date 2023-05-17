from .ccbandb import CCBanDB

async def setup(bot):
    await bot.add_cog(CCBanDB(bot))
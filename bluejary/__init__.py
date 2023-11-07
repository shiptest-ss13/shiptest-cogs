from .bluejary import BluejaryBot

async def setup(bot):
    await bot.add_cog(BluejaryBot(bot))

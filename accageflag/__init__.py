from .accageflag import AccountAgeFlagger

async def setup(bot):
    await bot.add_cog(AccountAgeFlagger(bot))

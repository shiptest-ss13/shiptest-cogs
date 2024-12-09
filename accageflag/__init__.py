from .accageflag import AccountAgeFlagger

async def setup(bot):
    bot.add_cog(AccountAgeFlagger(bot))

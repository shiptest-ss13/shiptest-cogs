from .ss13mon import SS13Mon

async def setup(bot):
    await bot.add_cog(SS13Mon(bot))

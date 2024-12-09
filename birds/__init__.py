from .birds import Birds

async def setup(bot):
    await bot.add_cog(Birds(bot))


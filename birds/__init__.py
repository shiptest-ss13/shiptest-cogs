from .birds import Birds

async def setup(bot):
    bot.add_cog(Birds(bot))


from .tgslink import TGSLink

async def setup(bot):
    await bot.add_cog(TGSLink(bot))

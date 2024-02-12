from .report import Report

async def setup(bot):
    await bot.add_cog(Report(bot))

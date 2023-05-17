from .gh import GithubPRRetriever

async def setup(bot):
    await bot.add_cog(GithubPRRetriever(bot))
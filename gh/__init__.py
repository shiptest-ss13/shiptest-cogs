from .gh import GithubPRRetriever

def setup(bot):
    bot.add_cog(GithubPRRetriever(bot))
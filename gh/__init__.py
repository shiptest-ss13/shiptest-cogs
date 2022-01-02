from .gh import GH

def setup(bot):
    bot.add_cog(GH(bot))
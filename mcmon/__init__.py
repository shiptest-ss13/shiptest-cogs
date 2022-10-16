from .mcmon import MCMon


def setup(bot):
    bot.add_cog(MCMon(bot))

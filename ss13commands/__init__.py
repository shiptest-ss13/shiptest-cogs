from .ss13commands import SS13Commands

def setup(bot):
    bot.add_cog(SS13Commands(bot))
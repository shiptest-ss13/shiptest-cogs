from .ss13status import SS13Commands

def setup(bot):
    bot.add_cog(SS13Commands(bot))
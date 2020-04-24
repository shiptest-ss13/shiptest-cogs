from .ss13multistatus import SS13MultiStatus

def setup(bot):
    bot.add_cog(SS13MultiStatus(bot))
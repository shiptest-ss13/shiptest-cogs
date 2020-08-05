from .ccbandb import CCBanDB

def setup(bot):
    bot.add_cog(CCBanDB(bot))
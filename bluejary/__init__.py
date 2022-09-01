from .bluejary import BluejaryBot


def setup(bot):
    bot.add_cog(BluejaryBot(bot))

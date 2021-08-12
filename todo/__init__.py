from .todo import ToDoCog

def setup(bot):
    bot.add_cog(ToDoCog(bot))
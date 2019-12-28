from discord.utils import find
from pysqlite3 import dbapi2 as sqlite
from sys import modules

def initialize(bot):
    bot.roles = {}

    bot.conn = sqlite.connect('./plugins/roles.db')

    for row in bot.conn.execute("SELECT * FROM role_reaction"):
        guild, role, reaction = row
        guild = int(guild)
        role = int(role)
        reaction = int(reaction)

        if not bot.roles.get(guild):
            bot.roles[guild] = {}

        bot.roles[guild][reaction] = int(role)

    print(bot.roles)


async def on_reaction(android18, payload):
    # cool now we need to check if it's in our table.
    roles = android18.roles

    if roles.get(payload.guild_id, {}).get(payload.emoji.id):
        # we got it cool!
        print('Adding role!')

        guild = find(lambda g: g.id == payload.guild_id, android18.guilds) 
        user = find(lambda m: m.id == payload.user_id, guild.members)
        await user.add_roles(guild.get_role(roles[guild.id][payload.emoji.id]))

    print("Called! %s" % payload)
    pass

def get_helpstr():
    return """
              role  <role_mention> <reaction> | Adds user to that role based on reaction.
           """

async def on_roles(android18, args, msg):
    roles = android18.roles.get(msg.guild.id, {}).items()
    await msg.channel.send('`Currently I support the following roles: (reactions are the roles the reaction will give!)`')

    for emoji, role in roles:
        r = msg.guild.get_role(role)
        e = await msg.guild.fetch_emoji(emoji)
        
        m = await msg.channel.send('`%s`' % (r.name))
        await m.add_reaction(e)
    
async def on_role(android18, args, msg):
    # Good one, kid.
    if not msg.author.guild_permissions.administrator: return

    role = msg.role_mentions[0]
    emoji = args[-1].split(':')[2][:-1]
    print(emoji)

    if not android18.roles.get(msg.guild.id):
        android18.roles[msg.guild.id] = {}

    android18.roles[msg.guild.id][int(emoji)] = role.id
    android18.conn.execute("INSERT INTO role_reaction(guild_id, role_id, reaction_id) VALUES ('%s', '%s', '%s')" % (msg.guild.id, role.id, emoji))
    android18.conn.commit()




async def on_message(android18, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(android18, msg, msg_obj)
        return True
    return False

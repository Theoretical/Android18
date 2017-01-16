from discord.utils import find
from sys import modules

def initialize(bot):
    pass

def get_helpstr():
    return """
              kiss  <user> |\tSends that user a kiss!
              clear <amt>  |\tClears the channel of messages (admin req)
              github       |\tPosts the github link of Zulia.
              avatar <user>|\tPosts the user's avatar (or current user)
           """
async def on_kiss(zulia, args, msg):
    emoji = ':kissing_heart:'
    user = msg.author
    if len(args) > 1:
        user = find(lambda m: m.mention == args[1], msg.server.members)

    await zulia.send_message(msg.channel, 'Here is your kiss {} {}'.format(user.mention, emoji))

async def on_clear(zulia, args, msg):
    if not msg.author.server_permissions.administrator: return
    await zulia.purge_from(msg.channel, limit=int(args[1]))

async def on_git(zulia, args, msg):
    await zulia.send_message(msg.channel, '`My github is located at: `https://github.com/Theoretical/Zulia')

async def on_avatar(zulia, args, msg):
    user = msg.author
    if len(args) > 1:
        user = find(lambda m: m.mention == args[1], msg.server.members)

    await zulia.send_message(msg.channel, '`{} avatar is: `{}'.format(user.name, user.avatar_url))

async def on_message(zulia, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(zulia, msg, msg_obj)
        return True
    return False

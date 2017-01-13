from discord.utils import find
from sys import modules

def initialize(zulia): pass

async def on_message(zulia, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(zulia, msg, msg_obj)
        return True
    return False

from sys import modules

async def initialize(bot):
    pass

async def on_clear(msg, msg_obj):
    return True

async def on_test(msg, msg_obj):
    print(msg_obj.author.server_permissions())
    print(msg_obj.author.server_permissions().administrator)

async def on_message(bot, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(msg, msg_obj)
        return True
    return False

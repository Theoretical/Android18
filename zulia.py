from aiohttp import get
from discord import Client, opus, enums
from discord.utils import get
from importlib import import_module, reload
from os import environ, listdir
import asyncio

# Load our Opus library for Discord so we can play music.
opus.load_opus('/usr/lib/x86_64-linux-gnu/libopus.so.0')


# Wrap Zulia around a normal Discord client, we're going to extend it on our own.
class Zulia(Client):
    def __init__(self, command_prefix):
        # Init the normal discord client.
        Client.__init__(self)

        self.command_prefix = command_prefix
        self.plugins = []

        # Load all of our bot extensions.
        self._load_plugins()

    def _load_plugins(self):
        self.plugins = [import_module('plugins.%s' % module.replace('.py', '')) for module in listdir('plugins/') if '.py' in module and '__' not in module]

        for plugin in self.plugins:
            # Initialize every plugin withour bot instance.
            plugin.initialize(self)

        print('Successfully loaded: %s plugins' % len(self.plugins))

    @asyncio.coroutine
    async def on_message(self, message):
        message_args = message.content.split(' ')

        # First character in a message SHOULD be our prefix.
        command_prefix = message_args[0][0]

        # We don't have  reason to be here.
        if command_prefix != self.command_prefix: return

        # Clean up so we don't include the prefix in every message.
        message_args[0] = message_args[0][1:]

        delete_message = False
        for plugin in self.plugins:
            should_remove = await plugin.on_message(self, message_args, message)

            if should_remove: delete_message = True

        # This is a Zulia only plugin used to reload all of our plugins during runtime.
        if message_args[0] == 'reload':
            if not message.author.server_permissions.administrator:
                await self.delete_message(message)
                return

            delete_message = True

            # Reload all plugin modules.
            self.plugins = [reload(plugin) for plugin in self.plugins]
            for plugin in self.plugins:
                # We're going to call our helper function to reinitialize the module.
                if hasattr(plugin, 'reinitialize'):
                    await plugin.reinitialize(self)

            await bot.send_message(message.channel, 'Successfully reloaded {} plugins'.format(len(self.plugins)))

        if delete_message: await self.delete_message(message)

zulia = Zulia('.')

@zulia.event
async def on_ready():
    servers = zulia.servers

    for server in servers:
        main_channel = get(server.channels, type=enums.ChannelType.text, position=0)

        fmt_msg = '`Hello members of {name}! I\'m {bot}! I will be here to assist you in any way that I can!`'
        await zulia.send_message(main_channel, fmt_msg.format(name=server.name, bot=zulia.user.name))
        print(fmt_msg.format(name=server.name, bot=zulia.user.name))

# TODO: Add a config file.
zulia.run(environ.get('DISCORD_TOKEN'))

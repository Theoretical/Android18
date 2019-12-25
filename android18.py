from configparser import ConfigParser
from discord import Client, opus, enums
from discord.utils import get
from importlib import import_module, reload
from os import environ, listdir
import asyncio

# Load our Opus library for Discord so we can play music.
opus.load_opus('/usr/lib/x86_64-linux-gnu/libopus.so.0')


# Wrap Android18 around a normal Discord client, we're going to extend it on our own.
class Android18(Client):
    def __init__(self, command_prefix):
        # Init the normal discord client.
        Client.__init__(self)

        self.command_prefix = command_prefix
        self.plugins = []

        self.config = ConfigParser()
        self.config.read('config.ini')

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

        # This is an Android18 only plugin used to call our help functions for each plugin.
        if message_args[0] == 'help':
            should_remove = True
            help_str = ''
            for plugin in self.plugins:
                if hasattr(plugin, 'get_helpstr'):
                    plugin_name = str(plugin).split('/')[-1].split(".")[0]
                    print(str(plugin))
                    help_str += 'Plugin: {}\n{}\n\n'.format(plugin_name, plugin.get_helpstr())

            await self.send_message(message.channel, '```{}```'.format(help_str))


        # This is an Android18 only plugin used to reload all of our plugins during runtime.
        elif message_args[0] == 'reload':
            if not message.author.guild_permissions.administrator:
                await message.delete()
                return

            delete_message = True

            # Reload all plugin modules.
            self.plugins = [reload(plugin) for plugin in self.plugins]
            for plugin in self.plugins:
                # We're going to call our helper function to reinitialize the module.
                if hasattr(plugin, 'reinitialize'):
                    await plugin.reinitialize(self)

            await message.channel.send('Successfully reloaded {} plugins'.format(len(self.plugins)))

        if delete_message: await message.delete()

android18 = Android18('.')

@android18.event
async def on_ready():
    servers = android18.guilds

    for server in servers:
        main_channel = get(server.channels, type=enums.ChannelType.text, position=0)

        fmt_msg = '`Hello members of {name}! I\'m {bot}! I will be here to assist you in any way that I can!`'
#        await android18.send_message(main_channel, fmt_msg.format(name=server.name, bot=zulia.user.name))

# TODO: Add a config file.
android18.run(android18.config['Discord']['Auth'])

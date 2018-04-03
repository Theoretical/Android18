from discord.utils import find
from sys import modules
from aiohttp import get, post
from lxml.html import fromstring

# zulia instance..
zulia = None
token = None
expires_at = None
refresh_token = None

async def login(zulia):
    user = zulia.config['Fortnite']['Username']
    password = zulia.config['Fortnite']['Password']
    launcher = zulia.config['Fortnite']['Launcher']
    client = zulia.config['Fortnite']['Client']

    # OAuth takes 3 steps.
    
    #1.) Step 1: Grab credentials token
    token_url = 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token'
    exchange_url = 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/exchange'

    cred_data = {
        'grant_type': 'password',
        'username': user,
        'password': password,
        'includePerms': True
    }

    cred = await post(token_url, headers={'Authorization': 'basic ' + launcher}, data=cred_data)
    data = await cred.json()
    refresh_token = data['access_token']

    exchange = await get(exchange_url, headers={'Authorization': 'bearer ' + refresh_token})
    exchange_data = await exchange.json()

    print(exchange_data)
    code = exchange_data['code']

    token_data = {
        'grant_type': 'exchange_code',
        'exchange_code': code,
        'includePerms': True,
        'token_type': 'egl'
    }

    token_res = await post(token_url, headers={'Authorization': 'basic ' + client}, data=token_data)
    token_data = await token_res.json()

    return token_data['expires_at'], token_data['access_token'], token_data['refresh_token']


async def call_fortnite(url, data=None):
    global token
    res = await get(url, headers={'Authorization': 'bearer ' + token}, data=data)
    return await res.json()

async def get_user(username):
    lookup_url = 'https://persona-public-service-prod06.ol.epicgames.com/persona/api/public/account/lookup?q={user}'
    res = await call_fortnite(lookup_url.format(user=username))
    return res.get('id')

async def get_stats(id):
    stats_url = 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/stats/accountId/{account}/bulk/window/alltime'
    stats = await call_fortnite(stats_url.format(account=id))
    return stats


async def on_fn(zulia, args, msg):
    user_id = await get_user(args[1])
    stats = await get_stats(user_id)
    
    from json import dumps
    print(dumps(stats, indent=4))

    await zulia.send_message(msg.channel, '```{}```'.format(stats))


def initialize(bot):
    pass

async def initialize_async(bot):
    global zulia, token, expires_at, refresh_token
    zulia = bot
    print('Logging in to fortnite!')
    expires_at, token, refresh_token = await login(zulia)

async def on_message(zulia, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(zulia, msg, msg_obj)
        return True
    return False
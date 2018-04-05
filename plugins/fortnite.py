from discord.utils import find
from sys import modules
from aiohttp import get, post
from lxml.html import fromstring
from terminaltables import AsciiTable


# zulia instance..
zulia = None
token = None
expires_at = None
refresh_token = None
tracker_key = None

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
    print (res)
    return res.get('id')

async def get_stats(id):
    stats_url = 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/stats/accountId/{account}/bulk/window/alltime'
    stats = await call_fortnite(stats_url.format(account=id))
    return stats


def convert_stats(stat_data):
    # Only do PC for now.
    solo = {'wins': 0}
    duo = {'wins': 0}
    squad = {'wins': 0}

    for obj in stat_data:
        stat = obj['name']
        value = obj['value']

        args = stat.split('_')
        stat = args[1]
        platform = args[2]
        mode = args[-1]

        if platform != 'pc': continue
        if stat == 'placetop1': stat = 'wins'

        if mode == 'p2': solo[stat] = value
        elif mode == 'p10': duo[stat] = value
        else: squad[stat] = value

    
    solo['kd'] = '%.2f' % (solo['kills'] / (solo['matchesplayed'] - solo['wins']))
    duo['kd'] = '%.2f' % (duo['kills'] / (duo['matchesplayed'] - duo['wins']))
    squad['kd'] = '%.2f' % (squad['kills'] / (squad['matchesplayed'] - squad['wins']))
    return solo, duo, squad

async def get_tracker(user):
    global tracker_key
    page = await get('https://api.fortnitetracker.com/v1/profile/pc/' + user, headers={'TRN-Api-Key': tracker_key})
    return await page.json()



async def on_fn(zulia, args, msg):
    user_id = await get_user(args[1])
    stats = await get_stats(user_id)
    solo, duo, squad = convert_stats(stats)
    tracker = await get_tracker(args[1])
    t_stats = tracker['stats']
    #u'p2', u'p9', u'p10'

    table = [
        ['Stat', 'Solo', 'Duo', 'Squad'],
        ['TRN ELO', t_stats['p2']['trnRating']['value'], t_stats['p10']['trnRating']['value'], t_stats['p9']['trnRating']['value']],
        ['TRN Percentile', t_stats['p2']['trnRating']['percentile'], t_stats['p10']['trnRating']['percentile'], t_stats['p9']['trnRating']['percentile']],
        ['Wins', solo['wins'], duo['wins'], squad['wins']],
        ['KD', solo['kd'], duo['kd'], squad['kd']],
        ['Kills', solo['kills'], duo['kills'], squad['kills']],
        ['Matches', solo['matchesplayed'], duo['matchesplayed'], squad['matchesplayed']]
    ]

    for n, match in enumerate(tracker['recentMatches'][:5]):
        table.append(
        ['Match %s' % (n+1), '%s kills' % match['kills'], '%s wins' % match['top1']])

    await zulia.send_message(msg.channel, '```User: {}\n{}```'.format(args[1].title(), AsciiTable(table).table))


def initialize(bot):
    pass

async def initialize_async(bot):
    global zulia, token, expires_at, refresh_token, tracker_key
    zulia = bot

    tracker_key = zulia.config['Fortnite']['Key']
    print('Logging in to fortnite!')
    expires_at, token, refresh_token = await login(zulia)

async def on_message(zulia, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(zulia, msg, msg_obj)
        return True
    return False

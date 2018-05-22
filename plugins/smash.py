from aiohttp import get
from sys import modules

def initialize(bot):
    pass

def get_helpstr():
    return """
              smash <player> | Pulls up that player's info (ALPHA!)!
           """

async def on_smash(android18, args, msg):
    user = msg.author
    CURRENT_TOURNAMENTS = [
        'https://smash.gg/tournament/dreamhack-atlanta-2017/events/super-smash-bros-for-wii-u/overview',
        'https://smash.gg/tournament/master-hand-12-ft-blazingskie-1-stl/events/wii-u-singles/overview'
        'https://smash.gg/tournament/midwest-mayhem-9-old-vs-new/events/wii-u-singles/overview',
        'https://smash.gg/tournament/allmid-smash-4-regional/events',
        'https://smash.gg/tournament/bourbon-state-gaming-old-fashioned/events',
    ]

    player_name = args[1]
    real_player_name = None
    player_id = None
    wins, losses = {}, {}

    for tournament in CURRENT_TOURNAMENTS:
        players = {}
        slug = tournament.split('/')[4]
        event_id = None
        phase_ids = []

        res = await get('https://api.smash.gg/tournament/{slug}?expand[]=event&expand[]=phase'.format(slug=slug))
        events = await res.json()

        for event in events['entities']['event']:
            if ('wii' in event['name'].lower() and 'single' in event['name'].lower()) or ('wii' in event['name'].lower() and 'double' not in event['name'].lower()) or ('smash 4' in event['name'].lower() and 'double' not in event['name'].lower()):
                event_id = event['id']
                break

        for phase in events['entities']['phase']:
            if phase['eventId'] == event_id:
                phase_ids.append(phase['id'])

        print ('Event: %s | Phase: %s | Slug: %s' % (event_id, phase_ids, slug))
        res = await get('https://api.smash.gg/tournament/{slug}?expand[]=event&expand[]=entrants&expand[]=phase&expand[]=groups'.format(slug=slug))
        data = await res.json()

        for player in data['entities']['entrants']:
            if not player or player['eventId'] != event_id: continue

            players[player['id']] = player['name']
            if player_name.lower() in player['name'].lower() or player_name.lower() == player['name'].lower():
                print ('Found player: %s (%s)' % (player['name'], player['id']))
                player_id = player['id']
                real_player_name = player['name']

        groups, sets = {}, []
        res = await get('https://api.smash.gg/tournament/{slug}?expand[]=groups'.format(slug=slug))
        group_json = await res.json()
        for group in group_json['entities']['groups']:
            if group['phaseId'] in phase_ids:
                groups[group["displayIdentifier"]] = {'id': group['id']}

        for tag, phase in groups.items():
            res = await get('https://api.smash.gg/phase_group/{phase}?expand[]=sets'.format(phase=phase['id']))
            data = await res.json()
            sets.extend(data['entities']['sets'])

        for match in sets:
            if match['entrant2PrereqType'] == 'bye' or not match['entrant1Id'] or not match['entrant2Id']:
                continue

            if (match['entrant1Id'] != player_id and match['entrant2Id'] != player_id) or not match['winnerId']:
                continue

            opponent = players[match['entrant1Id']] if match['entrant1Id'] != player_id else players[match['entrant2Id']]
            player_one = players[match['entrant1Id']]
            player_two = players[match['entrant2Id']]
            print ('Found a match! (%s) vs. (%s) (%s)' % (player_one, player_two, match['id']))

            if match['winnerId'] == player_id:
                if not wins.get(opponent):
                    wins[opponent] = 1
                else:
                    wins[opponent] = wins[opponent] + 1
            else:
                if not losses.get(opponent):
                    losses[opponent] = 1
                else:
                    losses[opponent] = losses[opponent] + 1

    print ('Starting player analysis...')
    win_count = sum(wins.values())
    lose_count = sum(losses.values())

    rival = max(losses, key=losses.get)
    await android18.send_message(msg.channel, '```{} has a w/l of: {}/{}\nTheir rival is: {} having {} wins over them!```'.format(real_player_name, win_count, lose_count, rival, losses[rival]))

async def on_message(android18, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(android18, msg, msg_obj)
        return True
    return False

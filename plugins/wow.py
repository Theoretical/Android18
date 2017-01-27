from aiohttp import get
from lxml.html import fromstring
from sys import modules
from json import loads
from subprocess import check_output

def initialize(zulia):
    pass

def get_helpstr():
    return """
	       emissary    | Gets list of current emissaries in NA.
           wq <region> | Gets list of current world quests in region.
           """


async def on_emissary(zulia, args, msg):
    page = await get('http://www.wowhead.com/world-quests/na')
    content = await page.text()
    nodes = fromstring(content)

    out_msg = ''
    for n in nodes.xpath('//div[@class="world-quests-header"]//dt'):
        faction = n.xpath('.//a')[0].text
        length = n.getnext().text
        out_msg += '%25s\t|\tExpires in: %25s\n' % (faction, length)

    await zulia.send_message(msg.channel, '```{}```'.format(out_msg))


async def on_wq(zulia, msg, msg_obj):
    zone = ' '.join(msg[1:]).lower()

    output = check_output(["casperjs", "wowhead.js"])
    data = loads(output)

    zone = int([k for k,v in data['zones'].items() if zone == v][0])
    world_quests =  [wq for wq in data['wq'] if zone in wq['zones']]

    out_msg = ''
    for wq in world_quests:
        id = str(wq['id'])
        quest_name = data['questws'][id]['name_enus']
        faction = data['factions'][str(wq['factions'][0])]['name_enus']
        items = []

        for i in wq['items']:
            item_name = data['items'][str(i['id'])]
            items.append('%50sx%s' % (item_name, i['qty']))

        # TODO: time...?
        out_msg += '%30s|%30s|%30s' % (quest_name, faction, '|'.join(items))
    await zulia.send_message(msg.channel, '```{}```'.format(out_msg))





async def on_message(zulia, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(zulia, msg, msg_obj)
        return True
    return False

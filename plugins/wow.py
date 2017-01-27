from aiohttp import get
from lxml.html import fromstring
from sys import modules

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
    

async def on_message(zulia, msg, msg_obj):
    callback_func = 'on_' + msg[0]

    if hasattr(modules[__name__], callback_func):
        await getattr(modules[__name__], callback_func)(zulia, msg, msg_obj)
        return True
    return False

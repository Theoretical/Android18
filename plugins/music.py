from aiohttp import get
from asyncio import Lock, gather
from datetime import timedelta
from discord.utils import find, get as discord_get
from lxml.html import fromstring
from os import listdir, unlink, environ, rename
from os.path import isfile
from random import shuffle
from spotipy import Spotify
from spotipy.util import prompt_for_user_token
from time import time
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import functools
import youtube_dl
from requests import Session
from zipfile import ZipFile
from shutil import rmtree

# We still will allow only skipping by 2 people unless the user has `admin`
class Skip:
    def __init__(self):
        self.users = set()

    def add(self, user):
        self.users.add(user)

    @property
    def allowed(self):
        return len(self.users) > 1

    def reset(self):
        self.users.clear()

# Our default format options for all youtube music.
ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': "mp3",
    'outtmpl': '/tmp/%(id)s',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': False,
    'no_warnings': True,
    'prefer_insecure': True,
    'source_address': '0.0.0.0'
}

def login_to_osu(android18):
    # for now hardcode this.
    username = android18.config['osu']['username']
    password = android18.config['osu']['password']
    headers = {
        "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding" : "gzip, deflate, sdch",
        "Accept-Language" : "en-US,en;q=0.8,pt;q=0.6",
        "Cache-Control" : "max-age=0",
        "Connection" : "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.81 Safari/537.36"
    }
    # request a defualt page.
    session = Session()
    session.headers.update(headers)
    session.allow_redirects = True
    initial_res = session.get('https://osu.ppy.sh/beatmapsets/444079/')
    nodes = fromstring(initial_res.content)
    token = nodes.xpath('//meta[@name="csrf-token"]')[0].get('content')
    login_res = session.post('https://osu.ppy.sh/session', {
        'username': username,
        'password': password,
        '_token': token
    })
    return session
    
def download_beatmap(obj):
    session = obj['session']
    url = obj['url']

    if '#' in url:
        url = url.split('#')[0]
    
    download_url = url + '/download'
    path = '/tmp/'
    
    beatmap_id = url.split('/')[-1]
    filename = beatmap_id + '.zip'
    req = session.get(download_url, stream=True)

    with open(path + filename, 'wb') as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                f.flush()
    
    req.close()

    with ZipFile(path + filename, "r") as z:
        z.extractall('/tmp/' + beatmap_id + 'z')

    zip_path = '/tmp/%sz' % beatmap_id
    # we don't know the actual file name lol.
    for name in listdir(zip_path):
        if '.mp3' in name or '.ogg' in name:
            rename('%s/%s' % (zip_path,name), '/tmp/' + beatmap_id)
    
    rmtree('/tmp/' + beatmap_id + 'z')
    return beatmap_id


def initialize(android18):
    # Each server android18 supports should be allowed to have their own music bot.
    android18.music = dict()
    android18.osu = login_to_osu(android18)
    print ('Loaded android18\'s music plugin.')


def get_helpstr():
    return """
              play <link> <side|shuffle>| Plays the specified media link (or playlist).
              spotify <link>            | Plays the specified spotify link.
              pause                     | Pauses the current song.
              resume                    | Resumes the current song.
              queue                     | Posts the current song queue.
              np                        | Posts current song details.
              shuffle                   | Shuffles the current playlist.
              volume <size>             | Adjusts the current playback volume.
              skip                      | Starts a skip vote (admins auto skip.)
              summon <user>             | Summons android18 to that user or the user.
           """


async def reinitialize(android18):
    for music in android18.music.values():
        await music.quit()

    android18.music = dict()

async def get_beatmap_info(url):
    from json import loads
    page = await get(url)
    content = await page.text()

    nodes = fromstring(content)
    json_data = nodes.xpath('//script[@id="json-beatmapset"]')[0].text

    data = loads(json_data)
    obj = {
        'title': data['title'],
        'artist': data['artist'],
        'duration': max([_['total_length'] for _ in data['beatmaps']]),
        'webpage_url': page.url
    }

    return obj


# These are our Spotify / Youtube helper functions.
# I will not document how they work.
async def search_youtube(title):
    print('https://www.googleapis.com/youtube/v3/search?part=id,snippet&q=%s&key=%s' % (quote(title), environ['YT_KEY']))
    page = await get('https://www.googleapis.com/youtube/v3/search?part=id,snippet&q=%s&key=%s' % (quote(title), environ['YT_KEY']))
    data = await page.json()

    # We're going to try to isolate these to better videos..
    videos = [x['id']['videoId'] for x in data['items'] if 'videoId' in x['id']]

    page = await get('https://www.googleapis.com/youtube/v3/videos?part=id,snippet,contentDetails,status&id=%s&key=%s' % (','.join(videos), environ['YT_KEY']))
    print('https://www.googleapis.com/youtube/v3/videos?part=id,snippet,contentDetails,status&id=%s&key=%s' % (','.join(videos), environ['YT_KEY']))
    data = await page.json()
    video_id = None

    for item in data['items']:
        details = item['contentDetails']
        blocked = details.get('regionRestriction', {}).get('blocked', [])
        allowed = details.get('regionRestriction', {}).get('allowed', [])
        if 'US' in blocked or (len(allowed) and 'US' not in allowed) or details['definition'] != 'hd':
            continue
        video_id = item['id']

    if video_id is None:
        # default to vevo..
        for item in data['items']:
            if 'vevo' in item['snippet']['channelTitle'].lower():
                video_id = item['id']
                break

    if video_id is None and len(videos):
        # oh well...
        video_id = videos[0]

    if video_id:
        return 'https://youtube.com/watch?v=%s' % video_id

    return None

async def get_spotify_playlist(url):
    # Url can be a spotify url or uri.
    user = ''
    playlist_id = ''
    songs = []

    token = prompt_for_user_token('mdeception', 'user-library-read')

    spotify = Spotify(auth=token)
    if not 'http' in url:
        user = url.split('user:')[1].split(':')[0]
        playlist_id = url.split(':')[-1]
    else:
        user = url.split('user/')[1].split('/')[0]
        playlist_id = url.split('/')[-1]

    playlist = spotify.user_playlist(user, playlist_id, fields='tracks, next, name')

    tracks = playlist['tracks']
    for t in tracks['items']:
        track = t['track']
        songs.append('%s %s' % (track['name'], ' & '.join(x['name'] for x in track['artists'])))

    while tracks['next']:
        tracks = spotify.next(tracks)
        for t in tracks['items']:
            track = t['track']
            songs.append('%s %s' % (track['name'], ' & '.join(x['name'] for x in track['artists'])))

    return (playlist['name'], user, songs)


class MusicPlayer:
    def __init__(self, android18, channel):
        self.android18 = android18
        self.channel = channel
        self.playlist = list()
        self.music_lock = Lock()
        self.skip = Skip()
        self.ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
        self.current_song = None
        self.playing = False
        self.paused = False
        self.volume = .05
        self.music_player = None

        # Julia if you're reading this know that I hate you.
        self.side_playlist = list()
        self.use_side_playlist = False

    @property
    # Gets our current voice connection.
    def voice(self):
        return self.android18.voice_client_in(self.channel.server)

    @property
    # Gets our current song progress.
    def progress(self):
        return round(self.music_player.loops * 0.02) if self.music_player else 0


    # Download osu file.
    def download_beatmap(self, url):
        thread_pool = ThreadPoolExecutor(max_workers=2)
        return self.android18.loop.run_in_executor(thread_pool, download_beatmap, {'url': url, 'session': self.android18.osu})

    # Youtube helper functions.
    def search_youtube(self, title):
        thread_pool = ThreadPoolExecutor(max_workers=4)
        return self.android18.loop.run_in_executor(thread_pool, search_youtube, title)

    def extract_info(self, *args, **kwargs):
        thread_pool = ThreadPoolExecutor(max_workers=2)
        return self.android18.loop.run_in_executor(thread_pool, functools.partial(self.ytdl.extract_info, *args, **kwargs))

    def process_info(self, item):
        thread_pool = ThreadPoolExecutor(max_workers=2)
        return self.android18.loop.run_in_executor(thread_pool, functools.partial(self.ytdl.process_ie_result, item, download=True))

    # Plays the next song in our playlist (makes it so sync -> async is possible.)
    def play(self):
        self.android18.loop.create_task(self.play_song())

    # Our callback for when a song finishes.
    def on_finished(self):
        try:
            # Delete the song file (storage space!)
            unlink('/tmp/' + self.current_song['id'])
        except:
            pass

        # Reset our current song/skip counter.
        self.current_song = None
        self.skip = Skip()

        if not self.playing:
            # Play the new songs.
            self.play()

    async def play_song(self):
        # if we're currently paused, resume our player.
        if self.paused:
            if self.music_player:
                self.paused = False
                self.music_player.resume()

        # if for some reason we're not connected, join our default channel (why networking why?!)
        if not self.voice:
            # default to AFK channel..
            channel = discord_get(self.channel.server.channels, name='Praying With android18')
            await self.android18.join_voice_channel(channel)

        # We do NOT want to have multiple songs attempting to play.
        with await self.music_lock:
            try:
                # I hate you Julia.
                if not self.use_side_playlist and not len(self.side_playlist):
                    self.current_song = self.playlist.pop(0)
                else:
                    self.current_song = self.side_playlist.pop(0)
                    self.use_side_playlist = False
            except:
                return

            # Create our music player and send our info to the channel.
            self.music_player = self.voice.create_ffmpeg_player('/tmp/' + self.current_song['id'], use_avconv=True)
            self.music_player.loops = 0 #???
            self.music_player.after = lambda: self.android18.loop.call_soon_threadsafe(self.on_finished)
            await self.send_np(self.channel)

            self.music_player.start()
            self.music_player.volume = self.volume

    async def quit(self):
        self.playlist = []
        self.playing = False
        self.side_playlist = []
        if self.music_player:
            self.music_player.stop()
        if self.voice:
            await self.voice.disconnect()

    async def process_commands(self, msg, msg_obj):
        callback_func = 'on_' + msg[0]

        if hasattr(self, callback_func):
            await getattr(self, callback_func)(msg, msg_obj)
            return True
        return False


    async def send_np(self, channel):
        if not self.current_song: return

        song = self.current_song
        position = str(timedelta(seconds=self.progress))
        length = str(timedelta(seconds=song.get('duration', 0)))
        playlist = 'side' if self.use_side_playlist else 'main'
        await self.android18.send_message(channel, '```Now Playing: {0} requested by {1} on {5} | Timestamp: {2} | Length: {3}\n{4}```'.format(song['title'], song['requestor'], position, length, song['webpage_url'], playlist))

    async def join_default_channel(self, member):
        if self.voice:
            return

        default_name = 'Praying with android18'
        channel = find(lambda m: m.id == member.id and m.server.id == member.server.id and m.voice_channel is not None, member.server.members)

        if channel is not None:
            await self.android18.join_voice_channel(channel.voice_channel)
            return

        channel = discord_get(member.server.channels, name=default_name)
        await self.android18.join_voice_channel(channel)


    async def on_spotify(self, msg, msg_obj):
        # Okay, so breaking down this function MIGHT get a bit confusing.

        # Step 1.) Set our current time and fetch the spotify playlist.
        t = time()
        playlist, user, songs = await get_spotify_playlist(msg[1])

        # Step 2.) Search youtube for every song .
        yt_search = gather(*(search_youtube(song) for song in songs))
        yt_songs = await yt_search
        yt_songs = [song for song in yt_songs if song is not None]

        # Step 3.) Assume my searching isn't ass.
        ended = time()
        total_songs = len(songs)
        await self.android18.send_message(msg_obj.channel, '`Found: %s songs in playlist: %s by %s in %s seconds.!`' % (total_songs, playlist, user, ended - t))
        await self.join_default_channel(msg_obj.author)

        # Find a bot channel if we have one...
        if msg_obj.channel.name != 'bot':
            channel = find(msg_obj.server.channels, name='bot')
            self.channel = channel or msg_obj.channel

        # Step 4.) Download all songs for the playlist.
        playlist_task = gather(*(self.extract_info(url=item, download=True) for item in yt_songs))
        playlist = await playlist_task
        playlist = [x for x in playlist if x]

        # Step 5.) Set the owner of the song for NP.
        for s in playlist:
            s['requestor'] = msg_obj.author.name

        self.playlist.extend(playlist)
        if not self.current_song:
            self.play()

        await self.on_queue(msg, msg_obj)

    async def on_np(self, msg, msg_obj):
        await self.send_np(msg_obj.channel)

    async def on_shuffle(self, msg, msg_obj):
        for i in range(0, 5):
            shuffle(self.playlist)

        await self.on_queue(msg, msg_obj)

    async def on_queue(self, msg, msg_obj):
        if self.current_song is None: return

        queue_str = ''

        playlist = self.playlist if not self.use_side_playlist else self.side_playlist
        for song in playlist[:15]:
            queue_str += '%s: (%ss). requested by: %s\n' % (song['title'], str(timedelta(seconds=song['duration'])), song['requestor'])

        position = str(timedelta(seconds=self.progress))
        length = str(timedelta(seconds=self.current_song.get('duration', 0)))
        total_len = sum([x.get('duration', 0) for x in self.playlist])
        current_playlist = 'Side' if self.use_side_playlist else 'Main'
        await self.android18.send_message(msg_obj.channel, '```Playlist: {} | Queue length: {} | Queue Size: {} | Current Song Progress: {}/{}\n{}```'.format(current_playlist, str(timedelta(seconds=total_len)), len(playlist), position, length, queue_str))

    async def on_play(self, msg, msg_obj):
        await self.join_default_channel(msg_obj.author)

        # Find a bot channel if we have one...
        if msg_obj.channel.name != 'bot':
            channel = discord_get(msg_obj.server.channels, name='bot')
            self.channel = channel or msg_obj.channel

        if 'playlist' not in msg[1]:
            song = await self.extract_info(url=msg[1], download=True)
            song['requestor'] = msg_obj.author.name

            if msg[-1] == 'side':
                self.side_playlist.append(song)
                self.use_side_playlist = True
            else:
                self.playlist.append(song)

        else:
            t = time()
            items = await self.extract_info(url=msg[1], process=False, download=False)
            playlist_task = gather(*(self.process_info(item) for item in items['entries']))
            playlist = await playlist_task
            playlist = [x for x in playlist if x]

            end = time()
            await self.android18.send_message(msg_obj.channel, '```Loaded: %s songs in %s seconds.```' % (len(playlist), end - t))
            if msg[-1] == 'shuffle':
                for i in range(0, 5):
                    shuffle(playlist)
            for song in playlist:
                song['requestor'] = msg_obj.author.name

            self.playlist.extend(playlist)

    
        if not self.current_song:
            self.play()

        if len(self.playlist) > 1:
            await self.on_queue(msg, msg_obj)

    async def on_pause(self, msg, msg_obj):
        if not self.music_player:
            return

        self.paused = True
        self.music_player.pause()

    async def on_resume(self, msg, msg_obj):
        if self.paused:
            self.paused = False
            self.music_player.resume()

    async def on_volume(self, msg, msg_obj):

        if len(msg) == 1:
            await self.android18.send_message(msg_obj.channel, '`Current Volume: %s`' % self.volume)
        else:
            if not str.isdigit(msg[1]): return
            self.volume = int(msg[1]) / 100

            if self.music_player:
                self.music_player.volume = self.volume

            await self.android18.send_message(msg_obj.channel, '`{} set the volume to {}`'.format(msg_obj.author, self.volume))

    async def on_skip(self, msg, msg_obj):
        self.skip.add(msg_obj.author)

        if (self.music_player and msg_obj.author.server_permissions.administrator) or self.skip.allowed:
            self.music_player.stop()
            self.music_player = None
            return True

        await self.android18.send_message(msg_obj.channel, '`{} Started a skip request! Need 1 more person to request a skip to continue!`'.format(msg_obj.author))

    async def on_summon(self, msg, msg_obj):
        if self.voice:
            await self.voice.disconnect()
        if len(msg) > 1:
            member = find(lambda m: m.mention == msg[1], msg_obj.server.members)
        else:
            member  = msg_obj.author

        channel = find(lambda m: m.id == member.id and m.server.id == member.server.id and m.voice_channel is not None, member.server.members)
        await self.android18.join_voice_channel(channel.voice_channel)
        await self.android18.send_message(msg_obj.channel, '`Joining channel with {}`'.format(member))

    async def on_osu(self, msg, msg_obj):
        await self.join_default_channel(msg_obj.author)

        url = msg[1]
        current_song = await get_beatmap_info(url)
        current_song['requestor'] = msg_obj.author.name

        beatmap_id = await self.download_beatmap(current_song['webpage_url'])
        current_song['id'] = beatmap_id
        
        self.playlist.append(current_song)

        if not self.current_song:
            self.play()

        if len(self.playlist) > 1:
            await self.on_queue(msg, msg_obj)

        await self.send_np(msg_obj.channel)



async def on_message(android18, msg, msg_obj):
    if msg_obj.server not in android18.music:
        android18.music[msg_obj.server] = MusicPlayer(android18, msg_obj.channel)

    return await android18.music[msg_obj.server].process_commands(msg, msg_obj)

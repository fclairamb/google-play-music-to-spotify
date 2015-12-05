#!/usr/bin/python

import sys
import logging
import requests
import requests_cache
import argparse
import HTMLParser

htmlParser = HTMLParser.HTMLParser()

from BeautifulSoup import BeautifulSoup

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)8s | %(filename).4s:%(lineno)4d | %(message)s",
    datefmt='%m-%d %H:%M:%S',
)


# regex_remove_par = re.compile(".*?\((.*?)\)")


def get_spotify_id_basic(title):
    title = title.strip(" ")
    logging.debug('get_spotify_id_basic( "%s" )', title)
    url = 'https://api.spotify.com/v1/search'
    response = requests.get(url, params={'type': 'track', 'q': title, 'limit': 1})

    if response.status_code != 200:
        print 'rate limit'
        exit(1)

    items = response.json()['tracks']['items']

    id = None
    if len(items):
        id = items[0]['id']
    return id


def get_spotify_id(title):
    original = title
    id = get_spotify_id_basic(title)

    if not id:
        start = title.find('(')
        end = title.find(')')
        if start != -1 and end != -1:
            title = title[start + 1:end]
            id = get_spotify_id_basic(title)

    if not id:
        title = title.replace('feat.', '')
        id = get_spotify_id_basic(title)

    if not id:
        title = title.replace('-', ' ')
        id = get_spotify_id_basic(title)

    if not id:
        title = title.replace('*ck', 'uck')

    if not id:
        logging.warn("Could not find an ID for: %s / %s", title, original)

    logging.info('get_spotify_id( "%s" ) : %s', title, id)


def parse_track(tr):
    logging.debug("parse_track( %s )", tr)
    track = '%s %s' % (
        tr.find('div', {'class': 'track-title'}).contents[0],
        tr.find('div', {'class': 'artist'}).contents[0]
    )
    return get_spotify_id(htmlParser.unescape(track))


def parse_playlist(content):
    # logging.debug("parse_playlist: %s", content)
    soup = BeautifulSoup(content)
    spotify_ids = map(parse_track, soup.findAll('tr', {'class': 'tracklist-entry'}))
    return [id for id in spotify_ids if id != '']


if __name__ == '__main__':
    # We disable logging for the HTTP requests
    # logging.getLogger("requests").setLevel(logging.CRITICAL)

    # We parse args
    parser = argparse.ArgumentParser(description='Google Play Music to Spotify importer')
    parser.add_argument('--gpm-playlist', '-g', help='Google Play Music URL',
                        default="https://play.google.com/music/playlist/AMaBXykhNg66Qky9PXUN9KNWNqlkMHaNi8q7DH37XKYenSG0mDL2oHq9nMxXNSVx6EliPv6p6V0gOUrUPiHFvFJG6O4KRNwQMQ==")
    parser.add_argument('--no-http-caching', '-c', help='Disable HTTP caching', action='store_true', default=False)
    args = parser.parse_args()

    if not args.no_http_caching:
        logging.info("Enabling HTTP caching...")
        requests_cache.install_cache('http_cache')

    # The GPM playlist URL must be changed a little bit
    gpm_url = args.gpm_playlist.replace('https://play.google.com/music/playlist/',
                                        'https://play.google.com/music/preview/pl/')

    # We fetch the playlist
    gpm_content = requests.get(gpm_url, verify=False).text

    parse_playlist(gpm_content)

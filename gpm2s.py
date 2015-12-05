#!/usr/bin/python

import sys
import logging
import requests
import requests_cache
import argparse
import HTMLParser
import json
from BeautifulSoup import BeautifulSoup

htmlParser = HTMLParser.HTMLParser()

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)8s | %(filename).4s:%(lineno)4d | %(message)s",
    datefmt='%m-%d %H:%M:%S',
)


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
    return id


def parse_track(tr):
    logging.debug("parse_track( %s )", tr)
    track = '%s %s' % (
        tr.find('div', {'class': 'track-title'}).contents[0],
        tr.find('div', {'class': 'artist'}).contents[0]
    )
    return get_spotify_id(htmlParser.unescape(track))


def gpm_parse_and_convert(content_soup):
    spotify_ids = map(parse_track, content_soup.findAll('tr', {'class': 'tracklist-entry'}))
    return [id for id in spotify_ids if id]


def gpm_parse_title(content_soup):
    return content_soup.find('div', {'class': 'title fade-out'}).a.text


def spotify_create_playlist(title, track_ids_list, args):
    data = {
        "name": title,
        "public": False
    }
    httpResponse = requests.post(
        'https://api.spotify.com/v1/users/{user}/playlists'.format(user=args.spotify_user),
        json.dumps(data),
        headers={
            'Authorization': 'Bearer ' + args.spotify_oauth
        }
    )

    if not httpResponse.ok:
        raise Exception('Could not create playlist !', httpResponse)

    playlist = json.loads(httpResponse.text)

    chunk_size = 50
    track_ids_sublists = [track_ids_list[x:(x + chunk_size)] for x in xrange(0, len(track_ids_list), chunk_size)]

    for list in track_ids_sublists:
        track_uris = ''
        for track_id in list:
            if track_uris:
                track_uris += ','
            track_uris += 'spotify:track:' + track_id
        httpResponse = requests.post(
            playlist['tracks']['href'] + '?uris=' + track_uris,
            '',
            headers={
                'Authorization': 'Bearer ' + args.spotify_oauth
            }
        )
        if not httpResponse.ok:
            raise Exception('Problem filling playlist', httpResponse)


if __name__ == '__main__':
    # We disable logging for the HTTP requests
    # logging.getLogger("requests").setLevel(logging.CRITICAL)

    # We parse args
    parser = argparse.ArgumentParser(description='Google Play Music to Spotify importer')
    parser.add_argument('--gpm-playlist', '-g', help='Google Play Music URL', required=True)
    parser.add_argument('--no-http-caching', '-c', help='Disable HTTP caching', action='store_true', default=False)
    parser.add_argument('--spotify_user', '-su', help='Spotify User', required=True)
    parser.add_argument('--spotify-oauth', '-so', help='Spotify OAuth token')
    args = parser.parse_args()

    if not args.no_http_caching:
        requests_cache.install_cache('http_cache')
    else:
        logging.warn("HTTP caching disabled")

    if not args.spotify_oauth:
        with open('.spotify_oauth', 'r') as s_oauth_file:
            args.spotify_oauth = s_oauth_file.read()

    if not args.spotify_oauth:
        logging.critical("You have to specify on oauth token by CLI or file")
        exit(1)

    # The GPM playlist URL must be changed a little bit
    gpm_url = args.gpm_playlist.replace('https://play.google.com/music/playlist/',
                                        'https://play.google.com/music/preview/pl/')

    # We fetch the playlist
    gpm_content = requests.get(gpm_url, verify=False).text

    gpm_soup = BeautifulSoup(gpm_content)
    title = gpm_parse_title(gpm_soup)
    track_ids_list = gpm_parse_and_convert(gpm_soup)
    spotify_create_playlist(title, track_ids_list, args)

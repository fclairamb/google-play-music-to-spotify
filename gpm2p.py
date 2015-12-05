import csv
import requests
from BeautifulSoup import BeautifulSoup


def get_spotify_id(track):
    url = 'https://api.spotify.com/v1/search'
    response = requests.get(url, params={'type': 'track', 'q': track, 'limit': 1})

    if response.status_code != 200:
        print 'rate limit'
        exit(1)

    items = response.json()['tracks']['items']
    if len(items) > 0:
        return 'spotify:track:' + items[0]['id']
    return ''


def parse_track(tr):
    track = '%s %s' % (
        tr.find('div', {'class': 'track-title'}).contents[0],
        tr.find('div', {'class': 'artist'}).contents[0]
    )
    return get_spotify_id(track.replace('&#39;', ''))


def parse_playlist(content):
    soup = BeautifulSoup(content)
    spotify_ids = map(parse_track, soup.findAll('tr', {'class': 'tracklist-entry'}))
    return [id for id in spotify_ids if id != '']

#!/usr/bin/env python3

from json.decoder import JSONDecodeError
from math import ceil
import os
from pprint import pformat, pprint

from bs4 import BeautifulSoup
import click
import requests

URL_PERFORMANCE_RANKING_ALL_LOCATIONS_FMT = 'https://osu.ppy.sh/p/pp?page={page_num}'
URL_PERFORMANCE_RANKING_USA = 'https://osu.ppy.sh/p/pp?s=3&o=1&c=US'
URL_API = 'https://osu.ppy.sh/api/'
URL_USER_PROFILE = 'https://osu.ppy.sh/u/'  # e.g., https://osu.ppy.sh/u/7695654
URL_USER_PROFILE_DATA = 'https://osu.ppy.sh/pages/include/profile-general.php?u=2&m=0'

ENDPOINT_GET_BEATMAPS = URL_API + 'get_beatmaps'
ENDPOINT_GET_USER = URL_API + 'get_user'
ENDPOINT_GET_SCORES = URL_API + 'get_scores'
ENDPOINT_GET_USER_BEST = URL_API + 'get_user_best'
ENDPOINT_GET_USER_RECENT = URL_API + 'get_user_recent'
ENDPOINT_GET_MATCH = URL_API + 'get_match'
ENDPOINT_GET_REPLAY = URL_API + 'get_replay'
API_KEY = os.environ.get('OSU_API_KEY')
BEATMAP_ID = 899732

def print_resp(resp):
    print('-' * 80)
    print(resp.url)
    try:
        json = resp.json()
    except JSONDecodeError as exception:
        json = '(JSONDecodeError)'
    pprint(json)
    print('status code = [%s]' % resp.status_code)


def convert_data(name2text):
    converted = {}

    # e.g., 'Accuracy': '98.78%' => 98.78 (float)
    converted['Accuracy'] = float(name2text['Accuracy'].replace('%', ''))

    # e.g., 'Performance': '\n13,009pp\n' => 13009 (int)
    perf = name2text['Performance'].replace('pp', '').replace(',', '').strip()
    converted['Performance'] = int(perf)

    # e.g., 'Play Count': '12,190 (lv.100)' => 12190 (int)
    play_count = name2text['Play Count']
    play_count = play_count.partition(' ')[0].replace(',', '')
    converted['Play Count'] = int(play_count)

    # e.g., 'Play Count': '12,190 (lv.100)' => 100 (int)
    level = name2text['Play Count'].partition(' ')[2].replace('(lv.', '')
    level = level.replace(')', '')
    converted['Level'] = int(level)

    # e.g., 'Player Name':
    converted['Player Name'] = name2text['Player Name'].strip()

    # e.g., 'Rank': '#1' => 1 (int)
    converted['Rank'] = int(name2text['Rank'].replace('#', ''))

    return converted

def get_page_range_for_ranks(rank_first, rank_last):
    NUM_RANKS_PER_PAGE = 50
    first_page = ceil(rank_first / NUM_RANKS_PER_PAGE)
    last_page = ceil(rank_last / NUM_RANKS_PER_PAGE)
    return first_page, last_page

def scrape_ranked_players(rank_first=1, rank_last=2):
    """
    Return the information for each of the players in the ranks
    {{rank_first}}..{{rank_last}}
    Returned data will look like:
        (key=rank, value = dict of info for player at that rank)
        {
            1: {
                'Rank': 1,
                'Player Name': 'Vaxei',
                'Accuracy': 97.94
                'Play Count': 85461,
                'Level': 100,
                'Performance': 12506,
                'position_6': 31,
                'position_7': 493,
                'position_8': 509,
                'player_id': '124493',
               }
        }
    """

    # 50 players per page
    # page 1: 1..50
    # page 2: 51..100
    # page n: ((n-1) * 50) + 1
    # To find page for rank:
    #   page = ceil(rank / 50) (integer division; rounded up if any decimal portion)

    # Grab the data from the osu.ppy.sh/p/pp
    # e.g.,
    #
    # Rank Player Name Accuracy  Play Count       Performance   SS  SS   A
    # ---- ----------- --------  --------------   -----------   --  ---  ---
    #  #1  Vaxei        97.94%   85,461 (lv.100)  12,506pp      31  493  509


    COLUMN_NAMES_TRANSLATION = {
        'position_6': 'no_miss_93',
        'position_7': 'no_miss_7',
        'position_8': 'no_miss_8',
    }

    first_page, last_page = get_page_range_for_ranks(rank_first, rank_last)
    rank2info = {}
    for page in range(first_page, last_page + 1):
        resp = requests.get(url=URL_PERFORMANCE_RANKING_ALL_LOCATIONS_FMT.format(page_num=page))
        assert resp.status_code == 200
        soup = BeautifulSoup(resp.content, features='html.parser')
        table = soup.find('table', class_='beatmapListing')
        # Note that some headers are only images, so there is no header.string for those.
        col_headers = [(head.string if head.string else 'position_%s' % (index + 1))
                       for index, head in enumerate(table.findAll('th'))]
        for row in table.findAll('tr')[1:]:
            cols = row.findAll('td')
            name2col = {tup[0]: tup[1] for tup in zip(col_headers, cols)}
            name2text = {name: col.text for name, col in name2col.items()}
            converted = convert_data(name2text)
            assert converted['Rank'] not in rank2info
            if converted['Rank'] > rank_last:
                break
            rank2info[converted['Rank']] = converted
            # e.g., href = '/u/124493'
            converted['player_id'] = name2col['Player Name'].a.attrs['href'].replace('/u/', '')
        if converted['Rank'] > rank_last:
            break
    return rank2info

def scrape_performance_ranking_page(url, page=1):
    resp = requests.get(url=URL_PERFORMANCE_RANKING_ALL_LOCATIONS)
    soup = BeautifulSoup(resp.content)
    table = soup.find('table', class_='beatmapListing')

def get_user_profile_data_page(user_id):
    # {user} can be username or user_id
    # e.g., url == https://osu.ppy.sh/u/7695654
    url = '{url}?u{user_id}&m=0'.format(url=URL_USER_PROFILE_DATA, user_id=user_id)
    resp = requests.get(url=url)
    return resp

def get_player_stats(player):
    # Here are the fields that scrape_ranked_players() gets, and the ones that this GET_USER endpoint also gets:
    #   scrape_ranked_players()   GET_USER
    #   --------------------   --------
    #   Accuracy               accuracy (with more precision)
    #   Level                  level (with more precision)
    #   Performance            --
    #   Play Count             playcount
    #   Player Name            username
    #   Rank                   pp_rank
    #   player_id              user_id
    # ENDPOINT_GET_USER example return:
    # [{'accuracy': '98.1125717163086',
    #   'count100': '384120',
    #   'count300': '3957346',
    #   'count50': '38012',
    #   'count_rank_a': '259',
    #   'count_rank_s': '437',
    #   'count_rank_ss': '8',
    #   'country': 'US',
    #   'events': [{'beatmap_id': '679943',
    #               'beatmapset_id': '139525',
    #               'date': '2017-03-12 07:00:35',
    #               'display_html': "<img src='/images/A_small.png'/> <b><a "
    #                               "href='/u/7695654'>PiorPie</a></b> achieved rank "
    #                               "#938 on <a href='/b/679943?m=0'>Lite Show Magic "
    #                               '(t+pazolite vs C-Show) - Crack Traxxxx '
    #                               "[Nathan's Ultra]</a> (osu!)",
    #               'epicfactor': '1'},
    #   ]
    #   'level': '100.035',
    #   'playcount': '23321',
    #   'pp_country_rank': '536',
    #   'pp_rank': '4004',
    #   'pp_raw': '5706.09',
    #   'ranked_score': '4977127878',
    #   'total_score': '30396667412',
    #   'user_id': '7695654',
    #   'username': 'PiorPie'}]
    resp = requests.get(url=ENDPOINT_GET_USER,
                        params=dict(k=API_KEY, u=player['player_id']))
    json = resp.json()
    if len(json) != 1:
        raise Exception('len(json) != 1, len=[%s]\n%s' % (len(json), pformat(json)))
    return json[0]
    
def get_all_players_stats(rank2player):
    player_id2dict = {}
    for player in rank2player.values():
        player_id = player['player_id']
        player_id2dict[player_id] = get_player_stats(player)
    return player_id2dict
'''
LEFT OFF: Fri 1/6/17 10:35pm
    table = soup.find('table')
    col_headers = [header.string for header in table.findAll('th')]
    col_idx = col_headers.index('Player Name')

    row_1 = table.findAll('tr')[1]
    cols = row_1.findAll('td')
    col_strings = [col.text for col in cols]
    assert col_strings[col_idx].strip() == 'Cookiezi'
'''

def get_all_endpoints(api_key, beatmap_id, username='PiorPie', beatmap_limit=5):
    resp = get_user_profile_data_page(user_id=username)
    print_resp(resp)

    resp = requests.get(url=ENDPOINT_GET_USER_RECENT,
                        params=dict(k=api_key, u=username))
    print_resp(resp)

    resp = requests.get(url=ENDPOINT_GET_USER,
                        params=dict(k=api_key, u=username))
    print_resp(resp)

    resp = requests.get(url=ENDPOINT_GET_USER_BEST,
                        params=dict(k=api_key, u=username))
    print_resp(resp)

    resp = requests.get(url=ENDPOINT_GET_BEATMAPS,
                        params=dict(k=api_key, b=beatmap_id, limit=beatmap_limit))
    print_resp(resp)

def add_pp_per_hour(player_id2dict):
    for player in player_id2dict.values():
        if player['play_time_hours']:
            pp_per_hour = float(player['pp_raw']) / player['play_time_hours']
        else:
            pp_per_hour = None
        player['pp_per_hour'] = pp_per_hour

def scrape_user_profile_pages(player_id2dict):
    player_num = 0
    for player in player_id2dict.values():
        player_num += 1
        resp = get_user_profile_data_page(user_id=player['user_id'])
        soup = BeautifulSoup(resp.content, features='html.parser')
        '''
        <div class="profileStatLine" title="Total time spent playing.">
            <b>Play Time</b>: 313 hours
        </div>
        '''
        play_time = soup.find('div', attrs=dict(title="Total time spent playing."))
        if play_time:
            play_time = play_time.text
            # e.g., play_time == 'Play Time: 313 hours'
            play_time = play_time.split(':')[1]  # play_time == ' 313 hours'
            play_time = play_time.strip()
            play_time = play_time.split(' ')[0]  # play_time == 313
            play_time = float(play_time)
        else:
            play_time = None
        player['play_time_hours'] = play_time

def print_players(player_id2dict):
    print('{username:12s} {pp_per_hour:5}  {rank_world:>4}  {rank_country:>7} {country} {url_profile}'.format(
        username='username',
        pp_per_hour='pp/hr',
        rank_world='world',
        rank_country='country',
        country='country',
        url_profile='profile',
    ))
    for player in player_id2dict.values():
        print('{username:12s} '
              '{pp_per_hour:5.1f} '
              '{rank_world:>4} '
              '{rank_country:>7} '
              '{country} '
              '{url_profile} '
              .format(
                  username=player['username'],
                  pp_per_hour=player['pp_per_hour'],
                  rank_world=player['pp_rank'],
                  rank_country=player['pp_country_rank'],
                  country=player['country'],
                  url_profile='{url}{user_id}'.format(url=URL_USER_PROFILE, user_id=player['user_id']),
        ))

if False:
    get_all_endpoints(username='PiorPie', api_key=API_KEY, beatmap_id=BEATMAP_ID)
    get_all_endpoints(username='Cookiezi', api_key=API_KEY, beatmap_id=BEATMAP_ID)

if True:
    rank2player = scrape_ranked_players(rank_first=1, rank_last=5)
    player_id2dict = get_all_players_stats(rank2player)
    scrape_user_profile_pages(player_id2dict)
    add_pp_per_hour(player_id2dict)
    # pprint(player_id2dict)
    print_players(player_id2dict)

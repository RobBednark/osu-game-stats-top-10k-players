import responses

from pull_stats import get_ranked_players


def test_valid_performance_ranking_page():
    resp = requests.get(url=URL_PERFORMANCE_RANKING_ALL_LOCATIONS)
    soup = BeautifulSoup(resp.content)
    table = soup.find('table', class_='beatmapListing')
    import pdb; pdb.set_trace()

# test from first, middle, and last page
def test_scrape_players_from_actual_page():
    # call the func
    # assert the number of players
    # assert the column/key names
    # assert the value types for each column
    pass

def test_mocked_get_ranked_players():
    rank_first = 1
    rank_last = 1
    # mock the request
    responses.add(method=responses.GET,
                  url=URL_PERFORMANCE_RANKING_ALL_LOCATIONS_FMT.format(page_num=1),
                  status=200,
                  content_type='application/json')
    # call the func
    players = get_ranked_players(first_rank=1, last_rank=1)
    # assert the data struct is identical

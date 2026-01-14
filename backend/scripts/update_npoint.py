import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from requests.models import Request
import requests_cache
from nba_api.stats.library.http import NBAStatsHTTP
from nba_api.stats.endpoints import leaguegamefinder, boxscoreadvancedv3
from nba_api.live.nba.endpoints import scoreboard
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import WNI, rate_limited_call

uri = os.environ['MONGO_URI']
client = MongoClient(uri, server_api=ServerApi('1'))

custom_headers = {
    'Host': 'stats.nba.com',
    'Connection': 'keep-alive',
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://www.nba.com',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://www.nba.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9'
}

def main():
    NBAStatsHTTP().headers = custom_headers
    try:
        playerCollection = client['player']['dataframe']
        advancedCollection = client['advanced']['dataframe']
        player_df = pd.DataFrame(list(playerCollection.find({}, {'_id': 0})))
        advanced_df = pd.DataFrame(list(advancedCollection.find({}, {'_id': 0})))
    except Exception as e:
        print(f"Error fetching from mongodb: {e}")
        return
    
    gamefinder = leaguegamefinder.LeagueGameFinder(
        league_id_nullable='00',
        season_nullable='2025-26',
        season_type_nullable='Regular Season',
        headers = custom_headers,
        timeout=60
    )

    df = gamefinder.get_data_frames()[0]
    df.dropna(subset=['WL'], inplace=True)
    df = df.sort_values('GAME_DATE')
    all_team_rows = []
    all_player_rows = []

    existingids = set(advanced_df['GAME_ID'])
    for gameid, teamcode, date in zip(df.GAME_ID, df.TEAM_ABBREVIATION, df.GAME_DATE):
        if gameid not in existingids:
            try:
                advanced_boxscore = rate_limited_call(gameid)

                if advanced_boxscore['boxScoreAdvanced']['awayTeam']['teamTricode'] == teamcode:
                    team = advanced_boxscore['boxScoreAdvanced']['awayTeam']
                    home = 0
                else:
                    team = advanced_boxscore['boxScoreAdvanced']['homeTeam']
                    home = 1
                team_stats = team['statistics']

                all_team_rows.append({
                    **team_stats,
                    "GAME_ID": gameid,
                    "TEAM_ABBREVIATION": teamcode,
                    "starters": [f"{p['firstName']} {p['familyName']}"
                                for p in team['players'][:5]],
                })

                for p in team['players']:
                    stats = p["statistics"]
                    player_name = f"{p['firstName']} {p['familyName']}"


                    all_player_rows.append({
                        "PLAYER_NAME": player_name,
                        "GAME_ID": gameid,
                        "GAME_DATE": date,
                        "TEAM_ABBREVIATION": teamcode,
                        "HOME": home,
                        "WNI": WNI(stats['PIE'], stats['minutes'], stats['usagePercentage'], p['comment']),
                    })        

            except Exception as e:
                print(f"Error processing {gameid}: {e}")

    new_advanced = pd.DataFrame(all_team_rows)
    new_player = pd.DataFrame(all_player_rows)
    
    if not new_player.empty:
        player_records = new_player.to_dict('records')
        playerCollection.insert_many(player_records)
        print(f"Added {len(player_records)} new player rows.")

    if not new_advanced.empty:
        advanced_records = new_advanced.to_dict('records')
        advancedCollection.insert_many(advanced_records)
        print(f"Added {len(advanced_records)} new advanced stats rows.")

if __name__ == "__main__":
    main()
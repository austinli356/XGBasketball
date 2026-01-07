import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from requests.models import Request
import requests_cache
from nba_api.stats.library.http import NBAStatsHTTP
from nba_api.stats.endpoints import leaguegamefinder, boxscoreadvancedv3
from nba_api.live.nba.endpoints import scoreboard

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import WNI, rate_limited_call
NPOINTadvanced = 'https://api.npoint.io/f6865f48b4a169d10f84'
NPOINTplayer = 'https://api.npoint.io/207625bb75818939a394'


def main():
    try:
        player = requests.get(NPOINTplayer)
        player.raise_for_status() # Check if the request was successful
        player_df = pd.DataFrame(player.json())
        advanced = requests.get(NPOINTadvanced)
        advanced.raise_for_status() # Check if the request was successful
        advanced_df = pd.DataFrame(advanced.json())
    except Exception as e:
        print(f"Error fetching from npoint: {e}")
        return
    
    gamefinder = leaguegamefinder.LeagueGameFinder(
        league_id_nullable='00',
        season_nullable='2025-26',
        season_type_nullable='Regular Season',
    )

    df = gamefinder.get_data_frames()[0]
    df.dropna(subset=['WL'], inplace=True)
    all_team_rows = []
    all_player_rows = []

    existingids = set(advanced_df['GAME_ID'])
    for gameid, teamcode, date in zip(df.GAME_ID, df.TEAM_ABBREVIATION, df.GAME_DATE):
        if gameid not in existingids:
            try:
                advanced_boxscore = rate_limited_call(gameid)

                if advanced_boxscore['boxScoreAdvanced']['awayTeam']['teamTricode'] == teamcode:
                    team = advanced_boxscore['boxScoreAdvanced']['awayTeam']
                else:
                    team = advanced_boxscore['boxScoreAdvanced']['homeTeam']
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

    updated_advanced = pd.concat([advanced_df, new_advanced], ignore_index=True)
    updated_player = pd.concat([player_df, new_player], ignore_index=True)

    updated_advanced_list = updated_advanced.to_dict(orient='records')
    updated_player_list = updated_player.to_dict(orient='records')

    update_advanced_response = requests.post(NPOINTadvanced, json=updated_advanced_list)
    update_player_response = requests.post(NPOINTplayer, json=updated_player_list)

if __name__ == "__main__":
    main()
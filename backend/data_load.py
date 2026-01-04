import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import pytz
import requests
from requests.models import Request
import requests_cache
from nba_api.stats.library.http import NBAStatsHTTP
from bs4 import BeautifulSoup
import unicodedata
from nba_api.stats.endpoints import leaguegamefinder, boxscoreadvancedv3
from nba_api.live.nba.endpoints import scoreboard
from utils import strip, WNI, rate_limited_call, get_lineups
from tqdm import tqdm

def load_data():
    cache_buster = int(time.time())
    url = f'https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json?t={cache_buster}'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com",
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    current_date = data['scoreboard']['gameDate']
    teams = ['ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW', 'HOU',
            'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK', 'OKC', 'ORL',
            'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS']

    seasons = ["2024-25", "2025-26"]

    drop_cols = ['TEAM_ID', 'TEAM_NAME', 'SEASON_ID']
    frames = []


    #get boxscores across every season in seasons
    for season in seasons:
        gamefinder = leaguegamefinder.LeagueGameFinder(
            league_id_nullable='00',
            season_nullable=season,
            season_type_nullable='Regular Season',
            date_to_nullable = (datetime.strptime(current_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        ) if season =='2025-26' else leaguegamefinder.LeagueGameFinder(
            league_id_nullable='00',
            season_nullable=season,
            season_type_nullable='Regular Season',
        )
        df = gamefinder.get_data_frames()[0]

        df = df.drop(columns=drop_cols)



        df.insert(3, "season", season)
        df.insert(4, "home", df["MATCHUP"].str.contains("vs").astype(int))
        df.insert(7, "target", None)
        df['WL'] = (df['WL'] == 'W').astype(int)

        frames.append(df)
    box_df = pd.concat(frames, ignore_index=True)
    box_df.reset_index(drop=True, inplace=True)
    box_df.sort_values(by=['TEAM_ABBREVIATION', 'season', 'GAME_DATE'], ascending=[True, True, True], inplace=True)


    all_data_list = []
    all_player_list = []

    all_team_rows = []
    all_player_rows = []

    for gameid, teamcode, date, season in tqdm(zip(box_df.GAME_ID, box_df.TEAM_ABBREVIATION, box_df.GAME_DATE, box_df.season)):
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

    # Build final DataFrames
    advanced_df = pd.DataFrame(all_team_rows)
    player_df   = pd.DataFrame(all_player_rows)

    player_df = player_df.sort_values(by=['GAME_DATE'])
    scraped_df = get_lineups()

    df = box_df.merge(advanced_df, on=['GAME_ID', 'TEAM_ABBREVIATION'], how='left')
    df = df.drop(columns=['minutes', 'estimatedOffensiveRating',
                        'estimatedDefensiveRating', 'estimatedNetRating',
                        'estimatedTeamTurnoverPercentage', 'usagePercentage',
                        'estimatedUsagePercentage', 'estimatedPace', 'REB', 'assistPercentage',
                        ])
    df['idx'] = df['GAME_DATE'].astype(str) + '_' + df['TEAM_ABBREVIATION'].astype(str)
    df.set_index('idx', inplace=True)

    return df, player_df, scraped_df, current_date



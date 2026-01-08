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
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
import sys

def load_data():
    teams = ['ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW', 'HOU',
            'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK', 'OKC', 'ORL',
            'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS']

    drop_cols = ['TEAM_ID', 'TEAM_NAME', 'SEASON_ID']


    #get boxscores across every season in seasons

    gamefinder = leaguegamefinder.LeagueGameFinder(
        league_id_nullable='00',
        season_nullable='2025-26',
        season_type_nullable='Regular Season',
    )
    
    box_df = gamefinder.get_data_frames()[0]
    box_df.dropna(subset=['WL'], inplace = True)
    box_df = box_df.drop(columns=drop_cols)
    box_df.insert(3, "season", '2025-26')
    box_df.insert(4, "home", box_df["MATCHUP"].str.contains("vs").astype(int))
    box_df.insert(7, "target", None)
    box_df['WL'] = (box_df['WL'] == 'W').astype(int)
    box_df.sort_values(by=['TEAM_ABBREVIATION', 'season', 'GAME_DATE'], ascending=[True, True, True], inplace=True)
    box_df.reset_index(drop=True, inplace=True)


    try:
        uri = os.environ.get("MONGO_URI")
        client = MongoClient(uri, server_api=ServerApi('1'))
        playerCollection = client['player']['dataframe']
        advancedCollection = client['advanced']['dataframe']
        player_df = pd.DataFrame(list(playerCollection.find({}, {'_id': 0})))
        advanced_df = pd.DataFrame(list(advancedCollection.find({}, {'_id': 0})))
    except Exception as e:
        print(f"Error fetching from mongodb: {e}")
        return
    
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

    return df, player_df, scraped_df



import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import pytz
import requests
from requests.models import Request
import requests_cache
from bs4 import BeautifulSoup
import unicodedata

from nba_api.stats.endpoints import leaguegamefinder, boxscoreadvancedv3
from nba_api.stats.library.http import NBAStatsHTTP
from nba_api.live.nba.endpoints import scoreboard


from utils import strip, WNI, rate_limited_call, get_rotowire_lineups

def load_data():
    teams = ['ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW', 'HOU',
            'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK', 'OKC', 'ORL',
            'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS']

    seasons = ["2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

    drop_cols = ['TEAM_ID', 'TEAM_NAME', 'SEASON_ID']
    frames = []

    # caching/rate limiting
    requests_cache.install_cache('nba_api_cache', expire_after=7*24*3600)
    NBAStatsHTTP._session = requests_cache.CachedSession('nba_api_cache', backend='sqlite')
    #get boxscores across every season in seasons
    for season in seasons:
        url = f"https://stats.nba.com/stats/leaguegamefinder?Conference=&DateFrom=&DateTo=&Division=&DraftNumber=&DraftRound=&DraftTeamID=&DraftYear=&EqAST=&EqBLK=&EqDD=&EqDREB=&EqFG3A=&EqFG3M=&EqFG3_PCT=&EqFGA=&EqFGM=&EqFG_PCT=&EqFTA=&EqFTM=&EqFT_PCT=&EqMINUTES=&EqOREB=&EqPF=&EqPTS=&EqREB=&EqSTL=&EqTD=&EqTOV=&GameID=&GtAST=&GtBLK=&GtDD=&GtDREB=&GtFG3A=&GtFG3M=&GtFG3_PCT=&GtFGA=&GtFGM=&GtFG_PCT=&GtFTA=&GtFTM=&GtFT_PCT=&GtMINUTES=&GtOREB=&GtPF=&GtPTS=&GtREB=&GtSTL=&GtTD=&GtTOV=&LeagueID=00&Location=&LtAST=&LtBLK=&LtDD=&LtDREB=&LtFG3A=&LtFG3M=&LtFG3_PCT=&LtFGA=&LtFGM=&LtFG_PCT=&LtFTA=&LtFTM=&LtFT_PCT=&LtMINUTES=&LtOREB=&LtPF=&LtPTS=&LtREB=&LtSTL=&LtTD=&LtTOV=&Outcome=&PORound=&PlayerID=&PlayerOrTeam=T&RookieYear=&Season={season}&SeasonSegment=&SeasonType=Regular+Season&StarterBench=&TeamID=&VsConference=&VsDivision=&VsTeamID=&YearsExperience="
        req = Request('GET', url).prepare()
        key = NBAStatsHTTP._session.cache.create_key(req)
        cached_response = NBAStatsHTTP._session.cache.get_response(key)

        if cached_response is not None:
            response = cached_response.json()
            df = pd.DataFrame(response['resultSets'][0]['rowSet'], columns = response['resultSets'][0]['headers'])
        else:
            gamefinder = leaguegamefinder.LeagueGameFinder(
                league_id_nullable='00',
                season_nullable=season,
                season_type_nullable='Regular Season',
                date_to_nullable= (datetime.now(pytz.timezone('US/Pacific')) - timedelta(days=1)).strftime('%Y-%m-%d')

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

    for gameid, teamcode, date, season in zip(box_df.GAME_ID, box_df.TEAM_ABBREVIATION, box_df.GAME_DATE, box_df.season):
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
                "starters": [strip(f"{p['firstName']} {p['familyName']}")
                            for p in team['players'][:5]],
            })

            for p in team['players']:
                stats = p["statistics"]
            if stats['minutes']:
                player_name = strip(f"{p['firstName']} {p['familyName']}")


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
    scraped_df = get_rotowire_lineups()

    df = box_df.merge(advanced_df, on=['GAME_ID', 'TEAM_ABBREVIATION'], how='left')
    df = df.drop(columns=['minutes', 'estimatedOffensiveRating',
                        'estimatedDefensiveRating', 'estimatedNetRating',
                        'estimatedTeamTurnoverPercentage', 'usagePercentage',
                        'estimatedUsagePercentage', 'estimatedPace', 'REB', 'assistPercentage',
                        ])
    df['idx'] = df['GAME_DATE'].astype(str) + '_' + df['TEAM_ABBREVIATION'].astype(str)
    df.set_index('idx', inplace=True)

    for _, row in scraped_df.iterrows():

        GAME_DATE = datetime.strptime(row['date'], "%B %d, %Y").strftime("%Y-%m-%d")
        home = row['home']
        away = row['away']
        # HOME

        idx = f"{GAME_DATE}_{home}"
        df.at[idx, 'season'] = '2025-26'
        df.at[idx, 'MATCHUP'] = f"{home} vs. {away}"
        df.at[idx, 'home'] = 1
        df.at[idx, 'GAME_DATE'] = GAME_DATE
        df.at[idx, 'TEAM_ABBREVIATION'] = home
        df.at[idx, 'starters'] = row['homeLineup']


        # AWAY
        idx = f"{GAME_DATE}_{away}"

        df.at[idx, 'season'] = '2025-26'
        df.at[idx, 'MATCHUP'] = f"{away} @ {home}"
        df.at[idx, 'home'] = 0
        df.at[idx, 'GAME_DATE'] = GAME_DATE
        df.at[idx, 'TEAM_ABBREVIATION'] = away
        df.at[idx, 'starters'] = row['awayLineup']

    return df, player_df, scraped_df



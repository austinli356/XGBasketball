import time
from datetime import datetime, timedelta
import unicodedata
import requests
import requests_cache
from requests.models import Request
import pandas as pd
import numpy as np
from nba_api.stats.endpoints import boxscoreadvancedv3

last_call = 0
MIN_INTERVAL = 1.2

def rate_limited_call(game_id):
    global last_call
    elapsed = time.time() - last_call
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)

    result = boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=game_id).get_dict()

    last_call = time.time()
    return result

def removeSuffix(s):
  split = s.strip().split(" ")
  out = split[0] + " " + split[1]
  suffixes = ['Jr.', 'Sr.', 'II', 'III', 'IV']
  for i in range(2, len(split)):
    if not split[i] in suffixes:
      out = out + " " + split[i]
  return out

def strip(s):
  normalized = unicodedata.normalize('NFD', s)
  stripped = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

  return removeSuffix(stripped)

def WNI(pie, mins, usg, comment): # calculates a players impact in a given game
  if mins:
    mins = float(mins.split(':')[0]) + float(mins.split(':')[1])/60
  else:
    if comment[:3]=="DNP": # handles DNP/DND context for player impact
      mins = 0
    else:
      return np.nan
  return mins * usg * pie

def add_rolling(df, group_cols, value_col, windows, prefix):
    for w in windows:
        df[f"{prefix}{w}_rolling_{value_col}"] = (
            df.groupby(group_cols)[value_col]
              .rolling(window=w, min_periods=1)
              .mean()
              .reset_index(level=list(range(len(group_cols))), drop=True)
        )
    return df

def find_weighted_team_averages(team, span, context, cols):
  team = team.copy()
  if context==1:
    homeMasked = team[cols].where(team['home'] == 1)
    awayMasked = team[cols].where(team['home'] == 0)

    ewmaHome = homeMasked.ewm(span=span, adjust=False).mean()
    ewmaAway = awayMasked.ewm(span=span, adjust=False).mean()

    out = ewmaHome.where(team['next_home'] == 1, ewmaAway)
    out = out.mask(team['next_home'].isna())
  else:
    out = team[cols].ewm(span=span, adjust=False).mean()
  return out

def computeStreak(group):
    streak = 0
    streak_list = []
    for result in group['WL']:
        if result == 1:
            streak = streak + 1 if streak >= 0 else 1
        else:
            streak = streak - 1 if streak <= 0 else -1
        streak_list.append(streak)
    # Return a Series with the same index
    return pd.Series(streak_list, index=group.index)

def computeRecord(group):
    wins = 0
    losts = 0
    record_list = []
    for result in group['WL']:
      if result == 1:
        wins+=1
      else:
        losts+=1
      record_list.append(wins/(wins+losts))
    return pd.Series(record_list, index = group.index)

def get_lineups():
    try:
      date = (datetime.now()).strftime('%Y%m%d')
      cache_buster = int(time.time())
      url = f'https://stats.nba.com/js/data/leaders/00_daily_lineups_{date}.json?={cache_buster}'
      headers = {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
          "Accept": "application/json, text/plain, */*",
          "Referer": "https://www.nba.com/",
          "Origin": "https://www.nba.com",
      }
      response = requests.get(url, headers=headers)

      if response.status_code != 200:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        cache_buster = int(time.time())
        url = f'https://stats.nba.com/js/data/leaders/00_daily_lineups_{date}.json?={cache_buster}'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.nba.com/",
            "Origin": "https://www.nba.com",
        }
        response = requests.get(url, headers=headers)
      data = response.json()
      date_formatted = date[:4] + "-" + date[4:6] + "-" + date[6:]
      game_data = data['games']
      games = []
      for game in game_data:
        awayStartingFive = []
        homeStartingFive = []
        for player_home, player_away in zip(game['homeTeam']['players'][:5], game['awayTeam']['players'][:5]):
          homeStartingFive.append(player_home['playerName'])
          homeStartingFive.append(player_away['playerName'])
        games.append({
          "matchup": f"{game['awayTeam']['teamAbbreviation']} @ {game['homeTeam']['teamAbbreviation']}",
          "away": game['awayTeam']['teamAbbreviation'],
          "home": game['homeTeam']['teamAbbreviation'],
          "awayLineup": awayStartingFive,
          "homeLineup": homeStartingFive,
          "date": date_formatted,
          "gameId": game['gameId']
        })
      return pd.DataFrame(games)
    except Exception as e:
            print("Error getting a lineup:", e)

def getEndpointDate():
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
  return data['scoreboard']['gameDate']
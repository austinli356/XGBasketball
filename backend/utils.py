import time
import unicodedata
import requests
import requests_cache
from requests.models import Request
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

from nba_api.stats.endpoints import boxscoreadvancedv3
from nba_api.stats.library.http import NBAStatsHTTP


requests_cache.install_cache('nba_api_cache', expire_after=7*24*3600)
NBAStatsHTTP._session = requests_cache.CachedSession('nba_api_cache', backend='sqlite')

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

last_call = 0
MIN_INTERVAL = 1.2
def rate_limited_call(game_id):
  global last_call
  url = f"https://stats.nba.com/stats/boxscoreadvancedv3?EndPeriod=0&EndRange=0&GameID={game_id}&RangeType=0&StartPeriod=0&StartRange=0"
  req = Request('GET', url).prepare()
  key = NBAStatsHTTP._session.cache.create_key(req)

  cached_response = NBAStatsHTTP._session.cache.get_response(key)
  if cached_response is not None:
        return cached_response.json()

  elapsed = time.time() - last_call
  if elapsed < MIN_INTERVAL:
      time.sleep(MIN_INTERVAL - elapsed)

  result = boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=game_id).get_dict()

  last_call = time.time()
  return result

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

def get_rotowire_lineups():
    headers = {"User-Agent": "Mozilla/5.0"}
    cache_buster = int(time.time())
    url = f"https://www.rotowire.com/basketball/nba-lineups.php?t={cache_buster}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    date = soup.find("div", class_="page-title__secondary")
    game_blocks = soup.find_all("div", class_="lineup__box")
    date_text = soup.find("div", class_="page-title__secondary").get_text(strip=True)
    prefix = len("Starting lineups for ")
    date = date_text[prefix:]
    games = []
    for game in game_blocks:
        try:
            # --- Teams ---

            teams = game.find_all("a", class_=("lineup__team"))

            away = teams[0].find("div", class_="lineup__abbr").get_text(strip=True)
            home = teams[1].find("div", class_="lineup__abbr").get_text(strip=True)

            lineup = game.find("div", class_="lineup__main")
            awayLineup = lineup.select_one("ul.lineup__list.is-visit")
            awayStatus = awayLineup.find("li", class_="lineup__status").get_text(strip=True)
            awayPlayers = awayLineup.find_all("li", class_="lineup__player")
            awayStartingFive = []
            homeLineup = lineup.select_one("ul.lineup__list.is-home")
            homeStatus = homeLineup.find("li", class_="lineup__status").get_text(strip=True)
            homePlayers = homeLineup.find_all("li", class_="lineup__player")
            homeStartingFive = []

            awayLineupStrength = 0
            homeLineupStrength = 0
            for player in awayPlayers[:5]:
              name = player.find("a").get("title")
              awayStartingFive.append(name)
            for player in homePlayers[:5]:
              name = player.find("a").get("title")
              homeStartingFive.append(name)
            games.append(
                {
                    "matchup": f"{away} @ {home}",
                    "away": away,
                    "home": home,
                    "awayStatus": awayStatus,
                    "homeStatus": homeStatus,
                    "awayLineup": awayStartingFive,
                    "homeLineup": homeStartingFive,
                    "date": date
                }
            )
        except Exception as e:
            print("Error parsing a game:", e)
    return pd.DataFrame(games)
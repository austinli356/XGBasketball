from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import os
from data_load import load_data
from data_process import process_data
from configs import features
from datetime import datetime
import pytz
import json
import time
from utils import getEndpointDate

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="/")
CORS(app)

# Dockerized XGB prediction service URL
XGB_SERVICE_URL = "https://xgb-predictor-latest.onrender.com/predict"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0...",
    "Accept": "application/json, text/plain, */*",
})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


print("Loading data...")
raw_df, player_df, scraped_df= load_data()
feature_df = process_data(raw_df, player_df, scraped_df)
date = getEndpointDate()

url = f'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json?t={int(time.time())}'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}
response = session.get(url, headers=headers)
scheduleLeagueV2data = response.json()
print("Data loaded and processed!")

@app.route("/run-calculations", methods=["POST"])
def get_predictions():
    try:
        data = request.get_json()
        gameid = data.get("gameId") 

        if not gameid:
            return jsonify({"error": "Missing 'home' in request body"}), 400
        game_rows = feature_df[((feature_df['next_GAME_ID'] == gameid) & (feature_df['next_home'] == 1))]
        if game_rows.empty:
            return jsonify({"error": f"No data found for team {gameid}"}), 404

        row_dict = game_rows[features].iloc[0].to_dict()

        try:
            response = requests.post(XGB_SERVICE_URL, json={"row": row_dict})
            response.raise_for_status()
            proba = response.json()
            home_win_prob = proba.get("home_win_prob")
        except Exception as e:
            print(f"XGB service error: {e}")
            home_win_prob = None
        return jsonify({"home_win_prob": home_win_prob})

    except Exception as e:
        print(f"Error in get_predictions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/nba-scores', methods=['GET'])
def get_nba_scores():
    cache_buster = int(time.time())
    selected_date = request.args.get("date")
    try:
        if selected_date == date: 
            url = f'https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json?t={cache_buster}'
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.nba.com/",
                "Origin": "https://www.nba.com",
            }
            response = session.get(url, headers=headers)
            data = response.json()
            games = data['scoreboard']['games']
        else:
            for day in scheduleLeagueV2data['leagueSchedule']['gameDates']: 
                formatted = day['gameDate'].split()[0]
                if datetime.strptime(formatted, "%m/%d/%Y").strftime("%Y-%m-%d") == selected_date:
                    games = day['games']
                
        boxscores = []

        for game in games:
            game_id = game['gameId']
            visitor_abbr = game['awayTeam']['teamTricode']
            home_abbr = game['homeTeam']['teamTricode']
            game_status = game['gameStatus']
            last_play = ""
            if game_status == 2:
                try:
                    url = f'https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json?t={cache_buster}'
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
                        "Accept": "application/json, text/plain, */*",
                        "Referer": "https://www.nba.com/",
                        "Origin": "https://www.nba.com",
                    }
                    response = session.get(url, headers=headers)
                    data = response.json()
                    last_play = data['game']['actions'][-1]['description']
                except Exception as e:
                    print(f"error: Failed to get play by play data: {e}")

            box = {
                'id': game_id,
                'visitorTeam': {
                    'name': game['awayTeam']['teamName'],
                    'abbreviation': visitor_abbr,
                    'score': game['awayTeam']['score'],
                    'color': '#AAAAAA',
                    'winProb': None
                },
                'homeTeam': {
                    'name': game['homeTeam']['teamName'],
                    'abbreviation': home_abbr,
                    'score': game['homeTeam']['score'],
                    'color': '#BBBBBB',
                    'winProb': None
                },
                'gameState': game_status,
                'gameStatusText': game['gameStatusText'] if game_status != 3 else "",
                'lastPlay' : last_play
            }
            boxscores.append(box)
        return jsonify(boxscores)

    except Exception as e:
        print(f"Error fetching NBA scores: {e}")
        return jsonify({"error": "Failed to fetch data from NBA API"}), 500

PORT = int(os.environ.get("PORT", 5000))
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=PORT, debug=True)

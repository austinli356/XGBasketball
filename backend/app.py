from flask import Flask, jsonify, g, request
from flask_cors import CORS
import requests
from data_load import load_data
from data_process import process_data
from configs import features
from datetime import datetime
import pytz
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

print("Loading data...")
raw_df, player_df, scraped_df = load_data()
games_to_predict = process_data(raw_df, player_df)
home_rows = games_to_predict[games_to_predict['next_home'] == 1]
print("Data loaded and processed!")

# Dockerized XGB prediction service URL
XGB_SERVICE_URL = "http://localhost:8000/predict"
@app.route("/run-calculations", methods=["POST"])
def get_predictions():
    try:
        data = request.get_json()
        home = data.get("home") 

        if not home:
            return jsonify({"error": "Missing 'home' in request body"}), 400

        team_rows = home_rows[home_rows['TEAM_ABBREVIATION'] == home]

        if team_rows.empty:
            return jsonify({"error": f"No data found for team {home}"}), 404

        row_dict = team_rows[features].iloc[0].to_dict()

        try:
            response = requests.post(XGB_SERVICE_URL, json={"row": row_dict})
            response.raise_for_status()
            proba = response.json()
            home_win_prob = proba.get("home_win_prob")
        except Exception as e:
            print(f"XGB service error: {e}")
            home_win_prob = None

        home_win_probs = {home: home_win_prob}
        return jsonify({"home_win_probs": home_win_probs})

    except Exception as e:
        print(f"Error in get_predictions: {e}")
        return jsonify({"error": str(e)}), 500

        
@app.route('/api/nba-scores', methods=['GET'])
def get_nba_scores():
    try:
        from nba_api.live.nba.endpoints import scoreboard
        s = scoreboard.ScoreBoard()
        games = s.get_dict()["scoreboard"]["games"]
        boxscores = []
        # with open("input.json", "r") as f:
        #     data = json.load(f)
        # target_date = datetime.today().strftime('%m/%d/%Y')
        # games = []
        # for game_date in data.get("leagueSchedule", {}).get("gameDates", []):
        #     if target_date in game_date.get("gameDate"):
        #         games = game_date.get("games", [])
        #         break  

        boxscores = []

        for game in games:
            game_id = game['gameId']
            visitor_abbr = game['awayTeam']['teamTricode']
            home_abbr = game['homeTeam']['teamTricode']
            game_status = game['gameStatus']
            is_live = True if game_status == 2 else False
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
                'isLive': is_live
            }
            boxscores.append(box)
        return jsonify(boxscores)

    except Exception as e:
        print(f"Error fetching NBA scores: {e}")
        return jsonify({"error": "Failed to fetch data from NBA API"}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)

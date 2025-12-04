from flask import Flask, jsonify, g
from flask_cors import CORS
from nba_api.live.nba.endpoints import scoreboard
import requests
from data_load import load_data
from data_process import process_data
from configs import features
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}}) 

# Dockerized XGB prediction service URL
XGB_SERVICE_URL = "http://localhost:8000/predict"

@app.before_request
def construct_df():
    try:
        raw_df, player_df, scraped_df = load_data()
        games_to_predict = process_data(raw_df, player_df)
        home_rows = games_to_predict[games_to_predict['next_home'] == 1]
        g.home_win_probs = {}

        for index, row in home_rows.iterrows():
            row_dict = row[features].to_dict()
            try:
                response = requests.post(XGB_SERVICE_URL, json={"row": row_dict})
                proba = response.json()
                home_win_prob = proba["home_win_prob"]
            except:
                home_win_prob = None
            g.home_win_probs[row['TEAM_ABBREVIATION']] = home_win_prob
    except Exception as e:
        print(f"Error processing game data: {e}")
        
@app.route('/api/nba-scores', methods=['GET'])
def get_nba_scores():
    try:
        s = scoreboard.ScoreBoard()
        games = s.get_dict()["scoreboard"]["games"]
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
                    'winProb': 1-g.home_win_probs[home_abbr]
                },
                'homeTeam': {
                    'name': game['homeTeam']['teamName'],
                    'abbreviation': home_abbr,
                    'score': game['homeTeam']['score'],
                    'color': '#BBBBBB',
                    'winProb': g.home_win_probs[home_abbr]
                },
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

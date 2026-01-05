# 🏀 NBA Game Predictor XGBasketball
![Recording 2026-01-04 161032 (2)](https://github.com/user-attachments/assets/c61e224b-6ecc-4bfa-9948-b862299baa67)

A full-stack machine learning application that predicts the outcome of NBA games with **72% accuracy**. This project leverages Bayesian optimization for model tuning and a fully vectorized data pipeline to process historical data for over 20,000 games.

## 🚀 Technical Highlights

* **Model Performance:** Achieved 72% accuracy on the 2025–26 season using an **XGBoost Classifier**.
* **Feature Engineering:** Engineered 200+ temporal metrics using **Exponentially Weighted Moving Averages (EWMA)** to capture team momentum. Included daily lineup data from an official NBA endpoint.
* **Optimization:** Utilized **Optuna** for Bayesian hyperparameter tuning and **SHAP** to interpret feature importance (e.g., identifying "Rest Days" and "net rating difference" as top predictors).
* **Sub-second Inference:** Designed a End to End application which delivers prediction from the docker containerized model to the frontend in under 1 second.

## 🏗️ System Architecture

The application is split into three core layers:

1. **Backend:** A robust Flash API pipeline that aggregates, cleans and engineers data from the `nba_api` and web-scraped sources into standardized DataFrames. 
2. **ML Service:** A Fast API that serves as the inference engine, running within a Docker container.
3. **Frontend:** A modern React/TypeScript dashboard that displays nba games and model prediction.

---

## 🛠️ Tech Stack

* **Languages:** Python
* **Machine Learning:** XGBoost, Scikit-learn, Optuna, SHAP
* **Data Processing:** Pandas, NumPy
* **Backend:** Flask, Fast API
* **Frontend:** Typescript, React, Tailwind CSS
* **DevOps:** Docker, GitHub

---

## 🚦 Getting Started

#### Requirements
* Node.js(v24.11.1+) and npm
* Python 3.10+


1. Clone the repository:
```bash
git clone https://github.com/yourusername/nba-xgboost-predictor.git
cd nba-live
```
2. Install the requirements:
```bash
cd backend
python -m venv venv # create a virtual environment
pip install -r requirements.txt
python app.py # start the Flask server
```
3. Create the distribution
```bash
cd frontend
npm run build
```
4.  Access the dashboard at `http://127.0.0.1:5000`.


---

## 📈 Future Roadmap

* [ ] Display detailed matchup statistics.
* [ ] Retrain and Redeploy XGBoost model with better engineered features and pregame betting spread data.
* [ ] Extend model prediction from binary classification to point spreads.

---

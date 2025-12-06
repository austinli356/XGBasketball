## 🏀 Predicting NBA Game Outcomes (72% Accuracy)

This project is an **end-to-end, production-ready Machine Learning system** designed to predict the outcome of NBA games. It features a robust data ingestion pipeline, advanced time-series feature engineering, and a fully dockerized inference service.

| Component | Stack | Key Feature |
| :--- | :--- | :--- |
| **Model** | XGBoost, scikit-learn, Optuna | Achieves **72%** accuracy and uses **SHAP** for interpretability. |
| **Data Pipeline** | Pandas, NBA API, Web Scraping | Aggregates 20k+ games, generating features in **subsecond** time. |
| **Inference Service** | Flask API, Docker | Serves predictions with **\<200ms latency** (if measured). |
| **Frontend** | React, TypeScript | Presents real-time predictions and backtesting analytics. |

<br>

## 🚀 Live Demo & Repository Status

| Status | Link |
| :--- | :--- |
| **Live Inference Service** | [loading...] |
| **Project Code** | [https://github.com/austinli356/XGBasketball] |
| **Experiment Tracking** | [loading...] |

-----

## 💻 MLOps & System Architecture

This system is built for **reproducibility and scalability**.

### 1\. Model Training & Optimization

  * **Hyperparameter Tuning:** Used **Optuna** with Bayesian optimization to significantly tune the XGBoost model parameters, achieving a **5%+ AUC improvement** over baseline models.
  * **Interpretability:** Integrated **SHAP** (SHapley Additive exPlanations) to provide local and global explanations for model predictions, ensuring trust and validating feature importance.

### 2\. Feature Engineering & Performance

  * **Vectorization:** All feature engineering is fully **vectorized** using NumPy and Pandas to achieve subsecond processing times for real-time predictions.
  * **Temporal Features:** Generated over 200 features based on multi-scale **Exponentially Weighted Moving Averages (EWMA)** to capture team performance trends and momentum better than simple rolling averages.

### 3\. Production Deployment

  * **Containerization:** The Flask API inference service is fully **Dockerized** to ensure consistent runtime across development, testing, and production environments.
  * **Full Stack:** The system utilizes a **Flask API** backend for serving the model weights and inference requests, coupled with a responsive **React/TypeScript** frontend for visualization.

-----

## 🛠️ How to Run Locally
Loading...

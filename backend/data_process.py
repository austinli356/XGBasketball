import pandas as pd
import numpy as np

from utils import add_rolling, computeStreak, computeRecord, find_weighted_team_averages


def process_data(df, player_df):
    df['starters'] = df.groupby(['TEAM_ABBREVIATION', 'season'])['starters'].shift(-1)

    player_df = player_df.sort_values(["PLAYER_NAME", "HOME", "GAME_DATE"])

    player_df = add_rolling(
        df=player_df,
        group_cols=["PLAYER_NAME", "HOME"],
        value_col="WNI",
        windows=[5, 10, 25],
        prefix="context_"
    )
    player_df = player_df.sort_values(["PLAYER_NAME", "GAME_DATE"])
    player_df = add_rolling(
        df=player_df,
        group_cols=["PLAYER_NAME"],
        value_col="WNI",
        windows=[5, 10, 25],
        prefix=""
    )

    df.reset_index(inplace=True, drop=True)
    df = df.sort_values("GAME_DATE")
    player_df = player_df.sort_values("GAME_DATE")

    rolling_cols = [
        "context_5_rolling_WNI",
        "context_10_rolling_WNI",
        "context_25_rolling_WNI",
        "5_rolling_WNI",
        "10_rolling_WNI",
        "25_rolling_WNI"
    ]

    games_exploded = df.explode("starters").rename(columns={"starters": "PLAYER_NAME"})

    merged = games_exploded.merge(
        player_df[["PLAYER_NAME", "GAME_DATE"] + rolling_cols],
        on=["PLAYER_NAME", "GAME_DATE"],
        how="left"
    )


    starter_rolling_sum = merged.groupby(['GAME_ID', 'TEAM_ABBREVIATION'])[rolling_cols].sum()

    df = df.merge(
        starter_rolling_sum.rename(columns=lambda x: f"lineup_{x}"),
        on=['GAME_ID', 'TEAM_ABBREVIATION'],
        how="left"
    )

    # Optional: make sure rows with missing starters are NaN
    df.loc[df["starters"].isna(), [f"lineup_{col}" for col in rolling_cols]] = np.nan

    df['target'] = df.groupby(['TEAM_ABBREVIATION', 'season'])['WL'].shift(-1).astype('Int64')
    df['next_home'] = df.groupby(['TEAM_ABBREVIATION', 'season'])['home'].shift(-1).astype('Int64')

    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'], format='%Y-%m-%d')
    df['next_GAME_DATE'] = df.groupby(['TEAM_ABBREVIATION', 'season'])['GAME_DATE'].shift(-1)

    df['rest_days'] = (df['next_GAME_DATE'] - df['GAME_DATE']).dt.days-1
    df['recent_intensity'] = (
        df.groupby(['TEAM_ABBREVIATION', 'season'])['GAME_DATE']
        .transform(lambda x: 4 / ((x - x.shift(3)).dt.days + 1))
    )
    df['GAME_DATE'] = df['GAME_DATE'].dt.strftime('%Y-%m-%d')
    df = df.drop(columns=['next_GAME_DATE'])

    df['streak'] = 0
    df['streak'] = df.groupby(['TEAM_ABBREVIATION', 'season'], group_keys=False).apply(computeStreak, include_groups=False)
    df['record'] = 0
    df['record'] = df.groupby(['TEAM_ABBREVIATION', 'season'], group_keys=False).apply(computeRecord, include_groups=False)
    df.sort_values(by=['TEAM_ABBREVIATION', 'season', 'GAME_DATE'], ascending=[True, True, True], inplace=True)
    df.reset_index(drop=True, inplace=True)


    GameTotals = ['PTS', 'STL', 'BLK', 'TOV', 'AST', 'PF', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTA', 'FTM', 'DREB', 'OREB']
    ppColumns = [f"pp_{col}" for col in GameTotals]
    df[ppColumns] = df[GameTotals].div(df['possessions'], axis=0)
    df.drop(columns=GameTotals, inplace=True)

    # Columns to exclude when computing weighted averages
    removed_columns = ['GAME_DATE', 'MATCHUP', 'target', 'streak', 'next_home', 'WL',
                    'MIN', 'TEAM_ABBREVIATION', 'season', 'home', "context_5_rolling_PIE",
                    "lineup_context_5_rolling_PIE",
                    "lineup_context_10_rolling_PIE",
                    "lineup_context_25_rolling_PIE",
                    "lineup_5_rolling_PIE",
                    "lineup_10_rolling_PIE",
                    "lineup_25_rolling_PIE", 'record', 'starters']

    selected_columns = df.columns[~df.columns.isin(removed_columns)]


    # EWM configurations
    configs = [
        (5, 1, "ewm5_context_", selected_columns),
        (10, 1, "ewm10_context_", selected_columns),
        (25, 1, "ewm25_context_", selected_columns),
        (5, 0, "ewm5_", selected_columns),
        (10, 0, "ewm10_", selected_columns),
        (25, 0, "ewm25_", selected_columns),
    ]

    # Compute EWM features
    copy = df.copy()
    ewm_features = []

    for span, context, prefix, cols in configs:
        temp = (
            copy
            .groupby(["TEAM_ABBREVIATION", "season"], group_keys=False)
            .apply(find_weighted_team_averages, span=span, context=context, cols=cols, include_groups=False)
            .add_prefix(prefix)
        )
        ewm_features.append(temp)

    # Concatenate EWM features back to main dataframe
    df = pd.concat([df] + ewm_features, axis=1)


    selected_columns = [column for column in df.columns if ('ewm' in column or 'lineup' in column)] + ['rest_days', 'recent_intensity', 'streak']
    game_features = df[['TEAM_ABBREVIATION', 'GAME_DATE', 'season', 'GAME_ID']+selected_columns].copy()

    game_features[selected_columns] = game_features.groupby(['TEAM_ABBREVIATION', 'season'])[selected_columns].shift(1)
    game_features = game_features.rename(columns={c: f"opp_{c}" for c in selected_columns})

    df['next_game_date'] =  df.groupby(['TEAM_ABBREVIATION', 'season'])['GAME_DATE'].shift(-1)
    df['next_opp'] = df.groupby(['TEAM_ABBREVIATION', 'season'])['MATCHUP'].shift(-1).str[-3:]


    result = df.merge(
        game_features,
        left_on=['next_game_date', 'next_opp'],
        right_on=['GAME_DATE', 'TEAM_ABBREVIATION'],
        how='left',
        suffixes=('', '_drop')
    )


    result = result.drop(columns=
    [
    'TEAM_ABBREVIATION_drop',
    'GAME_DATE_drop',
    'season_drop',
    'GAME_ID_drop',
    'next_opp',
    'next_game_date',
    ])
    df = result.copy()


    df["25_context_net_rating_difference"] = df["ewm25_context_netRating"] - df["opp_ewm25_context_netRating"]
    df["10_overall_net_rating_difference"] = df["ewm10_netRating"] - df["opp_ewm10_netRating"]
    df["5_context_net_rating_difference"] = df["ewm5_context_netRating"] - df["opp_ewm5_context_netRating"]
    df["25_overall_net_rating_difference"] = df["ewm25_netRating"] - df["opp_ewm25_netRating"]
    df["10_context_net_rating_difference"] = df["ewm10_context_netRating"] - df["opp_ewm10_context_netRating"]
    df["5_overall_net_rating_difference"] = df["ewm5_netRating"] - df["opp_ewm5_netRating"]
    df["context_season_lineup_difference"] = df['lineup_context_25_rolling_WNI'] - df['opp_lineup_context_25_rolling_WNI']
    df["context_month_lineup_difference"] = df['lineup_context_10_rolling_WNI'] - df['opp_lineup_context_10_rolling_WNI']
    df["context_recent_lineup_difference"] = df["lineup_context_5_rolling_WNI"] - df['opp_lineup_context_5_rolling_WNI']
    df["season_lineup_difference"] = df['lineup_25_rolling_WNI'] - df['opp_lineup_25_rolling_WNI']
    df["month_lineup_difference"] = df['lineup_10_rolling_WNI'] - df['opp_lineup_10_rolling_WNI']
    df["recent_lineup_difference"] = df["lineup_5_rolling_WNI"] - df['opp_lineup_5_rolling_WNI']
    df['rest_difference'] = df['rest_days'] - df['opp_rest_days']

    df[selected_columns] = df[selected_columns].astype(float)
    df = df.dropna(subset=selected_columns)
    df.reset_index(drop=True, inplace=True)

    future_X = df[df['target'].isna()]

    return future_X
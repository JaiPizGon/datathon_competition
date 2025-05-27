# Configuration settings for the Datathon Hub application

# Default maximum number of members per team
MAX_TEAM_SIZE = 4

# Add other global configurations here as needed
# Example:
# DEFAULT_COMPETITION_TYPE = "Regression"
# ALLOWED_FILE_TYPES = ['csv', 'txt']

# Leaderboard Display Configuration
DECIMAL_FORMAT = "{:.4f}" # For formatting scores in the leaderboard

PRIMARY_METRICS = {
    "regression": "R²",  # Or "MSE", "MAE" - R² is common for higher-is-better
    "classification": "F1-Score", # Or "Accuracy", "Precision", "Recall"
    "forecasting": "MAPE (%)",    # Or "RMSE" - MAPE is often preferred for interpretability
    "sarima": "MAPE (%) (SARIMA)" # Or "RMSE (SARIMA)"
}

# Defines sort order for the primary metric (True = Ascending, False = Descending)
PRIMARY_METRIC_SORT_ASCENDING = {
    "R²": False,          # Higher R² is better
    "F1-Score": False,    # Higher F1-Score is better
    "MAPE (%)": True,     # Lower MAPE is better
    "MAPE (%) (SARIMA)": True, # Lower MAPE is better
    "MSE": True,          # Lower MSE is better
    "MAE": True,          # Lower MAE is better
    "RMSE": True,         # Lower RMSE is better
    "RMSE (SARIMA)": True # Lower RMSE is better
    # Add other metrics if they can be chosen as primary
}

# Ensure the metric names used as keys in PRIMARY_METRIC_SORT_ASCENDING
# exactly match the values provided in PRIMARY_METRICS and the keys in the
# dictionaries returned by the metrics calculation functions in metrics.py.

# --- Teacher Admin Authentication ---
# IMPORTANT: Change this to a strong, unique, random token in your actual deployment!
# This token is used for the Teacher Admin Dashboard login.
TEACHER_ADMIN_TOKEN = "replace_this_with_a_very_secure_random_string"

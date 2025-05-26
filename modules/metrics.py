import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, precision_score, recall_score, f1_score

def calculate_regression_metrics(y_true_df: pd.DataFrame, y_pred_df: pd.DataFrame, target_col: str, pred_col: str) -> dict | None:
    """Calculates regression metrics: MSE, MAE, R-squared."""
    try:
        y_true = y_true_df[target_col]
        y_pred = y_pred_df[pred_col]

        if len(y_true) != len(y_pred):
            # st.error("True values and predictions have different lengths.") # Cannot use st here
            print("Error: True values and predictions have different lengths.")
            return None
        if y_true.isnull().any() or y_pred.isnull().any():
            # st.warning("Data contains NaN values. Metrics might be affected or fail. Attempting to drop NaNs for calculation.")
            print("Warning: Data contains NaN values. Metrics might be affected or fail. Attempting to drop NaNs for calculation.")
            combined = pd.DataFrame({'true': y_true, 'pred': y_pred}).dropna()
            y_true = combined['true']
            y_pred = combined['pred']
            if combined.empty:
                print("Error: All data removed after dropping NaNs. Cannot calculate metrics.")
                return None


        mse = mean_squared_error(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        return {"MSE": mse, "MAE": mae, "R²": r2}
    except KeyError as e:
        # st.error(f"Column not found: {e}. Ensure target column is '{target_col}' and prediction column is '{pred_col}'.")
        print(f"KeyError: Column not found: {e}. Ensure target column is '{target_col}' and prediction column is '{pred_col}'.")
        return None
    except Exception as e:
        # st.error(f"An error occurred during regression metrics calculation: {e}")
        print(f"An error occurred during regression metrics calculation: {e}")
        return None

def calculate_classification_metrics(y_true_df: pd.DataFrame, y_pred_df: pd.DataFrame, target_col: str, pred_col: str) -> dict | None:
    """Calculates classification metrics: Accuracy, Precision, Recall, F1-score."""
    try:
        y_true = y_true_df[target_col]
        y_pred = y_pred_df[pred_col]

        if len(y_true) != len(y_pred):
            print("Error: True values and predictions have different lengths.")
            return None
        # Basic check for NaNs, though classification metrics might handle them or require specific preprocessing.
        if y_true.isnull().any() or y_pred.isnull().any():
            print("Warning: Data contains NaN values. Metrics might be affected or fail. Attempting to drop NaNs for calculation.")
            combined = pd.DataFrame({'true': y_true, 'pred': y_pred}).dropna()
            y_true = combined['true']
            y_pred = combined['pred']
            if combined.empty:
                print("Error: All data removed after dropping NaNs. Cannot calculate metrics.")
                return None

        # Determine average method for multiclass precision, recall, f1
        # If binary or only a few unique values, can use 'binary' or 'micro'/'macro'/'weighted'
        # For simplicity, using 'weighted' for multi-class, auto-adjusts for binary.
        num_classes = y_true.nunique()
        average_method = 'binary' if num_classes == 2 else 'weighted'
        
        accuracy = accuracy_score(y_true, y_pred)
        # Specify zero_division=0 to return 0 instead of warning for ill-defined precision/recall
        precision = precision_score(y_true, y_pred, average=average_method, zero_division=0)
        recall = recall_score(y_true, y_pred, average=average_method, zero_division=0)
        f1 = f1_score(y_true, y_pred, average=average_method, zero_division=0)
        
        return {"Accuracy": accuracy, "Precision": precision, "Recall": recall, "F1-Score": f1}
    except KeyError as e:
        print(f"KeyError: Column not found: {e}. Ensure target column is '{target_col}' and prediction column is '{pred_col}'.")
        return None
    except Exception as e:
        print(f"An error occurred during classification metrics calculation: {e}")
        return None

def calculate_forecasting_metrics(y_true_df: pd.DataFrame, y_pred_df: pd.DataFrame, target_col: str, pred_col: str) -> dict | None:
    """Calculates forecasting metrics: RMSE, MAPE."""
    try:
        y_true = y_true_df[target_col]
        y_pred = y_pred_df[pred_col]

        if len(y_true) != len(y_pred):
            print("Error: True values and predictions have different lengths.")
            return None
        if y_true.isnull().any() or y_pred.isnull().any():
            print("Warning: Data contains NaN values. Metrics might be affected or fail. Attempting to drop NaNs for calculation.")
            combined = pd.DataFrame({'true': y_true, 'pred': y_pred}).dropna()
            y_true = combined['true']
            y_pred = combined['pred']
            if combined.empty:
                print("Error: All data removed after dropping NaNs. Cannot calculate metrics.")
                return None
        
        # Avoid division by zero for MAPE if y_true contains 0.
        # Replace 0 with a very small number, or handle as per specific requirements.
        # For now, we'll calculate MAPE carefully.
        y_true_mape = y_true.replace(0, np.finfo(float).eps) # Replace 0 with a tiny number for MAPE calculation
        mape = np.mean(np.abs((y_true - y_pred) / y_true_mape)) * 100
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        
        return {"RMSE": rmse, "MAPE (%)": mape}
    except KeyError as e:
        print(f"KeyError: Column not found: {e}. Ensure target column is '{target_col}' and prediction column is '{pred_col}'.")
        return None
    except Exception as e:
        print(f"An error occurred during forecasting metrics calculation: {e}")
        return None

def calculate_sarima_metrics(y_true_df: pd.DataFrame, y_pred_df: pd.DataFrame, target_col: str, pred_col: str) -> dict | None:
    """
    Calculates SARIMA-related metrics: MAPE.
    AIC and BIC typically require the fitted model object, which is not available here.
    So, this function will be similar to forecasting_metrics for now.
    """
    # For now, SARIMA will use the same core forecasting metrics (RMSE, MAPE)
    # as AIC/BIC require model parameters not available from just true/pred values.
    # This can be expanded if model objects or their summaries become available.
    metrics = calculate_forecasting_metrics(y_true_df, y_pred_df, target_col, pred_col)
    if metrics:
        # Potentially rename or add specific SARIMA context if needed in future
        # For now, just returning what calculate_forecasting_metrics provides
        return {"RMSE (SARIMA)": metrics.get("RMSE"), "MAPE (%) (SARIMA)": metrics.get("MAPE (%)")}
    return None

# Note: Streamlit components (st.error, st.warning) are not used here as this is a backend module.
# Calling functions should handle presenting errors/warnings to the UI if needed.

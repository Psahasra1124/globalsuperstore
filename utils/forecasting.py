import numpy as np
import pandas as pd


def _design_matrix(periods, origin):
    month = periods.month.to_numpy()
    trend = (periods.year.to_numpy() - origin.year) * 12 + month - origin.month
    seasonal = np.column_stack([(month == value).astype(float) for value in range(2, 13)])
    return np.column_stack([np.ones(len(periods)), trend, seasonal])


def _fit_predict(history, periods):
    origin = history.index[0]
    matrix = _design_matrix(history.index, origin)
    coefficients, _, _, _ = np.linalg.lstsq(matrix, history.to_numpy(dtype=float), rcond=None)
    predictions = _design_matrix(periods, origin) @ coefficients
    return pd.Series(np.maximum(predictions, 0), index=periods)


def forecast_monthly_sales(df, horizon=3):
    if horizon not in (3, 6):
        raise ValueError("Forecast horizon must be 3 or 6 months.")
    if df.empty or "Order Date" not in df.columns or "Sales" not in df.columns:
        return {"error": "Insufficient filtered data to forecast monthly sales."}

    monthly_sales = df.set_index("Order Date")["Sales"].resample("MS").sum()
    if len(monthly_sales) < 18:
        return {
            "error": (
                "At least 18 consecutive months are needed for a seasonal forecast; "
                f"the filtered dataset contains {len(monthly_sales)}."
            )
        }

    holdout = min(6, max(3, len(monthly_sales) // 5))
    training = monthly_sales.iloc[:-holdout]
    validation = monthly_sales.iloc[-holdout:]
    validation_predictions = _fit_predict(training, validation.index)
    errors = validation.to_numpy() - validation_predictions.to_numpy()
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    denominator = np.abs(validation.to_numpy()) + np.abs(validation_predictions.to_numpy())
    smape = float(
        np.mean(
            np.divide(
                200 * np.abs(errors),
                denominator,
                out=np.zeros_like(errors, dtype=float),
                where=denominator != 0,
            )
        )
    )

    full_forecast = _fit_predict(monthly_sales, monthly_sales.index)
    future_periods = pd.date_range(
        monthly_sales.index[-1] + pd.offsets.MonthBegin(1),
        periods=horizon,
        freq="MS",
    )
    future = _fit_predict(monthly_sales, future_periods)
    history = pd.DataFrame(
        {
            "Period": monthly_sales.index,
            "Actual Sales": monthly_sales.to_numpy(),
            "Backtest Forecast": np.where(
                monthly_sales.index.isin(validation.index),
                validation_predictions.reindex(monthly_sales.index).to_numpy(),
                np.nan,
            ),
            "Model Fit": full_forecast.reindex(monthly_sales.index).to_numpy(),
        }
    )
    projection = pd.DataFrame(
        {"Period": future.index, "Forecast Sales": future.to_numpy()}
    )
    return {
        "history": history,
        "future": projection,
        "metrics": {"MAE": mae, "RMSE": rmse, "sMAPE": smape},
        "training_months": len(training),
        "holdout_months": holdout,
        "model": "Additive linear trend with monthly seasonality",
    }

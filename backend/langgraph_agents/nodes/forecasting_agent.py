"""
Forecasting Agent Node

This agent specializes in:
- Time series forecasting using Prophet
- Trend decomposition (trend, seasonality, residuals)
- Multi-period forecasts with confidence intervals
- Scenario analysis and what-if predictions

Uses Facebook Prophet for robust time series forecasting combined with GPT-5 for insights.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from openai import AsyncOpenAI

from ..state import AgentState
from ..tools.analytics_tools import analyze_trend, simple_moving_average, exponential_moving_average, forecast_naive
# from ..tools.storage_tools import get_uploaded_file_data  # TODO: Implement this function
from ..governance_wrapper import governed_node

logger = logging.getLogger(__name__)

# Initialize Requesty AI client for GPT-5
client = AsyncOpenAI(
    api_key="",  # Will be set from env
    base_url="https://api.requesty.ai/v1",
)

# Try to import Prophet (will be added to requirements)
try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet not available. Using fallback forecasting methods.")


async def _forecast_with_prophet(
    df: pd.DataFrame, date_column: str, value_column: str, periods: int = 30
) -> Dict[str, Any]:
    """
    Forecast using Facebook Prophet.

    Args:
        df: DataFrame with time series data
        date_column: Name of date column
        value_column: Name of value column
        periods: Number of periods to forecast

    Returns:
        dict: Forecast results with predictions and confidence intervals
    """
    if not PROPHET_AVAILABLE:
        return {"error": "Prophet library not installed"}

    try:
        # Prepare data for Prophet (requires 'ds' and 'y' columns)
        prophet_df = pd.DataFrame({"ds": pd.to_datetime(df[date_column]), "y": df[value_column]})

        # Remove duplicates and sort
        prophet_df = prophet_df.drop_duplicates(subset=["ds"]).sort_values("ds")

        # Initialize Prophet model
        model = Prophet(
            yearly_seasonality="auto",
            weekly_seasonality="auto",
            daily_seasonality=False,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.05,  # Flexibility of trend
        )

        # Fit model
        model.fit(prophet_df)

        # Create future dataframe
        future = model.make_future_dataframe(periods=periods)

        # Make predictions
        forecast = model.predict(future)

        # Extract relevant columns
        forecast_results = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)

        # Calculate MAPE (Mean Absolute Percentage Error) on historical data
        historical_forecast = forecast[["ds", "yhat"]].head(len(prophet_df))
        merged = prophet_df.merge(historical_forecast, on="ds", how="inner")
        mape = np.mean(np.abs((merged["y"] - merged["yhat"]) / merged["y"])) * 100

        # Determine accuracy level
        if mape < 10:
            accuracy = "Excellent"
        elif mape < 20:
            accuracy = "Good"
        elif mape < 30:
            accuracy = "Fair"
        else:
            accuracy = "Poor"

        return {
            "method": "Prophet",
            "forecast_values": forecast_results["yhat"].tolist(),
            "lower_confidence": forecast_results["yhat_lower"].tolist(),
            "upper_confidence": forecast_results["yhat_upper"].tolist(),
            "forecast_dates": forecast_results["ds"].dt.strftime("%Y-%m-%d").tolist(),
            "periods": periods,
            "mape": round(mape, 2),
            "accuracy": accuracy,
            "last_historical_value": float(prophet_df["y"].iloc[-1]),
            "first_forecast_value": float(forecast_results["yhat"].iloc[0]),
            "last_forecast_value": float(forecast_results["yhat"].iloc[-1]),
        }

    except Exception as e:
        logger.error(f"Prophet forecasting error: {e}", exc_info=True)
        return {"error": str(e)}


@governed_node("forecasting_agent", "forecast")
async def forecasting_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Forecasting Agent - Predicts future values using time series analysis.

    Capabilities:
    1. Prophet-based forecasting (if available)
    2. Trend decomposition and analysis
    3. Moving average forecasts
    4. Confidence intervals and accuracy metrics
    5. Business interpretation of forecasts
    """
    logger.info("Forecasting Agent executing...")

    message = state["messages"][-1]
    user_query = message.content

    try:
        # Get uploaded file data if available
        file_info = state.get("file_info")
        df = None

        if file_info:
            file_id = file_info.get("file_id")
            if file_id:
                df = await get_uploaded_file_data(file_id)
                logger.info(f"Loaded file data: {len(df)} rows, {len(df.columns)} columns")

        if df is None or df.empty:
            response = (
                "I need time series data to create forecasts. "
                "Please upload a CSV or Excel file with:\n\n"
                "- **Date/Time column**: For time-based forecasting\n"
                "- **Value column**: The metric to forecast (sales, revenue, etc.)\n\n"
                "I can provide:\n"
                "- Future predictions with confidence intervals\n"
                "- Trend and seasonality analysis\n"
                "- Forecast accuracy metrics"
            )

            return {
                "messages": [{"role": "assistant", "content": response}],
                "next_agent": "supervisor",
            }

        # Identify date and value columns
        date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

        # Try to detect date columns stored as strings
        if not date_cols:
            for col in df.select_dtypes(include=["object"]).columns:
                try:
                    pd.to_datetime(df[col].head(10), errors="raise")
                    df[col] = pd.to_datetime(df[col])
                    date_cols.append(col)
                    break
                except:
                    continue

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not date_cols:
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "I need a date/time column to create forecasts. Please ensure your data includes a date column.",
                    }
                ],
                "next_agent": "supervisor",
            }

        if not numeric_cols:
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "I need numeric values to forecast. Please ensure your data includes numeric columns (sales, revenue, etc.).",
                    }
                ],
                "next_agent": "supervisor",
            }

        date_column = date_cols[0]

        # Find value column (prefer sales/revenue related)
        value_column = None
        for col in numeric_cols:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["sales", "revenue", "amount", "value", "total"]):
                value_column = col
                break

        if value_column is None:
            value_column = numeric_cols[0]

        # Determine forecast periods from query (default 30)
        periods = 30
        if "day" in user_query.lower():
            periods = 7
        elif "week" in user_query.lower():
            periods = 4
        elif "month" in user_query.lower():
            periods = 12
        elif "quarter" in user_query.lower():
            periods = 4
        elif "year" in user_query.lower():
            periods = 5

        # Extract number if specified (e.g., "forecast next 90 days")
        import re

        numbers = re.findall(r"\b(\d+)\b", user_query)
        if numbers:
            periods = int(numbers[0])

        logger.info(f"Forecasting {periods} periods for {value_column} using {date_column}")

        # Step 1: Trend analysis on historical data
        trend_analysis = analyze_trend(df, value_column=value_column, date_column=date_column)

        # Step 2: Generate forecast
        if PROPHET_AVAILABLE:
            forecast_results = await _forecast_with_prophet(df, date_column, value_column, periods)
        else:
            # Fallback to naive forecast
            forecast_results = forecast_naive(df, value_column, periods)

        if "error" in forecast_results:
            return {
                "messages": [
                    {"role": "assistant", "content": f"Error creating forecast: {forecast_results['error']}"}
                ],
                "next_agent": "supervisor",
            }

        # Step 3: Calculate moving averages for context
        df_sorted = df.sort_values(date_column).copy()
        sma_7 = simple_moving_average(df_sorted, value_column, window=7)
        ema_7 = exponential_moving_average(df_sorted, value_column, span=7)

        # Step 4: Generate insights using GPT-5
        system_prompt = """You are a forecasting analyst with expertise in time series analysis and business planning.

Your task is to:
1. Interpret the forecast results in business context
2. Explain the trend and its implications
3. Highlight key forecast insights
4. Provide actionable recommendations based on predictions
5. Discuss confidence levels and potential risks

Focus on:
- Business implications of the forecast
- Growth or decline patterns
- Seasonal effects (if present)
- Planning recommendations
- Risk factors and uncertainties
"""

        # Prepare context for GPT-5
        forecast_summary = f"""
User Query: {user_query}

Historical Data:
- Date Range: {df[date_column].min()} to {df[date_column].max()}
- Data Points: {len(df)}
- Metric: {value_column}
- Current Value: {df[value_column].iloc[-1]:.2f}

Trend Analysis:
- Direction: {trend_analysis['trend_direction']}
- Strength: {trend_analysis['trend_strength']}
- Statistical Significance: {'Yes' if trend_analysis['statistically_significant'] else 'No'}
- R²: {trend_analysis['r_squared']:.3f}

Forecast Results ({forecast_results['method']}):
- Periods: {forecast_results['periods']}
- Last Historical: {forecast_results.get('last_historical_value', df[value_column].iloc[-1]):.2f}
- First Forecast: {forecast_results['first_forecast_value']:.2f}
- Last Forecast: {forecast_results['last_forecast_value']:.2f}
"""

        if "mape" in forecast_results:
            forecast_summary += f"- Accuracy (MAPE): {forecast_results['mape']}% ({forecast_results['accuracy']})\n"

        # Calculate forecast change
        last_historical = forecast_results.get("last_historical_value", df[value_column].iloc[-1])
        last_forecast = forecast_results["last_forecast_value"]
        forecast_change = ((last_forecast - last_historical) / last_historical) * 100
        forecast_summary += f"- Projected Change: {forecast_change:+.1f}%\n"

        # Get GPT-5 insights
        response = await client.chat.completions.create(
            model="openai/gpt-5-chat-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": forecast_summary},
            ],
            temperature=0.2,
            seed=42,
        )

        insights = response.choices[0].message.content

        # Build response with forecast data
        final_response = f"""## Forecast Analysis: {value_column}

{insights}

---

**Forecast Summary**:
- Method: {forecast_results['method']}
- Periods: {forecast_results['periods']}
- Projected Change: {forecast_change:+.1f}%
"""

        if "mape" in forecast_results:
            final_response += f"- Forecast Accuracy: {forecast_results['accuracy']} (MAPE: {forecast_results['mape']}%)\n"

        final_response += f"\n**Historical Trend**: {trend_analysis['trend_direction']} ({trend_analysis['trend_strength']} strength)\n"

        # Store forecast results in metadata for potential charting
        metadata = {
            "agent": "forecasting",
            "agent_data": {
                "analysis_type": "forecast",
                "forecast_results": forecast_results,
                "trend_analysis": trend_analysis,
                "value_column": value_column,
                "date_column": date_column,
                "periods": periods,
            },
        }

        return {
            "messages": [{"role": "assistant", "content": final_response}],
            "metadata": metadata,
            "next_agent": "supervisor",
        }

    except Exception as e:
        logger.error(f"Error in forecasting agent: {e}", exc_info=True)
        error_response = (
            f"I encountered an error creating forecasts: {str(e)}\n\n"
            "Please ensure your data includes:\n"
            "- A date/time column for time series analysis\n"
            "- Numeric values to forecast (sales, revenue, etc.)\n"
            "- Sufficient historical data points (at least 10-20 observations)"
        )

        return {
            "messages": [{"role": "assistant", "content": error_response}],
            "next_agent": "supervisor",
        }
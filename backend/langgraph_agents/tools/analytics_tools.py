"""
Analytics Tools for Brand Performance, Forecasting, and Anomaly Detection

This module provides utilities for:
- Data quality assessment
- KPI calculation (growth rates, trends, market share)
- Statistical anomaly detection
- Trend analysis
- Forecasting utilities
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from scipy import stats
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DATA QUALITY ASSESSMENT
# ============================================================================

def assess_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Assess data quality of a DataFrame.

    Returns:
        dict: Quality metrics including completeness, consistency, and recommendations
    """
    total_cells = df.shape[0] * df.shape[1]
    missing_cells = df.isnull().sum().sum()

    quality_report = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "completeness_score": round((1 - missing_cells / total_cells) * 100, 2) if total_cells > 0 else 0,
        "missing_values": df.isnull().sum().to_dict(),
        "duplicate_rows": df.duplicated().sum(),
        "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
        "date_columns": df.select_dtypes(include=['datetime64']).columns.tolist(),
        "categorical_columns": df.select_dtypes(include=['object', 'category']).columns.tolist(),
    }

    # Add quality grade
    if quality_report["completeness_score"] >= 95:
        quality_report["grade"] = "Excellent"
    elif quality_report["completeness_score"] >= 80:
        quality_report["grade"] = "Good"
    elif quality_report["completeness_score"] >= 60:
        quality_report["grade"] = "Fair"
    else:
        quality_report["grade"] = "Poor"

    # Generate recommendations
    recommendations = []
    if missing_cells > 0:
        recommendations.append(f"Found {missing_cells} missing values - consider imputation or removal")
    if quality_report["duplicate_rows"] > 0:
        recommendations.append(f"Found {quality_report['duplicate_rows']} duplicate rows - consider deduplication")

    quality_report["recommendations"] = recommendations

    return quality_report


# ============================================================================
# KPI CALCULATION
# ============================================================================

def calculate_growth_rate(
    df: pd.DataFrame,
    value_column: str,
    date_column: Optional[str] = None,
    period: str = "month"
) -> Dict[str, Any]:
    """
    Calculate growth rates over time.

    Args:
        df: DataFrame with time series data
        value_column: Column containing values to analyze
        date_column: Column containing dates (auto-detected if None)
        period: Aggregation period ("day", "week", "month", "quarter", "year")

    Returns:
        dict: Growth metrics including rate, trend, and period comparisons
    """
    # Auto-detect date column if not provided
    if date_column is None:
        date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        if not date_cols:
            # Try to detect date columns stored as strings
            for col in df.select_dtypes(include=['object']).columns:
                try:
                    pd.to_datetime(df[col].head(), errors='raise')
                    date_column = col
                    df[col] = pd.to_datetime(df[col])
                    break
                except:
                    continue
        else:
            date_column = date_cols[0]

    if date_column is None:
        return {"error": "No date column found in data"}

    # Ensure date column is datetime
    if df[date_column].dtype != 'datetime64[ns]':
        df[date_column] = pd.to_datetime(df[date_column])

    # Sort by date
    df_sorted = df.sort_values(date_column).copy()

    # Aggregate by period
    period_map = {
        "day": "D",
        "week": "W",
        "month": "M",
        "quarter": "Q",
        "year": "Y"
    }

    freq = period_map.get(period, "M")
    df_sorted.set_index(date_column, inplace=True)
    aggregated = df_sorted[value_column].resample(freq).sum()

    # Calculate growth rates
    growth_rates = aggregated.pct_change() * 100

    # Calculate overall metrics
    if len(aggregated) > 1:
        overall_growth = ((aggregated.iloc[-1] - aggregated.iloc[0]) / aggregated.iloc[0]) * 100
        avg_growth_rate = growth_rates.mean()

        # Determine trend
        if avg_growth_rate > 5:
            trend = "Strong Growth"
        elif avg_growth_rate > 0:
            trend = "Moderate Growth"
        elif avg_growth_rate > -5:
            trend = "Slight Decline"
        else:
            trend = "Significant Decline"
    else:
        overall_growth = 0
        avg_growth_rate = 0
        trend = "Insufficient Data"

    return {
        "overall_growth_rate": round(overall_growth, 2),
        "average_period_growth": round(avg_growth_rate, 2),
        "trend": trend,
        "period": period,
        "periods_analyzed": len(aggregated),
        "latest_value": float(aggregated.iloc[-1]) if len(aggregated) > 0 else 0,
        "earliest_value": float(aggregated.iloc[0]) if len(aggregated) > 0 else 0,
        "period_values": aggregated.to_dict(),
        "period_growth_rates": growth_rates.dropna().to_dict()
    }


def calculate_market_share(
    df: pd.DataFrame,
    entity_column: str,
    value_column: str
) -> Dict[str, Any]:
    """
    Calculate market share for different entities.

    Args:
        df: DataFrame with entity and value data
        entity_column: Column containing entity names (brands, products, etc.)
        value_column: Column containing values (sales, revenue, etc.)

    Returns:
        dict: Market share analysis with percentages and rankings
    """
    # Aggregate by entity
    entity_totals = df.groupby(entity_column)[value_column].sum().sort_values(ascending=False)
    total = entity_totals.sum()

    # Calculate market share
    market_share = (entity_totals / total * 100).round(2)

    # Get top performers
    top_3 = market_share.head(3).to_dict()

    # Calculate concentration (HHI - Herfindahl-Hirschman Index)
    hhi = ((market_share / 100) ** 2).sum() * 10000

    # Determine market concentration
    if hhi > 2500:
        concentration = "Highly Concentrated"
    elif hhi > 1500:
        concentration = "Moderately Concentrated"
    else:
        concentration = "Competitive"

    return {
        "market_shares": market_share.to_dict(),
        "top_3_leaders": top_3,
        "market_leader": market_share.index[0] if len(market_share) > 0 else None,
        "leader_share": float(market_share.iloc[0]) if len(market_share) > 0 else 0,
        "hhi_index": round(hhi, 2),
        "market_concentration": concentration,
        "total_entities": len(entity_totals)
    }


def calculate_performance_metrics(
    df: pd.DataFrame,
    value_column: str,
    category_column: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate comprehensive performance metrics.

    Returns:
        dict: Statistical metrics including mean, median, std, min, max, percentiles
    """
    metrics = {
        "mean": float(df[value_column].mean()),
        "median": float(df[value_column].median()),
        "std_dev": float(df[value_column].std()),
        "min": float(df[value_column].min()),
        "max": float(df[value_column].max()),
        "q1": float(df[value_column].quantile(0.25)),
        "q3": float(df[value_column].quantile(0.75)),
        "total": float(df[value_column].sum()),
        "count": int(df[value_column].count())
    }

    # Add coefficient of variation (relative volatility)
    if metrics["mean"] != 0:
        metrics["coefficient_of_variation"] = round((metrics["std_dev"] / metrics["mean"]) * 100, 2)
    else:
        metrics["coefficient_of_variation"] = 0

    # Category-wise metrics if applicable
    if category_column and category_column in df.columns:
        category_metrics = df.groupby(category_column)[value_column].agg([
            'mean', 'median', 'sum', 'count'
        ]).to_dict('index')
        metrics["by_category"] = category_metrics

    return metrics


# ============================================================================
# ANOMALY DETECTION
# ============================================================================

def detect_outliers_iqr(
    df: pd.DataFrame,
    value_column: str,
    factor: float = 1.5
) -> Dict[str, Any]:
    """
    Detect outliers using Interquartile Range (IQR) method.

    Args:
        df: DataFrame with numeric data
        value_column: Column to analyze
        factor: IQR multiplier (default 1.5 for standard outliers)

    Returns:
        dict: Outlier analysis with indices, values, and bounds
    """
    Q1 = df[value_column].quantile(0.25)
    Q3 = df[value_column].quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - factor * IQR
    upper_bound = Q3 + factor * IQR

    # Find outliers
    outliers = df[(df[value_column] < lower_bound) | (df[value_column] > upper_bound)]

    return {
        "method": "IQR",
        "lower_bound": float(lower_bound),
        "upper_bound": float(upper_bound),
        "outlier_count": len(outliers),
        "outlier_percentage": round(len(outliers) / len(df) * 100, 2),
        "outlier_indices": outliers.index.tolist(),
        "outlier_values": outliers[value_column].tolist(),
        "q1": float(Q1),
        "q3": float(Q3),
        "iqr": float(IQR)
    }


def detect_outliers_zscore(
    df: pd.DataFrame,
    value_column: str,
    threshold: float = 3.0
) -> Dict[str, Any]:
    """
    Detect outliers using Z-score method.

    Args:
        df: DataFrame with numeric data
        value_column: Column to analyze
        threshold: Z-score threshold (default 3.0 for 99.7% confidence)

    Returns:
        dict: Outlier analysis with z-scores and identified anomalies
    """
    mean = df[value_column].mean()
    std = df[value_column].std()

    # Calculate z-scores
    z_scores = np.abs((df[value_column] - mean) / std)

    # Find outliers
    outliers = df[z_scores > threshold]
    outlier_z_scores = z_scores[z_scores > threshold]

    return {
        "method": "Z-Score",
        "threshold": threshold,
        "mean": float(mean),
        "std_dev": float(std),
        "outlier_count": len(outliers),
        "outlier_percentage": round(len(outliers) / len(df) * 100, 2),
        "outlier_indices": outliers.index.tolist(),
        "outlier_values": outliers[value_column].tolist(),
        "outlier_z_scores": outlier_z_scores.tolist(),
        "max_z_score": float(outlier_z_scores.max()) if len(outlier_z_scores) > 0 else 0
    }


def detect_anomalies_combined(
    df: pd.DataFrame,
    value_column: str,
    iqr_factor: float = 1.5,
    z_threshold: float = 3.0
) -> Dict[str, Any]:
    """
    Detect anomalies using combined IQR and Z-score methods.

    Returns:
        dict: Comprehensive anomaly analysis using both methods
    """
    iqr_results = detect_outliers_iqr(df, value_column, iqr_factor)
    zscore_results = detect_outliers_zscore(df, value_column, z_threshold)

    # Find consensus outliers (detected by both methods)
    iqr_set = set(iqr_results["outlier_indices"])
    zscore_set = set(zscore_results["outlier_indices"])
    consensus_outliers = list(iqr_set.intersection(zscore_set))

    return {
        "iqr_method": iqr_results,
        "zscore_method": zscore_results,
        "consensus_outliers": consensus_outliers,
        "consensus_count": len(consensus_outliers),
        "total_anomalies": len(iqr_set.union(zscore_set)),
        "confidence": "High" if len(consensus_outliers) > 0 else "Medium"
    }


# ============================================================================
# TREND ANALYSIS
# ============================================================================

def analyze_trend(
    df: pd.DataFrame,
    value_column: str,
    date_column: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze trend using linear regression.

    Returns:
        dict: Trend analysis with slope, direction, strength, and forecast
    """
    # Auto-detect date column if not provided
    if date_column is None:
        date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        if not date_cols:
            for col in df.select_dtypes(include=['object']).columns:
                try:
                    pd.to_datetime(df[col].head(), errors='raise')
                    date_column = col
                    df[col] = pd.to_datetime(df[col])
                    break
                except:
                    continue
        else:
            date_column = date_cols[0]

    if date_column is None:
        return {"error": "No date column found in data"}

    # Ensure date column is datetime
    if df[date_column].dtype != 'datetime64[ns]':
        df[date_column] = pd.to_datetime(df[date_column])

    # Sort by date
    df_sorted = df.sort_values(date_column).copy()

    # Convert dates to numeric (days since first date)
    df_sorted['days_from_start'] = (df_sorted[date_column] - df_sorted[date_column].min()).dt.days

    # Perform linear regression
    X = df_sorted['days_from_start'].values
    y = df_sorted[value_column].values

    slope, intercept, r_value, p_value, std_err = stats.linregress(X, y)

    # Determine trend direction and strength
    if slope > 0:
        direction = "Upward"
    elif slope < 0:
        direction = "Downward"
    else:
        direction = "Flat"

    # R-squared for trend strength
    r_squared = r_value ** 2
    if r_squared > 0.7:
        strength = "Strong"
    elif r_squared > 0.4:
        strength = "Moderate"
    else:
        strength = "Weak"

    # Statistical significance
    significant = p_value < 0.05

    return {
        "trend_direction": direction,
        "trend_strength": strength,
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_squared),
        "p_value": float(p_value),
        "statistically_significant": significant,
        "confidence": "High" if significant and r_squared > 0.5 else "Medium" if significant else "Low"
    }


# ============================================================================
# FORECASTING UTILITIES
# ============================================================================

def simple_moving_average(
    df: pd.DataFrame,
    value_column: str,
    window: int = 7
) -> pd.Series:
    """
    Calculate simple moving average.

    Args:
        df: DataFrame with time series data
        value_column: Column to calculate SMA for
        window: Rolling window size

    Returns:
        Series: Moving average values
    """
    return df[value_column].rolling(window=window, min_periods=1).mean()


def exponential_moving_average(
    df: pd.DataFrame,
    value_column: str,
    span: int = 7
) -> pd.Series:
    """
    Calculate exponential moving average.

    Args:
        df: DataFrame with time series data
        value_column: Column to calculate EMA for
        span: Span for exponential decay

    Returns:
        Series: Exponential moving average values
    """
    return df[value_column].ewm(span=span, adjust=False).mean()


def forecast_naive(
    df: pd.DataFrame,
    value_column: str,
    periods: int = 7
) -> Dict[str, Any]:
    """
    Simple naive forecast using last value and trend.

    Args:
        df: DataFrame with time series data
        value_column: Column to forecast
        periods: Number of periods to forecast

    Returns:
        dict: Forecast values and confidence intervals
    """
    values = df[value_column].values
    last_value = values[-1]

    # Calculate simple trend from last 7 values (or all if less than 7)
    trend_window = min(7, len(values))
    if trend_window > 1:
        recent_values = values[-trend_window:]
        trend = (recent_values[-1] - recent_values[0]) / (trend_window - 1)
    else:
        trend = 0

    # Generate forecast
    forecast = [last_value + trend * (i + 1) for i in range(periods)]

    # Simple confidence intervals (±10% of value)
    lower_bound = [v * 0.9 for v in forecast]
    upper_bound = [v * 1.1 for v in forecast]

    return {
        "forecast_values": forecast,
        "lower_confidence": lower_bound,
        "upper_confidence": upper_bound,
        "method": "Naive Trend",
        "periods": periods
    }
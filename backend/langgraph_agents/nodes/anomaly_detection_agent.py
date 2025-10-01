"""
Anomaly Detection Agent Node

This agent specializes in:
- Statistical outlier detection (IQR, Z-score)
- Machine learning-based anomaly detection (Isolation Forest, Local Outlier Factor)
- Time series anomaly detection
- Contextual anomaly analysis with business impact assessment

Uses multiple detection methods combined with GPT-5 for contextual interpretation.
"""

import logging
import os
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from openai import AsyncOpenAI

from ..state import AgentState
from ..tools.analytics_tools import detect_anomalies_combined, detect_outliers_iqr, detect_outliers_zscore
from ..tools.storage_tools import get_uploaded_file_data
from ..governance_wrapper import governed_node

logger = logging.getLogger(__name__)

# Initialize Requesty AI client for GPT-5
client = AsyncOpenAI(
    api_key=os.getenv("REQUESTY_AI_API_KEY", ""),
    base_url=os.getenv("REQUESTY_AI_API_BASE", "https://router.requesty.ai/v1"),
)

# Try to import scikit-learn for ML-based detection
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Using statistical methods only.")


def _detect_anomalies_isolation_forest(df: pd.DataFrame, value_column: str, contamination: float = 0.1) -> Dict[str, Any]:
    """
    Detect anomalies using Isolation Forest algorithm.

    Args:
        df: DataFrame with numeric data
        value_column: Column to analyze
        contamination: Expected proportion of outliers (default 0.1 = 10%)

    Returns:
        dict: Anomaly detection results
    """
    if not SKLEARN_AVAILABLE:
        return {"error": "scikit-learn not installed"}

    try:
        # Prepare data
        X = df[[value_column]].values

        # Fit Isolation Forest
        iso_forest = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)

        predictions = iso_forest.fit_predict(X)

        # -1 indicates anomaly, 1 indicates normal
        anomaly_indices = df.index[predictions == -1].tolist()
        anomaly_values = df.loc[anomaly_indices, value_column].tolist()

        # Get anomaly scores (lower is more anomalous)
        anomaly_scores = iso_forest.score_samples(X)
        anomaly_score_values = [anomaly_scores[i] for i in anomaly_indices]

        return {
            "method": "Isolation Forest",
            "anomaly_count": len(anomaly_indices),
            "anomaly_percentage": round(len(anomaly_indices) / len(df) * 100, 2),
            "anomaly_indices": anomaly_indices,
            "anomaly_values": anomaly_values,
            "anomaly_scores": anomaly_score_values,
            "contamination": contamination,
        }

    except Exception as e:
        logger.error(f"Isolation Forest error: {e}", exc_info=True)
        return {"error": str(e)}


def _detect_anomalies_lof(df: pd.DataFrame, value_column: str, n_neighbors: int = 20, contamination: float = 0.1) -> Dict[str, Any]:
    """
    Detect anomalies using Local Outlier Factor algorithm.

    Args:
        df: DataFrame with numeric data
        value_column: Column to analyze
        n_neighbors: Number of neighbors to consider
        contamination: Expected proportion of outliers

    Returns:
        dict: Anomaly detection results
    """
    if not SKLEARN_AVAILABLE:
        return {"error": "scikit-learn not installed"}

    try:
        # Prepare data
        X = df[[value_column]].values

        # Fit LOF
        lof = LocalOutlierFactor(n_neighbors=min(n_neighbors, len(df) - 1), contamination=contamination)

        predictions = lof.fit_predict(X)

        # -1 indicates anomaly, 1 indicates normal
        anomaly_indices = df.index[predictions == -1].tolist()
        anomaly_values = df.loc[anomaly_indices, value_column].tolist()

        # Get negative outlier factor scores
        lof_scores = lof.negative_outlier_factor_
        anomaly_score_values = [lof_scores[i] for i in anomaly_indices]

        return {
            "method": "Local Outlier Factor",
            "anomaly_count": len(anomaly_indices),
            "anomaly_percentage": round(len(anomaly_indices) / len(df) * 100, 2),
            "anomaly_indices": anomaly_indices,
            "anomaly_values": anomaly_values,
            "anomaly_scores": anomaly_score_values,
            "n_neighbors": n_neighbors,
            "contamination": contamination,
        }

    except Exception as e:
        logger.error(f"LOF error: {e}", exc_info=True)
        return {"error": str(e)}


@governed_node("anomaly_detection_agent", "detect_anomalies")
async def anomaly_detection_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Anomaly Detection Agent - Identifies outliers and anomalies in data.

    Capabilities:
    1. Statistical methods (IQR, Z-score)
    2. Machine learning methods (Isolation Forest, LOF)
    3. Consensus anomaly detection
    4. Contextual analysis and impact assessment
    5. Business interpretation of anomalies
    """
    logger.info("Anomaly Detection Agent executing...")

    message = state["messages"][-1]
    user_query = message.content

    try:
        # Get uploaded file data if available
        uploaded_files = state.get("uploaded_files", [])
        df = None

        if uploaded_files:
            # Get database session from state (should be added by graph)
            from core.database import get_db
            async for db_session in get_db():
                file_data_dict = await get_uploaded_file_data(uploaded_files, db_session)
                if file_data_dict:
                    # Get the first file's DataFrame
                    df = next(iter(file_data_dict.values()))
                    logger.info(f"Loaded file data: {len(df)} rows, {len(df.columns)} columns")
                break

        if df is None or df.empty:
            response = (
                "I need data to detect anomalies and outliers. "
                "Please upload a CSV or Excel file with numeric data.\n\n"
                "I can detect:\n"
                "- Statistical outliers (IQR, Z-score methods)\n"
                "- Machine learning-based anomalies (Isolation Forest, LOF)\n"
                "- Contextual anomalies with business impact\n\n"
                "Useful for:\n"
                "- Quality control\n"
                "- Fraud detection\n"
                "- Performance monitoring\n"
                "- Data validation"
            )

            return {
                "messages": [{"role": "assistant", "content": response}],
                "agent_response": response,
                "next_agent": "supervisor",
            }

        # Identify numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not numeric_cols:
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "I need numeric data to detect anomalies. Please ensure your file contains numeric columns.",
                    }
                ],
                "next_agent": "supervisor",
            }

        # Find value column (prefer sales/revenue/amount related)
        value_column = None
        for col in numeric_cols:
            col_lower = col.lower()
            if any(
                keyword in col_lower
                for keyword in ["sales", "revenue", "amount", "value", "total", "price", "cost", "quantity"]
            ):
                value_column = col
                break

        if value_column is None:
            value_column = numeric_cols[0]

        logger.info(f"Analyzing anomalies in column: {value_column}")

        # Step 1: Statistical anomaly detection
        statistical_results = detect_anomalies_combined(df, value_column)

        # Step 2: ML-based anomaly detection (if available)
        ml_results = {}
        if SKLEARN_AVAILABLE and len(df) >= 10:  # Need sufficient data for ML methods
            iso_forest_results = _detect_anomalies_isolation_forest(df, value_column, contamination=0.1)
            if "error" not in iso_forest_results:
                ml_results["isolation_forest"] = iso_forest_results

            lof_results = _detect_anomalies_lof(df, value_column, n_neighbors=min(20, len(df) - 1), contamination=0.1)
            if "error" not in lof_results:
                ml_results["local_outlier_factor"] = lof_results

        # Step 3: Combine all methods to find high-confidence anomalies
        all_anomaly_indices = set()

        # Add statistical anomalies
        all_anomaly_indices.update(statistical_results["consensus_outliers"])

        # Add ML-based anomalies
        if "isolation_forest" in ml_results:
            all_anomaly_indices.update(ml_results["isolation_forest"]["anomaly_indices"])
        if "local_outlier_factor" in ml_results:
            all_anomaly_indices.update(ml_results["local_outlier_factor"]["anomaly_indices"])

        # Calculate consensus (detected by multiple methods)
        detection_count = {}
        for idx in all_anomaly_indices:
            count = 0
            if idx in statistical_results["consensus_outliers"]:
                count += 1
            if "isolation_forest" in ml_results and idx in ml_results["isolation_forest"]["anomaly_indices"]:
                count += 1
            if "local_outlier_factor" in ml_results and idx in ml_results["local_outlier_factor"]["anomaly_indices"]:
                count += 1
            detection_count[idx] = count

        # High-confidence anomalies (detected by 2+ methods)
        high_confidence_anomalies = [idx for idx, count in detection_count.items() if count >= 2]

        # Get anomaly details
        if high_confidence_anomalies:
            anomaly_details = df.loc[high_confidence_anomalies, [value_column]].copy()
            anomaly_details["detection_count"] = [detection_count[idx] for idx in high_confidence_anomalies]
            anomaly_details = anomaly_details.sort_values("detection_count", ascending=False)
        else:
            anomaly_details = None

        # Step 4: Statistical summary
        mean = df[value_column].mean()
        std = df[value_column].std()
        median = df[value_column].median()

        # Step 5: Generate insights using GPT-5
        system_prompt = """You are an anomaly detection specialist with expertise in data quality and business impact analysis.

Your task is to:
1. Interpret the anomaly detection results
2. Explain what makes these values anomalous
3. Assess potential business impact and root causes
4. Provide actionable recommendations
5. Distinguish between legitimate outliers and data errors

Focus on:
- Business context and implications
- Potential causes (data errors, fraud, exceptional events, etc.)
- Risk assessment
- Recommended actions
- Data quality considerations
"""

        # Prepare context for GPT-5
        anomaly_summary = f"""
User Query: {user_query}

Data Overview:
- Total Records: {len(df)}
- Analyzed Column: {value_column}
- Mean: {mean:.2f}
- Median: {median:.2f}
- Std Dev: {std:.2f}

Detection Results:

Statistical Methods:
- IQR Method: {statistical_results['iqr_method']['outlier_count']} anomalies ({statistical_results['iqr_method']['outlier_percentage']}%)
- Z-Score Method: {statistical_results['zscore_method']['outlier_count']} anomalies ({statistical_results['zscore_method']['outlier_percentage']}%)
- Consensus: {len(statistical_results['consensus_outliers'])} anomalies
"""

        if ml_results:
            anomaly_summary += "\nMachine Learning Methods:\n"
            if "isolation_forest" in ml_results:
                anomaly_summary += f"- Isolation Forest: {ml_results['isolation_forest']['anomaly_count']} anomalies ({ml_results['isolation_forest']['anomaly_percentage']}%)\n"
            if "local_outlier_factor" in ml_results:
                anomaly_summary += f"- Local Outlier Factor: {ml_results['local_outlier_factor']['anomaly_count']} anomalies ({ml_results['local_outlier_factor']['anomaly_percentage']}%)\n"

        anomaly_summary += f"""
High-Confidence Anomalies (2+ methods): {len(high_confidence_anomalies)}
Total Unique Anomalies: {len(all_anomaly_indices)}
"""

        if anomaly_details is not None and len(anomaly_details) > 0:
            anomaly_summary += f"\nTop Anomalies:\n"
            for idx, row in anomaly_details.head(5).iterrows():
                anomaly_summary += f"- Index {idx}: {row[value_column]:.2f} (detected by {int(row['detection_count'])} methods)\n"

        # Get GPT-5 insights
        response = await client.chat.completions.create(
            model="openai/gpt-5-chat-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": anomaly_summary},
            ],
            temperature=0.2,
            seed=42,
        )

        insights = response.choices[0].message.content

        # Build response
        final_response = f"""## Anomaly Detection Analysis: {value_column}

{insights}

---

**Detection Summary**:
- Total Records: {len(df)}
- High-Confidence Anomalies: {len(high_confidence_anomalies)} ({round(len(high_confidence_anomalies)/len(df)*100, 2)}%)
- Total Anomalies: {len(all_anomaly_indices)} ({round(len(all_anomaly_indices)/len(df)*100, 2)}%)

**Methods Used**:
- Statistical: IQR + Z-Score
"""

        if ml_results:
            final_response += "- Machine Learning: Isolation Forest + Local Outlier Factor\n"

        final_response += f"\n**Data Statistics**:\n- Mean: {mean:.2f}\n- Median: {median:.2f}\n- Std Dev: {std:.2f}\n"

        # Store results in metadata
        metadata = {
            "agent": "anomaly_detection",
            "agent_data": {
                "analysis_type": "anomaly_detection",
                "value_column": value_column,
                "total_records": len(df),
                "total_anomalies": len(all_anomaly_indices),
                "high_confidence_anomalies": len(high_confidence_anomalies),
                "anomaly_percentage": round(len(all_anomaly_indices) / len(df) * 100, 2),
                "statistical_results": statistical_results,
                "ml_results": ml_results if ml_results else None,
                "anomaly_indices": list(all_anomaly_indices),
                "high_confidence_indices": high_confidence_anomalies,
            },
        }

        return {
            "messages": [{"role": "assistant", "content": final_response}],
            "agent_response": final_response,
            "metadata": metadata,
            "next_agent": "supervisor",
        }

    except Exception as e:
        logger.error(f"Error in anomaly detection agent: {e}", exc_info=True)
        error_response = (
            f"I encountered an error detecting anomalies: {str(e)}\n\n"
            "Please ensure your data includes:\n"
            "- Numeric columns for analysis\n"
            "- Sufficient data points (at least 10-20 observations)\n"
            "- Clean data without too many missing values"
        )

        return {
            "messages": [{"role": "assistant", "content": error_response}],
            "agent_response": error_response,
            "next_agent": "supervisor",
        }
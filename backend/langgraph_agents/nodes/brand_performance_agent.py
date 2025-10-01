"""
Brand Performance Agent Node

This agent specializes in:
- Data quality assessment and validation
- KPI calculation and tracking (growth rates, market share, performance metrics)
- Business insights and recommendations
- Performance trend analysis

Uses GPT-5 for business context interpretation combined with statistical analytics.
"""

import logging
from typing import Dict, Any
from openai import AsyncOpenAI

from ..state import AgentState
from ..tools.analytics_tools import (
    assess_data_quality,
    calculate_growth_rate,
    calculate_market_share,
    calculate_performance_metrics,
    analyze_trend,
)
# from ..tools.storage_tools import get_uploaded_file_data  # TODO: Implement this function
from ..governance_wrapper import governed_node

logger = logging.getLogger(__name__)

# Initialize Requesty AI client for GPT-5
client = AsyncOpenAI(
    api_key="",  # Will be set from env
    base_url="https://api.requesty.ai/v1",
)


@governed_node("brand_performance_agent", "analyze_performance")
async def brand_performance_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Brand Performance Agent - Analyzes brand/product performance with KPIs and insights.

    Capabilities:
    1. Data quality assessment
    2. KPI calculation (growth rates, market share, trends)
    3. Performance benchmarking
    4. Business insights generation
    """
    logger.info("Brand Performance Agent executing...")

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
            # No data to analyze
            response = (
                "I need data to perform brand performance analysis. "
                "Please upload a CSV or Excel file containing your brand performance data. "
                "\n\nExpected data format:\n"
                "- Date/Time column for trend analysis\n"
                "- Brand/Product column for comparison\n"
                "- Performance metrics (sales, revenue, units, etc.)"
            )

            return {
                "messages": [{"role": "assistant", "content": response}],
                "next_agent": "supervisor",
            }

        # Step 1: Assess data quality
        quality_report = assess_data_quality(df)
        logger.info(f"Data quality: {quality_report['grade']} ({quality_report['completeness_score']}%)")

        # Step 2: Identify key columns for analysis
        numeric_cols = quality_report["numeric_columns"]
        categorical_cols = quality_report["categorical_columns"]
        date_cols = quality_report["date_columns"]

        # Try to identify main value column (sales, revenue, etc.)
        value_column = None
        for col in numeric_cols:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["sales", "revenue", "amount", "value", "total"]):
                value_column = col
                break

        if value_column is None and len(numeric_cols) > 0:
            value_column = numeric_cols[0]  # Use first numeric column

        # Try to identify brand/product column
        entity_column = None
        for col in categorical_cols:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["brand", "product", "name", "category"]):
                entity_column = col
                break

        if entity_column is None and len(categorical_cols) > 0:
            entity_column = categorical_cols[0]  # Use first categorical column

        # Step 3: Calculate KPIs
        analysis_results = {
            "data_quality": quality_report,
        }

        if value_column:
            # Growth rate analysis (if date column exists)
            if len(date_cols) > 0:
                growth_analysis = calculate_growth_rate(
                    df, value_column=value_column, date_column=date_cols[0], period="month"
                )
                analysis_results["growth_analysis"] = growth_analysis

                # Trend analysis
                trend_analysis = analyze_trend(df, value_column=value_column, date_column=date_cols[0])
                analysis_results["trend_analysis"] = trend_analysis

            # Market share analysis (if entity column exists)
            if entity_column:
                market_share = calculate_market_share(df, entity_column=entity_column, value_column=value_column)
                analysis_results["market_share"] = market_share

            # Overall performance metrics
            performance_metrics = calculate_performance_metrics(
                df, value_column=value_column, category_column=entity_column if entity_column else None
            )
            analysis_results["performance_metrics"] = performance_metrics

        # Step 4: Generate business insights using GPT-5
        system_prompt = """You are a brand performance analyst with expertise in business intelligence and KPI analysis.

Your task is to:
1. Interpret the statistical analysis results
2. Provide clear, actionable business insights
3. Highlight key findings and trends
4. Make data-driven recommendations
5. Use business language (avoid technical jargon)

Focus on:
- Growth opportunities
- Performance trends
- Competitive positioning
- Areas of concern
- Strategic recommendations
"""

        # Prepare context for GPT-5
        analysis_summary = f"""
User Query: {user_query}

Data Overview:
- Dataset: {quality_report['total_rows']} rows, {quality_report['total_columns']} columns
- Quality: {quality_report['grade']} ({quality_report['completeness_score']}% complete)
- Analysis Column: {value_column if value_column else 'N/A'}
- Entity Column: {entity_column if entity_column else 'N/A'}

"""

        if "growth_analysis" in analysis_results:
            ga = analysis_results["growth_analysis"]
            analysis_summary += f"""
Growth Analysis:
- Overall Growth: {ga['overall_growth_rate']}%
- Average Period Growth: {ga['average_period_growth']}%
- Trend: {ga['trend']}
- Latest Value: {ga['latest_value']}
- Earliest Value: {ga['earliest_value']}
"""

        if "trend_analysis" in analysis_results:
            ta = analysis_results["trend_analysis"]
            analysis_summary += f"""
Trend Analysis:
- Direction: {ta['trend_direction']}
- Strength: {ta['trend_strength']}
- R²: {ta['r_squared']}
- Statistical Significance: {ta['statistically_significant']}
- Confidence: {ta['confidence']}
"""

        if "market_share" in analysis_results:
            ms = analysis_results["market_share"]
            analysis_summary += f"""
Market Share Analysis:
- Market Leader: {ms['market_leader']} ({ms['leader_share']}%)
- Top 3: {ms['top_3_leaders']}
- Market Concentration: {ms['market_concentration']} (HHI: {ms['hhi_index']})
- Total Entities: {ms['total_entities']}
"""

        if "performance_metrics" in analysis_results:
            pm = analysis_results["performance_metrics"]
            analysis_summary += f"""
Performance Metrics:
- Mean: {pm['mean']:.2f}
- Median: {pm['median']:.2f}
- Std Dev: {pm['std_dev']:.2f}
- Range: {pm['min']:.2f} - {pm['max']:.2f}
- Coefficient of Variation: {pm['coefficient_of_variation']}%
- Total: {pm['total']:.2f}
"""

        # Get GPT-5 insights
        response = await client.chat.completions.create(
            model="openai/gpt-5-chat-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analysis_summary},
            ],
            temperature=0.2,  # Low temperature for consistent analysis
            seed=42,
        )

        insights = response.choices[0].message.content

        # Combine analysis with insights
        final_response = f"""## Brand Performance Analysis

{insights}

---

**Data Quality**: {quality_report['grade']} ({quality_report['completeness_score']}% complete)

"""

        # Add data quality recommendations if any
        if quality_report.get("recommendations"):
            final_response += "\n**Data Quality Notes**:\n"
            for rec in quality_report["recommendations"]:
                final_response += f"- {rec}\n"

        # Store analysis results in metadata
        metadata = {
            "agent": "brand_performance",
            "agent_data": {
                "analysis_type": "brand_performance",
                "kpis": analysis_results,
                "data_quality": quality_report["grade"],
                "value_column": value_column,
                "entity_column": entity_column,
            },
        }

        return {
            "messages": [{"role": "assistant", "content": final_response}],
            "metadata": metadata,
            "next_agent": "supervisor",
        }

    except Exception as e:
        logger.error(f"Error in brand performance agent: {e}", exc_info=True)
        error_response = (
            f"I encountered an error analyzing brand performance: {str(e)}\n\n"
            "Please ensure your data includes:\n"
            "- Numeric columns for metrics (sales, revenue, etc.)\n"
            "- Date/time column for trend analysis\n"
            "- Category column for brand/product comparison"
        )

        return {
            "messages": [{"role": "assistant", "content": error_response}],
            "next_agent": "supervisor",
        }
"""
Chart Tools - Chart generation utilities for LangGraph agents

Provides utilities for:
- Generating chart code with GPT-5
- Executing chart code safely
- Creating charts end-to-end
"""

from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import io
import base64
from openai import AsyncOpenAI
from core.config import settings
import numpy as np


def _analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze DataFrame to determine best chart type and data characteristics.

    Args:
        df: DataFrame to analyze

    Returns:
        Dict with analysis results
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()

    # Try to detect date columns that are stored as strings
    for col in categorical_cols[:]:
        if df[col].dtype == 'object':
            try:
                pd.to_datetime(df[col].head(10), errors='raise')
                date_cols.append(col)
                categorical_cols.remove(col)
            except:
                pass

    # Suggest chart type based on data structure
    suggested_chart = "bar"  # Default

    if len(date_cols) > 0 and len(numeric_cols) > 0:
        suggested_chart = "line"  # Time series
    elif len(categorical_cols) == 1 and len(numeric_cols) == 1:
        if len(df) > 20:
            suggested_chart = "bar"  # Many categories
        else:
            suggested_chart = "bar"  # Few categories, could also be pie
    elif len(categorical_cols) >= 1 and len(numeric_cols) >= 2:
        suggested_chart = "grouped_bar"  # Multiple series comparison
    elif len(numeric_cols) >= 2 and len(categorical_cols) == 0:
        suggested_chart = "scatter"  # Correlation analysis

    return {
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "date_columns": date_cols,
        "suggested_chart_type": suggested_chart,
        "total_rows": len(df),
        "total_columns": len(df.columns)
    }


async def generate_chart_code(
    user_query: str,
    df: pd.DataFrame,
    model: str = "openai/gpt-5-chat-latest",
) -> Optional[str]:
    """
    Generate Plotly chart code using GPT-5.

    Args:
        user_query: User's chart request
        df: DataFrame with data
        model: OpenAI model to use (default: gpt-5-chat-latest)

    Returns:
        Optional[str]: Python code to generate chart, or None if failed
    """
    try:
        client = AsyncOpenAI(
            api_key=settings.REQUESTY_AI_API_KEY,
            base_url=settings.REQUESTY_AI_API_BASE
        )

        # Prepare dataframe info
        dataframe_info = {
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample": df.head(5).to_string(),
            "rows": len(df),
        }

        # Analyze data to determine best chart type
        data_analysis = _analyze_dataframe(df)

        # Build system prompt with strict guidelines
        system_prompt = """You are an expert data visualization engineer who creates accurate, consistent charts.

Available imports in the execution environment:
- pd (pandas)
- go (plotly.graph_objects)
- px (plotly.express)
- df (the data DataFrame)

CRITICAL REQUIREMENTS:
1. ALWAYS use the SAME chart type for the SAME data pattern - be consistent
2. Choose chart types based on data structure, not random interpretation:
   - Time series data → Line chart or Area chart
   - Categories + Values → Bar chart (horizontal for long labels, vertical otherwise)
   - Part-to-whole relationships → Pie chart or Donut chart
   - Comparisons across groups → Grouped or Stacked bar chart
   - Distribution → Histogram or Box plot
   - Correlation between two variables → Scatter plot
   - Geographic data → Map visualization

3. Data preparation:
   - Clean column names (strip whitespace, handle special characters)
   - Convert numeric columns properly (handle strings like "$1,234" or "1.5K")
   - Sort time series by date chronologically
   - Aggregate data if there are duplicates
   - Handle missing values (dropna or fillna appropriately)

4. Chart styling:
   - Use clear, descriptive titles based on the data
   - Label axes with actual column names
   - Use consistent color schemes (Plotly default palette)
   - Add hover information showing all relevant data points
   - Make legends clear and positioned appropriately

5. Return a go.Figure object stored in variable 'fig'
6. Do NOT include any data loading code, imports, or print statements

The DataFrame is available as variable 'df'. Generate deterministic, reproducible code.
"""

        # Build enhanced user prompt with data analysis
        user_prompt = f"""Create a chart for this request: "{user_query}"

DataFrame information:
- Columns: {dataframe_info.get('columns', [])}
- Data types: {dataframe_info.get('dtypes', {})}
- Row count: {dataframe_info.get('rows', 0)}
- Sample data (first 5 rows):
{dataframe_info.get('sample', 'N/A')}

Data analysis:
- Numeric columns: {data_analysis['numeric_columns']}
- Categorical columns: {data_analysis['categorical_columns']}
- Date columns: {data_analysis['date_columns']}
- Suggested chart type: {data_analysis['suggested_chart_type']}

IMPORTANT:
1. Analyze the user's request to understand what relationship they want to see
2. Use the suggested chart type unless the request explicitly asks for something else
3. Ensure data is properly cleaned and sorted before plotting
4. Be consistent - same query should produce same chart type
5. Focus on accuracy - verify that x-axis and y-axis make sense for the data

Generate only the Python code (no explanations, no markdown, just pure Python code)."""

        # Call GPT-5 with very low temperature for consistency
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,  # Zero temperature for maximum consistency
            seed=42,  # Fixed seed for deterministic output
        )

        code = response.choices[0].message.content

        # Extract code from markdown if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return code

    except Exception as e:
        print(f"Error generating chart code: {e}")
        return None


async def execute_chart_code(
    code: str,
    df: pd.DataFrame,
) -> Tuple[Optional[go.Figure], Optional[str]]:
    """
    Execute chart generation code safely.

    Args:
        code: Python code to execute
        df: DataFrame to use in code

    Returns:
        Tuple[Optional[go.Figure], Optional[str]]: (Figure object, error message)
    """
    try:
        # Create execution namespace
        namespace = {
            "df": df,
            "pd": pd,
            "go": go,
            "px": px,
            "fig": None,
        }

        # Execute code
        exec(code, namespace)

        # Get figure
        fig = namespace.get("fig")

        if fig is None or not isinstance(fig, go.Figure):
            return None, "Code did not produce a valid Plotly figure"

        return fig, None

    except Exception as e:
        return None, f"Error executing chart code: {str(e)}"


async def create_chart(
    user_query: str,
    df: pd.DataFrame,
    model: str = "openai/gpt-5-chat-latest",
) -> Dict[str, Any]:
    """
    Create a chart end-to-end from user query.

    Args:
        user_query: User's chart request
        df: DataFrame with data
        model: OpenAI model to use

    Returns:
        Dict[str, Any]: Result with chart data or error
            {
                "success": bool,
                "chart_html": Optional[str],
                "chart_png": Optional[str],  # base64 encoded
                "error": Optional[str],
            }
    """
    # Generate code with improved data analysis
    code = await generate_chart_code(user_query, df, model)
    if code is None:
        return {
            "success": False,
            "chart_html": None,
            "chart_png": None,
            "error": "Failed to generate chart code",
        }

    # Execute code
    fig, error = await execute_chart_code(code, df)
    if error:
        return {
            "success": False,
            "chart_html": None,
            "chart_png": None,
            "error": error,
        }

    # Convert to HTML (interactive) - only the div, not full page
    chart_html = fig.to_html(
        include_plotlyjs="cdn",
        div_id="chart",
        full_html=False,  # Only return the div, not full HTML page
    )

    # Convert to PNG (downloadable) - base64 encoded
    try:
        chart_png_bytes = fig.to_image(format="png", width=1200, height=800)
        chart_png_base64 = base64.b64encode(chart_png_bytes).decode("utf-8")
    except Exception as e:
        print(f"Warning: Could not generate PNG: {e}")
        chart_png_base64 = None

    return {
        "success": True,
        "chart_html": chart_html,
        "chart_png": chart_png_base64,
        "error": None,
        "code": code,  # Include generated code for debugging
    }


def validate_dataframe_for_chart(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
    """
    Check if DataFrame is suitable for chart generation.

    Args:
        df: DataFrame to validate

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if df is None or df.empty:
        return False, "No data available"

    if len(df) < 2:
        return False, "Not enough data points (minimum 2 required)"

    if len(df.columns) < 1:
        return False, "No columns found in data"

    return True, None
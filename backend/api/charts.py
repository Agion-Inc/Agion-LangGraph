"""
Agent-Chat Charts API
Serve chart images as static files
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter()

# Charts directory
CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)


@router.get("/charts/{chart_id}")
async def get_chart(chart_id: str):
    """Serve a chart image file"""

    # Validate chart_id to prevent path traversal
    if ".." in chart_id or "/" in chart_id or "\\" in chart_id:
        raise HTTPException(status_code=400, detail="Invalid chart ID")

    # Look for the chart file - try PNG first, then HTML
    chart_path = os.path.join(CHARTS_DIR, f"{chart_id}.png")

    if not os.path.exists(chart_path):
        # Try HTML format as fallback
        chart_path = os.path.join(CHARTS_DIR, f"{chart_id}.html")
        if not os.path.exists(chart_path):
            raise HTTPException(status_code=404, detail="Chart not found")

        # Return HTML file
        return FileResponse(
            chart_path,
            media_type="text/html",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )

    return FileResponse(
        chart_path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )


@router.get("/charts")
async def list_charts():
    """List available charts"""
    try:
        charts = []
        for filename in os.listdir(CHARTS_DIR):
            if filename.endswith('.png'):
                chart_id = filename[:-4]
                charts.append({
                    "id": chart_id,
                    "url": f"/api/v1/charts/{chart_id}"
                })
        return {"charts": charts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list charts: {str(e)}")
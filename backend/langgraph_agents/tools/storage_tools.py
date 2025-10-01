"""
Storage Tools - Azure Blob Storage operations for LangGraph agents

Provides utilities for:
- Loading files from blob storage
- Saving charts to blob storage
- Listing session files
"""

from typing import Optional, List, Dict, Any
import io
import pandas as pd
from azure.storage.blob.aio import BlobServiceClient
from core.config import settings


async def get_blob_service_client() -> BlobServiceClient:
    """
    Get Azure Blob Storage client.

    Returns:
        BlobServiceClient: Azure storage client
    """
    return BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    )


async def load_file_from_storage(
    blob_path: str,
    container_name: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """
    Load a file from Azure Blob Storage and parse it.

    Args:
        blob_path: Blob path in storage (e.g., "csv/2025/09/29/file.csv")
        container_name: Container name (default: from settings)

    Returns:
        Optional[pd.DataFrame]: Parsed file data, or None if failed
    """
    try:
        if container_name is None:
            container_name = settings.azure_storage_container_name

        blob_service = await get_blob_service_client()
        blob_client = blob_service.get_blob_client(
            container=container_name,
            blob=blob_path,
        )

        # Download blob content
        download_stream = await blob_client.download_blob()
        blob_data = await download_stream.readall()

        # Parse based on file extension
        if blob_path.endswith(".csv"):
            return pd.read_csv(io.BytesIO(blob_data))
        elif blob_path.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(blob_data))
        elif blob_path.endswith(".json"):
            return pd.read_json(io.BytesIO(blob_data))
        else:
            # Unsupported format
            return None

    except Exception as e:
        print(f"Error loading file from storage: {e}")
        return None
    finally:
        # Close the client
        await blob_service.close()


async def save_chart_to_storage(
    chart_data: bytes,
    filename: str,
    container_name: Optional[str] = None,
) -> Optional[str]:
    """
    Save a chart to Azure Blob Storage.

    Args:
        chart_data: Chart file bytes (PNG, HTML, etc.)
        filename: Filename for the chart
        container_name: Container name (default: from settings)

    Returns:
        Optional[str]: Blob URL if successful, None if failed
    """
    try:
        if container_name is None:
            container_name = settings.azure_storage_container_name

        blob_service = await get_blob_service_client()
        container_client = blob_service.get_container_client(container_name)

        # Ensure container exists
        try:
            await container_client.create_container()
        except Exception:
            # Container already exists, ignore
            pass

        # Upload chart
        blob_client = blob_service.get_blob_client(
            container=container_name,
            blob=filename,
        )
        await blob_client.upload_blob(chart_data, overwrite=True)

        # Return public URL (construct from account name)
        account_name = _extract_account_name(settings.azure_storage_connection_string)
        return f"https://{account_name}.blob.core.windows.net/{container_name}/{filename}"

    except Exception as e:
        print(f"Error saving chart to storage: {e}")
        return None
    finally:
        await blob_service.close()


async def list_session_files(
    session_id: str,
    container_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List all files for a session.

    Args:
        session_id: Chat session ID
        container_name: Container name (default: from settings)

    Returns:
        List[Dict[str, Any]]: List of file metadata
    """
    try:
        if container_name is None:
            container_name = settings.azure_storage_container_name

        blob_service = await get_blob_service_client()
        container_client = blob_service.get_container_client(container_name)

        # List blobs with session prefix
        blobs = []
        async for blob in container_client.list_blobs(name_starts_with=f"{session_id}/"):
            blobs.append({
                "name": blob.name,
                "size": blob.size,
                "created": blob.creation_time,
                "content_type": blob.content_settings.content_type if blob.content_settings else None,
            })

        return blobs

    except Exception as e:
        print(f"Error listing session files: {e}")
        return []
    finally:
        await blob_service.close()


async def load_multiple_files(
    file_paths: List[str],
    container_name: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Load multiple files from storage.

    Args:
        file_paths: List of blob paths
        container_name: Container name (default: from settings)

    Returns:
        Dict[str, pd.DataFrame]: Map of file_path -> DataFrame
    """
    result = {}

    for file_path in file_paths:
        df = await load_file_from_storage(file_path, container_name)
        if df is not None:
            result[file_path] = df

    return result


async def get_uploaded_file_data(
    file_ids: List[str],
    db_session
) -> Dict[str, pd.DataFrame]:
    """
    Get uploaded file data from database and load from storage.

    This function is used by analytics agents to load user-uploaded files.

    Args:
        file_ids: List of file IDs from database
        db_session: Database session

    Returns:
        Dict[str, pd.DataFrame]: Map of file_id -> DataFrame
    """
    from langgraph_agents.tools.database_tools import load_file_metadata

    try:
        # Load file metadata from database
        file_metadata = await load_file_metadata(db_session, file_ids)

        if not file_metadata:
            return {}

        # Load files from storage
        result = {}
        for file in file_metadata:
            df = await load_file_from_storage(file.file_path)
            if df is not None:
                result[file.id] = df

        return result

    except Exception as e:
        print(f"Error getting uploaded file data: {e}")
        return {}


def _extract_account_name(connection_string: str) -> str:
    """Extract account name from connection string"""
    for part in connection_string.split(';'):
        if part.startswith('AccountName='):
            return part.split('=', 1)[1]
    return ""
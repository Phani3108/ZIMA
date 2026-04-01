"""
Blob Store — Azure Blob Storage wrapper for conversation archive and file storage.

Usage::

    from zeta_ima.infra.blob_store import get_blob_store
    bs = get_blob_store()
    url = await bs.upload("conversations/t1/sess-123.json", data_bytes)
    data = await bs.download("conversations/t1/sess-123.json")
"""

from __future__ import annotations

import logging
from typing import Any

from zeta_ima.config import settings

log = logging.getLogger(__name__)

_instance: "BlobStore | None" = None


def get_blob_store() -> "BlobStore":
    """Return the blob store singleton."""
    global _instance
    if _instance is None:
        _instance = BlobStore()
        log.info("Blob store initialised (container=%s)", settings.azure_storage_container)
    return _instance


class BlobStore:
    """
    Async wrapper around Azure Blob Storage.

    Falls back to local filesystem when ``azure_storage_connection_string`` is empty
    (for local dev without Azure).
    """

    def __init__(self) -> None:
        self._conn_str = settings.azure_storage_connection_string
        self._container = settings.azure_storage_container
        self._local_root = "/tmp/zeta_ima_blobs"  # noqa: S108
        self._container_client: Any = None

    @property
    def _is_azure(self) -> bool:
        return bool(self._conn_str)

    async def _get_container(self):
        if self._container_client is None:
            if self._is_azure:
                from azure.storage.blob.aio import ContainerClient
                self._container_client = ContainerClient.from_connection_string(
                    self._conn_str,
                    container_name=self._container,
                )
                # Ensure container exists
                try:
                    await self._container_client.create_container()
                except Exception:
                    pass  # Already exists
            else:
                import os
                os.makedirs(self._local_root, exist_ok=True)
        return self._container_client

    async def upload(self, blob_path: str, data: bytes, content_type: str = "application/json") -> str:
        """
        Upload bytes to blob storage. Returns the blob URL.

        ``blob_path``: e.g. "conversations/team1/session-abc.json"
        """
        if self._is_azure:
            container = await self._get_container()
            blob = container.get_blob_client(blob_path)
            await blob.upload_blob(data, overwrite=True, content_settings={"content_type": content_type})
            url = blob.url
            log.debug("Uploaded blob: %s", blob_path)
            return url
        else:
            import os
            full_path = os.path.join(self._local_root, blob_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(data)
            log.debug("Uploaded local blob: %s", full_path)
            return f"file://{full_path}"

    async def download(self, blob_path: str) -> bytes | None:
        """Download blob contents. Returns None if not found."""
        if self._is_azure:
            container = await self._get_container()
            blob = container.get_blob_client(blob_path)
            try:
                stream = await blob.download_blob()
                return await stream.readall()
            except Exception:
                return None
        else:
            import os
            full_path = os.path.join(self._local_root, blob_path)
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    return f.read()
            return None

    async def exists(self, blob_path: str) -> bool:
        """Check if a blob exists."""
        if self._is_azure:
            container = await self._get_container()
            blob = container.get_blob_client(blob_path)
            try:
                await blob.get_blob_properties()
                return True
            except Exception:
                return False
        else:
            import os
            return os.path.exists(os.path.join(self._local_root, blob_path))

    async def delete(self, blob_path: str) -> None:
        """Delete a blob."""
        if self._is_azure:
            container = await self._get_container()
            blob = container.get_blob_client(blob_path)
            try:
                await blob.delete_blob()
            except Exception:
                pass
        else:
            import os
            full_path = os.path.join(self._local_root, blob_path)
            if os.path.exists(full_path):
                os.remove(full_path)

    async def list_blobs(self, prefix: str) -> list[str]:
        """List blob names under a prefix."""
        if self._is_azure:
            container = await self._get_container()
            names = []
            async for blob in container.list_blobs(name_starts_with=prefix):
                names.append(blob.name)
            return names
        else:
            import os
            root = os.path.join(self._local_root, prefix)
            if not os.path.exists(root):
                return []
            results = []
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    rel = os.path.relpath(os.path.join(dirpath, fn), self._local_root)
                    results.append(rel)
            return results

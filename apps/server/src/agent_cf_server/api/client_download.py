"""Serve only the configured Windows installer, never arbitrary PC filesystem paths."""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


def client_download_router(installer_path: Path):
    router = APIRouter(prefix="/v1/client", tags=["client-desktop"])

    @router.get("/desktop", operation_id="getClientDesktop")
    def metadata():
        return {"platform": "windows-x64", "protocol": "agentcf", "installer_available": installer_path.is_file(), "download_url": "/v1/client/windows-installer"}

    @router.get("/windows-installer", operation_id="downloadClientInstaller", response_class=FileResponse,
        responses={200: {"description": "Windows x64 installer", "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}, 503: {"description": "Installer has not been built"}})
    def download():
        if not installer_path.is_file():
            raise HTTPException(503, "Chưa có bộ cài Windows. Chạy infra/build-client.ps1 trên máy Server.")
        return FileResponse(installer_path, filename="CF Client Setup.exe", media_type="application/octet-stream", headers={"Cache-Control": "no-store"})

    return router

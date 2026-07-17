"""Integration tests for the ADMS (iClock) router."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.modules.adms.dependencies import get_adms_service
from app.modules.adms.router import router as adms_router


@pytest.fixture
def mock_adms_service() -> AsyncMock:
    """Mock stand-in for ADMSService."""
    return AsyncMock()


@pytest.fixture
def adms_app():
    """Mounts the ADMS router on the production app factory."""
    application = create_app()
    # Mounted at prefix '/iclock'
    application.include_router(adms_router, prefix="/iclock")
    return application


@pytest_asyncio.fixture
async def adms_client(adms_app, mock_adms_service: AsyncMock):
    """An async HTTP client bound to the app with the ADMS service mocked."""
    adms_app.dependency_overrides[get_adms_service] = lambda: mock_adms_service
    transport = ASGITransport(app=adms_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    adms_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cdata_get_handshake(adms_client: AsyncClient, mock_adms_service: AsyncMock) -> None:
    mock_adms_service.handle_cdata_get.return_value = "OK"
    resp = await adms_client.get("/iclock/cdata?SN=SN123&options=all")
    assert resp.status_code == 200
    assert resp.text == "OK"
    assert resp.headers["content-type"] == "text/plain; charset=utf-8"
    mock_adms_service.handle_cdata_get.assert_called_once()
    query_params = mock_adms_service.handle_cdata_get.call_args[1]["query_params"]
    assert query_params["SN"] == "SN123"
    assert query_params["options"] == "all"


@pytest.mark.asyncio
async def test_cdata_post_upload(adms_client: AsyncClient, mock_adms_service: AsyncMock) -> None:
    mock_adms_service.handle_cdata_post.return_value = "OK"
    resp = await adms_client.post("/iclock/cdata?SN=SN123&table=ATTLOG", content="punch-data")
    assert resp.status_code == 200
    assert resp.text == "OK"
    mock_adms_service.handle_cdata_post.assert_called_once_with(
        sn="SN123",
        table="ATTLOG",
        payload="punch-data",
        client_ip="127.0.0.1",
    )


@pytest.mark.asyncio
async def test_getrequest_queue(adms_client: AsyncClient, mock_adms_service: AsyncMock) -> None:
    mock_adms_service.handle_getrequest.return_value = "OK"
    resp = await adms_client.get("/iclock/getrequest?SN=SN123&INFO=status-info")
    assert resp.status_code == 200
    assert resp.text == "OK"
    mock_adms_service.handle_getrequest.assert_called_once_with(
        sn="SN123",
        info_str="status-info",
        client_ip="127.0.0.1",
    )


@pytest.mark.asyncio
async def test_devicecmd_ack(adms_client: AsyncClient, mock_adms_service: AsyncMock) -> None:
    mock_adms_service.handle_devicecmd_post.return_value = "OK"
    resp = await adms_client.post("/iclock/devicecmd?SN=SN123", content="cmd-response")
    assert resp.status_code == 200
    assert resp.text == "OK"
    mock_adms_service.handle_devicecmd_post.assert_called_once_with(
        sn="SN123",
        payload="cmd-response",
        client_ip="127.0.0.1",
    )


@pytest.mark.asyncio
async def test_cdata_aspx_get_handshake(adms_client: AsyncClient, mock_adms_service: AsyncMock) -> None:
    mock_adms_service.handle_cdata_get.return_value = "OK"
    resp = await adms_client.get("/iclock/cdata.aspx?SN=SN123&options=all")
    assert resp.status_code == 200
    assert resp.text == "OK"
    assert resp.headers["content-type"] == "text/plain; charset=utf-8"
    mock_adms_service.handle_cdata_get.assert_called_once()
    query_params = mock_adms_service.handle_cdata_get.call_args[1]["query_params"]
    assert query_params["SN"] == "SN123"
    assert query_params["options"] == "all"


@pytest.mark.asyncio
async def test_cdata_aspx_post_upload(adms_client: AsyncClient, mock_adms_service: AsyncMock) -> None:
    mock_adms_service.handle_cdata_post.return_value = "OK"
    resp = await adms_client.post("/iclock/cdata.aspx?SN=SN123&table=ATTLOG", content="punch-data")
    assert resp.status_code == 200
    assert resp.text == "OK"
    mock_adms_service.handle_cdata_post.assert_called_once_with(
        sn="SN123",
        table="ATTLOG",
        payload="punch-data",
        client_ip="127.0.0.1",
    )


@pytest.mark.asyncio
async def test_getrequest_aspx_queue(adms_client: AsyncClient, mock_adms_service: AsyncMock) -> None:
    mock_adms_service.handle_getrequest.return_value = "OK"
    resp = await adms_client.get("/iclock/getrequest.aspx?SN=SN123&INFO=status-info")
    assert resp.status_code == 200
    assert resp.text == "OK"
    mock_adms_service.handle_getrequest.assert_called_once_with(
        sn="SN123",
        info_str="status-info",
        client_ip="127.0.0.1",
    )



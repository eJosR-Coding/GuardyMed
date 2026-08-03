import pytest
from httpx import AsyncClient
from pathlib import Path

from apps.api.app.main import app


@pytest.mark.anyio
async def test_web_mount_and_root_redirect_exist(client: AsyncClient) -> None:
    paths = {route.path for route in app.routes}

    assert "/" in paths
    assert "/app" in paths

    root = await client.get("/", follow_redirects=False)
    assert root.status_code in {307, 308}
    assert root.headers["location"] == "/app"


@pytest.mark.anyio
async def test_web_static_assets_exist_and_contain_expected_ui_markers(client: AsyncClient) -> None:
    web_dir = Path(__file__).resolve().parents[1] / "apps" / "web"
    styles = (web_dir / "styles.css").read_text()
    script = (web_dir / "app.js").read_text()
    index = (web_dir / "index.html").read_text()

    assert ":root {" in styles
    assert ".workflow-strip" in styles
    assert ".overview-panel" in styles
    assert ".camera-stage" in styles

    assert "roleMeta" in script
    assert "humanizeErrorMessage" in script
    assert "window.guardyMedApp" in script
    assert 'attendance/cv/attempts' in script
    assert '"/auth/login"' in script
    assert '"/scheduling/departments"' in script

    assert "GuardyMed" in index
    assert "Manager planning workflow" in index
    assert "Worker workflow" in index
    assert "Manager review workflow" in index
    assert 'x-data="guardyMedApp()"' in index
    assert "alpinejs" in index
    assert "Check in with face verification" in index

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
    root = Path(__file__).resolve().parents[1]
    source_dir = root / "apps" / "frontend"
    web_dir = root / "apps" / "web"

    package_json = (source_dir / "package.json").read_text()
    app_vue = (source_dir / "src" / "App.vue").read_text()
    source_styles = (source_dir / "src" / "styles.css").read_text()
    index = (web_dir / "index.html").read_text()
    built_assets = sorted((web_dir / "assets").glob("*"))

    assert '"vue"' in package_json
    assert '"vite"' in package_json

    assert "Manager workspace" in app_vue
    assert "Worker workspace" in app_vue
    assert "Face attendance" in app_vue
    assert "attendance/cv/attempts" in app_vue

    assert ".camera-frame" in source_styles
    assert ".workspace-intro" in source_styles
    assert ".evidence-card" in source_styles

    assert '<div id="app"></div>' in index
    assert "/assets/" in index
    assert built_assets

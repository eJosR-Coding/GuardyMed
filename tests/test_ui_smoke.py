import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from apps.api.app.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.anyio
async def test_web_mount_and_root_redirect_exist(client: AsyncClient) -> None:
    paths = {route.path for route in app.routes}

    assert "/" in paths
    assert "/app" in paths

    root = await client.get("/", follow_redirects=False)
    assert root.status_code in {307, 308}
    assert root.headers["location"] == "/app"


@pytest.mark.anyio
async def test_built_frontend_is_served_with_its_assets(client: AsyncClient) -> None:
    page = await client.get("/app/")

    assert page.status_code == 200
    assert '<div id="app"></div>' in page.text
    asset_paths = [part.split('"')[0] for part in page.text.split('"/app/')[1:] if part.startswith("assets/")]
    assert any(path.endswith(".js") for path in asset_paths) and any(path.endswith(".css") for path in asset_paths)
    for asset in asset_paths:
        response = await client.get(f"/app/{asset}")
        assert response.status_code == 200, asset


def test_frontend_sources_and_manifest_are_consistent() -> None:
    package = json.loads((ROOT / "apps" / "frontend" / "package.json").read_text())
    version = (ROOT / "VERSION").read_text().strip()

    assert {"vue", "@fontsource/ibm-plex-sans"} <= set(package["dependencies"])
    assert package["version"] == version
    for view in ("manager/ManagerApp.vue", "worker/WorkerApp.vue", "LoginView.vue"):
        assert (ROOT / "apps" / "frontend" / "src" / "views" / view).exists(), view


def test_all_version_sources_agree() -> None:
    import tomllib

    version = (ROOT / "VERSION").read_text().strip()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["version"] == version
    assert version in (ROOT / "CHANGELOG.md").read_text()

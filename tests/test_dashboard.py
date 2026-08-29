from pathlib import Path

from fastapi.testclient import TestClient

from dbie.services.run_workspace import RunWorkspaceManager
from dbie.web import create_dashboard_app


def dashboard_client(tmp_path: Path) -> tuple[TestClient, Path]:
    workspace = RunWorkspaceManager(tmp_path).ensure("run-123")
    (workspace.conversations / "market.log").write_text(
        "Crew says <script>alert('no')</script>", encoding="utf-8"
    )
    (workspace.deliverables / "idea.md").write_text(
        "# Strong idea\n\n<script>alert('no')</script>\n\n"
        "[unsafe](javascript:alert('no'))\n\n"
        "| A | B |\n| - | - |\n| 1 | 2 |",
        encoding="utf-8",
    )
    (workspace.deliverables / "state.json").write_text(
        '{"status":"BUILD"}', encoding="utf-8"
    )
    (workspace.deliverables / "archive.bin").write_bytes(b"\x00\x01")
    return TestClient(create_dashboard_app(tmp_path, auto_refresh_seconds=3)), workspace.root


def test_index_shows_current_run_and_artifacts(tmp_path: Path) -> None:
    client, _ = dashboard_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "run-123 · current" in response.text
    assert "market.log" in response.text
    assert "idea.md" in response.text
    assert '<meta http-equiv="refresh" content="3">' in response.text


def test_conversation_is_preformatted_and_html_escaped(tmp_path: Path) -> None:
    client, _ = dashboard_client(tmp_path)

    response = client.get("/runs/run-123/conversations/market.log")

    assert response.status_code == 200
    assert '<pre class="conversation">' in response.text
    assert "&lt;script&gt;alert" in response.text
    assert "<script>alert" not in response.text
    assert "javascript:" not in response.text


def test_markdown_is_rendered_without_allowing_raw_html(tmp_path: Path) -> None:
    client, _ = dashboard_client(tmp_path)

    response = client.get("/runs/run-123/deliverables/idea.md")

    assert response.status_code == 200
    assert "<h1>Strong idea</h1>" in response.text
    assert "<table>" in response.text
    assert "&lt;script&gt;alert" in response.text
    assert "<script>alert" not in response.text


def test_json_is_readable_and_binary_is_downloadable(tmp_path: Path) -> None:
    client, _ = dashboard_client(tmp_path)

    json_response = client.get("/runs/run-123/deliverables/state.json")
    binary_response = client.get("/runs/run-123/deliverables/archive.bin")

    assert "  &#34;status&#34;: &#34;BUILD&#34;" in json_response.text
    assert binary_response.content == b"\x00\x01"
    assert "archive.bin" in binary_response.headers["content-disposition"]


def test_current_shortcut_and_read_only_contract(tmp_path: Path) -> None:
    client, _ = dashboard_client(tmp_path)

    current = client.get("/current", follow_redirects=False)

    assert current.status_code == 303
    assert current.headers["location"] == "/runs/run-123"
    assert client.post("/runs/run-123").status_code == 405
    assert client.get("/runs/not-a-run").status_code == 404


def test_empty_dashboard_has_useful_state(tmp_path: Path) -> None:
    response = TestClient(create_dashboard_app(tmp_path)).get("/")

    assert response.status_code == 200
    assert "No runs yet" in response.text

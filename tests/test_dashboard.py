import json
from pathlib import Path

from fastapi.testclient import TestClient

from dbie.services.run_workspace import RunWorkspaceManager
from dbie.web import create_dashboard_app
from dbie.web.app import _dossier_summary


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
    (workspace.deliverables / "run-overview.json").write_text(
        '{"artifact_type":"run_overview","funnel":'
        '{"observed_signals":12,"raw_ideas":50}}',
        encoding="utf-8",
    )
    (workspace.deliverables / "dossier.json").write_text(
        """{
          "candidate_id": "hidden-candidate-uuid",
          "title": "Control Mapping API",
          "thesis": "Automate control mapping for regulated teams.",
          "decision": "BUILD",
          "why_now": "Rules are machine-readable.",
          "customer": "Regulated companies",
          "buyer": "Chief compliance officer",
          "automation_ratio": 0.95,
          "human_minutes_per_customer_at_10x": 1.5,
          "economics": {"gross_margin_base": 0.8, "source": "fixture"},
          "ranking": {"rank": 2, "stability": 1.0},
          "assumptions": [{
            "statement": "Demand exists",
            "status": "RESEARCH_SUPPORTED",
            "evidence_for": [
              {"title": "Official regulator — Primary evidence", "summary": "The required workflow is documented.", "url": "https://regulator.test/rule"},
              {"title": "Industry measurement — Primary evidence", "summary": "The repeated burden was measured."}
            ],
            "evidence_against": [],
            "independent_lineages": 2
          }],
          "unknowns": [],
          "competitors": ["Manual workflow"],
          "business_model_variants": ["Subscription"],
          "red_team_findings": ["Challenge resolved"],
          "recommended_experiments": ["Pricing test"],
          "reason_codes": ["HARD_GATES_PASSED"]
        }""",
        encoding="utf-8",
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
    assert "Business case · Human-readable analysis" in response.text
    assert "Run funnel and outcomes" in response.text
    assert "Observed problems / signals" in response.text
    assert "12 current" in response.text
    assert "250–500" in response.text
    assert "bytes ·" not in response.text
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


def test_dossier_json_is_a_concise_human_decision_brief(tmp_path: Path) -> None:
    client, workspace = dashboard_client(tmp_path)

    response = client.get("/runs/run-123/deliverables/dossier.json")

    assert response.status_code == 200
    assert "Control Mapping API" in response.text
    assert "Business opportunity" in response.text
    assert "BUILD" in response.text
    assert "95%" in response.text
    assert "1/1" in response.text
    assert "2" in response.text
    assert "Pricing test" in response.text
    assert "Opportunity description" in response.text
    assert "Demand exists" in response.text
    assert "Research Supported" in response.text
    assert "Supporting evidence" in response.text
    assert "Acceptance-fixture values" not in response.text
    assert "hidden-candidate-uuid" not in response.text
    assert "Official regulator — Primary evidence" in response.text
    assert "The required workflow is documented." in response.text
    assert 'href="https://regulator.test/rule"' in response.text
    assert "evidence links" not in response.text
    assert "evidence_for" not in response.text
    assert "hidden-candidate-uuid" in (
        workspace / "deliverables" / "dossier.json"
    ).read_text(encoding="utf-8")
    payload = json.loads((workspace / "deliverables" / "dossier.json").read_text())
    summary = _dossier_summary(payload)
    assert summary is not None
    assert len(summary["description"].split()) >= 100


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

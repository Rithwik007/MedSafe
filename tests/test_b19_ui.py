from __future__ import annotations

from pathlib import Path
import re

from fastapi.testclient import TestClient

from medsafe.api.app import app


STATIC = Path("medsafe/api/static")
BANNER = "Research prototype. Decision support only. Pharmacist review required. Use synthetic data only."


def test_ui_and_static_routes_have_csp_and_banner():
    with TestClient(app) as client:
        page = client.get("/")
        script = client.get("/static/app.js")
        style = client.get("/static/styles.css")
    assert page.status_code == 200
    assert page.headers["content-security-policy"].startswith("default-src 'self'")
    assert BANNER in page.text
    assert script.status_code == 200 and style.status_code == 200
    assert (STATIC / "index.html").is_file()
    assert (STATIC / "app.js").is_file()
    assert (STATIC / "styles.css").is_file()


def test_static_ui_lint_rejects_unsafe_rendering_external_urls_and_storage():
    sources = [path.read_text(encoding="utf-8") for path in
               (STATIC / "index.html", STATIC / "app.js", STATIC / "styles.css")]
    joined = "\n".join(sources)
    assert "innerHTML" not in joined
    assert not re.search(r"https?://", joined, re.I)
    assert "localStorage" not in joined
    assert "sessionStorage" not in joined


def test_config_is_allowlisted_and_has_no_credential_or_model_fields(monkeypatch):
    monkeypatch.setenv("MEDSAFE_DISABLE_DOTENV", "1")
    monkeypatch.setenv("MEDSAFE_LLM_ENABLED", "0")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MEDSAFE_LLM_MODEL", raising=False)
    with TestClient(app) as client:
        response = client.get("/config")
    body = response.json()
    assert response.status_code == 200
    assert set(body) == {"ml_available", "llm_available", "version"}
    assert "api_key" not in response.text.casefold()
    assert "groq_api_key" not in response.text.casefold()
    assert "anthropic_api_key" not in response.text.casefold()
    assert "model" not in response.text.casefold()


def test_request_body_sentinel_is_not_written_to_application_logs(caplog):
    sentinel = "request-body-sentinel-unprinted"
    with TestClient(app) as client:
        response = client.post("/analyze-text", json={
            "patient": {}, "prescription_text": sentinel,
        })
    assert response.status_code == 200
    assert sentinel not in caplog.text

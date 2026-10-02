from __future__ import annotations

import io
import json
import logging
import zipfile
from pathlib import Path

import pytest

import medsafe.llm.client as llm_client
from medsafe.llm.client import EnvFileError, LlmConfig, parse_env_file, readiness


def test_env_parser_allowlist_quotes_comments_and_size_limit(tmp_path):
    sentinel = "offline-sentinel-value"
    env_file = tmp_path / "sample.env"
    env_file.write_text(
        f"# comment\n\nGROQ_API_KEY=\"{sentinel}\"\n"
        "MEDSAFE_LLM_PROVIDER='groq'\nMEDSAFE_LLM_MODEL=model-from-test\n"
        "MEDSAFE_LLM_ENABLED=1\nANTHROPIC_API_KEY=ignored\n",
        encoding="utf-8",
    )
    values = parse_env_file(env_file)
    assert values == {"GROQ_API_KEY": sentinel,
                      "MEDSAFE_LLM_PROVIDER": "groq",
                      "MEDSAFE_LLM_MODEL": "model-from-test"}

    env_file.write_text("GROQ_API_KEY=" + sentinel + "\n" + "# padding\n" * 4096,
                        encoding="utf-8")
    with pytest.raises(EnvFileError) as error:
        parse_env_file(env_file)
    assert sentinel not in str(error.value)


def test_env_missing_malformed_are_content_free(tmp_path):
    assert parse_env_file(tmp_path / "missing.env") == {}
    sentinel = "offline-sentinel-value"
    malformed = tmp_path / "malformed.env"
    malformed.write_text(f"GROQ_API_KEY={sentinel}\nnot-a-key-value-line\n", encoding="utf-8")
    with pytest.raises(EnvFileError) as error:
        parse_env_file(malformed)
    assert sentinel not in str(error.value)


def test_process_environment_wins_and_dotenv_does_not_enable(monkeypatch, tmp_path):
    sentinel_file = "file-sentinel-value"
    sentinel_process = "process-sentinel-value"
    (tmp_path / ".env").write_text(
        f"GROQ_API_KEY={sentinel_file}\nMEDSAFE_LLM_PROVIDER=groq\n"
        "MEDSAFE_LLM_MODEL=model-from-file\nMEDSAFE_LLM_ENABLED=1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(llm_client, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(llm_client, "_env_loaded", False)
    monkeypatch.delenv("MEDSAFE_DISABLE_DOTENV", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", sentinel_process)
    monkeypatch.delenv("MEDSAFE_LLM_ENABLED", raising=False)
    monkeypatch.delenv("MEDSAFE_LLM_MODEL", raising=False)
    config = LlmConfig.from_env()
    assert config.api_key == sentinel_process
    assert config.model == "model-from-file"
    assert config.enabled is False
    assert sentinel_process not in repr(config)
    assert sentinel_process not in str(config)


def test_config_requires_explicit_opt_in_and_model():
    assert readiness(LlmConfig(enabled=False, api_key="unit-test-value", model="m", provider="groq"), True)[0] == "DISABLED"
    assert readiness(LlmConfig(enabled=True, api_key="unit-test-value", model=None, provider="groq"), True)[0] == "DISABLED"


def test_groq_request_format_and_content_free_failure(monkeypatch):
    sentinel = "offline-sentinel-value"
    config = LlmConfig(enabled=True, api_key=sentinel, model="model-from-test", provider="groq")
    seen = {}

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def read(self):
            return b'{"choices":[{"message":{"content":"synthetic response"}}]}'

    def fake_open(request, timeout):
        seen["url"] = request.full_url
        seen["headers"] = dict(request.header_items())
        seen["payload"] = json.loads(request.data)
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_open)
    llm_client.reset_groq_request_budget()
    result = llm_client.GroqClient(config).complete("synthetic system", "synthetic prompt")
    assert result == "synthetic response"
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["payload"]["model"] == "model-from-test"
    assert seen["payload"]["temperature"] == 0
    assert seen["payload"]["max_completion_tokens"] == 800
    assert seen["payload"]["messages"] == [
        {"role": "system", "content": "synthetic system"},
        {"role": "user", "content": "synthetic prompt"},
    ]
    assert seen["timeout"] <= 10
    assert sentinel not in repr(config) and sentinel not in str(config)

    def fail_open(*_args, **_kwargs):
        raise OSError(sentinel)
    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fail_open)
    llm_client.reset_groq_request_budget()
    with pytest.raises(llm_client.ProviderError) as error:
        llm_client.GroqClient(config).complete("synthetic system", "synthetic prompt")
    assert sentinel not in str(error.value)

def test_groq_gpt_oss_uses_low_reasoning_effort(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return b'{"choices":[{"message":{"content":"ok"}}]}'
    seen = {}
    def fake_open(request, timeout):
        seen["payload"] = json.loads(request.data)
        return Response()
    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_open)
    llm_client.reset_groq_request_budget()
    llm_client.GroqClient(LlmConfig(True, "test-key", "openai/gpt-oss-120b", "groq")).complete("Return JSON only.", "p")
    assert seen["payload"]["reasoning_effort"] == "low"
    assert seen["payload"]["response_format"] == {"type": "json_object"}


def test_groq_retries_429_once_and_then_falls_back(monkeypatch):
    calls = []
    def fail_open(*_args, **_kwargs):
        calls.append(1)
        raise llm_client.urllib.error.HTTPError("url", 429, "private detail", {}, io.BytesIO(b"secret"))
    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fail_open)
    llm_client.reset_groq_request_budget()
    with pytest.raises(llm_client.ProviderError) as error:
        llm_client.GroqClient(LlmConfig(True, "offline-sentinel-value", "model-from-test", "groq")) \
            .complete("synthetic system", "synthetic prompt")
    assert len(calls) == 2
    assert "private detail" not in str(error.value)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("failure", [TimeoutError("offline sentinel"), OSError("offline sentinel")])
def test_parser_provider_failure_retains_deterministic_parse(failure):
    from medsafe.llm.parser_fallback import fallback_parse
    from medsafe.nlp.parser import parse_prescription

    class FailingClient:
        def complete(self, *_args):
            raise failure

    line = "Paracetmol 500 mg BD"
    parsed = parse_prescription(line)
    config = LlmConfig(enabled=True, api_key="offline-sentinel-value",
                       model="model-from-test", provider="groq")
    result, counts, _reason = fallback_parse(line, parsed, config, FailingClient(), True)
    assert result.model_dump(mode="json") == parsed.model_dump(mode="json")
    assert counts["parse_accepted"] == 0


def test_groq_invalid_json_has_fixed_error(monkeypatch):
    sentinel = "offline-sentinel-value"
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def read(self):
            return (sentinel + "{").encode()
    monkeypatch.setattr(llm_client.urllib.request, "urlopen", lambda *_a, **_k: Response())
    llm_client.reset_groq_request_budget()
    with pytest.raises(llm_client.ProviderError) as error:
        llm_client.GroqClient(LlmConfig(True, "another-test-value", "model-from-test", "groq")) \
            .complete("synthetic system", "synthetic prompt")
    assert sentinel not in str(error.value)


def test_rejected_summary_keeps_report_findings_unchanged():
    from medsafe.checkers.engine import analyze
    from medsafe.kb.rules import RULES
    from medsafe.llm.summaries import generate_summary
    from medsafe.models.domain import MedOrder, Patient, Prescription
    rule = next(row for row in RULES if row.kind.value == "DDI" and row.severity.value == "MAJOR")
    report = analyze(Prescription(patient=Patient(current_meds=[MedOrder(drug_name=rule.drugs[0])]),
                                  new_orders=[MedOrder(drug_name=rule.drugs[1])]))
    finding = next(item for item in report.findings if item.rule_id == rule.rule_id)
    before = [item.model_dump(mode="json") for item in report.findings]
    class ExtraClinicalSentence:
        def complete(self, *_args):
            return "Major finding; pharmacist review required. Extra invented sentence."
    summary, _reason = generate_summary(finding, ExtraClinicalSentence())
    assert summary is None
    assert [item.model_dump(mode="json") for item in report.findings] == before


def test_zip_builder_excludes_fake_env_and_temporary_content(tmp_path, monkeypatch):
    import scripts.make_submission_zip as zipper
    root = tmp_path / "project"
    (root / "reports").mkdir(parents=True)
    (root / "data" / "raw" / "ddinter").mkdir(parents=True)
    (root / ".env").write_text("GROQ_API_KEY=offline-sentinel-value", encoding="utf-8")
    (root / ".env.local").write_text("ignored", encoding="utf-8")
    (root / ".env.example").write_text("GROQ_API_KEY=your-key-here", encoding="utf-8")
    (root / "README.md").write_text("synthetic", encoding="utf-8")
    (root / "data" / "raw" / "ddinter" / "ddinter_downloads_code_A.csv").write_text("raw", encoding="utf-8")
    monkeypatch.setattr(zipper, "ROOT", root)
    archive_path = root / "reports" / "test.zip"
    entries, _ = zipper.build(archive_path)
    names = {name for name, _size in entries}
    assert ".env.example" in names
    assert ".env" not in names and ".env.local" not in names
    assert "README.md" in names
    assert "data/raw/ddinter/ddinter_downloads_code_A.csv" not in names
    with zipfile.ZipFile(archive_path) as archive:
        assert all(Path(name).name == ".env.example" or not Path(name).name.startswith(".env")
                   for name in archive.namelist())


def test_llm_status_and_logs_do_not_render_key(caplog):
    sentinel = "offline-sentinel-value"
    config = LlmConfig(enabled=False, api_key=sentinel, model=None, provider="groq")
    state, reason = readiness(config, True)
    logging.getLogger("medsafe.llm").warning("provider status: %s %s", state, reason)
    assert state == "DISABLED"
    assert sentinel not in state + reason + caplog.text + repr(config) + str(config)

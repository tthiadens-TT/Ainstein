"""load_brand_core_context() moet CORE (verbal_identity.md secties 1-3) betrouwbaar
isoleren, nooit crashen bij ontbrekende sentinels, en agent.py moet het onvoorwaardelijk
injecteren ongeacht skill — dat is precies het gat dat dit dichtte (verbal_identity.md
werd voorheen alleen "geraadpleegd" door een handvol skills, nooit gegarandeerd)."""
import time

import pytest

import tools


@pytest.fixture(autouse=True)
def _reset_brand_core_cache():
    """De cache heeft een TTL van 5 minuten — zonder reset lekt de ene test in de andere."""
    tools._brand_core_cache["content"] = None
    tools._brand_core_cache["loaded_at"] = 0.0
    yield
    tools._brand_core_cache["content"] = None
    tools._brand_core_cache["loaded_at"] = 0.0


def _write_verbal_identity(tmp_path, monkeypatch, content: str):
    marketing_dir = tmp_path / "04_Marketing"
    marketing_dir.mkdir(parents=True)
    (marketing_dir / "verbal_identity.md").write_text(content, encoding="utf-8")
    monkeypatch.setattr(tools, "SOURCE_ROOT", tmp_path)


def test_load_brand_core_context_extracts_only_core(tmp_path, monkeypatch):
    content = (
        "# Verbal Identity\n\n"
        "<!-- CORE:START -->\n## 1. Tone of voice\nGeen em dash.\n<!-- CORE:END -->\n\n"
        "<!-- PATTERNS:START -->\n## 4. Patterns\nEvoluerende vocabulaire.\n<!-- PATTERNS:END -->\n"
    )
    _write_verbal_identity(tmp_path, monkeypatch, content)

    ctx = tools.load_brand_core_context()
    assert "Geen em dash" in ctx
    assert "Evoluerende vocabulaire" not in ctx


def test_load_brand_core_context_empty_when_sentinels_missing(tmp_path, monkeypatch):
    _write_verbal_identity(tmp_path, monkeypatch, "# Verbal Identity\n\nGeen sentinels.")
    ctx = tools.load_brand_core_context()
    assert ctx == ""


def test_load_brand_core_context_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "SOURCE_ROOT", tmp_path)  # geen 04_Marketing/verbal_identity.md
    ctx = tools.load_brand_core_context()
    assert ctx == ""


def test_load_brand_core_context_is_cached(tmp_path, monkeypatch):
    content = "<!-- CORE:START -->\nversie A\n<!-- CORE:END -->"
    _write_verbal_identity(tmp_path, monkeypatch, content)
    eerste = tools.load_brand_core_context()

    # Bestand wijzigt, maar binnen de TTL moet de gecachete waarde terugkomen
    (tmp_path / "04_Marketing" / "verbal_identity.md").write_text(
        "<!-- CORE:START -->\nversie B\n<!-- CORE:END -->", encoding="utf-8"
    )
    tweede = tools.load_brand_core_context()
    assert eerste == tweede == "versie A"


def test_load_brand_core_context_truncates_at_max_chars(tmp_path, monkeypatch):
    lange_inhoud = "x" * 10_000
    content = f"<!-- CORE:START -->\n{lange_inhoud}\n<!-- CORE:END -->"
    _write_verbal_identity(tmp_path, monkeypatch, content)

    ctx = tools.load_brand_core_context(max_chars=100)
    assert len(ctx) <= 100 + len("\n...[rest weggelaten]")
    assert "...[rest weggelaten]" in ctx


def test_agent_injects_brand_core_unconditionally_without_skill(tmp_path, monkeypatch):
    """De kern van de fix: CORE moet in de system-prompt zitten ongeacht skill —
    zelfde garantie als gaps.md/kennis_laag.md. Regressietest tegen het gat dat
    verbal_identity.md voorheen alleen bij een handvol skills werd geraadpleegd.

    Let op: `import agent` triggert `load_dotenv(override=True)` (agent.py:27) —
    als agent voor het eerst in dit testproces wordt geimporteerd, zet dat de echte
    GOOGLE_SERVICE_ACCOUNT_FILE terug in os.environ en ondermijnt de env-strip uit
    conftest.py._no_drive_writes_in_tests. Gevonden tijdens het schrijven van deze
    test (de eerste run las stilzwijgend de live Drive i.p.v. de tmp_path-fixture).
    Daarom hier expliciet _is_drive_mode() forceren i.p.v. op env-vars te vertrouwen."""
    content = "<!-- CORE:START -->\nEm dash nooit gebruiken.\n<!-- CORE:END -->"
    _write_verbal_identity(tmp_path, monkeypatch, content)

    import agent as agent_mod
    monkeypatch.setattr(tools, "_is_drive_mode", lambda: False)

    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured["system"] = kwargs.get("system")

            class FakeResp:
                content = []
                stop_reason = "end_turn"
                usage = type("U", (), {"input_tokens": 0, "output_tokens": 0})()

            return FakeResp()

    class FakeClient:
        messages = FakeMessages()

    agent_mod.run_agent(
        [{"role": "user", "content": "test"}], FakeClient(), skill=None, max_iterations=1
    )

    texts = [b.get("text", "") for b in captured.get("system", []) if isinstance(b, dict)]
    brand_blocks = [t for t in texts if "Brand CORE" in t]
    assert len(brand_blocks) == 1
    assert "Em dash nooit gebruiken" in brand_blocks[0]

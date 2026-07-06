"""load_brand_facts_context() moet brand_core.md (naam, purpose, oprichtingsverhaal,
bevestigde merkbelofte) betrouwbaar laden en agent.py moet het onvoorwaardelijk
injecteren — dit bestand bestond al met geverifieerde inhoud maar werd nergens
gebruikt (gevonden 2026-07-06), zelfde soort gat als verbal_identity.md eerder."""
import pytest

import tools


@pytest.fixture(autouse=True)
def _reset_brand_facts_cache():
    tools._brand_facts_cache["content"] = None
    tools._brand_facts_cache["loaded_at"] = 0.0
    yield
    tools._brand_facts_cache["content"] = None
    tools._brand_facts_cache["loaded_at"] = 0.0


def _write_brand_core(tmp_path, monkeypatch, content: str):
    marketing_dir = tmp_path / "04_Marketing"
    marketing_dir.mkdir(parents=True)
    (marketing_dir / "brand_core.md").write_text(content, encoding="utf-8")
    monkeypatch.setattr(tools, "SOURCE_ROOT", tmp_path)


def test_load_brand_facts_context_returns_full_file(tmp_path, monkeypatch):
    content = "# Brand Core\n\nMerknaam: Minkowski\nOpgericht: oktober 2017 door Jörgen van der Sloot."
    _write_brand_core(tmp_path, monkeypatch, content)

    ctx = tools.load_brand_facts_context()
    assert "Minkowski" in ctx
    assert "oktober 2017" in ctx


def test_load_brand_facts_context_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "SOURCE_ROOT", tmp_path)
    assert tools.load_brand_facts_context() == ""


def test_load_brand_facts_context_truncates_at_max_chars(tmp_path, monkeypatch):
    _write_brand_core(tmp_path, monkeypatch, "x" * 10_000)
    ctx = tools.load_brand_facts_context(max_chars=50)
    assert len(ctx) <= 50 + len("\n...[rest weggelaten]")
    assert "...[rest weggelaten]" in ctx


def test_load_brand_facts_context_is_cached(tmp_path, monkeypatch):
    _write_brand_core(tmp_path, monkeypatch, "versie A")
    eerste = tools.load_brand_facts_context()
    (tmp_path / "04_Marketing" / "brand_core.md").write_text("versie B", encoding="utf-8")
    tweede = tools.load_brand_facts_context()
    assert eerste == tweede == "versie A"


def test_agent_injects_brand_facts_unconditionally_without_skill(tmp_path, monkeypatch):
    content = "# Brand Core\n\nMerknaam: Minkowski. Opgericht oktober 2017."
    _write_brand_core(tmp_path, monkeypatch, content)

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
    facts_blocks = [t for t in texts if "Brand Facts" in t]
    assert len(facts_blocks) == 1
    assert "oktober 2017" in facts_blocks[0]

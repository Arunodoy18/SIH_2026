from redzone.data import store
from redzone.report.narrative import _cr, _facts, generate_narrative


def test_cr_formats_rupees_as_crore_string():
    assert _cr(6_465_000_000) == "₹646.5 cr"
    assert _cr(None) == "n/a"


def test_facts_preformats_money_no_raw_rupee_fields():
    summary = store.load_json("summary")
    plan = store.load_json("relocation_plan")
    f = _facts(summary, plan)
    assert "capex" in f["relocation_totals"]
    assert f["relocation_totals"]["capex"].startswith("₹")
    for ph in f["relocation_phases"]:
        assert ph["capex"].startswith("₹")
    for h in f["top_habitations"]:
        assert h["capex"].startswith("₹") or h["capex"] == "n/a"


def test_generate_narrative_without_any_key_is_template(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    summary = store.load_json("summary")
    plan = store.load_json("relocation_plan")
    out = generate_narrative(summary, plan)
    assert out["mode"] == "template"
    assert out["provider"] is None
    assert "₹" in out["text"]  # pre-formatted money made it into the template too

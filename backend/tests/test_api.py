from fastapi.testclient import TestClient

from redzone.api.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_habitations_featurecollection():
    fc = client.get("/habitations").json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 20
    props = fc["features"][0]["properties"]
    assert {"hab_id", "haz_tier", "priority_tier", "svi"} <= set(props)


def test_habitation_detail_breakdown():
    fid = client.get("/habitations").json()["features"][0]["properties"]["hab_id"]
    b = client.get(f"/habitations/{fid}").json()["breakdown"]
    assert set(b["hazard"]) == {"landslide", "glof", "seismic", "flood"}
    assert "deficit_ratio" in b["carrying_capacity"]


def test_layers():
    for name in ("hazard_tiers", "glacial_lakes", "rivers", "destination_sites", "historical_losses"):
        assert client.get(f"/layers/{name}").json()["type"] == "FeatureCollection"
    assert client.get("/layers/nope").status_code == 404


def test_summary_carries_seismic_outlook_and_landslide_method():
    s = client.get("/summary").json()
    assert s["hazard"]["landslide_method"] in ("ml", "heuristic")
    outlook = s["seismic_outlook"]
    assert outlook["elastic_rebound"]["last_major_event"] == 2011
    assert len(outlook["elastic_rebound"]["windows"]) == 3
    assert len(outlook["gutenberg_richter"]["by_magnitude"]) == 3


def test_report_narrative_falls_back_to_template_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.get("/report/narrative")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "template"
    assert body["model"] is None
    assert len(body["text"]) > 100


def test_scenario_changes_weights():
    base = client.get("/summary").json()["hazard"]["weights"]
    r = client.post("/scenario", json={"hazard_weights": {"glof": 0.7}, "use_calibrated_weights": True})
    assert r.status_code == 200
    w = r.json()["summary"]["hazard"]["weights"]
    assert w["glof"] > base["glof"]
    assert abs(sum(w.values()) - 1.0) < 0.02

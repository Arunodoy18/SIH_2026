import numpy as np
import pytest

from redzone.config import Settings
from redzone.data import store
from redzone.hazard import build_hazard
from redzone.hazard.grid import GRID
from redzone.ml import landslide_ml


@pytest.fixture(scope="module")
def trained():
    if not landslide_ml.is_available():
        pytest.skip("no trained model on disk — run `python -m redzone.ml.train_landslide_model`")
    return True


def test_model_metadata_reports_a_credible_auc(trained):
    meta = landslide_ml.load_metadata()
    assert meta is not None
    assert meta["model"] == "RandomForestClassifier"
    # a real AUC, not a coin flip and not suspiciously perfect for 6 coarse proxy features
    assert 0.6 < meta["roc_auc_test"] < 0.95
    assert set(meta["feature_importances"]) == {
        "slope", "rainfall_norm", "forest_norm", "river_dist_km", "fault_dist_km", "northness",
    }


def test_predict_field_shape_and_range(trained):
    habitations = store.load_interim("habitations")
    rivers = store.load_interim("rivers")
    faults = store.load_interim("faults")
    field = landslide_ml.predict_field(habitations, rivers, faults)
    assert field.shape == (GRID.ny, GRID.nx)
    assert np.all((field >= 0) & (field <= 1))


def test_build_hazard_uses_ml_by_default(trained):
    hz = build_hazard(Settings())
    assert hz.landslide_method == "ml"
    assert hz.landslide_model_metadata is not None


def test_build_hazard_falls_back_to_heuristic_when_requested():
    s = Settings()
    s.hazard.landslide_method = "heuristic"
    hz = build_hazard(s)
    assert hz.landslide_method == "heuristic"
    assert hz.landslide_model_metadata is None

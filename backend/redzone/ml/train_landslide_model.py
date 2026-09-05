"""Train a RandomForest landslide-susceptibility classifier on the inventory.

Standard LSM workflow: presence + pseudo-absence points, terrain/rainfall/land-cover
features, a binary classifier, evaluated by ROC-AUC on a held-out split. Swap
`generate_landslide_inventory.py`'s synthetic points for a real GSI/Bhukosh inventory and
this script is unchanged.

Run:  python -m redzone.ml.train_landslide_model
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import geopandas as gpd
import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from redzone.config import INTERIM_DIR, MODELS_DIR
from redzone.ml.features import FEATURE_NAMES

MODEL_PATH = MODELS_DIR / "landslide_rf.joblib"
METADATA_PATH = MODELS_DIR / "landslide_rf_metadata.json"


def main() -> None:
    path = INTERIM_DIR / "landslide_inventory.parquet"
    if not path.exists():
        raise SystemExit(
            "no inventory — run `python -m redzone.ml.generate_landslide_inventory` first"
        )
    gdf = gpd.read_parquet(path)

    X = gdf[list(FEATURE_NAMES)].to_numpy(dtype="float64")
    y = gdf["label"].to_numpy(dtype=int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42,
    )

    clf = RandomForestClassifier(
        n_estimators=300, max_depth=8, min_samples_leaf=5,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )
    t0 = time.time()
    clf.fit(X_train, y_train)
    fit_s = time.time() - t0

    proba_test = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba_test)
    importances = dict(zip(FEATURE_NAMES, np.round(clf.feature_importances_, 4).tolist()))

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    metadata = {
        "model": "RandomForestClassifier",
        "sklearn_version": sklearn.__version__,
        "features": list(FEATURE_NAMES),
        "n_train": len(y_train),
        "n_test": len(y_test),
        "n_presence": int(y.sum()),
        "n_absence": int((y == 0).sum()),
        "roc_auc_test": round(float(auc), 4),
        "feature_importances": importances,
        "fit_seconds": round(fit_s, 2),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_data": (
            "synthetic inventory (redzone/ml/generate_landslide_inventory.py) — replace "
            "with a real GSI/Bhukosh inventory for deployment"
        ),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    print(f"trained RandomForest on {len(y_train)} train / {len(y_test)} test points")
    print(f"  ROC-AUC (held-out): {auc:.3f}")
    print(f"  feature importances: {importances}")
    print(f"  saved -> {MODEL_PATH}")


if __name__ == "__main__":
    main()

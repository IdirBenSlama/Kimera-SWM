from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import numpy as np
from ..vault.database import ScarDB, GeoidDB
from ..core.native_math import NativeDistance
from ..utils.config import get_api_settings
from ..config.settings import get_settings
import logging

logger = logging.getLogger(__name__)

class AxisStabilityMonitor:
    """Calculate simplified global stability metrics for the MVP."""

    def __init__(self, db: Session):
        self.settings = get_api_settings()
        logger.debug(f"   Environment: {self.settings.environment}")
        self.db = db

    def get_stability_metrics(self) -> dict:
        """Return a dictionary of global stability metrics."""

        # Metric 1: Vault Pressure - recent knowledge consolidation rate
        recent_scars_count = self.db.query(ScarDB).filter(
            ScarDB.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)
        ).count()
        vault_pressure = min(recent_scars_count / 10.0, 1.0)

        # Metric 2: Semantic Cohesion - focus of recent geoids
        recent_geoids = (
            self.db.query(GeoidDB)
            .order_by(GeoidDB.geoid_id.desc())
            .limit(20)
            .all()
        )
        semantic_cohesion = 1.0
        if len(recent_geoids) > 1:
            try:
                vectors = [g.semantic_vector for g in recent_geoids if g.semantic_vector is not None]
                if len(vectors) > 1:
                    min_len = min(len(v) for v in vectors)
                    norm_vectors = [v[:min_len] for v in vectors]
                    # Compute pairwise cosine distances using native implementation
                    distances = NativeDistance.condensed_distances(norm_vectors, metric="cosine")
                    if distances:
                        avg_distance = float(np.mean(distances))
                        if not np.isnan(avg_distance):
                            semantic_cohesion = max(0.0, min(1.0, 1.0 - avg_distance))
            except Exception as e:
                # Fallback to default value if computation fails
                semantic_cohesion = 0.5

        # Metric 3: Entropic Stability - trend of entropy change
        recent_scars = (
            self.db.query(ScarDB)
            .order_by(ScarDB.timestamp.desc())
            .limit(20)
            .all()
        )
        entropic_stability = 0.5
        if recent_scars:
            avg_delta_entropy = float(np.mean([s.delta_entropy for s in recent_scars]))
            entropic_stability = (avg_delta_entropy + 1.0) / 2.0

        return {
            "vault_pressure": vault_pressure,
            "semantic_cohesion": semantic_cohesion,
            "entropic_stability": entropic_stability,
            "axis_convergence": semantic_cohesion,
            "vault_resonance": 1.0 - vault_pressure,
            "contradiction_lineage_ambiguity": vault_pressure,
        }


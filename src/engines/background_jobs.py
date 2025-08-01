from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Callable, Optional

from sqlalchemy.orm import Session

from ..vault.database import SessionLocal, ScarDB, GeoidDB
from ..utils.config import get_api_settings
from ..config.settings import get_settings

scheduler = BackgroundScheduler()
_embedding_fn: Optional[Callable[[str], list[float]]] = None

DECAY_RATE = 0.1
CRYSTAL_WEIGHT_THRESHOLD = 20.0


def decay_job() -> None:
    db: Session = SessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    scars = db.query(ScarDB).filter(ScarDB.last_accessed < cutoff).all()
    for scar in scars:
        scar.weight = max(scar.weight - DECAY_RATE, 0.0)
    db.commit()
    db.close()


def fusion_job() -> None:
    db: Session = SessionLocal()
    groups: defaultdict[str, list[ScarDB]] = defaultdict(list)
    for scar in db.query(ScarDB).all():
        groups[scar.reason].append(scar)
    for scars in groups.values():
        if len(scars) > 2:
            base = scars[0]
            base.weight = sum(s.weight for s in scars)
            for extra in scars[1:]:
                db.delete(extra)
    db.commit()
    db.close()


def crystallization_job() -> None:
    if _embedding_fn is None:
        return
    db: Session = SessionLocal()
    high_scars = db.query(ScarDB).filter(ScarDB.weight > CRYSTAL_WEIGHT_THRESHOLD).all()
    for scar in high_scars:
        geoid_id = f"CRYSTAL_{scar.scar_id}"
        if db.query(GeoidDB).filter(GeoidDB.geoid_id == geoid_id).first():
            continue
        vector = _embedding_fn(scar.reason)
        new_geoid = GeoidDB(
            geoid_id=geoid_id,
            symbolic_state={
                'type': 'crystallized_scar', 
                'principle': scar.reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            metadata_json={
                'source_scar_id': scar.scar_id, 
                'crystallization_date': datetime.now(timezone.utc).isoformat(),
                'created_by': 'crystallization_process'
            },
            semantic_state_json={},
            semantic_vector=vector,
        )
        db.add(new_geoid)
        scar.weight = 0.0
    db.commit()
    db.close()


def start_background_jobs(embedding_fn: Callable[[str], list[float]]) -> None:
    global _embedding_fn
    _embedding_fn = embedding_fn
    scheduler.add_job(decay_job, "interval", hours=1)
    scheduler.add_job(fusion_job, "interval", hours=2)
    scheduler.add_job(crystallization_job, "interval", hours=3)
    scheduler.start()


def stop_background_jobs() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


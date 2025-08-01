"""Graph helper functions for common node/relationship operations.

This is **not** an OGM.  It is a thin utility layer around *neo4j-driver* that
keeps Cypher in one place while allowing higher-level code (VaultManager,
UnderstandingVaultManager, API) to remain agnostic.

The philosophy is:
    • keep functions small & explicit (e.g. `create_geoid`, `get_geoid`)
    • pass/return **plain dicts** so callers are decoupled from the driver
    • embed Cypher in triple-quoted strings for readability and ease of
      migration scripts.

Only Geoid and Scar operations are provided for the first migration slice;
additional entities can be added incrementally.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

# Try to import Neo4j driver, but don't fail if it's not available
try:
    from neo4j import Transaction
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    # Create dummy class to avoid errors
    class Transaction: pass

from .session import get_session, is_neo4j_available

# Configure logging
logger = logging.getLogger(__name__)

__all__ = [
    "create_geoid",
    "get_geoid",
    "create_scar",
    "get_scar",
    "is_graph_available",
]

# ---------------------------------------------------------------------------
# Helper functions for property serialization
# ---------------------------------------------------------------------------

def _serialize_properties(props: Dict[str, Any]) -> Dict[str, Any]:
    """Convert dict/list properties to JSON strings for Neo4j storage."""
    serialized = {}
    for key, value in props.items():
        if isinstance(value, (dict, list)) and not isinstance(value, str):
            # Serialize complex types to JSON strings
            serialized[key] = json.dumps(value)
        else:
            # Keep primitive types as-is
            serialized[key] = value
    return serialized


def _deserialize_properties(props: Dict[str, Any]) -> Dict[str, Any]:
    """Convert JSON string properties back to dict/list."""
    deserialized = {}
    for key, value in props.items():
        if isinstance(value, str) and key in ['semantic_state', 'symbolic_state', 
                                               'metadata', 'metadata_json', 'geoids',
                                               'semantic_features', 'symbolic_content',
                                               'embedding_vector', 'semantic_vector',
                                               'scar_vector']:
            try:
                # Try to deserialize known JSON fields
                deserialized[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # If it fails, keep as string
                deserialized[key] = value
        else:
            deserialized[key] = value
    return deserialized

# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

def is_graph_available() -> bool:
    """Check if the graph database is available and connected."""
    return is_neo4j_available()

# ---------------------------------------------------------------------------
# Geoid helpers
# ---------------------------------------------------------------------------

def _tx_create_geoid(tx: Transaction, props: Dict[str, Any]) -> None:
    # Serialize complex properties before storing
    serialized_props = _serialize_properties(props)
    tx.run(
        """
        MERGE (g:Geoid {geoid_id: $geoid_id})
        SET g += $props
        """,
        geoid_id=serialized_props["geoid_id"],
        props={k: v for k, v in serialized_props.items() if k != "geoid_id"},
    )


def create_geoid(props: Dict[str, Any]) -> bool:
    """Create or update a :Geoid node.

    Parameters
    ----------
    props : dict
        Must include `geoid_id`; everything else becomes node properties.
        
    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    if not is_graph_available():
        logger.debug("Neo4j not available. Skipping geoid creation.")
        return False
        
    if "geoid_id" not in props:
        logger.error("create_geoid(): requires geoid_id in props")
        return False
        
    try:
        with get_session() as s:
            if s is None:
                return False
                
            s.write_transaction(_tx_create_geoid, props)
            return True
    except Exception as e:
        logger.warning(f"Failed to create geoid in Neo4j: {e}")
        return False


def _tx_get_geoid(tx: Transaction, geoid_id: str) -> Optional[Dict[str, Any]]:
    rec = tx.run(
        "MATCH (g:Geoid {geoid_id: $geoid_id}) RETURN g",
        geoid_id=geoid_id,
    ).single()
    if rec:
        # Deserialize properties when retrieving
        return _deserialize_properties(dict(rec["g"]))
    return None


def get_geoid(geoid_id: str) -> Optional[Dict[str, Any]]:
    """Get a geoid by ID.
    
    Parameters
    ----------
    geoid_id : str
        The ID of the geoid to retrieve.
        
    Returns
    -------
    Optional[Dict[str, Any]]
        The geoid data if found, None otherwise.
    """
    if not is_graph_available():
        logger.debug("Neo4j not available. Cannot get geoid.")
        return None
        
    try:
        with get_session() as s:
            if s is None:
                return None
                
            return s.read_transaction(_tx_get_geoid, geoid_id)
    except Exception as e:
        logger.warning(f"Failed to get geoid from Neo4j: {e}")
        return None

# ---------------------------------------------------------------------------
# Scar helpers
# ---------------------------------------------------------------------------

def _tx_create_scar(tx: Transaction, props: Dict[str, Any]) -> None:
    # Serialize complex properties before storing
    serialized_props = _serialize_properties(props)
    # Extract geoids before serialization (it's used in the query)
    geoids = props.get("geoids", [])
    
    # Create Scar node and relationships to involved geoids
    tx.run(
        """
        MERGE (s:Scar {scar_id: $scar_id})
        SET s += $props
        WITH s
        UNWIND $geoids AS gid
        MATCH (g:Geoid {geoid_id: gid})
        MERGE (s)-[:INVOLVES]->(g)
        """,
        scar_id=serialized_props["scar_id"],
        props={k: v for k, v in serialized_props.items() if k not in {"scar_id", "geoids"}},
        geoids=geoids,
    )


def create_scar(props: Dict[str, Any]) -> bool:
    """Create or update a :Scar node.
    
    Parameters
    ----------
    props : dict
        Must include `scar_id`; everything else becomes node properties.
        
    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    if not is_graph_available():
        logger.debug("Neo4j not available. Skipping scar creation.")
        return False
        
    if "scar_id" not in props:
        logger.error("create_scar(): requires scar_id in props")
        return False
        
    try:
        with get_session() as s:
            if s is None:
                return False
                
            s.write_transaction(_tx_create_scar, props)
            return True
    except Exception as e:
        logger.warning(f"Failed to create scar in Neo4j: {e}")
        return False


def _tx_get_scar(tx: Transaction, scar_id: str) -> Optional[Dict[str, Any]]:
    rec = tx.run("MATCH (s:Scar {scar_id: $sid}) RETURN s", sid=scar_id).single()
    if rec:
        # Deserialize properties when retrieving
        return _deserialize_properties(dict(rec["s"]))
    return None


def get_scar(scar_id: str) -> Optional[Dict[str, Any]]:
    """Get a scar by ID.
    
    Parameters
    ----------
    scar_id : str
        The ID of the scar to retrieve.
        
    Returns
    -------
    Optional[Dict[str, Any]]
        The scar data if found, None otherwise.
    """
    if not is_graph_available():
        logger.debug("Neo4j not available. Cannot get scar.")
        return None
        
    try:
        with get_session() as s:
            if s is None:
                return None
                
            return s.read_transaction(_tx_get_scar, scar_id)
    except Exception as e:
        logger.warning(f"Failed to get scar from Neo4j: {e}")
        return None

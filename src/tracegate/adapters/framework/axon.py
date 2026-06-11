"""Axon (event-sourcing) framework adapter: domain events + projections.

The event-sourcing-aware extractors are the IP no generic doc tool produces: the event
catalog (with emitters/handlers) and the projection canvas (with @ResetHandler
idempotence flagging). Wraps the proven Phase-0 collectors.
"""
from __future__ import annotations

from ...core.config import Config
from ... import generate_code_docs as cd


def sections(cfg: Config) -> dict[str, str]:
    g = cd.CodeDocs(cfg)
    events = g.collect_events()
    projections = g.collect_projections()
    return {
        "events": g.render_events(events),
        "projections": g.render_projections(projections),
        "events-graph": g.render_events_graph(events, projections),
    }

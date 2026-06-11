"""Spring framework adapter: HTTP endpoints + module canvas + config + ports.

Wraps the proven Phase-0 collectors. The Spring-specific value is the @*Mapping route
inventory (with Spring Cloud Contract matching), the Modulith module canvas, the
hexagonal ports matrix, the JTE template tree, and the property inventory.
"""
from __future__ import annotations

from ...core.config import Config
from ... import generate_code_docs as cd


def sections(cfg: Config) -> dict[str, str]:
    g = cd.CodeDocs(cfg)
    route_constants = g.collect_route_constants()
    contracts = g.load_contracts()
    endpoints = g.collect_endpoints(route_constants, contracts)
    modules = g.collect_modules()
    return {
        "http-endpoints": g.render_endpoints(endpoints),
        "modules": g.render_modules(modules),
        "modules-graph": g.render_modules_graph(modules),
        "domain-model": g.render_domain_model(g.collect_domain_model()),
        "ports": g.render_ports(g.collect_ports()),
        "templates": g.render_templates(g.collect_jte_templates()),
        "config": g.render_config(g.collect_config_properties()),
    }

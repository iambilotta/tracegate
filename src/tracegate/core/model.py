"""The catalog model — the language- and framework-neutral facts tracegate owns.

A `Requirement` is one test method (the tests-as-requirements IP). The `Spec`
holds its given/when/then plus optional ADR/US/AC traceability. `Catalog` is the
whole as-built picture: requirements plus the framework-extracted facts (endpoints,
events, ...) that adapters attach as opaque sections.

The ID is derived here (see `ids.py`), so the same `<CAT>-<module>.<Unit>#<method>`
shape works for Java, Python, or TypeScript: only the *parser* differs per language.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import ids


@dataclass
class Spec:
    """The structured spec of one test, parsed from its doc-comment tags."""

    given: str = ""
    when: str = ""
    then: str = ""
    adr: str = ""
    us: str = ""
    ac: str = ""  # acceptance criterion id (AC1, AC2, ...) within the cited US

    def is_complete(self) -> bool:
        return bool(self.given and self.when and self.then)


@dataclass
class Requirement:
    """One test method = one requirement.

    `category` is FR/NFR/INV/CON/E2E; `module` is the dotted module the test lives in
    (e.g. `auth.legacy`); `unit` is the class/file the test belongs to (suffix already
    stripped to a clean name); `method` is the test method/title; `file_rel` is the
    canonical repo-relative path (see `core.paths`).
    """

    category: str
    module: str
    unit: str          # clean class/file name, category suffix already stripped
    method: str
    file_rel: str
    spec: Spec = field(default_factory=Spec)

    @property
    def id(self) -> str:
        return ids.requirement_id(self.category, self.module, self.unit, self.method)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "module": self.module,
            "unit": self.unit,
            "method": self.method,
            "file": self.file_rel,
            "spec": {
                "given": self.spec.given,
                "when": self.spec.when,
                "then": self.spec.then,
                "adr": self.spec.adr,
                "us": self.spec.us,
                "ac": self.spec.ac,
                "complete": self.spec.is_complete(),
            },
        }


@dataclass
class Catalog:
    """The full as-built catalog for one target.

    `requirements` is the core IP. `sections` is a name -> rendered-markdown map the
    framework adapters fill (http-endpoints, events, schema, ...); the core renders
    requirements itself and treats the rest as opaque pre-rendered blocks so a new
    adapter never has to touch the renderer.
    """

    label: str
    requirements: list[Requirement] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)  # name -> markdown body
    # Section names derived from a BUILD ARTIFACT (e.g. coverage from a JaCoCo CSV that
    # only exists after `mvn verify`). The bool is whether that input was present at
    # generation time. The drift-gate (ADR-0008) regenerates these best-effort but does
    # NOT hard-fail when the input is absent: a clean checkout with no `target/` would
    # otherwise report a permanent false drift. Code-derived sections stay hard-gated.
    build_artifact_sections: dict[str, bool] = field(default_factory=dict)

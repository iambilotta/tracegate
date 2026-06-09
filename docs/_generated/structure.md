# Structure — `tracegate`

Convention-driven skeleton of the repository: the git-tracked files (respecting `.gitignore`, so no `node_modules` / `target` / build output), rendered as a tree. A single readable snapshot of where everything lives, for a human or an agent orienting in a fresh session. Regenerated on every commit like every `_generated` doc; the source of truth is the filesystem, never this markdown.

_82 tracked paths._

```
tracegate/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── _generated/
│   ├── requirements-by-us.md
│   ├── requirements.json
│   └── requirements.md
├── bin/
│   └── generate-requirements.sh
├── decisions/
│   ├── 0001-implementation-language.md
│   ├── 0002-adapter-spi.md
│   ├── 0003-traceability-id-schema.md
│   ├── 0004-config-and-autodetect.md
│   ├── 0005-commodity-boundary.md
│   ├── 0006-output-model-and-gate.md
│   ├── 0007-canonical-file-paths.md
│   ├── 0008-build-artifact-soft-gate.md
│   ├── 0009-zero-config-canonical-output.md
│   └── README.md
├── docs/
│   ├── _generated/
│   │   ├── adr-index.md
│   │   ├── coverage.md
│   │   ├── dependencies.md
│   │   ├── MANIFEST.md
│   │   ├── requirements-by-us.md
│   │   ├── requirements.json
│   │   ├── requirements.md
│   │   ├── structure.md
│   │   └── todo.md
│   └── INSTALL.md
├── packaging/
│   ├── build_binary.py
│   └── entry.py
├── src/
│   └── tracegate/
│       ├── adapters/
│       │   ├── framework/
│       │   │   ├── __init__.py
│       │   │   ├── axon.py
│       │   │   ├── commondocs.py
│       │   │   ├── flyway.py
│       │   │   ├── playwright.py
│       │   │   └── spring.py
│       │   ├── lang/
│       │   │   ├── __init__.py
│       │   │   ├── java.py
│       │   │   └── python.py
│       │   └── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── detect.py
│       │   ├── gate.py
│       │   ├── ids.py
│       │   ├── javadoc_render.py
│       │   ├── model.py
│       │   ├── orchestrator.py
│       │   ├── paths.py
│       │   ├── render.py
│       │   └── specdoc.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── check_spec_javadoc.py
│       ├── cli.py
│       ├── config.py
│       ├── diff_requirements.py
│       ├── generate_code_docs.py
│       ├── generate_dora.py
│       ├── generate_requirements.py
│       └── javadoc_render.py
├── tests/
│   ├── fixtures/
│   │   ├── gest-mini/
│   │   │   ├── e2e/
│   │   │   │   └── tests/
│   │   │   │       └── smoke.spec.ts
│   │   │   └── src/
│   │   │       └── test/
│   │   │           └── java/
│   │   │               └── it/
│   │   │                   └── housetreespa/
│   │   │                       └── gest/
│   │   │                           └── sample/
│   │   │                               └── domain/
│   │   │                                   ├── SampleInvariantTest.java
│   │   │                                   └── SampleTest.java
│   │   ├── py-mini/
│   │   │   ├── tests/
│   │   │   │   ├── test_invariant_sample.py
│   │   │   │   └── test_sample.py
│   │   │   └── pyproject.toml
│   │   └── expected-requirements.md
│   ├── test_adapter_java.py
│   ├── test_adapter_python.py
│   ├── test_convergence.py
│   ├── test_detect.py
│   ├── test_generate_requirements_golden.py
│   ├── test_orchestrator.py
│   └── test_structure.py
├── .gitignore
├── CLAUDE.md
├── Makefile
├── PLAN.md
├── PRODUCT.md
├── pyproject.toml
├── README.md
├── requirements.txt
└── tracegate.toml
```

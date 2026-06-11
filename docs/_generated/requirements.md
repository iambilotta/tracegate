# Requirements — tracegate

Auto-generated from test sources by tracegate. Do NOT edit by hand: edit the test javadoc / docstring instead and rerun. Single source of truth is the test code.

**Convention**: category from the test name (`*Test`=FR, `*NfrTest`=NFR, `*InvariantTest`=INV, `*ContractTest`=CON; Python file markers `*invariant*`/`*nfr*`/`*contract*` map the same way; Playwright E2E tests join as **E2E**). Spec from doc-comment tags `@spec.given` / `@spec.when` / `@spec.then` (plus optional `@spec.adr` / `@spec.us`). Tests without a complete spec are listed with `(spec missing)` so they're visible and lintable.

## Coverage

- Total tests scanned: **30**
- With complete spec javadoc: **19** (63%)
- FR: 30

## Module `tests`

### Functional Requirements

#### `FR-tests.test_adapter_java#test_class_name_suffix_drives_the_category`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_adapter_java.py`

#### `FR-tests.test_adapter_java#test_extracts_requirements_with_canonical_repo_relative_paths`

- **Given**: a Java JUnit test fixture under a repo root
- **When**: the java adapter extracts its requirements
- **Then**: every file path is canonical full repo-relative, never a truncated form
- **User Story**: US-004-canonical-paths
- **File**: `tests/test_adapter_java.py`

#### `FR-tests.test_adapter_java#test_undocumented_test_is_present_but_incomplete`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_adapter_java.py`

#### `FR-tests.test_adapter_python#test_extracts_a_documented_python_requirement`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_adapter_python.py`

#### `FR-tests.test_adapter_python#test_invariant_filename_routes_to_inv_category`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_adapter_python.py`

#### `FR-tests.test_adapter_python#test_undocumented_python_test_is_incomplete`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_adapter_python.py`

#### `FR-tests.test_convergence#test_check_is_green_without_jacoco_csv_but_still_catches_code_drift`

- **Given**: a clean checkout with NO build artifact (no target/jacoco.csv)
- **When**: the catalog is generated then `--check` runs, first in sync then after a code-derived file is tampered
- **Then**: the gate is GREEN in sync (coverage is soft-skipped, not a false drift) yet still exits 2 when a code-derived requirement is tampered
- **User Story**: US-004-build-artifact-soft-gate
- **File**: `tests/test_convergence.py`

#### `FR-tests.test_convergence#test_coverage_is_hard_gated_once_the_csv_is_present`

- **Given**: a JaCoCo CSV present on disk (a build ran)
- **When**: the catalog is generated then coverage.md is tampered and `--check` runs
- **Then**: the gate exits 2: coverage IS gated when its input exists
- **User Story**: US-004-build-artifact-soft-gate
- **File**: `tests/test_convergence.py`

#### `FR-tests.test_convergence#test_e2e_id_strips_spec_suffix_like_every_other_adapter`

- **Given**: a Playwright `*.spec.ts` E2E test
- **When**: the playwright adapter derives its requirement ID
- **Then**: the `.spec` suffix is stripped (`E2E-e2e.smoke#...`, not `...smoke.spec#...`)
- **User Story**: US-003-zero-config-convergence
- **File**: `tests/test_convergence.py`

#### `FR-tests.test_convergence#test_zero_config_catalog_equals_explicit_subcommands`

- **Given**: a repo with tests + framework + commodity sources
- **When**: `tracegate .` runs and the explicit requirements + code-docs subcommands run
- **Then**: both produce the IDENTICAL set of files with byte-identical content
- **User Story**: US-003-zero-config-convergence
- **File**: `tests/test_convergence.py`

#### `FR-tests.test_convergence#test_zero_config_emits_requirements_json_and_commodity_sections`

- **Given**: a repo detected with zero config
- **When**: `tracegate .` runs
- **Then**: the canonical catalog includes requirements.json AND the commodity sections (coverage, todo, adr-index, dependencies, MANIFEST)
- **User Story**: US-003-zero-config-convergence
- **File**: `tests/test_convergence.py`

#### `FR-tests.test_detect#test_detects_a_java_spring_app_with_flyway_and_axon`

- **Given**: a Maven repo with Spring + Axon deps and a Flyway migration dir
- **When**: zero-config detection runs
- **Then**: it enables the java language and the spring, axon and flyway adapters
- **User Story**: US-003-stack-detection
- **File**: `tests/test_detect.py`

#### `FR-tests.test_detect#test_detects_a_python_app_from_pyproject`

- **Given**: a directory with a pyproject.toml and .py files
- **When**: zero-config detection runs
- **Then**: it enables the python language adapter and not java
- **User Story**: US-003-stack-detection
- **File**: `tests/test_detect.py`

#### `FR-tests.test_detect#test_empty_dir_still_returns_one_config_so_a_run_never_no_ops`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_detect.py`

#### `FR-tests.test_detect#test_infers_the_java_package_root_from_the_single_child_chain`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_detect.py`

#### `FR-tests.test_detect#test_tracegate_toml_overrides_detected_frameworks`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_detect.py`

#### `FR-tests.test_diagrams#test_diagrams_are_drift_gated`

- **Given**: the generated diagrams on disk
- **When**: one diagram is tampered and `--check` runs
- **Then**: the drift-gate exits 2: the diagrams are hard-gated like every other doc
- **User Story**: US-005-architecture-diagrams
- **File**: `tests/test_diagrams.py`

#### `FR-tests.test_diagrams#test_diagrams_are_indexed_in_the_manifest`

- **Given**: a generated catalog
- **When**: the MANIFEST is rendered
- **Then**: it lists the three architecture diagrams under their topic groups
- **User Story**: US-005-architecture-diagrams
- **File**: `tests/test_diagrams.py`

#### `FR-tests.test_diagrams#test_domain_model_diagram_renders_records_sealed_and_enums`

- **Given**: a domain with a sealed interface (Status + permits), records, and enums
- **When**: the domain-model diagram is generated
- **Then**: domain-model.md is a Mermaid classDiagram with the sealed hierarchy (`<|--`), record fields, and `<<enumeration>>`-tagged enums with their constants
- **User Story**: US-005-architecture-diagrams
- **File**: `tests/test_diagrams.py`

#### `FR-tests.test_diagrams#test_event_choreography_diagram_wires_emitter_event_projection`

- **Given**: a domain event with an emitter call-site and a projection handler
- **When**: the event-choreography diagram is generated
- **Then**: events-graph.md is a Mermaid flowchart with emitter --emits--> event --handled by--> projection (group name shown), all derived from the AST
- **User Story**: US-005-architecture-diagrams
- **File**: `tests/test_diagrams.py`

#### `FR-tests.test_diagrams#test_module_map_diagram_renders_cross_module_dependencies`

- **Given**: two modules where `audit` imports from `sample`
- **When**: the module-map diagram is generated
- **Then**: modules-graph.md is a Mermaid flowchart with the cross-module arc, derived from the SAME import data modules.md lists (no new parsing), and a cycle verdict line
- **User Story**: US-005-architecture-diagrams
- **File**: `tests/test_diagrams.py`

#### `FR-tests.test_generate_requirements_golden#test_fixture_covers_the_three_behaviors_the_golden_pins`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_generate_requirements_golden.py`

#### `FR-tests.test_generate_requirements_golden#test_generator_output_matches_the_golden_file`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_generate_requirements_golden.py`

#### `FR-tests.test_orchestrator#test_check_on_missing_dir_reports_drift`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `tests/test_orchestrator.py`

#### `FR-tests.test_orchestrator#test_drift_gate_passes_when_in_sync_and_fails_after_edit`

- **Given**: a generated catalog on disk
- **When**: the drift-gate (--check) runs, first in sync then after a tamper
- **Then**: it exits 0 when in sync and 2 when a generated file drifted
- **User Story**: US-002-drift-gate
- **File**: `tests/test_orchestrator.py`

#### `FR-tests.test_orchestrator#test_zero_config_run_produces_md_and_json`

- **Given**: a target repo detected with zero config
- **When**: the orchestrator runs without --check
- **Then**: it writes requirements.md (humans) and requirements.json (machines)
- **User Story**: US-001-zero-config-run
- **File**: `tests/test_orchestrator.py`

#### `FR-tests.test_structure#test_structure_is_indexed_first_in_the_manifest`

- **Given**: a generated catalog
- **When**: the MANIFEST is rendered
- **Then**: it lists structure.md under the read-first Map group, so a fresh session orients from the repo tree before anything else
- **File**: `tests/test_structure.py`

#### `FR-tests.test_structure#test_structure_section_renders_a_convention_driven_tree`

- **Given**: a target repo (the py-mini fixture, no git, so the walk fallback runs)
- **When**: the orchestrator runs and emits the commodity structure section
- **Then**: structure.md renders an ASCII tree of the repo skeleton (tree connectors, a fenced block) and excludes build/dep dirs, never crashing on a plain dir
- **File**: `tests/test_structure.py`

#### `FR-tests.test_structure#test_tree_helper_handles_an_empty_repo`

- **Given**: no paths at all (an empty or fully-ignored repo)
- **When**: the tree is built and rendered
- **Then**: it yields an empty line list, never raising
- **File**: `tests/test_structure.py`

#### `FR-tests.test_structure#test_tree_helper_is_deterministic_and_lists_dirs_before_files`

- **Given**: a flat list of repo-relative paths mixing directories and files
- **When**: the tree is built and rendered
- **Then**: output is stable, nests by directory, and at each level directories come before files (so the snapshot reads like a `tree` command, not a flat dump)
- **File**: `tests/test_structure.py`

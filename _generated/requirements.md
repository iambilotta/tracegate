# Requirements — tracegate

Auto-generated from test sources by tracegate. Do NOT edit by hand: edit the test javadoc / docstring instead and rerun. Single source of truth is the test code.

**Convention**: category from the test name (`*Test`=FR, `*NfrTest`=NFR, `*InvariantTest`=INV, `*ContractTest`=CON; Python file markers `*invariant*`/`*nfr*`/`*contract*` map the same way; Playwright E2E tests join as **E2E**). Spec from doc-comment tags `@spec.given` / `@spec.when` / `@spec.then` (plus optional `@spec.adr` / `@spec.us`). Tests without a complete spec are listed with `(spec missing)` so they're visible and lintable.

## Coverage

- Total tests scanned: **16**
- With complete spec javadoc: **5** (31%)
- FR: 16

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

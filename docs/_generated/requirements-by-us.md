# Requirements — tracegate, grouped by User Story

Auto-generated companion to `requirements.md`. Tests link to a User Story via the javadoc tag `@spec.us=US-NNN-slug` (the slug points to a User Story defined in `PRODUCT.md`). Implementation-detail tests with no `@spec.us` are collected at the bottom; declared User Stories in PRODUCT.md with zero linked tests are listed as **not implemented yet**.

## Coverage

- Total tests scanned: **21**
- Tests linked to a User Story: **10**
- Tests without `@spec.us` (implementation detail): **11**
- User Stories declared in PRODUCT.md: **4**
- User Stories with at least one linked test: **4**
- User Stories declared but **not yet implemented**: **0**

## `US-001-zero-config-run`

- `FR-tests.test_orchestrator#test_zero_config_run_produces_md_and_json`
  - **Then**: it writes requirements.md (humans) and requirements.json (machines)

## `US-002-drift-gate`

- `FR-tests.test_orchestrator#test_drift_gate_passes_when_in_sync_and_fails_after_edit`
  - **Then**: it exits 0 when in sync and 2 when a generated file drifted

## `US-003-stack-detection`

- `FR-tests.test_detect#test_detects_a_java_spring_app_with_flyway_and_axon`
  - **Then**: it enables the java language and the spring, axon and flyway adapters
- `FR-tests.test_detect#test_detects_a_python_app_from_pyproject`
  - **Then**: it enables the python language adapter and not java

## `US-003-zero-config-convergence`  _(unknown to PRODUCT.md)_

- `FR-tests.test_convergence#test_e2e_id_strips_spec_suffix_like_every_other_adapter`
  - **Then**: the `.spec` suffix is stripped (`E2E-e2e.smoke#...`, not `...smoke.spec#...`)
- `FR-tests.test_convergence#test_zero_config_catalog_equals_explicit_subcommands`
  - **Then**: both produce the IDENTICAL set of files with byte-identical content
- `FR-tests.test_convergence#test_zero_config_emits_requirements_json_and_commodity_sections`
  - **Then**: the canonical catalog includes requirements.json AND the commodity sections (coverage, todo, adr-index, dependencies, MANIFEST)

## `US-004-build-artifact-soft-gate`  _(unknown to PRODUCT.md)_

- `FR-tests.test_convergence#test_check_is_green_without_jacoco_csv_but_still_catches_code_drift`
  - **Then**: the gate is GREEN in sync (coverage is soft-skipped, not a false drift) yet still exits 2 when a code-derived requirement is tampered
- `FR-tests.test_convergence#test_coverage_is_hard_gated_once_the_csv_is_present`
  - **Then**: the gate exits 2: coverage IS gated when its input exists

## `US-004-canonical-paths`

- `FR-tests.test_adapter_java#test_extracts_requirements_with_canonical_repo_relative_paths`
  - **Then**: every file path is canonical full repo-relative, never a truncated form

## Implementation detail (no `@spec.us` link)

These tests are valid requirements but exist below the user-story horizon (unit-level mechanism, internal invariant, white-box assertion). Add `@spec.us` if a user story should claim them.

### Module `tests`

- `FR-tests.test_adapter_java#test_class_name_suffix_drives_the_category`
- `FR-tests.test_adapter_java#test_undocumented_test_is_present_but_incomplete`
- `FR-tests.test_adapter_python#test_extracts_a_documented_python_requirement`
- `FR-tests.test_adapter_python#test_invariant_filename_routes_to_inv_category`
- `FR-tests.test_adapter_python#test_undocumented_python_test_is_incomplete`
- `FR-tests.test_detect#test_empty_dir_still_returns_one_config_so_a_run_never_no_ops`
- `FR-tests.test_detect#test_infers_the_java_package_root_from_the_single_child_chain`
- `FR-tests.test_detect#test_tracegate_toml_overrides_detected_frameworks`
- `FR-tests.test_generate_requirements_golden#test_fixture_covers_the_three_behaviors_the_golden_pins`
- `FR-tests.test_generate_requirements_golden#test_generator_output_matches_the_golden_file`
- `FR-tests.test_orchestrator#test_check_on_missing_dir_reports_drift`

# Requirements — gest-mini

Auto-generated from test sources by tracegate. Do NOT edit by hand: edit the test javadoc / docstring instead and rerun. Single source of truth is the test code.

**Convention**: category from the test name (`*Test`=FR, `*NfrTest`=NFR, `*InvariantTest`=INV, `*ContractTest`=CON; Python file markers `*invariant*`/`*nfr*`/`*contract*` map the same way; frontend vitest tests join as **FE**; Playwright E2E tests join as **E2E**). Spec from doc-comment tags `@spec.given` / `@spec.when` / `@spec.then` (plus optional `@spec.adr` / `@spec.us`). Tests without a complete spec are listed with `(spec missing)` so they're visible and lintable.

## Coverage

- Total tests scanned: **3**
- With complete spec javadoc: **2** (67%)
- FR: 2
- INV: 1

## Module `sample.domain`

### Functional Requirements

#### `FR-sample.domain.Sample#fully_documented_test_renders_in_the_catalog`

- **Given**: a golden input with `inline code` in the javadoc
- **When**: the generator parses this method
- **Then**: the spec renders with the code span converted to backticks
- **User Story**: US-001-sample-story
- **File**: `src/test/java/it/housetreespa/gest/sample/domain/SampleTest.java`

#### `FR-sample.domain.Sample#undocumented_test_is_flagged_as_spec_missing`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `src/test/java/it/housetreespa/gest/sample/domain/SampleTest.java`

### Domain Invariants

#### `INV-sample.domain.Sample#suffix_routes_to_the_invariant_category`

- **Given**: the Invariant class-name suffix
- **When**: the generator categorizes this test
- **Then**: it lands in the INV bucket, not FR
- **File**: `src/test/java/it/housetreespa/gest/sample/domain/SampleInvariantTest.java`

# Requirements — apps/gest

Auto-generated from JUnit test sources by `scripts/generate-requirements.sh`. Do NOT edit by hand: edit the test javadoc instead and rerun. Single source of truth is the test code.

**Convention**: category from class-name suffix (`*Test`=FR, `*NfrTest`=NFR, `*InvariantTest`=INV, `*ContractTest`=CON; the `*IT` Spring/Testcontainers variant suffix is orthogonal: `*NfrIT`/`*InvariantIT`/`*ContractIT` get the matching category). Playwright E2E tests (`apps/gest/e2e/tests/*.spec.ts`) join as **E2E**. Spec from javadoc / JSDoc tags `@spec.given` / `@spec.when` / `@spec.then` (plus optional `@spec.adr` / `@spec.us`). Tests without a complete spec are listed with `(spec missing)` so they're visible and lintable.

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
- **File**: `gest-mini/src/test/java/it/housetreespa/gest/sample/domain/SampleTest.java`

#### `FR-sample.domain.Sample#undocumented_test_is_flagged_as_spec_missing`

- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_
- **File**: `gest-mini/src/test/java/it/housetreespa/gest/sample/domain/SampleTest.java`

### Domain Invariants

#### `INV-sample.domain.Sample#suffix_routes_to_the_invariant_category`

- **Given**: the Invariant class-name suffix
- **When**: the generator categorizes this test
- **Then**: it lands in the INV bucket, not FR
- **File**: `gest-mini/src/test/java/it/housetreespa/gest/sample/domain/SampleInvariantTest.java`

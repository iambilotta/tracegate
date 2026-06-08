package it.housetreespa.gest.sample.domain;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/** Golden fixture: one fully-spec'd FR test + one spec-missing test. */
@Tag("unit")
class SampleTest {

    /**
     * @spec.given a golden input with {@code inline code} in the javadoc
     * @spec.when the generator parses this method
     * @spec.then the spec renders with the code span converted to backticks
     * @spec.us US-001-sample-story
     * @spec.ac AC1
     */
    @Test
    void fully_documented_test_renders_in_the_catalog() { }

    @Test
    void undocumented_test_is_flagged_as_spec_missing() { }
}

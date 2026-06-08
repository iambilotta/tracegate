package it.housetreespa.gest.sample.domain;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/** Golden fixture: class-name suffix drives the INV category. */
@Tag("unit")
class SampleInvariantTest {

    /**
     * @spec.given the Invariant class-name suffix
     * @spec.when the generator categorizes this test
     * @spec.then it lands in the INV bucket, not FR
     */
    @Test
    void suffix_routes_to_the_invariant_category() { }
}

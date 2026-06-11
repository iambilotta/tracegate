package it.housetreespa.gest.audit;

import it.housetreespa.gest.sample.domain.event.SampleCreated;
import org.axonframework.config.ProcessingGroup;
import org.axonframework.eventhandling.EventHandler;
import org.axonframework.eventhandling.ResetHandler;

/**
 * Read model of created samples, rebuildable from the stream. Golden fixture for the
 * projection node + the read-model link in the event-choreography graph. Lives in the
 * `audit` module so the module graph has a real cross-module dependency on `sample`.
 */
@ProcessingGroup("sample-audit")
public class SampleAuditProjection {

    /** Projects a created sample into the `sample_audit` read model. */
    @EventHandler
    void on(SampleCreated event) { }

    @ResetHandler
    void reset() { }
}

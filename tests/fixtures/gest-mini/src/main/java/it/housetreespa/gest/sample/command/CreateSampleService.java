package it.housetreespa.gest.sample.command;

import it.housetreespa.gest.sample.domain.SampleKind;
import it.housetreespa.gest.sample.domain.event.SampleCreated;
import java.util.UUID;

/** Emits {@link SampleCreated}. Golden fixture: the emitter site of the event-choreography graph. */
public final class CreateSampleService {

    public SampleCreated create(long id, SampleKind kind) {
        return new SampleCreated(id, kind, UUID.randomUUID());
    }
}

package it.housetreespa.gest.sample.domain.event;

import it.housetreespa.gest.sample.domain.SampleKind;
import java.util.UUID;

/** Domain event: a sample was created. Golden fixture for the event-choreography graph. */
public record SampleCreated(long sampleId, SampleKind kind, UUID correlationId) { }

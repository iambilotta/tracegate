package it.housetreespa.gest.sample.domain.status;

import java.time.Instant;

/**
 * Sum type for a sample's current status. Variant-specific payload makes invalid combinations
 * unrepresentable. Golden fixture for the domain-model class diagram (sealed + permits).
 */
public sealed interface Status permits
        Status.Planned,
        Status.Cancelled,
        Status.Executed {

    /** Default state on creation. */
    record Planned() implements Status { }

    /** A cancelled sample carries the reason and the moment. */
    record Cancelled(String reason, Instant cancelledAt) implements Status { }

    /** An executed sample carries the outcome and the moment. */
    record Executed(StatusKind outcome, Instant executedAt) implements Status { }
}

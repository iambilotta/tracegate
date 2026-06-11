package it.housetreespa.gest.sample.domain.status;

/** PII-free discriminator of a {@link Status}: the state without its variant payload. */
public enum StatusKind {
    PLANNED,
    CANCELLED,
    EXECUTED
}

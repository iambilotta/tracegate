package it.housetreespa.gest.sample.domain.status;

/**
 * The sample state machine as declared data: one constant per write operation, naming the
 * {@link StatusKind} the sample is in after it succeeds. Golden fixture for the
 * state-machine diagram (a `*Transition` enum whose constants carry a StatusKind argument).
 * A null argument means the operation asserts no single target state.
 */
public enum SampleTransition {

    /** CREATE: a new sample starts Planned. */
    CREATE(StatusKind.PLANNED),

    /** EDIT: a generic edit; the state is unchanged. */
    EDIT(null),

    /** CANCEL: the sample is cancelled. */
    CANCEL(StatusKind.CANCELLED),

    /** EXECUTE: the sample is executed. */
    EXECUTE(StatusKind.EXECUTED);

    private final StatusKind resultingStatus;

    SampleTransition(StatusKind resultingStatus) {
        this.resultingStatus = resultingStatus;
    }

    public StatusKind resultingStatus() {
        return resultingStatus;
    }
}

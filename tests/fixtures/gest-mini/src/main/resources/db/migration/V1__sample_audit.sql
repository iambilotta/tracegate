-- the sample_audit read model populated by the sample-audit projection
CREATE TABLE sample_audit (
    sample_id BIGINT PRIMARY KEY,
    kind VARCHAR(32) NOT NULL
);

# Decisions (ADR)

MADR-lite, supersede-mai-editare. Le porte a senso unico del piano (`../PLAN.md` sez. 5).

| ADR | Tema | Stato |
|---|---|---|
| [0001](./0001-implementation-language.md) | Linguaggio/distribuzione: Python core + binario (Nuitka) | **accepted (lean)** |
| [0002](./0002-adapter-spi.md) | SPI degli adapter (come un terzo aggiunge un linguaggio/framework) | **accepted** |
| [0003](./0003-traceability-id-schema.md) | Schema degli ID di tracciabilita' (generalizzato a qualsiasi linguaggio) | **accepted** |
| [0004](./0004-config-and-autodetect.md) | Formato config (`tracegate.toml`) + auto-deduzione dello stack | **accepted** |
| [0005](./0005-commodity-boundary.md) | Confine commodity-wrap (cosa si delega vs cosa si possiede) | **accepted (lean)** |
| [0006](./0006-output-model-and-gate.md) | Modello di output (markdown + JSON) + contratto del drift-gate | **accepted** |
| [0007](./0007-canonical-file-paths.md) | Path canonici: full repo-relative ovunque | **accepted** |
| [0008](./0008-build-artifact-soft-gate.md) | Sezioni da build-artifact (coverage) soft nel drift-gate | **accepted** |
| [0009](./0009-zero-config-canonical-output.md) | Zero-config E' il catalog canonico; i subcommand sono viste | **accepted** |

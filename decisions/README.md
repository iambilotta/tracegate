# Decisions (ADR)

MADR-lite, supersede-mai-editare. Le porte a senso unico del piano (`../PLAN.md` sez. 5).

| ADR | Tema | Stato |
|---|---|---|
| [0001](./0001-implementation-language.md) | Linguaggio/distribuzione: Python core + binario (Nuitka) | **accepted (lean)** |
| 0002 | SPI degli adapter (come un terzo aggiunge un linguaggio/framework) | proposed (da scrivere) |
| 0003 | Schema degli ID di tracciabilita' (generalizzare `<CAT>-<module>.<Class>#<method>` a qualsiasi linguaggio) | proposed |
| 0004 | Formato config (`tracegate.toml`) + strategia di auto-deduzione dello stack | proposed |
| 0005 | Confine commodity-wrap (cosa si delega vs cosa si possiede) | proposed |
| 0006 | Modello di output (markdown + JSON/llms.txt-style) + contratto del drift-gate | proposed |

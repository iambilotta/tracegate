# CLAUDE.md — tracegate (repo contract)

OSS iambilotta, Apache-2.0. Gemello disciplinare di spring-gdpr/spring-aiact.
Piano fondativo: `PLAN.md`. Strategia/posizionamento OSS: `~/knowledge/entities/iambilotta.md` (Atomi di autorita').

## Cos'e' (identita', non negoziabile)

tracegate e' il **layer verificabile** che tiene requisiti e codice **in lockstep**, drift-gated in CI,
e genera l'as-built catalog come **sottoprodotto**.
- **Il GATE e' il prodotto, i doc sono il sottoprodotto.** Output **deterministico**, mai LLM-generated.
- NON e' "un doc generator" (categoria affollata) ne' "contesto LLM per agenti" (ridondante/dannoso, ricerca 2026).
- E' ground-truth verificabile di cui umani e agenti si fidano + il diff dei requisiti sulle PR.

## Architettura (core universale + adapter)

- **core**: orchestrazione AST (tree-sitter) + modello catalogo + **drift-gate engine** + ID tracciabilita' + unificazione + MANIFEST + output (markdown + JSON).
- **adapters/lang**: java, typescript/js, python, php (tree-sitter per linguaggio).
- **adapters/framework**: spring, spring-modulith, axon, playwright, flyway, nextjs, laravel, ...
- **adapters/commodity**: **wrap-don't-reinvent** su SchemaSpy, springdoc/OpenAPI, Spring Modulith Documenter, log4brains, JaCoCo, mvn/npm, scanner TODO.
- **self**: tracegate documenta tracegate (dogfooding).

## Principi (hard)

- **Auto-deduttivo, zero-config**: rileva lo stack e abilita gli adapter da solo; al massimo `tracegate.toml` per override (convention-over-configuration).
- **La convenzione e' un ENHANCEMENT, non un prerequisito**: i requisiti si derivano da nomi/struttura dei test anche senza annotazioni; zero-config deve dare valore al primo run su un repo non istrumentato (load-bearing per l'adozione).
- **Pareto / wrap-don't-reinvent**: il core possiede solo il non-commodity (tests-as-requirements, ID tracciabilita', copertura per-US, drift-gate, adapter ES/Modulith/hexagonal). Il commodity si delega.
- **Il gate (`--check`) e' first-class**: exit code, commento PR del diff requisiti, fail-on-drift.
- **Output deterministico e machine-readable** (md + JSON): stesso albero, due rese.
- **DX alla Laravel**: batteries-included, un comando, installer per ecosistema.
- **Adapter solo per stack dogfoodati**, mai speculativi (HARVEST-FIRST).

## Implementazione

Core **Python + tree-sitter** (Pareto: cio' che gia' gira in housetree), distribuito come **singolo binario per-OS** (Nuitka), installer per-ecosistema. ADR-0001.

Layout reale (v1.1): `src/tracegate/core/` (model · ids · detect · gate · render · paths · orchestrator · config · specdoc) + `src/tracegate/adapters/lang/{java,python}` + `adapters/framework/{spring,axon,flyway,playwright,commondocs}`. Gli adapter espongono `extract(cfg)` (lang) o `sections(cfg)`/`requirements(cfg)`/`build_artifact_sections(cfg)` (framework), SPI in ADR-0002. L'output zero-config (`tracegate .`) E' il catalog canonico: i subcommand espliciti (`requirements`/`code-docs`) sono viste filtrate sullo stesso motore (ADR-0009), mai un code path separato. CLI zero-config: `tracegate [DIR] [--check] [--json]`.

## Governance (canon)

- ADR in `decisions/` (MADR-lite, supersede-mai-editare).
- Requisiti EARS to-be in `docs/requirements/` (dogfooding: + i propri tests-as-requirements).
- **Drift-gate su SE STESSO** nel CI di tracegate (la prova vivente del prodotto).
- SemVer + CHANGELOG keep-a-changelog + OSS hygiene (LICENSE Apache-2.0, CONTRIBUTING, SECURITY, CoC).
- Consumer dogfood: housetree (sostituisce `scripts/`), spring-gdpr, spring-aiact.

## Read order (sessione fredda)

`README.md` (DX + how-it-works) → `PLAN.md` → `decisions/` (ADR-0001..0009) → `docs/_generated/` (il self-catalog: tracegate documenta tracegate).

# tracegate — piano totale (prodotto + architettura + migrazione + PM)

Repo: `git@github.com:iambilotta/tracegate.git` (OSS iambilotta, Apache-2.0, gemello di spring-gdpr/spring-aiact).
Documento fondativo. Si itera; le decisioni lockate diventano ADR in `decisions/`.

## 1. Cos'è (posizionamento difendibile)

**tracegate e' il layer VERIFICABILE che tiene i requisiti e il codice in lockstep, e genera l'as-built catalog come sottoprodotto.**

NON e' "un altro doc generator" (categoria affollata: Pickles, Concordion, jboz).
NON e' "contesto LLM-generato per agenti" (ricerca 2026: il contesto generato puo' PEGGIORARE l'agente, ridondante con cio' che legge diretto).
E' il **GATE**: i tuoi test SONO i requisiti, machine-checked, **drift-gated in CI**, output **deterministico** (mai allucinato, sempre vero). E' il tipo di contesto che NON danneggia un agente perche' e' ground-truth verificata, non una congettura.

Una riga di vendita: **"your tests are your requirements; tracegate proves they never drift, in any stack."**

### Perche' conta nell'era agentica
- Gli agenti leggono il codice diretto, ma serve loro una **mappa fidata e sempre-vera** (non stale, non indovinata) e un **gate** che tenga l'intento umano (requisiti) e il codice allineati.
- tracegate fornisce la spina verificabile + il diff dei requisiti sulle PR: l'umano e l'agente vedono *cosa e' cambiato nei requisiti*, non solo nel codice.

### ICP (chi compra l'adozione)
- Team poliglotti che vogliono **tracciabilita' requisiti + governance** senza ALM pesante.
- Team compliance-conscious (gancio col dogfooding spring-gdpr/spring-aiact: la tracciabilita' e' evidenza).
- Chi lavora con agenti AI e vuole un contratto verificabile, non prosa generata.

### Assunzione piu' rischiosa (pd-discovery) e mitigazione
Rischio: l'adozione richiede una **convenzione** (oggi la javadoc `@spec`) = barriera.
Mitigazione (load-bearing per "adozione facile"): **auto-deduttivo prima di tutto**. tracegate deriva requisiti dai NOMI e dalla struttura dei test *anche senza* annotazioni; la convenzione `@spec`/equivalente e' un **enhancement opzionale**, non un prerequisito. Zero-config deve dare valore al primo run, su un repo non istrumentato.

## 2. Architettura (core universale + adapter)

```
tracegate
├── core            orchestrazione AST (tree-sitter) + modello catalogo + drift-gate engine + ID tracciabilita' + unificazione/normalizzazione + MANIFEST + output (md + JSON)
├── adapters/
│   ├── lang/       java · typescript/js · python · php           (tree-sitter per linguaggio)
│   ├── framework/  spring · spring-modulith · axon · playwright · flyway · nextjs · laravel · ...
│   └── commodity/  wrapper su tool esistenti (NON reinventare): schemaspy · springdoc/openapi · spring-modulith-documenter · log4brains · jacoco · mvn/npm · todo-scanner
└── self            tracegate documenta tracegate (dogfooding)
```

Principi NON negoziabili:
- **Auto-configurante / auto-deduttivo**: al run rileva lo stack (linguaggi presenti, framework via manifest/marker), abilita gli adapter giusti, **zero config**. Al massimo un `tracegate.toml` per override mirati (convention-over-configuration, DHH).
- **Pareto / wrap-don't-reinvent**: il core POSSIEDE cio' che e' IP (tests-as-requirements, ID tracciabilita', copertura per-US, drift-gate, unificazione, gli adapter ES/Modulith/hexagonal che nessuno fa). Per il commodity (schema, endpoint, moduli, adr, coverage, deps, todo) **delega** a SchemaSpy/springdoc/Modulith-Documenter/log4brains/JaCoCo/native/scanner. Il valore = il catalogo UNIFICATO + tracciabilita' + gate SOPRA, non la re-implementazione.
- **Output deterministico e machine-readable**: markdown (umani) + JSON/llms.txt-style (agenti/CI). Stesso albero, due rese.
- **Drift-gate first-class**: modalita' `--check` (exit code), commento PR del diff requisiti, fail-on-drift. E' il prodotto.
- **DX alla Laravel**: batteries-included, default sensati, un comando (`tracegate`), `tracegate init` opzionale, installer per ecosistema (composer/npm/pip/maven-plugin che fetchano il binario o il pacchetto).

Decisione (ADR-0001, lean): **core Python + packaging a binario**. Python PUO' produrre eseguibili standalone (Nuitka compila a C; PyInstaller/PyOxidizer/shiv bundlano runtime+deps), quindi si tiene cio' che gia' gira (Pareto, tree-sitter Python) E si distribuisce come **singolo binario per-OS** senza dipendenze, con installer per-ecosistema (composer/npm/pip/brew che fetchano il binario). Niente riscrittura Rust/Go (butterebbe il funzionante). Cautela reale (passata avversaria in ADR): size/startup del binario + bundling delle `.so` di tree-sitter.

## 3. Migrazione (da housetree/scripts → tracegate)

| Fase | Cosa | Esito |
|---|---|---|
| **0 — Harvest** | estrai i generatori esistenti (`generate_requirements.py`, `generate_code_docs.py`, wrapper bash, golden test) nel repo tracegate come **core v0 + adapter Java/Spring/Axon/Playwright/Flyway** (cio' che gia' gira) | tracegate v0 = quello che gia' funziona, isolato |
| **1 — Core/Adapter + zero-config** | refactor in core + adapter SPI; **rilevamento stack automatico**; zero-config default; output md+JSON | un comando su un repo qualsiasi produce valore |
| **2 — Poliglotta** | adapter per gli ecosistemi che servono al dogfooding: Python, Next.js, Laravel/PHP (Pareto: prima quelli usati davvero) | universale per i nostri asset |
| **3 — Commodity wrap** | adapter opzionali su SchemaSpy/springdoc/Modulith-Documenter/log4brains | smette di reinventare il commodity |
| **4 — Flip dei consumer** | housetree sostituisce `scripts/` con la dipendenza tracegate; **spring-gdpr e spring-aiact** lo adottano; tracegate documenta se stesso | dogfooding completo, housetree liberato dal non-core |
| **1.0 — Public** | MMP non MVP: slice stretta ed eccellente, README Diataxis, esempi per stack, launch | prodotto di cui andare fieri |

Ogni fase: gated, canon-governed (ADR + requisiti + test verdi), nessun big-bang.

## 4. Product management (governance canon)

- **Struttura repo canon-compliant** (come housetree/spring-*): `CLAUDE.md` (contratto tecnico), `decisions/` (ADR MADR-lite), `docs/requirements/` (EARS to-be), drift-gate **su se stesso**, SemVer, CHANGELOG keep-a-changelog, CI, OSS hygiene (LICENSE Apache-2.0, CONTRIBUTING, SECURITY, CoC).
- **Dogfooding totale**: tracegate usa tracegate (tests-as-requirements + drift-gate nel suo CI). E' la prova vivente del prodotto + il self-documenting che chiedevi.
- **Roadmap**: v0 harvest → v0.x core+adapter+zero-config → v0.y poliglotta → v0.z commodity-wrap → **v1.0 public**.
- **DX/adozione** (il "vende ad altri dev"): install one-command per ecosistema, zero-config che da' valore al primo run, README eccellente (tutorial 5-min + how-to + reference + explanation), esempi runnable per Spring/Python/Next.js/Laravel.
- **Marketing** (leggero, MMP): messaggio "verifiable spec-traceability + drift-gate, polyglot, for the agentic era"; launch solo quando v1.0 e' genuinamente buono.
- **Metrica che conta**: non le stelle, ma "cattura drift e gap di requisiti che sarebbero passati" (il valore reale, dimostrabile sui nostri repo).

## 5. ADR da scrivere (le porte a senso unico)

- ADR-0001 linguaggio/distribuzione (Python vs binario Rust/Go).
- ADR-0002 SPI degli adapter (come un terzo aggiunge un linguaggio/framework).
- ADR-0003 schema degli ID di tracciabilita' (generalizzare il `<CAT>-<module>.<Class>#<method>` Java a qualsiasi linguaggio).
- ADR-0004 formato config + strategia di auto-deduzione dello stack.
- ADR-0005 confine commodity-wrap (cosa deleghiamo vs cosa possediamo).
- ADR-0006 modello di output (md + JSON/llms.txt) e contratto del drift-gate.

## 6. Rischi (top-5, sw-management)

| Rischio | Mitigazione |
|---|---|
| Categoria affollata, me-too | wedge = il GATE verificabile, non i doc; deterministico vs LLM-generated |
| Adozione frenata dalla convenzione | auto-deduttivo senza annotazioni; convenzione = enhancement |
| Manutenzione di N adapter da soli | core stretto + SPI; adapter solo per stack dogfoodati; community per il resto |
| Over-engineering "universale" | Pareto: parti da cio' che gira; adapter on-demand, mai speculativi |
| Tempo/fuoco (e' un side asset) | MMP, slice stretta; il dogfooding in housetree/spring-* lo fa maturare gratis |

---
Prossimo passo operativo: aprire il repo con la struttura canon (CLAUDE.md + decisions/ + i 6 ADR-stub) e la Fase 0 (harvest dei generatori esistenti). Da fare quando Francesco da' il via, dopo il PR del riallineamento housetree.

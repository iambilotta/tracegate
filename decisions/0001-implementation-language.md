# ADR-0001 — Implementation language: Python core + binary packaging

Status: **accepted (lean)** 2026-06-08. Owner: Francesco. Scope: come si implementa e si distribuisce tracegate.
Significativita': senso-unico-leggero (cambiare linguaggio dopo = riscrivere; la distribuzione e' reversibile).

## Context

tracegate nasce dall'**estrazione dei generatori esistenti** (Python + tree-sitter) gia' in
esercizio in housetree (`scripts/generate_*.py`): Pareto dice di partire da cio' che gira.
Ma "adozione facile cross-stack" (un dev Laravel/Next.js/Spring deve poterlo installare ed
eseguire senza un ambiente Python) spinge verso una distribuzione **senza dipendenze**.

La domanda chiave: da Python si fanno eseguibili? **Si'**: Nuitka compila a C (eseguibile
nativo), PyInstaller/PyOxidizer/shiv bundlano runtime+deps in un singolo file. Quindi non
serve riscrivere in Rust/Go.

## Decision

- **Core in Python + tree-sitter** (si tiene cio' che gia' funziona, zero riscrittura).
- **Distribuzione come singolo binario per-OS** via **Nuitka** (PyInstaller/PyOxidizer come fallback).
- **Installer per-ecosistema** che fetchano il binario: `brew`, `npm`/`npx`, `pip`/`pipx`, `composer`, eventuale Maven plugin wrapper. DX "scarica-ed-esegui".

## Alternatives considered

- **Riscrittura Rust/Go + tree-sitter**: scartata. Butterebbe il codice funzionante, allunga il time-to-value, e tree-sitter ha ottimi binding Python; il vantaggio (binario piu' piccolo/veloce) non giustifica la riscrittura a questa fase.
- **Solo `pip install`**: scartata come default. Richiede un ambiente Python = frizione d'adozione per dev non-Python (l'opposto della DX Laravel). Resta come canale secondario per chi ha gia' Python.

## Consequences

- + Si parte da cio' che gira (Pareto) **e** si ottiene distribuzione senza dipendenze.
- - Da validare con passata avversaria prima di lockare: **size e startup** del binario Nuitka, e il **bundling delle `.so`** dei grammar tree-sitter dentro il binario (rischio principale).
- Reversal cost: distribuzione bassa (cambiare packager); linguaggio del core alto (ma resta Python).

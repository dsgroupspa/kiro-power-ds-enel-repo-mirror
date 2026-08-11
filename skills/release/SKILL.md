---
name: release
description: Esegue la release di un'app mirror (avvio pipeline, attesa esito, clone locale o report errori)
---

# Release di un'app mirror

## Step 1: identifica app e versione

Se l'utente non li ha indicati, usa il tool `list_apps` per mostrare le app
disponibili e chiedi la versione (formato tipico `1.15.14-0_IT`;
MOBAUTH usa `8.2.7`).

## Step 2: avvia la pipeline

Chiama `start_release(app, version)` e comunica subito all'utente l'URL
della pipeline restituito.

## Step 3: attendi l'esito

Chiama `release_status(uuid, wait_seconds=240)` e ripeti finche' lo stato
non e' COMPLETED. Informa l'utente che l'attesa tipica e' di 2-5 minuti.

## Step 4a: successo

Chiama `clone_mirror(app, version)` e apri la cartella restituita
eseguendo: `kiro "<cartella>"`.

## Step 4b: fallimento

Mostra all'utente il blocco "ERRORI DA SEGNALARE AL TEAM DI SVILUPPO"
cosi' com'e', con l'URL della pipeline, e digli di inoltrarlo ai dev.
NON riprovare automaticamente: gli errori indicano ref/tag mancanti che
devono essere sistemati dal team.

## Credenziali

Se un tool segnala credenziali mancanti, chiedi all'utente email Atlassian
e API token personale (link e scope sono nel messaggio del tool) e chiama
`setup_credentials`. Non mostrare mai il token nelle risposte.

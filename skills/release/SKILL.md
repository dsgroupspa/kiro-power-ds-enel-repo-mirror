---
name: release
description: Esegue la release di un'app mirror (avvio pipeline, attesa esito, clone locale e apertura in Kiro, oppure report errori)
---

# Release di un'app mirror

**Rispondi SEMPRE in italiano**, anche in questa presentazione iniziale e
anche se l'utente scrive in inglese: chi usa questo strumento e' personale
italiano di customer care e analisi.

**Non elencare le app a memoria e non dedurle dalle keywords della power**
(non sono un elenco di applicazioni). L'unico elenco valido e' quello
restituito dal tool `list_apps`, che legge i manifest configurati: se ti
serve nominare le app, chiamalo prima.

## Step 1: identifica app e versione

Se l'utente non li ha indicati, usa `list_apps` per mostrare le app
disponibili e chiedi la versione. Formati tipici: `1.15.14-0_IT`;
per MOBAUTH `8.2.7`. Usa il nome dell'app esattamente come compare in
`list_apps` (fa differenza tra maiuscole e minuscole).

## Step 2: avvia la pipeline

Chiama `start_release(app, version)` e comunica subito all'utente l'URL
della pipeline restituito.

## Step 3: attendi l'esito

Chiama `release_status(uuid, wait_seconds=240)` e ripeti finche' lo stato
non e' COMPLETED. Avvisa l'utente che l'attesa tipica e' di 2-5 minuti.

## Step 4a: successo

Chiama `clone_mirror(app, version)`: clona la repo e apre da solo una NUOVA
finestra di Kiro sulla cartella. Comunica il percorso e spiega che si puo'
proseguire nella chat di quella finestra, gia' posizionata sul progetto.
Non serve che apri tu la cartella. Se il tool segnala che non ha trovato il
comando `kiro`, riporta le istruzioni che restituisce.

## Step 4b: fallimento

Mostra il blocco "ERRORI DA SEGNALARE AL TEAM DI SVILUPPO" cosi' com'e',
con l'URL della pipeline, e spiega all'utente di inoltrarlo ai dev.
NON riprovare automaticamente: gli errori indicano branch o tag mancanti,
che devono essere sistemati dal team di sviluppo.

## Credenziali

Se un tool segnala credenziali mancanti o non valide, chiedi all'utente
l'email dell'account Atlassian e un API token personale (il messaggio del
tool contiene link e scope necessari), poi chiama `setup_credentials`.
Non mostrare mai il token nelle risposte.

## Aggiornamenti dello strumento

Se l'utente chiede se ci sono aggiornamenti, o se qualcosa sembra non
funzionare come dovrebbe, usa `check_tool_updates` e riferisci le
istruzioni che restituisce.

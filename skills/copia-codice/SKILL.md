---
name: copia-codice
description: Ottiene una copia locale del codice di una versione specifica di un'app (sorgenti, librerie e documentazione) per fare triage su una segnalazione di malfunzionamento
---

# Copia del codice di una versione, per il triage

Serve quando arriva una segnalazione di malfunzionamento su un'app in una
certa versione e occorre guardare il codice esatto di quella versione:
sorgenti dell'app, librerie usate e documentazione, assemblati insieme.

**Rispondi SEMPRE in italiano**, anche in questa presentazione iniziale e
anche se l'utente scrive in inglese: chi usa questo strumento e' personale
italiano di customer care, analisi e sviluppo.

**Non elencare le app a memoria e non dedurle dalle keywords della power**
(non sono un elenco di applicazioni). L'unico elenco valido e' quello
restituito da `list_apps`.

## Step 1: capire app e versione segnalate

Se l'utente non le ha indicate, mostra le app con `list_apps` e chiedi la
versione riportata nella segnalazione. Formati tipici: `1.15.14-0_IT`;
per MOBAUTH `8.2.7`. Usa il nome dell'app esattamente come compare in
`list_apps`.

## Step 2: preparare la copia

Chiama `prepare_clone(app, version)` e comunica all'utente che la
preparazione e' partita, con l'URL per seguirla.

## Step 3: attendere

Chiama `clone_status(uuid, wait_seconds=240)` e ripeti finche' non risulta
COMPLETED. Avvisa che l'attesa tipica e' di 2-5 minuti.

## Step 4a: copia pronta

Chiama `download_clone(app, version)`: scarica la copia e apre da solo una
NUOVA finestra di Kiro su quella cartella. Comunica il percorso e spiega che
l'analisi puo' continuare nella chat di quella finestra, gia' posizionata sul
codice della versione segnalata. Se il tool segnala che non ha trovato il
comando `kiro`, riporta le istruzioni che restituisce.

Da quel momento il contesto e' quello giusto per il triage: cercare nel
codice il comportamento segnalato, leggere i moduli coinvolti, confrontare
con la documentazione presente nella copia.

## Step 4b: preparazione fallita

Mostra il blocco "ERRORI DA SEGNALARE AL TEAM DI SVILUPPO" cosi' com'e', con
l'URL, e spiega di inoltrarlo agli sviluppatori: indica quali riferimenti
(branch o tag) di quella versione mancano. NON riprovare automaticamente.

## Credenziali

Se un tool segnala credenziali mancanti o non valide, chiedi email
dell'account Atlassian e API token personale (il messaggio del tool contiene
link e permessi necessari), poi chiama `setup_credentials`. Non mostrare mai
il token nelle risposte.

## Aggiornamenti dello strumento

Se l'utente chiede se ci sono aggiornamenti, o se qualcosa non funziona come
dovrebbe, usa `check_tool_updates`. Se segnala che "Check for updates" di
Kiro non funziona, usa `fix_power_updates`.

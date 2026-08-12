---
name: prerequisiti
description: Verifica e installa i prerequisiti della power (Git e Python 3) quando gli strumenti non risultano disponibili, guidando l'utente passo passo. Tutte le spiegazioni vanno date in italiano.
---

# Installazione guidata dei prerequisiti

Usa questa procedura quando **gli strumenti della power non sono
disponibili** (il server MCP non risulta connesso, oppure l'utente dice che
la power non funziona / non compare nessuno strumento). Nella quasi totalita'
dei casi manca **Python 3** oppure Kiro e' stato avviato prima della sua
installazione.

**Parla sempre in italiano e in modo semplice**, anche se l'utente scrive in
inglese: intestazioni, elenco dei prerequisiti e messaggi vanno in italiano
(scrivi "Prerequisiti", non "Requirements"). L'utente puo' non essere
tecnico: spiega cosa stai per fare prima di farlo.

## Step 1: verifica cosa manca

Esegui nel terminale (PowerShell) questi comandi, uno per volta, e riporta
all'utente il risultato in modo comprensibile:

    git --version
    python --version
    py -3 --version

Se un comando risponde con un numero di versione, quel prerequisito c'e'.
Se risponde "termine non riconosciuto" (o simile), manca.

Se **tutti** rispondono correttamente, il problema non e' l'assenza dei
programmi: passa allo Step 4.

## Step 2: chiedi il consenso e installa

Spiega all'utente che serve installare un programma sul suo PC e **chiedi
conferma prima di procedere**. Poi esegui solo cio' che serve:

Python 3 (il caso piu' frequente):

    winget install --id Python.Python.3.12 -e --scope user --accept-package-agreements --accept-source-agreements

Git (se mancava):

    winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements

Note da riferire all'utente se compaiono problemi:

- Se `winget` non esiste, l'installazione va fatta a mano da
  https://www.python.org/downloads/windows/ spuntando
  **"Add python.exe to PATH"**.
- Se l'azienda blocca le installazioni, serve aprire una richiesta all'IT:
  in quel caso di' esattamente cosa chiedere ("Python 3 per l'utente
  corrente, con aggiunta al PATH").

## Step 3: verifica l'installazione

Esegui di nuovo:

    py -3 --version

Se risponde con la versione, l'installazione e' andata a buon fine.

## Step 4: riavvio di Kiro (necessario)

Spiega all'utente che **deve chiudere e riaprire Kiro**: i programmi appena
installati vengono riconosciuti solo dalle finestre aperte dopo
l'installazione. Questo vale anche quando Python era gia' presente ma Kiro
era stato avviato prima.

Dopo il riavvio, invita l'utente a riprovare: se gli strumenti compaiono, si
puo' procedere con la skill `copia-codice`.

## Step 5: se ancora non funziona

Chiedi all'utente di aprire in Kiro il pannello **MCP Servers**, cercare il
server della power e riportare il messaggio di errore che vede: il launcher
della power scrive lì il motivo esatto (per esempio "Python 3 non trovato").
Con quel messaggio, invita l'utente a contattare il team di sviluppo,
riportandolo integralmente.

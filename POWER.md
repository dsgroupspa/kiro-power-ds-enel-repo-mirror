---
name: "DS Group - Mirror Repository per progetti Enel"
description: "Triage delle segnalazioni sulle app mobile realizzate da DS Group per il cliente Enel. Procura in locale una copia del codice di una versione specifica (app, librerie e documentazione assemblati) e la apre in Kiro per analizzare il malfunzionamento."
author: "DS Group S.p.A."
version: 1.8.2
keywords:
  - "enel"
  - "forcebeat"
  - "segnalazione"
  - "malfunzionamento"
  - "bug"
  - "anomalia"
  - "triage"
  - "analisi codice"
  - "verifica versione"
  - "copia codice"
  - "scarica app"
  - "versione app"
  - "mirror"
  - "bitbucket"
  - "mece"
  - "medi"
  - "megm"
  - "mere"
  - "mesi"
  - "meve"
  - "smdp"
  - "smpr"
  - "smtu"
  - "mobauth"
  - "trace"
---

# DS Group - Mirror Repository per progetti Enel

> **LINGUA: SEMPRE ITALIANO.** Ogni risposta, presentazione, elenco di
> prerequisiti, messaggio di errore e riepilogo va scritto in italiano,
> anche se l'utente scrive in inglese e anche quando riassumi il contenuto
> di questo documento. Non tradurre in inglese i titoli delle sezioni
> ("Prerequisiti", "Requisiti", "Come si usa") e non usare formule inglesi
> tipo "Requirements" o "Prerequisites". Gli utenti sono personale italiano
> di customer care, analisi e sviluppo.

## A cosa serve

Quando arriva una segnalazione di malfunzionamento su un'app in una certa
versione, questa power procura in locale una copia del codice di quella
esatta versione (sorgenti dell'app, librerie usate e documentazione
assemblati insieme) e la apre in una nuova finestra di Kiro, pronta per
l'analisi.

Non serve a preparare rilasci: le copie sono generate e di sola lettura.

## Ambito

Solo le app mobile realizzate da DS Group per il cliente Enel (progetti
ForceBeat e affini), i cui sorgenti risiedono in repository privati sul
Bitbucket Server di Enel e sul workspace Bitbucket Cloud di DS Group.
Serve un accesso autorizzato a entrambi. Installare la power non concede
alcun accesso al codice. Per progetti di altri clienti non e' applicabile.

## Come si usa

Scrivi in chat, per esempio:

    di quali app posso avere il codice?
    mi serve il codice di MECE versione 1.15.14-0_IT, ho una segnalazione

Il flusso e' descritto nella skill `copia-codice`:

1. `list_apps` - elenco delle app configurate (unico elenco valido: non
   dedurre i nomi dalle keywords)
2. `prepare_clone(app, version)` - prepara la copia della versione indicata
3. `clone_status(uuid, wait_seconds=240)` - attende l'esito (2-5 minuti)
4. `download_clone(app, version)` - scarica la copia e la apre in una nuova
   finestra di Kiro
5. se la preparazione fallisce, mostra all'utente il blocco "ERRORI DA
   SEGNALARE AL TEAM DI SVILUPPO" cosi' com'e', senza riprovare da solo

## Prerequisiti

- **Git** e **Python 3** installati sul PC. Se mancano, da PowerShell:
  `winget install --id Git.Git -e` e
  `winget install --id Python.Python.3.12 -e`, poi chiudere e riaprire Kiro.
- Un account Bitbucket Cloud con accesso al workspace DS Group
  (dsteamdev), con API token personale (permessi di lettura/scrittura su
  repository e pipeline). Al primo utilizzo la power guida la
  configurazione: le credenziali restano solo sul PC dell'utente nel file
  `~/.ds-release.conf`.
- NON serve alcun accesso al Bitbucket di Enel: i repository del cliente
  vengono letti dalla pipeline su repo-mirror, con un token configurato
  lato server. Se l'utente chiede se gli servono credenziali Enel, la
  risposta e' no.

## Se gli strumenti non sono disponibili

Se in chat non risulta disponibile alcuno strumento di questa power, manca
un prerequisito sul PC (quasi sempre Python 3, oppure Kiro e' stato aperto
prima di installarlo). NON limitarti a segnalarlo: segui la skill
`prerequisiti`, che verifica Git e Python 3 nel terminale, li installa con
il consenso dell'utente tramite `winget` e spiega il riavvio di Kiro.
Procedura sintetica:

1. verifica: `git --version`, `python --version`, `py -3 --version`
2. se manca Python, con il consenso dell'utente:
   `winget install --id Python.Python.3.12 -e --scope user --accept-package-agreements --accept-source-agreements`
3. verifica con `py -3 --version`
4. chiedi all'utente di chiudere e riaprire Kiro, poi riprovare

## Note

- Le copie scaricate sono generate: non committarci modifiche, andrebbero
  perse. Le correzioni si fanno nei repository di sviluppo.
- Aggiornamenti della power: Powers > Check for updates, oppure chiedendo
  in chat "ci sono aggiornamenti?" (tool `check_tool_updates`).

# Copia codice per triage - Kiro Power

Power per Kiro che serve a **indagare le segnalazioni di malfunzionamento**
sulle app mobile realizzate da DS Group per il cliente Enel: dato il nome di
un'app e la versione segnalata, procura in locale una copia del codice di
quella esatta versione (sorgenti, librerie e documentazione assemblati) e la
apre in una nuova finestra di Kiro, pronta per l'analisi.

Non serve a preparare rilasci: le copie sono generate e di sola lettura.

## Ambito e prerequisiti di accesso

**Strumento interno.** Funziona solo per i progetti Enel di DS Group, i cui
sorgenti risiedono in repository PRIVATI sul Bitbucket Server di Enel e sul
workspace Bitbucket Cloud di DS Group. Senza credenziali autorizzate su
entrambi non e' utilizzabile: installarla non da' alcun accesso al codice.
Per progetti di altri clienti non e' applicabile.

## Installazione

Kiro > pannello Powers > **Add Custom Power** > *Import power from GitHub* >
incolla l'URL di questo repository > **Install**.

## Aggiornamenti

Kiro > Powers > la power > **Check for updates** > *Install updates*.
In chat puoi anche chiedere "ci sono aggiornamenti?" (tool `check_tool_updates`).

## Uso

Scrivi in chat a Kiro, ad esempio:

    di quali app posso avere il codice?
    mi serve il codice di <APP> versione <VERSIONE>, ho una segnalazione

## Requisiti

- Kiro con supporto Powers, `git` e `python3` nel PATH
- Un account Bitbucket autorizzato sul workspace DS Group e sul Bitbucket
  Server di Enel, con un API token con permessi di lettura/scrittura su
  repository e pipeline (la power guida la configurazione al primo utilizzo)

Le credenziali restano solo sul PC dell'utente (`~/.ds-release.conf`, permessi 600).
Questo repository contiene esclusivamente il tooling: nessun codice
applicativo, nessuna credenziale.

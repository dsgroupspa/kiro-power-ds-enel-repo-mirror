# ds-release - Kiro Power

Power per Kiro che automatizza la preparazione delle repo "mirror" delle app
mobile: avvia la pipeline di build su Bitbucket, ne monitora l'esito, clona in
locale il risultato e riporta gli eventuali errori da segnalare al team.

## Installazione

Kiro > pannello Powers > **Add Custom Power** > *Import power from GitHub* >
incolla l'URL di questo repository > **Install**.

## Aggiornamenti

Kiro > Powers > la power > **Check for updates** > *Install updates*.
In chat puoi anche chiedere "ci sono aggiornamenti?" (tool `check_tool_updates`).

## Uso

Scrivi in chat a Kiro, ad esempio:

    che app posso rilasciare?
    fammi la release di <APP> <VERSIONE>

## Requisiti

- Kiro con supporto Powers, `git` e `python3` nel PATH
- Un account Bitbucket con accesso al workspace aziendale e un API token con
  scope `read/write:repository:bitbucket` e `read/write:pipeline:bitbucket`
  (la power guida la configurazione al primo utilizzo)

Le credenziali restano solo sul PC dell'utente (`~/.ds-release.conf`, permessi 600).
Questo repository contiene esclusivamente il tooling: nessun codice applicativo,
nessuna credenziale.

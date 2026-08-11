# Triage sul codice delle app DS Group

**Lingua: rispondi sempre in italiano** quando usi questa power (utenti
italiani di customer care, analisi e sviluppo), anche nell'onboarding.

A cosa serve: quando arriva una segnalazione di malfunzionamento su un'app
in una certa versione, questa power procura in locale una copia del codice
di quella esatta versione (app + librerie + documentazione), cosi' che si
possa indagare sul codice giusto invece di ricostruirlo a mano.
Non e' uno strumento per preparare rilasci.

Quando l'utente parla di "segnalazione", "malfunzionamento", "bug",
"analizzare/verificare il codice di una versione", "scaricare un'app",
usa i tool del server MCP `ds-release` seguendo la skill `copia-codice`.

Regole:

- L'elenco delle app disponibili si ottiene SOLO con `list_apps`: le
  keywords della power non sono un elenco di applicazioni.
- Le copie scaricate sono GENERATE a partire dalle repo originali: sono per
  sola lettura e analisi. Ricorda all'utente di non committarci modifiche:
  andrebbero perse e non arriverebbero comunque al codice reale. Le
  correzioni vanno fatte nei repo di sviluppo.
- Se la preparazione fallisce, mostra il riepilogo integrale: elenca i
  riferimenti mancanti di quella versione e serve al team di sviluppo.
- Non riprovare da solo una preparazione fallita per riferimenti mancanti.
- Aggiornamenti dello strumento: `check_tool_updates`; se "Check for
  updates" di Kiro non funziona: `fix_power_updates`.

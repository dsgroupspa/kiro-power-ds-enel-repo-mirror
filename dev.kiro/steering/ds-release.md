# Release app mirror DS Group

**Lingua: rispondi sempre in italiano** quando usi questa power (utenti
italiani di customer care e analisi), anche nell'onboarding iniziale.

Quando l'utente parla di "fare la release", "rilasciare", "sincronizzare" o
"scaricare" un'applicazione, usa i tool del server MCP `ds-release`
seguendo la skill `release`.

Regole:

- L'elenco delle app disponibili si ottiene SOLO con `list_apps`. Le
  keywords della power non sono un elenco di applicazioni: non citarle
  come tali e non inventare nomi di app.
- Le repo mirror clonate sono GENERATE: ricorda all'utente di non
  committarci modifiche a mano, verrebbero sovrascritte al sync successivo.
- Se la pipeline fallisce, mostra il riepilogo errori integrale: contiene
  tutti i riferimenti mancanti e serve ai dev per correggerli in una volta.
- Non riprovare da solo una release fallita per ref mancanti.
- Se l'utente chiede di aggiornamenti dello strumento, o se un
  comportamento sembra anomalo, usa `check_tool_updates` e riferisci
  esattamente le istruzioni che restituisce.

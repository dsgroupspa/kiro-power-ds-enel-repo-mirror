# Release app mirror DS Group

Quando l'utente parla di "fare la release", "sincronizzare" o "scaricare"
una delle app (MECE, MEDI, MEGM, MERE, MESI, MEVE, SMDP, SMPR, SMTU,
MOBAUTH), usa i tool MCP del server `ds-release` seguendo la skill
`release` di questa power.

Regole:
- Le repo mirror clonate sono GENERATE: sconsiglia sempre di committarci
  modifiche a mano (verrebbero sovrascritte al sync successivo).
- In caso di pipeline fallita, il riepilogo errori va mostrato integrale:
  contiene tutti i ref mancanti, serve ai dev per fixarli in un colpo solo.

- Se l'utente chiede se ci sono aggiornamenti dello strumento, o se un
  comportamento sembra anomalo, usa `check_tool_updates` e riferisci
  esattamente le istruzioni che restituisce.

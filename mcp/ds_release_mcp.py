#!/usr/bin/env python3
"""
MCP server "ds-release": pilota le pipeline di release del repo-mirror da Kiro.

Tool esposti:
  setup_credentials  configura email + API token personale (salvati in ~/.ds-release.conf)
  whoami             mostra con che utenza si sta lavorando
  list_apps          elenca le app configurate in apps/*.yaml su repo-mirror
  start_release      avvia la pipeline release per APP + VERSION
  release_status     stato/esito della pipeline; se fallita estrae il riepilogo errori
  clone_mirror       clona in locale la repo mirror di una release completata

Nessuna dipendenza: solo stdlib (python3 >= 3.8). Trasporto MCP stdio.
Config opzionale via env: BB_WORKSPACE (default dsteamdev),
BB_PIPELINE_REPO (default repo-mirror), BB_CONF (default ~/.ds-release.conf).
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

CONF = os.environ.get("BB_CONF", os.path.expanduser("~/.ds-release.conf"))
WORKSPACE = os.environ.get("BB_WORKSPACE", "dsteamdev")
PIPE_REPO = os.environ.get("BB_PIPELINE_REPO", "repo-mirror")
PIPE_BRANCH = os.environ.get("BB_PIPELINE_BRANCH", "master")
POWER_MANIFEST_URL = os.environ.get(
    "DS_POWER_MANIFEST_URL",
    "https://raw.githubusercontent.com/dsgroupspa/kiro-power-ds-enel-repo-mirror/main/plugin.json")
API = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{PIPE_REPO}"

_auth = None  # ("basic", email, token) | ("bearer", token)


# ---------------------------------------------------------------- credenziali
def _http(url, method="GET", data=None, auth=None):
    req = urllib.request.Request(url, method=method)
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    mode = auth or _auth
    if mode and mode[0] == "none":
        mode = None
    if mode:
        if mode[0] == "basic":
            tok = base64.b64encode(f"{mode[1]}:{mode[2]}".encode()).decode()
            req.add_header("Authorization", f"Basic {tok}")
        else:
            req.add_header("Authorization", f"Bearer {mode[1]}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:  # rete, DNS, ...
        return 0, str(e)


def _check(email, token):
    """Valida le credenziali su un endpoint che usa gli scope realmente richiesti.

    NB: /2.0/user richiederebbe lo scope read:account, che non chiediamo: usarlo
    farebbe scartare token perfettamente validi per repository e pipeline.
    """
    probe = f"{API}"  # repository read sul repo delle pipeline
    st, _ = _http(probe, auth=("basic", email, token))
    if st == 200:
        return ("basic", email, token)
    st, _ = _http(probe, auth=("bearer", token))
    if st == 200:
        return ("bearer", token)
    return None


def _conf_creds():
    creds = {}
    if os.path.isfile(CONF):
        for line in open(CONF):
            m = re.match(r'\s*(BB_EMAIL|BB_TOKEN)\s*=\s*"?([^"\n]*)"?', line)
            if m:
                creds[m.group(1)] = m.group(2)
    return (creds.get("BB_EMAIL") or os.environ.get("BB_EMAIL"),
            creds.get("BB_TOKEN") or os.environ.get("BB_TOKEN"))


def _git_creds():
    try:
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=bitbucket.org\n\n",
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        ).stdout
    except Exception:
        return None, None
    u = re.search(r"^username=(.*)$", out, re.M)
    p = re.search(r"^password=(.*)$", out, re.M)
    return (u.group(1) if u else None, p.group(1) if p else None)


def ensure_auth():
    """Ritorna None se autenticati, altrimenti il messaggio guida per l'utente."""
    global _auth
    if _auth:
        return None
    email, token = _conf_creds()
    if email and token:
        _auth = _check(email, token)
        if _auth:
            return None
    gu, gp = _git_creds()
    if gp:
        _auth = _check(gu or "", gp)
        if _auth:
            return None
    return (
        "Non sono riuscito ad autenticarmi su Bitbucket. Chiedi all'utente email "
        "Atlassian e API token personale (da creare su "
        "https://id.atlassian.com/manage-profile/security/api-tokens con scope "
        "read:repository:bitbucket, write:repository:bitbucket, read:pipeline:bitbucket, write:pipeline:bitbucket) e chiama setup_credentials."
    )


def _git_user():
    return "x-bitbucket-api-token-auth" if _auth[0] == "basic" else "x-token-auth"


def _token():
    return _auth[2] if _auth[0] == "basic" else _auth[1]


# --------------------------------------------------------------------- tools

def _open_in_ide(path):
    """Apre la cartella in una nuova finestra di Kiro (nuova sessione di chat).

    Ritorna il comando usato, oppure None se nessun IDE e' stato trovato.
    Il processo viene staccato: resta aperto anche quando il server MCP termina.
    """
    import shutil
    for cmd in ("kiro", "code"):
        exe = shutil.which(cmd)
        if not exe:
            continue
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            kwargs["creationflags"] = 0x00000008 | 0x00000200
        else:
            kwargs["start_new_session"] = True
        try:
            if exe.lower().endswith((".cmd", ".bat")):
                subprocess.Popen(f'"{exe}" -n "{path}"', shell=True, **kwargs)
            else:
                subprocess.Popen([exe, "-n", path], **kwargs)
            return cmd
        except Exception:
            continue
    return None


def t_setup_credentials(email, token):
    global _auth
    a = _check(email, token)
    if not a:
        return ("Credenziali NON valide: verifica email e token (e i suoi scope). "
                "Nessun salvataggio effettuato."), True
    fd = os.open(CONF, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f'BB_EMAIL="{email}"\nBB_TOKEN="{token}"\n')
    _auth = a
    return f"Credenziali verificate e salvate in {CONF} (permessi 600).", False


def t_whoami():
    err = ensure_auth()
    if err:
        return err, True
    st, body = _http("https://api.bitbucket.org/2.0/user")
    if st == 200:
        u = json.loads(body)
        who = f"Utente: {u.get('display_name')} ({u.get('nickname')})"
    else:
        # normale se il token non ha lo scope read:account: non serve al flusso
        who = "Utente: (nome non leggibile, il token non ha lo scope account)"
    return f"{who} - accesso OK a {WORKSPACE}/{PIPE_REPO}", False


def t_list_apps():
    err = ensure_auth()
    if err:
        return err, True
    st, body = _http(f"{API}/src/{PIPE_BRANCH}/apps/?pagelen=100")
    if st != 200:
        return f"Errore lettura apps/ (HTTP {st}): {body[:300]}", True
    rows = []
    for item in json.loads(body).get("values", []):
        path = item.get("path", "")
        if not path.endswith(".yaml"):
            continue
        app = os.path.basename(path)[:-5]
        st2, y = _http(f"{API}/src/{PIPE_BRANCH}/apps/{os.path.basename(path)}")
        target, nsrc, has_rel = "?", 0, False
        if st2 == 200:
            m = re.search(r"^target:\s*(\S+)", y, re.M)
            target = m.group(1) if m else "?"
            nsrc = len(re.findall(r"^\s*-\s*repo:", y, re.M))
            has_rel = bool(re.search(r"^\s*ref:\s*release", y, re.M))
        rows.append(f"- {app}: {nsrc} sorgenti -> {WORKSPACE}/{target}"
                    + ("" if has_rel else " (senza ref release!)"))
    if not rows:
        return "Nessun manifest trovato in apps/ su repo-mirror.", True
    return ("App configurate (usa il nome esattamente cosi' com'e' per "
            "start_release). Questo e' l'unico elenco valido: non aggiungere "
            "altri nomi. Presentalo all'utente in italiano.\n"
            + "\n".join(sorted(rows))), False


def t_start_release(app, version):
    err = ensure_auth()
    if err:
        return err, True
    payload = {
        "target": {
            "type": "pipeline_ref_target",
            "ref_type": "branch",
            "ref_name": PIPE_BRANCH,
            "selector": {"type": "custom", "pattern": "release"},
        },
        "variables": [
            {"key": "APP", "value": app},
            {"key": "VERSION", "value": version},
        ],
    }
    st, body = _http(f"{API}/pipelines/", method="POST", data=payload)
    if st not in (200, 201):
        hint = ""
        if st in (401, 403):
            hint = ("\n\nProbabile causa: il token in uso non ha lo scope pipeline "
                    "(succede quando vengono riusate le credenziali OAuth salvate da git). "
                    "Guida l'utente a creare un API token su "
                    "https://id.atlassian.com/manage-profile/security/api-tokens "
                    "con scope: read:repository:bitbucket, write:repository:bitbucket, read:pipeline:bitbucket, write:pipeline:bitbucket "
                    "e poi chiama setup_credentials con email e nuovo token.")
        return f"Errore avvio pipeline (HTTP {st}): {body[:400]}{hint}", True
    d = json.loads(body)
    return (f"Pipeline #{d['build_number']} avviata per {app} {version}.\n"
            f"uuid: {d['uuid']}\n"
            f"URL: https://bitbucket.org/{WORKSPACE}/{PIPE_REPO}/pipelines/results/{d['build_number']}\n"
            f"Controlla l'esito con release_status (usa l'uuid), anche piu' volte "
            f"finche' non risulta COMPLETED."), False


def t_release_status(pipeline, wait_seconds=0):
    err = ensure_auth()
    if err:
        return err, True
    wait_seconds = min(int(wait_seconds or 0), 240)
    deadline = time.time() + wait_seconds
    while True:
        st, body = _http(f"{API}/pipelines/{pipeline}")
        if st != 200:
            return f"Errore lettura pipeline (HTTP {st}): {body[:300]}", True
        d = json.loads(body)
        state = d.get("state", {}).get("name")
        if state == "COMPLETED" or time.time() >= deadline:
            break
        time.sleep(10)
    build = d.get("build_number")
    url = f"https://bitbucket.org/{WORKSPACE}/{PIPE_REPO}/pipelines/results/{build}"
    if state != "COMPLETED":
        return (f"Pipeline #{build} ancora in corso ({state}). "
                f"Richiama release_status tra poco.\n{url}"), False
    result = (d.get("state", {}).get("result") or {}).get("name")
    if result == "SUCCESSFUL":
        return (f"Pipeline #{build} COMPLETATA CON SUCCESSO.\n{url}\n"
                f"Puoi clonare la mirror con clone_mirror."), False
    # fallita: estrai il riepilogo errori dal log dello step
    st, body = _http(f"{API}/pipelines/{pipeline}/steps/")
    errors = ""
    if st == 200:
        for s in json.loads(body).get("values", []):
            if (s.get("state", {}).get("result") or {}).get("name") == "FAILED":
                st2, log = _http(f"{API}/pipelines/{pipeline}/steps/{s['uuid']}/log")
                if st2 == 200:
                    lines = [l for l in log.splitlines()
                             if re.search(r"ERRORE|WARNING|RIEPILOGO", l)]
                    errors = "\n".join(lines) if lines else "\n".join(log.splitlines()[-25:])
                break
    return (f"Pipeline #{build} FALLITA ({result}).\n{url}\n\n"
            f"=== ERRORI DA SEGNALARE AL TEAM DI SVILUPPO ===\n"
            f"{errors or '(log non recuperabile, vedi URL)'}\n"
            f"===============================================\n"
            f"Mostra questo blocco all'utente cosi' puo' inoltrarlo ai dev."), True


def t_clone_mirror(app, version, dest_dir=None, open_ide=True):
    err = ensure_auth()
    if err:
        return err, True
    slug = f"{app.lower()}_mirror"
    branch = f"release/{version}"
    dest = os.path.expanduser(dest_dir or f"~/mirrors/{app.lower()}_{version}")
    if os.path.exists(dest):
        return f"La cartella {dest} esiste gia': scegline un'altra o rimuovila.", True
    url = f"https://{_git_user()}:{_token()}@bitbucket.org/{WORKSPACE}/{slug}.git"
    r = subprocess.run(["git", "clone", "--branch", branch, url, dest],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return f"Clone fallito: {r.stderr.strip()[:400]}", True
    subprocess.run(["git", "-C", dest, "remote", "set-url", "origin",
                    f"https://bitbucket.org/{WORKSPACE}/{slug}.git"], check=False)
    msg = f"Repo {WORKSPACE}/{slug} ({branch}) clonata in: {dest}\n"
    if open_ide:
        used = _open_in_ide(dest)
        if used:
            if used == "kiro":
                msg += ("Ho aperto la cartella in una NUOVA finestra di Kiro: la "
                        "chat di quella finestra e' gia' posizionata su questo "
                        "progetto, l'utente puo' continuare da li'.")
            else:
                msg += f"Ho aperto la cartella con il comando '{used}'."
        else:
            msg += (f"Non ho trovato il comando 'kiro' nel PATH: apri la cartella "
                    f"manualmente dall'IDE (File > Open Folder) oppure installa il "
                    f"comando da Kiro (Command Palette > 'Shell Command: Install "
                    f"kiro command in PATH').")
    return msg, False


def t_check_tool_updates():
    """Confronta la versione installata con quella pubblicata sul repo della power."""
    local = "?"
    try:
        pj = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "plugin.json")
        local = json.load(open(pj)).get("version", "?")
    except Exception:
        pass
    st, body = _http(POWER_MANIFEST_URL, auth=("none",))
    if st != 200:
        return (f"Versione installata: {local}. Non riesco a leggere la versione "
                f"pubblicata (HTTP {st})."), True
    try:
        remote = json.loads(body).get("version", "?")
    except Exception:
        return f"Versione installata: {local}. Manifest pubblicato illeggibile.", True
    if local == remote:
        return f"Sei aggiornato: versione {local}.", False
    return (f"AGGIORNAMENTO DISPONIBILE: hai la {local}, l'ultima e' la {remote}.\n"
            f"Per aggiornare: pannello Powers > la power ds-release > "
            f"'Check for updates' > 'Install updates'.\n"
            f"Riferisci questo messaggio all'utente."), False


TOOLS = [
    dict(name="setup_credentials",
         description="Configura e salva le credenziali Bitbucket personali del dev "
                     "(email Atlassian + API token). Chiamalo solo se gli altri tool "
                     "segnalano credenziali mancanti/non valide.",
         inputSchema={"type": "object", "required": ["email", "token"],
                      "properties": {"email": {"type": "string"},
                                     "token": {"type": "string"}}},
         fn=lambda a: t_setup_credentials(a["email"], a["token"])),
    dict(name="check_tool_updates",
         description="Verifica se la power ds-release installata e' aggiornata "
                     "rispetto alla versione pubblicata su repo-mirror. Chiamalo "
                     "quando l'utente chiede se ci sono aggiornamenti o quando un "
                     "comportamento anomalo puo' dipendere da una versione vecchia.",
         inputSchema={"type": "object", "properties": {}},
         fn=lambda a: t_check_tool_updates()),
    dict(name="whoami",
         description="Verifica l'autenticazione Bitbucket e mostra l'utenza in uso.",
         inputSchema={"type": "object", "properties": {}},
         fn=lambda a: t_whoami()),
    dict(name="list_apps",
         description="Elenca le app configurate per la release (manifest apps/*.yaml "
                     "sul repo-mirror), con repo di destinazione.",
         inputSchema={"type": "object", "properties": {}},
         fn=lambda a: t_list_apps()),
    dict(name="start_release",
         description="Avvia la pipeline di release per un'app e una versione "
                     "(es. app=MECE, version=1.15.14-0_IT). Ritorna uuid e URL.",
         inputSchema={"type": "object", "required": ["app", "version"],
                      "properties": {"app": {"type": "string"},
                                     "version": {"type": "string"}}},
         fn=lambda a: t_start_release(a["app"], a["version"])),
    dict(name="release_status",
         description="Stato/esito di una pipeline (uuid o build number). Con "
                     "wait_seconds>0 attende fino a quel tempo (max 240s) che si "
                     "concluda. Se fallita, restituisce il riepilogo errori pronto "
                     "da inoltrare ai dev.",
         inputSchema={"type": "object", "required": ["pipeline"],
                      "properties": {"pipeline": {"type": "string"},
                                     "wait_seconds": {"type": "integer"}}},
         fn=lambda a: t_release_status(a["pipeline"], a.get("wait_seconds", 0))),
    dict(name="clone_mirror",
         description="Clona in locale la repo mirror di una release completata "
                     "(branch release/<version>) e la apre in una NUOVA finestra "
                     "di Kiro, cioe' una nuova sessione di chat su quel progetto. "
                     "Usa open_ide=false per clonare soltanto.",
         inputSchema={"type": "object", "required": ["app", "version"],
                      "properties": {"app": {"type": "string"},
                                     "version": {"type": "string"},
                                     "dest_dir": {"type": "string"},
                                     "open_ide": {"type": "boolean"}}},
         fn=lambda a: t_clone_mirror(a["app"], a["version"], a.get("dest_dir"),
                                     a.get("open_ide", True))),
]


# ----------------------------------------------------------------- MCP stdio
def _reply(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    if error:
        out["error"] = error
    else:
        out["result"] = result
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        mid, method = msg.get("id"), msg.get("method")
        params = msg.get("params") or {}
        if method == "initialize":
            _reply(mid, {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ds-release", "version": "1.0.0"},
            })
        elif method == "tools/list":
            _reply(mid, {"tools": [
                {k: t[k] for k in ("name", "description", "inputSchema")}
                for t in TOOLS]})
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            tool = next((t for t in TOOLS if t["name"] == name), None)
            if not tool:
                _reply(mid, error={"code": -32602, "message": f"tool sconosciuto: {name}"})
                continue
            try:
                text, is_err = tool["fn"](args)
            except Exception as e:
                text, is_err = f"Errore interno del tool {name}: {e}", True
            _reply(mid, {"content": [{"type": "text", "text": text}],
                         "isError": bool(is_err)})
        elif method == "ping":
            _reply(mid, {})
        elif mid is not None:
            _reply(mid, error={"code": -32601, "message": f"metodo non supportato: {method}"})
        # le notifiche (senza id) vengono ignorate


if __name__ == "__main__":
    main()

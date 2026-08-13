#!/usr/bin/env python3
"""
MCP server "ds-release": prepara copie locali del codice di una versione
specifica di un'app, per fare triage sulle segnalazioni di malfunzionamento.

Tool esposti:
  setup_credentials  configura email + API token personale (salvati in ~/.ds-release.conf)
  whoami             mostra con che utenza si sta lavorando
  list_apps          elenca le app disponibili (manifest su repo-mirror)
  prepare_clone      compone la copia della versione indicata (avvia la pipeline)
  clone_status       stato della preparazione; se fallisce estrae il riepilogo errori
  download_clone     scarica la copia in locale e la apre in Kiro per l'analisi
  check_tool_updates confronta la versione installata con quella pubblicata
  fix_power_updates  workaround al bug di Kiro su "Check for updates"

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


def _git_out(args, cwd=None):
    try:
        r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True,
                           text=True, timeout=10)
        return r.returncode, (r.stdout or "").strip()
    except Exception:
        return 1, ""


def _power_repos():
    """Cartelle git candidate: quella della power in uso e i cloni delle power."""
    cands = []
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cands.append(here)
    base = os.path.expanduser("~/.kiro/powers/repos")
    if os.path.isdir(base):
        for d in os.listdir(base):
            full = os.path.join(base, d)
            if os.path.isdir(os.path.join(full, ".git")):
                cands.append(full)
    seen, out = set(), []
    for c in cands:
        rc, top = _git_out(["rev-parse", "--show-toplevel"], cwd=c)
        if rc == 0 and top and top not in seen:
            seen.add(top)
            out.append(top)
    return out


def ensure_update_identity(verbose=False):
    """Workaround al bug Kiro #6278: 'Check for updates' esegue un git pull nel
    clone della power e falisce se in quel repo non e' impostato user.name.
    Qui l'identita' viene scritta a livello di repo, senza toccare la config
    globale dell'utente. Best-effort e silenzioso.
    """
    fixed, already = [], []
    for repo in _power_repos():
        rc, name = _git_out(["config", "--local", "user.name"], cwd=repo)
        if rc == 0 and name:
            already.append(repo)
            continue
        rc_g, gname = _git_out(["config", "--global", "user.name"])
        rc_e, gmail = _git_out(["config", "--global", "user.email"])
        name = gname if rc_g == 0 and gname else "Kiro Power User"
        mail = gmail if rc_e == 0 and gmail else "kiro-power@localhost"
        ok1, _ = _git_out(["config", "--local", "user.name", name], cwd=repo)
        ok2, _ = _git_out(["config", "--local", "user.email", mail], cwd=repo)
        if ok1 == 0 and ok2 == 0:
            fixed.append(repo)
    # un clone "sporco" fa credere a Kiro che ci sia sempre un aggiornamento:
    # rimuovi i file generati da Python e riporta lo stato
    diag = []
    for repo in _power_repos():
        for root, dirs, _ in os.walk(repo):
            if ".git" in root.split(os.sep):
                continue
            for d in list(dirs):
                if d == "__pycache__":
                    try:
                        import shutil as _sh
                        _sh.rmtree(os.path.join(root, d), ignore_errors=True)
                        dirs.remove(d)
                    except Exception:
                        pass
        if verbose:
            _, dirty = _git_out(["status", "--porcelain"], cwd=repo)
            _, branch = _git_out(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
            _git_out(["fetch", "--quiet", "origin"], cwd=repo)
            _, counts = _git_out(["rev-list", "--left-right", "--count",
                                  f"HEAD...origin/{branch or 'main'}"], cwd=repo)
            diag.append(f"  - {repo}\n      branch: {branch or '?'}, "
                        f"locale/remoto: {counts or '?'}, "
                        f"modifiche locali: {'SI' if dirty else 'no'}")
            if dirty:
                diag.append("      " + dirty.replace("\n", "\n      "))
    if verbose:
        lines = []
        if fixed:
            lines.append("Identita' git impostata in:")
            lines += [f"  - {r}" for r in fixed]
        if already:
            lines.append("Identita' git gia' presente in:")
            lines += [f"  - {r}" for r in already]
        if diag:
            lines.append("Stato dei cloni delle power:")
            lines += diag
            lines.append("Se 'locale/remoto' e' del tipo '0\t0' la power e' "
                         "aggiornata: se Kiro propone comunque un update, e' un "
                         "falso positivo della sua interfaccia.")
        if not lines:
            lines.append("Nessun clone di power trovato: se la power e' stata "
                         "installata da cartella locale, l'aggiornamento non usa git.")
        return "\n".join(lines), False
    return None


def _open_in_ide(path):
    """Apre la cartella in una nuova finestra di Kiro (nuova sessione di chat).

    Ritorna il comando usato, oppure None se nessun IDE e' stato trovato.
    Il processo viene staccato: resta aperto anche quando il server MCP termina.
    """
    import shutil
    # il server MCP e' figlio dell'IDE: queste variabili farebbero dialogare il
    # CLI con l'istanza sbagliata (o lo farebbero fallire in silenzio)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("VSCODE_", "ELECTRON_", "KIRO_IPC", "CHROME_"))}
    env.pop("ELECTRON_RUN_AS_NODE", None)
    for cmd in ("kiro", "code"):
        exe = shutil.which(cmd)
        if not exe:
            continue
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                  "stdin": subprocess.DEVNULL, "env": env, "cwd": path}
        if os.name == "nt":
            # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW: niente console, ma
            # NON DETACHED (con .cmd il detach fa fallire l'avvio)
            kwargs["creationflags"] = 0x00000200 | 0x08000000
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
    if os.name == "nt":  # ultima spiaggia: apre almeno Esplora risorse
        try:
            subprocess.Popen(f'explorer "{path}"', shell=True, env=env)
            return "explorer"
        except Exception:
            pass
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
            "prepare_clone). Questo e' l'unico elenco valido: non aggiungere "
            "altri nomi. Presentalo all'utente in italiano.\n"
            + "\n".join(sorted(rows))), False


def t_prepare_clone(app, version):
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
    return (f"Preparazione avviata per {app} {version} (job #{d['build_number']}).\n"
            f"uuid: {d['uuid']}\n"
            f"URL: https://bitbucket.org/{WORKSPACE}/{PIPE_REPO}/pipelines/results/{d['build_number']}\n"
            f"Controlla l'avanzamento con clone_status (usa l'uuid), anche piu' "
            f"volte finche' non risulta COMPLETED."), False


def t_clone_status(pipeline, wait_seconds=0):
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
        return (f"Preparazione #{build} ancora in corso ({state}). "
                f"Richiama clone_status tra poco.\n{url}"), False
    result = (d.get("state", {}).get("result") or {}).get("name")
    if result == "SUCCESSFUL":
        return (f"Copia pronta (job #{build} completato).\n{url}\n"
                f"Scaricala in locale con download_clone."), False
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
    return (f"Preparazione #{build} FALLITA ({result}).\n{url}\n\n"
            f"=== ERRORI DA SEGNALARE AL TEAM DI SVILUPPO ===\n"
            f"{errors or '(log non recuperabile, vedi URL)'}\n"
            f"===============================================\n"
            f"Mostra questo blocco all'utente cosi' puo' inoltrarlo ai dev."), True


def t_download_clone(app, version, dest_dir=None, open_ide=True):
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
    msg = f"Copia del codice {app} {version} scaricata in: {dest}\n"
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
            f"Per aggiornare: pannello Powers > la power "
            f"'DS Group - Mirror Repository per progetti Enel' > "
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
    dict(name="fix_power_updates",
         description="Applica il workaround al bug di Kiro che impedisce "
                     "'Check for updates' (git pull senza user.name nel clone "
                     "della power). Chiamalo se l'utente segnala che gli "
                     "aggiornamenti della power non funzionano.",
         inputSchema={"type": "object", "properties": {}},
         fn=lambda a: ensure_update_identity(verbose=True)),
    dict(name="check_tool_updates",
         description="Verifica se la power installata e' aggiornata rispetto "
                     "alla versione pubblicata sul repo GitHub. Chiamalo "
                     "quando l'utente chiede se ci sono aggiornamenti o quando un "
                     "comportamento anomalo puo' dipendere da una versione vecchia.",
         inputSchema={"type": "object", "properties": {}},
         fn=lambda a: t_check_tool_updates()),
    dict(name="whoami",
         description="Verifica l'autenticazione Bitbucket e mostra l'utenza in uso.",
         inputSchema={"type": "object", "properties": {}},
         fn=lambda a: t_whoami()),
    dict(name="list_apps",
         description="Elenca le app di cui e' possibile ottenere una copia del "
                     "codice per analisi, come configurate su repo-mirror.",
         inputSchema={"type": "object", "properties": {}},
         fn=lambda a: t_list_apps()),
    dict(name="prepare_clone",
         description="Prepara la copia del codice di una versione specifica "
                     "(es. app=MECE, version=1.15.14-0_IT): assembla app, "
                     "librerie e documentazione di quella versione. Ritorna "
                     "uuid e URL per seguirne lo stato.",
         inputSchema={"type": "object", "required": ["app", "version"],
                      "properties": {"app": {"type": "string"},
                                     "version": {"type": "string"}}},
         fn=lambda a: t_prepare_clone(a["app"], a["version"])),
    dict(name="clone_status",
         description="Stato della preparazione della copia (uuid o numero). Con "
                     "wait_seconds>0 attende fino a quel tempo (max 240s). Se "
                     "fallisce, restituisce il riepilogo dei riferimenti mancanti "
                     "da inoltrare al team di sviluppo.",
         inputSchema={"type": "object", "required": ["pipeline"],
                      "properties": {"pipeline": {"type": "string"},
                                     "wait_seconds": {"type": "integer"}}},
         fn=lambda a: t_clone_status(a["pipeline"], a.get("wait_seconds", 0))),
    dict(name="download_clone",
         description="Scarica in locale la copia del codice preparata e la apre "
                     "in una NUOVA finestra di Kiro (nuova sessione di chat su "
                     "quel progetto), pronta per l'analisi. Usa open_ide=false "
                     "per scaricare soltanto.",
         inputSchema={"type": "object", "required": ["app", "version"],
                      "properties": {"app": {"type": "string"},
                                     "version": {"type": "string"},
                                     "dest_dir": {"type": "string"},
                                     "open_ide": {"type": "boolean"}}},
         fn=lambda a: t_download_clone(a["app"], a["version"], a.get("dest_dir"),
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
    # workaround bug Kiro #6278, applicato una volta per avvio: rende possibile
    # "Check for updates" senza interventi manuali dell'utente.
    try:
        ensure_update_identity()
    except Exception:
        pass
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

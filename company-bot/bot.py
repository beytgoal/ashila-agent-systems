#!/usr/bin/env python3
"""company-bot — mesin bot otomatis Moderate (bot-first, agent-on-exception).

Satu mesin untuk semua divisi. Pekerjaan berpola tetap (cek layanan, polling,
hitung ambang, validasi, pantau antrean/saldo) dijalankan skrip ini dengan
0 token Muse, mengikuti pipeline datahub:

    sumber -> bot memeriksa -> event (hanya saat berubah) -> dh.py index
    -> digest.md -> agent membaca hasil, mengevaluasi, memperbaiki.

Agent TIDAK pernah dipakai di tengah pipeline. Bot ini hanya menulis event
saat status berubah (atau pengingat berkala saat status tidak-ok), sehingga
yang dibaca agent selalu ringkasan kecil, bukan log mentah.

Jenis job (konfigurasi JSON di jobs/):
  http         cek URL: kode status + substring opsional
  process      cek proses hidup via pgrep -f
  command      jalankan perintah: exit code (+ regex opsional)
  command_json jalankan perintah, parse stdout JSON, bandingkan angka di path
  json         baca file JSON: nilai di path, atau hitung item (count_where)

Ambang angka: warn_below / fail_below / warn_above / fail_above.
Aksi perbaikan opsional per job: action.on_fail (perintah), dijalankan setelah
action.after_fails kegagalan beruntun, dibatasi action.max_per_hour dan
action.cooldown_s. Tanpa action, bot murni mengamati + melapor (mode aman).

CLI:
  bot.py list | run-once [--job ID] | loop | start | stop | status | digest
State: state/<job>.json - Event: events/events-YYYYMMDD.jsonl - Digest: digest.md
Hanya stdlib. Konfigurasi dianggap tepercaya (perintah dari file job sendiri).
"""
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

BASE = os.path.dirname(os.path.abspath(__file__))
HOME_DIR = os.path.dirname(os.path.dirname(BASE))
WORKSPACE_DIR = os.path.join(HOME_DIR, "workspace")
JOBS_DIR = os.path.join(BASE, "jobs")
STATE_DIR = os.path.join(BASE, "state")
EVENTS_DIR = os.path.join(BASE, "events")
LOGS_DIR = os.path.join(BASE, "logs")
DIGEST = os.path.join(BASE, "digest.md")
PIDFILE = os.path.join(STATE_DIR, "bot.pid")
DH = os.path.join(WORKSPACE_DIR, "divisi", "data", "bin", "dh.py")
TZ = ZoneInfo("Asia/Jakarta")


def expand_workspace_path(value):
    """Ubah awalan ~ berdasarkan lokasi bot, bukan $HOME proses.

    Daemon systemd dapat berjalan tanpa HOME yang benar; padahal seluruh
    konfigurasi Moderate berada di workspace yang memuat bot ini. Jangan
    biarkan ekspansi path bergantung pada konteks pemanggil.
    """
    if not isinstance(value, str):
        return value
    value = value.replace("~/workspace", WORKSPACE_DIR)
    if value == "~":
        return HOME_DIR
    if value.startswith("~/"):
        return os.path.join(HOME_DIR, value[2:])
    return value


def command_env():
    env = os.environ.copy()
    env["HOME"] = HOME_DIR
    return env

for d in (STATE_DIR, EVENTS_DIR, LOGS_DIR):
    os.makedirs(d, exist_ok=True)


def now():
    return datetime.now(TZ)


def now_iso():
    return now().strftime("%Y-%m-%d %H:%M:%S %Z")


def log(msg):
    line = f"[{now_iso()}] {msg}"
    print(line, flush=True)


# ---------------------------------------------------------------- konfigurasi
def load_jobs():
    jobs = []
    if not os.path.isdir(JOBS_DIR):
        return jobs
    for name in sorted(os.listdir(JOBS_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(JOBS_DIR, name)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log(f"KONFIG RUSAK {name}: {e}")
            continue
        for job in data.get("jobs", []):
            job["_file"] = name
            jobs.append(job)
    return jobs


# ---------------------------------------------------------------- state
def state_path(job_id):
    return os.path.join(STATE_DIR, f"{job_id}.json")


def load_state(job_id):
    try:
        with open(state_path(job_id), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"status": None, "fail_streak": 0, "restarts": [], "last_event": {}}


def save_state(job_id, st):
    tmp = state_path(job_id) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, ensure_ascii=False)
    os.replace(tmp, state_path(job_id))


# ---------------------------------------------------------------- pemeriksa
def dotted(obj, path):
    if not path:
        return obj
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur[part]
        elif isinstance(cur, list):
            cur = cur[int(part)]
        else:
            raise KeyError(path)
    return cur


def thresholds(value, job):
    """Kembalikan status dari nilai angka menurut ambang job."""
    if value is None:
        return "fail", "nilai tidak terbaca"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "fail", f"nilai bukan angka: {value!r}"
    if job.get("fail_below") is not None and v < job["fail_below"]:
        return "fail", f"{v} < fail_below {job['fail_below']}"
    if job.get("fail_above") is not None and v > job["fail_above"]:
        return "fail", f"{v} > fail_above {job['fail_above']}"
    if job.get("warn_below") is not None and v < job["warn_below"]:
        return "warn", f"{v} < warn_below {job['warn_below']}"
    if job.get("warn_above") is not None and v > job["warn_above"]:
        return "warn", f"{v} > warn_above {job['warn_above']}"
    return "ok", f"nilai {v}"


def check_http(job):
    url = job["url"]
    timeout = job.get("timeout_s", 10)
    expect = job.get("expect_status", [200])
    req = urllib.request.Request(url, headers={"User-Agent": "company-bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(65536).decode("utf-8", "ignore")
            code = r.status
    except urllib.error.HTTPError as e:
        body = e.read(65536).decode("utf-8", "ignore") if e.fp else ""
        code = e.code
    except Exception as e:
        return "fail", f"{url} tidak menjawab: {type(e).__name__}: {e}", None
    if code not in expect:
        return "fail", f"{url} -> HTTP {code} (diharapkan {expect})", code
    sub = job.get("expect_substring")
    if sub and sub not in body:
        return "fail", f"{url} HTTP {code} tapi '{sub}' tidak ditemukan", code
    return "ok", f"{url} -> HTTP {code}", code


def check_process(job):
    pat = job["pattern"]
    r = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True)
    pids = [p for p in r.stdout.split() if p.strip()]
    if pids:
        return "ok", f"proses hidup: {pat} (pid {', '.join(pids[:3])})", len(pids)
    return "fail", f"proses tidak ditemukan: {pat}", 0


def run_command(job):
    cmd = expand_workspace_path(job["command"])
    timeout = job.get("timeout_s", 120)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout, cwd=BASE, env=command_env())
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out


def check_command(job):
    try:
        code, out = run_command(job)
    except subprocess.TimeoutExpired:
        return "fail", f"perintah timeout: {job['command'][:80]}", None
    tail = out.strip()[-300:]
    if job.get("fail_if_regex") and re.search(job["fail_if_regex"], out):
        return "fail", f"fail_if_regex cocok. {tail}", code
    if job.get("ok_if_regex"):
        if re.search(job["ok_if_regex"], out):
            return "ok", tail, code
        return "fail", f"ok_if_regex tidak cocok. {tail}", code
    ok_codes = job.get("ok_codes", [0])
    if code in ok_codes:
        return "ok", tail, code
    return "fail", f"exit {code}. {tail}", code


def check_command_json(job):
    try:
        code, out = run_command(job)
    except subprocess.TimeoutExpired:
        return "fail", f"perintah timeout: {job['command'][:80]}", None
    if code != 0:
        return "fail", f"exit {code}. {out.strip()[-200:]}", None
    try:
        data = json.loads(out)
        value = dotted(data, job.get("path", ""))
    except Exception as e:
        return "fail", f"parse JSON/path gagal: {e}", None
    status, detail = thresholds(value, job)
    return status, detail, value


def check_json_file(job):
    path = expand_workspace_path(job["file"])
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return "fail", f"file tidak terbaca {path}: {e}", None
    cw = job.get("count_where")
    if cw:
        try:
            items = dotted(data, cw.get("path", ""))
            value = sum(1 for it in items
                        if isinstance(it, dict) and it.get(cw["key"]) == cw["equals"])
        except Exception as e:
            return "fail", f"count_where gagal: {e}", None
    else:
        try:
            value = dotted(data, job.get("path", ""))
        except Exception as e:
            return "fail", f"path tidak ditemukan: {e}", None
    status, detail = thresholds(value, job)
    return status, f"{detail} (dari {os.path.basename(path)})", value


CHECKS = {
    "http": check_http,
    "process": check_process,
    "command": check_command,
    "command_json": check_command_json,
    "json": check_json_file,
}


# ---------------------------------------------------------------- event
def emit_event(job, st, old_status, new_status, detail, value, action=None):
    ev = {
        "ts": now_iso(),
        "job": job["id"],
        "division": job.get("division", "-"),
        "title": job.get("title", job["id"]),
        "from": old_status,
        "to": new_status,
        "value": value,
        "detail": detail[-400:],
    }
    if action:
        ev["action"] = action
    path = os.path.join(EVENTS_DIR, f"events-{now().strftime('%Y%m%d')}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    log(f"EVENT {job['id']}: {old_status} -> {new_status} | {detail[:120]}")
    # Index ke datahub hanya untuk kejadian berarti (bukan ok rutin).
    if new_status in ("warn", "fail") or (old_status in ("warn", "fail") and new_status == "ok"):
        title = f"Bot {job['id']}: {old_status} -> {new_status}"
        body = (f"{job.get('title', job['id'])} — status {new_status}. {detail[:300]}"
                + (f" Aksi bot: {action}" if action else ""))
        try:
            subprocess.run(
                [sys.executable, DH, "index", "--division", job.get("division", "data"),
                 "--type", "perubahan", "--title", title, "--body", body],
                capture_output=True, text=True, timeout=30)
        except Exception:
            pass  # datahub tidak boleh menjatuhkan bot


def maybe_action(job, st, status):
    """Jalankan perintah perbaikan bila dikonfigurasi dan ambang terpenuhi."""
    act = job.get("action") or {}
    cmd = act.get("on_fail")
    if not cmd or status == "ok":
        return None
    if st.get("fail_streak", 0) < act.get("after_fails", 2):
        return None
    now_ts = time.time()
    last = st.get("last_action_ts", 0)
    if now_ts - last < act.get("cooldown_s", 600):
        return None
    st["restarts"] = [t for t in st.get("restarts", []) if now_ts - t < 3600]
    if len(st["restarts"]) >= act.get("max_per_hour", 2):
        return None
    try:
        r = subprocess.run(expand_workspace_path(cmd), shell=True,
                           capture_output=True, text=True,
                           timeout=act.get("timeout_s", 120),
                           cwd=BASE, env=command_env())
        result = f"on_fail jalan (exit {r.returncode})"
    except Exception as e:
        result = f"on_fail gagal: {e}"
    st["restarts"].append(now_ts)
    st["last_action_ts"] = now_ts
    return result


def run_job(job):
    fn = CHECKS.get(job["type"])
    if not fn:
        log(f"Jenis job tidak dikenal: {job['type']} ({job['id']})")
        return
    st = load_state(job["id"])
    old = st.get("status")
    try:
        status, detail, value = fn(job)
    except Exception as e:
        status, detail, value = "fail", f"pemeriksa error: {e}", None
    if status == "ok":
        st["fail_streak"] = 0
    else:
        st["fail_streak"] = st.get("fail_streak", 0) + 1
    action = maybe_action(job, st, status)
    now_ts = time.time()
    cooldown = job.get("cooldown_s", 900)
    last_ev = st.get("last_event", {}).get(status, 0)
    changed = (status != old)
    remind = (status != "ok" and now_ts - last_ev >= cooldown)
    if changed or remind or action:
        emit_event(job, st, old, status, detail, value, action)
        st.setdefault("last_event", {})[status] = now_ts
        if changed:
            st["since"] = now_iso()
    st.update({"status": status, "value": value, "detail": detail[-300:],
               "last_run": now_iso()})
    save_state(job["id"], st)
    return status


# ---------------------------------------------------------------- digest
def write_digest(jobs):
    lines = [f"# Digest Bot Perusahaan — {now_iso()}",
             "", "Hasil olahan bot untuk dibaca agent (evaluasi + perbaikan).", ""]
    attention, ok_count = [], 0
    for job in jobs:
        if not job.get("enabled", True):
            continue
        st = load_state(job["id"])
        if st.get("status") in ("warn", "fail"):
            attention.append((job, st))
        elif st.get("status") == "ok":
            ok_count += 1
    lines.append(f"## Perlu perhatian ({len(attention)})")
    if attention:
        for job, st in attention:
            lines.append(f"- **{st['status'].upper()}** [{job.get('division','-')}] "
                         f"{job.get('title', job['id'])} — sejak {st.get('since', '?')}. "
                         f"{st.get('detail', '')[:200]}")
    else:
        lines.append("- Tidak ada. Semua job terpantau ok.")
    lines.append("")
    lines.append(f"## Ringkasan: {ok_count} ok, {len(attention)} perlu perhatian")
    # Event terakhir (maks 15) dari berkas hari ini dan kemarin.
    evs = []
    for back in (0, 1):
        d = now().fromordinal(now().toordinal() - back)
        p = os.path.join(EVENTS_DIR, f"events-{d.strftime('%Y%m%d')}.jsonl")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                evs += [json.loads(x) for x in f if x.strip()]
    lines.append("")
    lines.append("## Event terakhir")
    for ev in evs[-15:]:
        lines.append(f"- {ev['ts']} [{ev['division']}] {ev['job']}: "
                     f"{ev['from']} -> {ev['to']} — {ev['detail'][:140]}")
    if not evs:
        lines.append("- Belum ada event.")
    with open(DIGEST, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- mode jalan
def enabled_jobs(only=None):
    return [j for j in load_jobs()
            if j.get("enabled", True) and (not only or j["id"] == only)]


def run_once(only=None):
    jobs = enabled_jobs(only)
    for job in jobs:
        run_job(job)
    write_digest(load_jobs())
    log(f"run-once selesai: {len(jobs)} job")


def process_is_bot(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmdline = f.read().replace(b"\0", b" ").decode("utf-8", "ignore")
    except Exception:
        return False
    return "bot.py" in cmdline and (" loop" in cmdline or " start" in cmdline)


def loop():
    existing_pid = read_pid()
    if (existing_pid and existing_pid != os.getpid()
            and process_is_bot(existing_pid)):
        log(f"loop lain sudah jalan (pid {existing_pid}); loop ini berhenti "
            "agar tidak ada daemon ganda")
        return
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    jobs = enabled_jobs()
    next_run = {j["id"]: 0 for j in jobs}
    log(f"loop mulai: {len(jobs)} job")
    while True:
        t = time.time()
        for job in jobs:
            if t >= next_run[job["id"]]:
                try:
                    run_job(job)
                except Exception as e:
                    log(f"job {job['id']} error: {e}")
                next_run[job["id"]] = t + job.get("interval_s", 300)
        write_digest(load_jobs())
        sleep = min(5, max(1, min(next_run.values()) - time.time())) if jobs else 5
        time.sleep(max(1, sleep))


def daemonize():
    pid = os.fork()
    if pid > 0:
        print(f"bot start: pid induk {pid}")
        return
    os.setsid()
    pid2 = os.fork()
    if pid2 > 0:
        os._exit(0)
    sys.stdout.flush()
    sys.stderr.flush()
    logf = open(os.path.join(LOGS_DIR, "bot.log"), "a", buffering=1)
    os.dup2(logf.fileno(), sys.stdout.fileno())
    os.dup2(logf.fileno(), sys.stderr.fileno())
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    loop()


def read_pid():
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    only = None
    if "--job" in args:
        only = args[args.index("--job") + 1]
    if cmd == "list":
        for j in load_jobs():
            print(f"{j['id']:28} {j.get('division','-'):18} {j['type']:12} "
                  f"tiap {j.get('interval_s', 300)}s  "
                  f"{'AKTIF' if j.get('enabled', True) else 'nonaktif'}  {j.get('title','')}")
    elif cmd == "run-once":
        run_once(only)
    elif cmd == "loop":
        loop()
    elif cmd == "start":
        if read_pid():
            print("bot sudah jalan")
        else:
            daemonize()
    elif cmd == "stop":
        pid = read_pid()
        if pid:
            os.kill(pid, signal.SIGTERM)
            print(f"bot pid {pid} dihentikan")
        else:
            print("bot tidak jalan")
    elif cmd == "status":
        pid = read_pid()
        print(f"loop daemon: {'JALAN pid ' + str(pid) if pid else 'tidak jalan'}")
        for j in load_jobs():
            if not j.get("enabled", True):
                continue
            st = load_state(j["id"])
            print(f"{j['id']:28} {str(st.get('status')):6} terakhir {st.get('last_run', '-')}"
                  f" — {str(st.get('detail', ''))[:90]}")
    elif cmd == "digest":
        write_digest(load_jobs())
        with open(DIGEST, encoding="utf-8") as f:
            print(f.read())
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()

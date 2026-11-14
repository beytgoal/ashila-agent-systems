#!/usr/bin/env python3
"""clipper-views-watch — pantau akumulasi views kolam link TERDAFTAR
campaign "7 Karyawan VS 1 Clipper" (Ternak Klip) untuk Company Bot
Divisi Freelancer & Clipper. Read-only penuh (hanya baca konektor).

Daftar tautan dibaca dari bot/state/submit_queue.json (field link_status
== "TERDAFTAR" per platform; disinkronkan dari submit-campaign-ledger.md).
Views per video via konektor (cara terbukti divisi):
  - Instagram: instagram-cli individual-post-insights -> "views" =
    ig_clips_play_count + instagram_clips_video_replay_count (plays +
    replays; TERBUKTI identik dengan angka panel Insight yang dipakai
    ledger: c02 153, c05 158, c06 172 — total 815 IG per 31 Okt 21:16;
    ig_clips_play_count saja lebih kecil dan BUKAN metrik panel).
    ID media numerik
    di-resolve dari `instagram-cli posts` (url -> post_id), di-cache.
  - Threads: threads-cli post-insights -> metric "views" (lifetime).
    ID numerik di-resolve dari `threads-cli post --url`, di-cache.
Baseline = total terakhir yang DILAPORKAN (bukan total run sebelumnya):
event hanya bila total naik >= +500 dari baseline ("views_up") atau
menembus gerbang submit 10.000 ("views_gate_10000"); saat event,
baseline diperbarui ke total baru. Run pertama = seed tanpa event.
Kegagalan fetch per tautan: nilai terakhir yang diketahui dipakai lagi
(total tidak runtuh); semua tautan gagal DAN belum ada nilai -> diam
({"changed": [], "fetch": "error"}). Output tepat SATU baris JSON:
    {"changed": [...], "events": [...]}
Pengajuan submission BUKAN di sini — agent-on-event via hook
clipper-trigger-views.
"""
import json
import os
import subprocess
import sys

BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(BOT_DIR, "state", "submit_queue.json")
HARVEST = os.path.join(BOT_DIR, "state", "ig-posts-harvest-2026-10-31.json")
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
STATE = os.path.join(STATE_DIR, "views_state.json")
IG_ACCOUNT = "YOUR_IG_ACCOUNT_ID"
TH_ACCOUNT = "YOUR_THREADS_ACCOUNT_ID"
GATE = 10000
STEP = 500
CALL_TIMEOUT = 120


def run_cli(args, timeout=CALL_TIMEOUT):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise IOError(f"rc={r.returncode}: {(r.stderr or '')[:120]}")
    return json.loads(r.stdout)


def registered_links():
    with open(QUEUE, encoding="utf-8") as f:
        q = json.load(f)
    out = []
    for it in q.get("items", []):
        for plat, st in (it.get("link_status") or {}).items():
            if st == "TERDAFTAR" and plat in ("instagram", "threads"):
                url = (it.get("urls") or {}).get(plat)
                if url:
                    out.append({"key": f"{plat}:{it['file']}",
                                "platform": plat, "url": url})
    return out


def resolve_ig(url, cache):
    if url in cache:
        return cache[url]
    # Benih dari panen konektor 31 Okt (url -> post_id) bila ada.
    try:
        with open(HARVEST, encoding="utf-8") as f:
            for p in json.load(f).get("posts", []):
                if p.get("url") and p.get("post_id"):
                    cache.setdefault(p["url"], str(p["post_id"]))
    except Exception:
        pass
    if url in cache:
        return cache[url]
    d = run_cli(["instagram-cli", "posts", "--account-id", IG_ACCOUNT])
    for p in d.get("posts", []):
        if p.get("url") and p.get("post_id"):
            cache[p["url"]] = str(p["post_id"])
    return cache.get(url)


def ig_views(media_id):
    d = run_cli(["instagram-cli", "individual-post-insights",
                 "--account-id", IG_ACCOUNT, "--post", media_id])
    m = d.get("metrics") or {}

    def tot(k):
        v = m.get(k)
        return v.get("total") if isinstance(v, dict) else v

    play, replay = tot("ig_clips_play_count"), \
        tot("instagram_clips_video_replay_count")
    if play is not None:
        return play + (replay or 0)
    return tot("instagram_organic_media_content_views_count")


def resolve_threads(url, cache):
    if url in cache:
        return cache[url]
    d = run_cli(["threads-cli", "post", "--url", url,
                 "--account-id", TH_ACCOUNT])
    posts = d.get("posts") or []
    if posts and posts[0].get("post_id"):
        cache[url] = str(posts[0]["post_id"])
    return cache.get(url)


def threads_views(post_id):
    d = run_cli(["threads-cli", "post-insights", "--post-id", post_id,
                 "--account-id", TH_ACCOUNT])
    posts = d.get("posts") or []
    if not posts:
        return None
    for mr in posts[0].get("metric_results", []):
        if mr.get("metric") == "views":
            return (mr.get("lifetime") or {}).get("value")
    return None


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(tmp, STATE)


def main():
    links = registered_links()
    st = load_state() or {}
    per_link = dict(st.get("per_link") or {})
    ig_cache = dict(st.get("ig_ids") or {})
    th_cache = dict(st.get("th_ids") or {})
    ok_count, fail = 0, []
    for lk in links:
        try:
            if lk["platform"] == "instagram":
                mid = resolve_ig(lk["url"], ig_cache)
                if not mid:
                    raise IOError("media_id tidak ter-resolve")
                v = ig_views(mid)
            else:
                pid = resolve_threads(lk["url"], th_cache)
                if not pid:
                    raise IOError("post_id tidak ter-resolve")
                v = threads_views(pid)
            if v is None:
                raise IOError("views None")
            per_link[lk["key"]] = int(v)
            ok_count += 1
        except Exception as e:
            fail.append(f"{lk['key']}: {e}")
    if ok_count == 0 and not per_link:
        print(json.dumps({"changed": [], "events": [], "fetch": "error",
                          "gagal": fail[:3]}))
        return 0
    total = sum(per_link[k] for k in
                [lk["key"] for lk in links] if k in per_link)
    new_st = {"per_link": per_link, "ig_ids": ig_cache, "th_ids": th_cache,
              "last_total": total, "fetch_ok": ok_count,
              "fetch_fail": len(fail)}
    if st.get("baseline_total") is None:
        new_st["baseline_total"] = total
        save_state(new_st)
        print(json.dumps({"changed": [], "events": [], "seeded": True,
                          "total": total, "tautan": len(links)}))
        return 0
    baseline = st["baseline_total"]
    new_st["baseline_total"] = baseline
    changed, events = [], []
    if total >= GATE and baseline < GATE:
        changed.append("views_gate_10000")
        events.append({"event": "views_gate_10000", "from": baseline,
                       "to": total,
                       "aksi": "gerbang submit Ternak Klip tercapai — "
                               "ajukan submission dari pemilih"})
        new_st["baseline_total"] = total
    elif total - baseline >= STEP:
        changed.append("views_up")
        events.append({"event": "views_up", "from": baseline, "to": total,
                       "delta": total - baseline})
        new_st["baseline_total"] = total
    save_state(new_st)
    print(json.dumps({"changed": changed, "events": events,
                      "total": total, "baseline": new_st["baseline_total"],
                      "fetch_ok": ok_count, "fetch_fail": len(fail)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
# Batch 8 niche — render cutter_720 v3.6 dari clips8-<id>.json (seleksi MANUAL).
# Menunggu marker transkrip, lalu menunggu file clips8 per sumber (dibuat manual).
# TIDAK memanggil highlight.py / LLM apa pun.
set -u
SCRATCH="$HOME/workspace/scratch/cliptest2"
BASE="$HOME/workspace/divisi/freelancer-clipper/produksi/2026-10-31/batch-8/niche"
HD="$SCRATCH/hd-sources"
REVIEW="$BASE/review"
LOG="$SCRATCH/batch8-niche-pipeline.log"
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
mkdir -p "$REVIEW"
log "Menunggu transkripsi batch 8 selesai..."
for i in $(seq 1 900); do
  grep -q "SEMUA TRANSCRIPT BATCH 8 NICHE SELESAI" "$SCRATCH/batch8-niche-transcribe.log" 2>/dev/null && break
  sleep 120
done
run_source() {
  local id="$1"
  local srt="$BASE/transcript-$id/transcript.srt" words="$BASE/transcript-$id/words.json"
  local clips="$SCRATCH/clips8-$id.json"
  for i in $(seq 1 900); do
    [ -s "$clips" ] && break
    sleep 120
  done
  if [ ! -s "$clips" ]; then log "SKIP $id: clips8 tidak ada setelah menunggu."; return; fi
  if [ ! -s "$srt" ]; then log "SKIP $id: transkrip tidak ada."; return; fi
  local src="$BASE/$id.mp4"; [ -s "$HD/$id.mp4" ] && src="$HD/$id.mp4"
  log "Potong $id dari $src (cutter_720 v3.6, 720x1280)..."
  local extra=""
  [ -f "$BASE/no-subs-$id" ] && extra="$extra --no-subs"
  [ -f "$BASE/facetrack-$id" ] && extra="$extra --facetrack"
  [ -s "$words" ] && extra="$extra --words $words" || log "PERINGATAN $id: words.json tidak ada — fallback SRT polos."
  python3 "$SCRATCH/cutter/cutter_720.py" --video "$src" --srt "$srt" \
    --clips "$clips" --outdir "$REVIEW" $extra >> "$LOG" 2>&1
  cp "$REVIEW/summary.json" "$REVIEW/summary-$id.json" 2>/dev/null || true
  log "Selesai $id."
}
run_source 1xqIK4dFZts
run_source e4rkrjzV6Mk
run_source qGsDzrVSAN8
run_source bc0EdznQ_VM
run_source sYAU98ejav4
python3 - "$REVIEW" "$SCRATCH" <<'PYEOF' >> "$LOG" 2>&1
import json, glob, os, sys
review, scratch = sys.argv[1], sys.argv[2]
clips = []
for hl_path in sorted(glob.glob(os.path.join(scratch, "highlights8-*.json"))):
    hl = json.load(open(hl_path))
    summ = {}
    sp = os.path.join(review, f"summary-{hl['source']}.json")
    if os.path.exists(sp):
        for s in json.load(open(sp)):
            summ[s["name"]] = s
    for c in hl["clips"]:
        s = summ.get(c["name"], {})
        clips.append({"file": os.path.basename(s.get("path", c["name"] + ".mp4")),
            "name": c["name"], "source": hl["source"], "start": c["start"], "end": c["end"],
            "duration_s": s.get("duration_s", round(c["end"] - c["start"], 1)),
            "hook": c.get("hook", ""), "score": c.get("score"), "ok": bool(s.get("ok")),
            "width": s.get("width"), "height": s.get("height"), "error": s.get("error", "")})
json.dump({"batch": "2026-10-31/batch-8/niche", "total": len(clips), "clips": clips},
          open(os.path.join(review, "manifest.json"), "w"), indent=1, ensure_ascii=False)
print("MANIFEST", len(clips), "klip")
PYEOF
echo "BATCH 8 PIPELINE DONE" | tee -a "$LOG"
touch "$SCRATCH/batch8-niche-pipeline.done"

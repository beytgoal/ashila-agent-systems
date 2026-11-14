#!/usr/bin/env bash
# Rantai batch 8 v2 (per-sumber, tumpang-tindih unduh+transkripsi):
# untuk tiap sumber: tunggu file finalnya ada -> transkripsi sumber itu ->
# setelah semua: tulis marker -> pipeline (pipeline menunggu clips8 manual).
set -u
VENV="$HOME/workspace/scratch/cliptest/AI-Youtube-Shorts-Generator/venv/bin/python"
MODEL="$HOME/workspace/scratch/cliptest2/models/faster-whisper-large-v3-turbo"
BASE="$HOME/workspace/divisi/freelancer-clipper/produksi/2026-10-31/batch-8/niche"
HD="$HOME/workspace/scratch/cliptest2/hd-sources"
SCRATCH="$HOME/workspace/scratch/cliptest2"
LOG="$SCRATCH/batch8-niche-transcribe.log"
wait_src() {
  local id="$1"
  for i in $(seq 1 1440); do
    [ -s "$HD/$id.mp4" ] || [ -s "$BASE/$id.mp4" ] && return 0
    sleep 60
  done
  return 1
}
run_one() {
  local id="$1" src=""
  wait_src "$id" || { echo "=== $(date '+%F %T') SKIP $id (sumber tak muncul)" | tee -a "$LOG"; return; }
  [ -s "$HD/$id.mp4" ] && src="$HD/$id.mp4" || src="$BASE/$id.mp4"
  if [ -s "$BASE/transcript-$id/transcript.srt" ] && [ -s "$BASE/transcript-$id/words.json" ]; then
    echo "=== $(date '+%F %T') SKIP $id (transkrip sudah lengkap)" | tee -a "$LOG"; return
  fi
  echo "=== $(date '+%F %T') MULAI $src -> transcript-$id" | tee -a "$LOG"
  "$VENV" "$SCRATCH/transcribe_chunked.py" \
    --model "$MODEL" --audio "$src" --outdir "$BASE/transcript-$id" \
    --language id --chunk-s 240 --word-timestamps --beam-size 1 >> "$LOG" 2>&1
  echo "=== $(date '+%F %T') SELESAI $id (exit $?)" | tee -a "$LOG"
}
run_one 1xqIK4dFZts
run_one e4rkrjzV6Mk
run_one qGsDzrVSAN8
run_one bc0EdznQ_VM
run_one sYAU98ejav4
echo "=== $(date '+%F %T') SEMUA TRANSCRIPT BATCH 8 NICHE SELESAI" | tee -a "$LOG"
bash "$SCRATCH/run-batch8-pipeline.sh"

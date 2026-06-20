#!/usr/bin/env python3
"""Step 2: Transcribe audio using faster-whisper (local, free)."""
import argparse, json, sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="/tmp/vw_work/manifest.json")
    p.add_argument("--model_size", default="base", choices=["tiny", "base", "small", "medium", "large-v3"],
                   help="Whisper model size (larger = more accurate, slower)")
    p.add_argument("--language", default=None, help="Force language, e.g. 'zh' or 'en' (auto-detect if omitted)")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    return p.parse_args()


def main():
    args = parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        sys.exit(f"Manifest not found: {manifest_path}. Run step1_extract.py first.")

    manifest = json.loads(manifest_path.read_text())
    audio_path = manifest["audio"]

    print(f"Loading faster-whisper model: {args.model_size} on {args.device}")
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model_size, device=args.device, compute_type="int8")

    print(f"Transcribing: {audio_path}")
    segments, info = model.transcribe(
        audio_path,
        language=args.language,
        beam_size=5,
        vad_filter=True,
    )

    print(f"Detected language: {info.language} (prob={info.language_probability:.2f})")

    full_text = []
    timed_segments = []
    for seg in segments:
        full_text.append(seg.text.strip())
        timed_segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        print(f"  [{seg.start:.1f}s → {seg.end:.1f}s] {seg.text.strip()}")

    transcript = {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "full_text": " ".join(full_text),
        "segments": timed_segments,
    }

    out_dir = Path(manifest["out_dir"])
    transcript_path = out_dir / "transcript.json"
    transcript_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False))

    manifest["transcript"] = str(transcript_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    print(f"\n=== Transcript saved → {transcript_path} ===")
    print(f"Full text: {transcript['full_text'][:300]}{'...' if len(transcript['full_text']) > 300 else ''}")


if __name__ == "__main__":
    main()

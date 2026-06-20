#!/usr/bin/env python3
"""Step 1: Extract audio and sample frames from a video file."""
import argparse, os, subprocess, sys, json
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("video", help="Input video file path")
    p.add_argument("--out_dir", default="/tmp/vw_work", help="Working directory")
    p.add_argument("--fps", default="0.5", help="Frame extraction rate (frames/sec)")
    p.add_argument("--max_frames", type=int, default=6, help="Max frames to keep")
    return p.parse_args()


def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result


def main():
    args = parse_args()
    video = Path(args.video)
    if not video.exists():
        sys.exit(f"Video not found: {video}")

    out = Path(args.out_dir)
    frames_dir = out / "frames"
    out.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    audio_path = str(out / "audio.wav")
    print(f"[1/2] Extracting audio → {audio_path}")
    run(["ffmpeg", "-y", "-i", str(video),
         "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
         audio_path])

    print(f"[2/2] Extracting frames at {args.fps} fps → {frames_dir}/")
    run(["ffmpeg", "-y", "-i", str(video),
         "-vf", f"fps={args.fps}",
         str(frames_dir / "frame_%04d.jpg")])

    all_frames = sorted(frames_dir.glob("frame_*.jpg"))
    if len(all_frames) > args.max_frames:
        # keep evenly spaced sample
        step = len(all_frames) // args.max_frames
        selected = [all_frames[i] for i in range(0, len(all_frames), step)][:args.max_frames]
        for f in all_frames:
            if f not in selected:
                f.unlink()
        all_frames = selected

    result = {
        "video": str(video),
        "audio": audio_path,
        "frames": [str(f) for f in sorted(frames_dir.glob("frame_*.jpg"))],
        "out_dir": str(out),
    }
    manifest = out / "manifest.json"
    manifest.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

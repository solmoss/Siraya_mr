#!/usr/bin/env python3
"""
Video Quality Workflow — main orchestrator.
Usage:
    python3 run_workflow.py <video_path> [options]
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Video transcription + quality assessment workflow")
    p.add_argument("video", help="Path to input video file")
    p.add_argument("--out_dir", default="/tmp/vw_work", help="Working directory")
    p.add_argument("--fps", default="0.5", help="Frame sampling rate")
    p.add_argument("--max_frames", type=int, default=6)
    p.add_argument("--whisper_model", default="base",
                   choices=["tiny", "base", "small", "medium", "large-v3"])
    p.add_argument("--language", default=None, help="Force transcription language")
    p.add_argument("--api_key", default=os.environ.get("SIRAYA_API_KEY", ""))
    p.add_argument("--base_url", default="https://llm.siraya.ai/v1")
    p.add_argument("--model", default="gemini-2.5-pro", help="Vision model for quality assessment")
    p.add_argument("--skip_transcribe", action="store_true", help="Skip transcription step")
    return p.parse_args()


def run_step(name, cmd, env=None):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    t0 = time.time()
    result = subprocess.run(cmd, env=env or os.environ.copy())
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"\n[FAILED] {name} (exit {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)
    print(f"\n[OK] {name} completed in {elapsed:.1f}s")
    return elapsed


def main():
    args = parse_args()
    if not args.api_key:
        sys.exit("SIRAYA_API_KEY not set. Export it or pass --api_key.")

    script_dir = Path(__file__).parent
    manifest = f"{args.out_dir}/manifest.json"

    timings = {}

    # Step 1: Extract
    timings["extract"] = run_step(
        "Step 1/3 — Extract audio & frames",
        [
            sys.executable, str(script_dir / "step1_extract.py"),
            args.video,
            "--out_dir", args.out_dir,
            "--fps", args.fps,
            "--max_frames", str(args.max_frames),
        ]
    )

    # Step 2: Transcribe
    if not args.skip_transcribe:
        cmd = [
            sys.executable, str(script_dir / "step2_transcribe.py"),
            "--manifest", manifest,
            "--model_size", args.whisper_model,
        ]
        if args.language:
            cmd += ["--language", args.language]
        timings["transcribe"] = run_step("Step 2/3 — Transcribe audio", cmd)
    else:
        print("\n[SKIP] Step 2: transcription skipped")

    # Step 3: Quality
    timings["quality"] = run_step(
        "Step 3/3 — Quality assessment via Siraya",
        [
            sys.executable, str(script_dir / "step3_quality.py"),
            "--manifest", manifest,
            "--api_key", args.api_key,
            "--base_url", args.base_url,
            "--model", args.model,
        ]
    )

    # Final report
    result = json.loads(Path(manifest).read_text())
    quality = json.loads(Path(result["quality"]).read_text())

    transcript_text = ""
    if "transcript" in result:
        t = json.loads(Path(result["transcript"]).read_text())
        transcript_text = t.get("full_text", "")

    print(f"\n{'='*60}")
    print("  WORKFLOW COMPLETE")
    print(f"{'='*60}")
    print(f"\n[转文字结果]")
    print(transcript_text or "(已跳过)")
    print(f"\n[质量评分]")
    print(f"  综合评分  : {quality['overall_score']}/10")
    print(f"  清晰度    : {quality['resolution_quality']}")
    print(f"  光线      : {quality['lighting']}")
    print(f"  稳定性    : {quality['stability']}")
    print(f"  构图      : {quality['framing']}")
    print(f"  内容完整  : {quality['content_completeness']}")
    print(f"  问题列表  : {', '.join(quality['issues']) if quality['issues'] else '无'}")
    print(f"  结论      : {quality['recommendation']}")
    print(f"  总结      : {quality['summary']}")
    print(f"\n[耗时] 提取={timings['extract']:.1f}s "
          f"转文字={timings.get('transcribe', 0):.1f}s "
          f"质量评估={timings['quality']:.1f}s")
    print(f"\n[输出文件]")
    print(f"  {args.out_dir}/manifest.json")
    print(f"  {args.out_dir}/transcript.json")
    print(f"  {args.out_dir}/quality.json")


if __name__ == "__main__":
    main()

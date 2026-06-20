#!/usr/bin/env python3
"""Step 3: Assess video quality using multimodal LLM via Siraya."""
import argparse, base64, json, os, sys, time
from pathlib import Path
from openai import OpenAI

QUALITY_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "video_quality",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "overall_score": {
                    "type": "integer",
                    "description": "Overall quality score 1-10"
                },
                "resolution_quality": {
                    "type": "string",
                    "enum": ["清晰", "一般", "模糊", "严重模糊"]
                },
                "lighting": {
                    "type": "string",
                    "enum": ["正常", "偏暗", "过暗", "过曝", "不均匀"]
                },
                "stability": {
                    "type": "string",
                    "enum": ["稳定", "轻微抖动", "明显抖动", "严重抖动"]
                },
                "framing": {
                    "type": "string",
                    "enum": ["构图良好", "主体偏移", "主体截断", "构图混乱"]
                },
                "content_completeness": {
                    "type": "string",
                    "enum": ["完整", "部分缺失", "严重缺失"]
                },
                "issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific quality issues found"
                },
                "recommendation": {
                    "type": "string",
                    "enum": ["通过", "建议修改", "拒绝"]
                },
                "summary": {
                    "type": "string",
                    "description": "One-sentence quality summary in Chinese"
                }
            },
            "required": [
                "overall_score", "resolution_quality", "lighting",
                "stability", "framing", "content_completeness",
                "issues", "recommendation", "summary"
            ],
            "additionalProperties": False
        }
    }
}

SYSTEM_PROMPT = """你是专业的视频质量审核员。
你将收到从视频中均匀采样的帧图像，以及该视频的语音转文字结果（如有）。
请综合评估视频质量，输出结构化的 JSON 评分。
评分维度：
- overall_score: 1（极差）~ 10（完美）
- resolution_quality: 画面清晰度
- lighting: 光线情况
- stability: 画面稳定性（是否抖动）
- framing: 画面构图/取景
- content_completeness: 内容完整性
- issues: 列出具体问题（若无问题则为空数组）
- recommendation: 通过 / 建议修改 / 拒绝
- summary: 一句话总结视频质量
"""


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="/tmp/vw_work/manifest.json")
    p.add_argument("--api_key", default=os.environ.get("SIRAYA_API_KEY", ""))
    p.add_argument("--base_url", default="https://llm.siraya.ai/v1")
    p.add_argument("--model", default="gemini-2.5-pro")
    p.add_argument("--provider_sort", default="price", choices=["price", "latency", "throughput"])
    return p.parse_args()


def main():
    args = parse_args()
    if not args.api_key:
        sys.exit("SIRAYA_API_KEY not set")

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        sys.exit(f"Manifest not found: {manifest_path}. Run step1_extract.py first.")

    manifest = json.loads(manifest_path.read_text())
    frames = manifest.get("frames", [])
    if not frames:
        sys.exit("No frames found. Run step1_extract.py first.")

    transcript_text = ""
    if "transcript" in manifest:
        t = json.loads(Path(manifest["transcript"]).read_text())
        transcript_text = t.get("full_text", "")

    print(f"Frames: {len(frames)}, Transcript length: {len(transcript_text)} chars")
    print(f"Model: {args.model} via {args.base_url}")

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)

    # Build multimodal content
    content = []
    for i, frame_path in enumerate(frames):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encode_image(frame_path)}"
            }
        })

    user_text = f"以上是从视频中均匀采样的 {len(frames)} 帧画面。"
    if transcript_text:
        user_text += f"\n\n语音转文字内容：\n{transcript_text[:1000]}"
    user_text += "\n\n请评估视频质量，输出 JSON 评分。"
    content.append({"type": "text", "text": user_text})

    print("Calling Siraya for quality assessment...")
    t0 = time.time()
    response = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        response_format=QUALITY_SCHEMA,
        max_completion_tokens=1024,
        extra_body={
            "provider": {
                "sort": args.provider_sort,
                "allow_fallbacks": True,
            }
        }
    )
    elapsed = time.time() - t0

    raw = response.choices[0].message.content
    quality = json.loads(raw)

    quality_path = Path(manifest["out_dir"]) / "quality.json"
    quality_path.write_text(json.dumps(quality, indent=2, ensure_ascii=False))

    manifest["quality"] = str(quality_path)
    manifest["quality_model"] = response.model
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    print(f"\n=== Quality Report (in {elapsed:.1f}s, model={response.model}) ===")
    print(json.dumps(quality, indent=2, ensure_ascii=False))
    print(f"\nSaved → {quality_path}")

    tokens = response.usage
    print(f"Tokens: prompt={tokens.prompt_tokens} completion={tokens.completion_tokens}")


if __name__ == "__main__":
    main()

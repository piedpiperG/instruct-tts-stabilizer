# Instruct-TTS Stabilizer

Code, project page, and audio demos for the Interspeech 2026 paper:

**Stabilizing Instruction Supervision for Instruct-TTS via Controllable Diversification and Drift Filtering**

- Project page: https://piedpiperg.github.io/instruct-tts-stabilizer/
- Paper PDF: `docs/instruct-tts-stabilizer.pdf`
- Demo assets: `docs/demopage/`

This repository open-sources the data-centric recipe behind the paper. The
main idea is to stabilize the label-to-instruction pipeline before supervised
fine-tuning:

```text
structured labels
  -> controllable instruction diversification
  -> drift scoring and filtering
  -> attribute-aligned audio perturbation
  -> SFT manifest
  -> evaluation and demo page
```

## What Is Included

The repository is organized around the three mechanisms in the paper.

| Paper component | Code |
| --- | --- |
| Controllable instruction diversification | `src/instruct_tts_stabilizer/diversify/` |
| LLM-based drift filtering | `src/instruct_tts_stabilizer/filter/` |
| Attribute-aligned supervision | `src/instruct_tts_stabilizer/perturb/` |
| SFT manifest building | `src/instruct_tts_stabilizer/manifests/` |
| Demo-page asset building | `src/instruct_tts_stabilizer/demo/` |
| CER helper | `src/instruct_tts_stabilizer/eval/` |

The code is intentionally data-provider agnostic. It does not require the
private speech corpus used in the paper. You can run the same recipe on your
own speech clips and structured labels.

## Installation

```bash
git clone git@github.com:piedpiperG/instruct-tts-stabilizer.git
cd instruct-tts-stabilizer
python -m pip install -e .
```

Audio perturbation uses `ffmpeg` for pitch, speed, and volume changes. The
other pipeline stages use only the Python standard library.

## Quick Offline Smoke Test

The offline path uses deterministic templates and a lightweight heuristic
verifier, so it works without API keys.

```bash
mkdir -p outputs

python scripts/generate_candidates.py \
  --seeds examples/seed_attributes.demo.jsonl \
  --personas configs/personas.json \
  --constraints configs/constraints.json \
  --provider offline \
  --output outputs/candidates.demo.jsonl

python scripts/score_candidates.py \
  --input outputs/candidates.demo.jsonl \
  --provider heuristic \
  --output outputs/scored.demo.jsonl

python scripts/filter_candidates.py \
  --input outputs/scored.demo.jsonl \
  --threshold 5 \
  --output outputs/filtered.demo.jsonl \
  --rejected-output outputs/rejected.demo.jsonl

python scripts/perturb_audio.py \
  --input examples/audio_manifest.demo.jsonl \
  --config configs/perturbation.json \
  --output-dir outputs/perturbed_audio \
  --manifest-output outputs/perturbed.demo.jsonl \
  --dry-run

python scripts/build_sft_manifest.py \
  --audio examples/audio_manifest.demo.jsonl \
  --instructions outputs/filtered.demo.jsonl \
  --perturbed outputs/perturbed.demo.jsonl \
  --format cosyvoice2 \
  --output outputs/sft_manifest.demo.jsonl
```

## Online LLM Generation and Filtering

The LLM client is OpenAI-compatible and can be used with OpenAI, DeepSeek,
Qwen-compatible gateways, or a local vLLM server.

Examples:

```bash
export OPENAI_API_KEY=...
python scripts/generate_candidates.py \
  --seeds my_seed_attributes.jsonl \
  --personas configs/personas.json \
  --constraints configs/constraints.json \
  --provider openai \
  --model gpt-4o-mini \
  --output outputs/candidates.jsonl
```

On Windows PowerShell, use `$env:OPENAI_API_KEY="..."` or
`$env:DEEPSEEK_API_KEY="..."` instead of `export`.

```bash
export DEEPSEEK_API_KEY=...
python scripts/score_candidates.py \
  --input outputs/candidates.jsonl \
  --provider deepseek \
  --model deepseek-reasoner \
  --vote-times 3 \
  --output outputs/scored.jsonl
```

For GPT-4o-style strict verification:

```bash
export OPENAI_API_KEY=...
python scripts/score_candidates.py \
  --input outputs/candidates.jsonl \
  --provider openai \
  --model gpt-4o \
  --vote-times 3 \
  --output outputs/scored.jsonl
```

Then filter:

```bash
python scripts/filter_candidates.py \
  --input outputs/scored.jsonl \
  --threshold 5 \
  --output outputs/filtered.jsonl \
  --rejected-output outputs/rejected.jsonl
```

The threshold follows the paper setup: candidates with verifier score `<= 5`
are treated as drifted. If multiple scores are present, majority voting is used
for self-consistency.

## Input Formats

Seed attributes:

```json
{"id":"seed_0001","category":"模仿电台DJ","slot_type":"speaker","attributes":{"speaker_style":"电台DJ"},"required_terms":["电台DJ"]}
```

Audio manifest:

```json
{"id":"utt_0001","seed_id":"seed_0001","text":"接下来为您播放一段音乐。","audio_path":"/path/to/utt_0001.wav"}
```

Generated candidates:

```json
{"id":"seed_0001__plain__short","seed_id":"seed_0001","category":"模仿电台DJ","sentence":"请模仿电台DJ。"}
```

## Attribute-Aligned Supervision

The paper augments speech clips through pitch, speaking-rate, and volume
perturbations. The default config mirrors that design:

```json
{
  "pitch_semitones": [-3, -2, -1, 1, 2, 3],
  "speed_factors": [0.8, 0.9, 1.1, 1.2, 1.3],
  "volume_db": [-9, -6, -3, 3, 6, 9]
}
```

Run without `--dry-run` once `ffmpeg` is installed and the audio paths are real:

```bash
python scripts/perturb_audio.py \
  --input my_audio_manifest.jsonl \
  --config configs/perturbation.json \
  --output-dir outputs/perturbed_audio \
  --manifest-output outputs/perturbed.jsonl
```

## Build a CosyVoice2-Style SFT Manifest

```bash
python scripts/build_sft_manifest.py \
  --audio my_audio_manifest.jsonl \
  --instructions outputs/filtered.jsonl \
  --perturbed outputs/perturbed.jsonl \
  --format cosyvoice2 \
  --output outputs/cosyvoice2_sft.jsonl
```

The generated rows contain:

- `text`: transcript text
- `prompt_text`: stabilized natural-language instruction
- `audio`: path to the speech clip
- `meta`: seed and instruction-source metadata

Adapt the output fields in `src/instruct_tts_stabilizer/manifests/build.py` if
your training stack expects a different schema.

## Demo Page

The public project page is served from `docs/`. Existing audio examples are in
`docs/demopage/`.

To copy a new set of evaluation outputs into a demo asset directory:

```bash
python scripts/build_demo_page.py \
  --list eval/list.jsonl \
  --system-dir eval/base \
  --system-dir eval/sft \
  --system-dir eval/voxinstruct \
  --system-dir eval/full \
  --tasks APS,DSD,RP \
  --output-dir docs/demopage
```

## Tests

```bash
python -m unittest discover -s tests
```

## Notes on Reproducibility

The paper uses a Chinese speech collection, CosyVoice2 as the backbone, and
LLM families including DeepSeek-R1 and GPT-4o for instruction generation and
verification. Those external assets are not bundled here. This repository
provides the reusable data pipeline, prompts, filtering logic, perturbation
recipe, and manifest builders so the method can be applied to new datasets.

## Citation

```bibtex
@inproceedings{geng2026stabilizing,
  title = {Stabilizing Instruction Supervision for Instruct-TTS via Controllable Diversification and Drift Filtering},
  author = {Geng, Yizhong and Mao, Kecan and Li, Qifei and Wang, Cong and Gao, Yingming and Wang, Ruimin and Wang, Chunfeng and Li, Hao and Li, Ya},
  booktitle = {Proceedings of Interspeech 2026},
  year = {2026}
}
```

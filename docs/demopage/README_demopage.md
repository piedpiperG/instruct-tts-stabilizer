# demopage 目录说明

路径：`/mnt/volumes/base-tts-ali-sh-mix/gengyizhong/data/instructttseval/demopage`

这个目录用于制作/展示 demo page：

- `list.jsonl` 定义 demo 使用的条目集合（按行序即索引）。
- 其余子目录按“系统/版本”组织音频结果；每个系统下再按任务/提示类型分为 `APS`、`DSD`、`RP`。

## 目录结构

```text
demopage/
  list.jsonl
  base/
    APS/
    DSD/
    RP/
  full/
    APS/
    DSD/
    RP/
  sft/
    APS/
    DSD/
    RP/
  qwen3tts/
    APS/
    DSD/
    RP/
  voxinstruct/
    APS/
    DSD/
    RP/
```

## 文件命名与匹配规则

`list.jsonl` 是 JSON Lines 格式：每行一个 JSON 对象，代表一条 demo 样本。

- **索引（index）**：通常用“行号”作为索引（1-based）。例如第 1 行就是索引 1。
- **样本 id**：每行都有 `id`（例如 `zh_0`），用于和音频文件名对齐。
- **音频文件名**：统一为 `${id}.wav`（例如 `zh_0.wav`）。
- **音频所在位置**：音频不放在 JSON 里，而是放在对应“系统/版本”目录下的 `APS/DSD/RP` 子目录中。

### `list.jsonl` 字段说明（结合示例）

`list.jsonl` 的典型字段如下：

- `id`：样本唯一标识，用于定位音频（`${id}.wav`）。
- `text`：需要合成的文本内容。
- `APS` / `DSD` / `RP`：三种不同的提示/条件文本（用于三类任务或三种风格设定）。
- `reference_audio`：参考音频元信息（路径/采样率）。注意这里的 `reference_audio.path` 通常指向“原始参考音频”，不等同于 demo page 展示的各系统输出音频。

示例（`list.jsonl` 第 1 行，已做断行以便阅读）：

```json
{
  "id": "zh_0",
  "text": "他不行了,都怪我害了他,他就相信您叶老师,您救救他吧。",
  "APS": "音高: 中高音...",
  "DSD": "体现标准普通话的发音...",
  "RP": "像一位在深夜单独打电话寻求朋友原谅的青年...",
  "reference_audio": {
    "path": "audio/zh/zh_0.wav",
    "sampling_rate": 16000
  }
}
```

### demo page 如何用索引取音频

假设你要展示“索引 N 的样本”在不同系统、不同任务下的音频：

1. 读取 `list.jsonl` 第 N 行，得到 `id`（例如 `zh_31`）。
2. 选择系统目录（例如 `sft`）。
3. 选择任务目录（`APS`/`DSD`/`RP`）。
4. 组合路径并加载音频：
   - `demopage/sft/APS/zh_31.wav`
   - `demopage/sft/DSD/zh_31.wav`
   - `demopage/sft/RP/zh_31.wav`

如果要做“多系统对比”，只需要把第 2 步的系统目录替换为 `base/`、`full/` 等。

## 子目录含义

- `APS/`：以条目中的 `APS` 文本作为提示/条件生成的音频。
- `DSD/`：以条目中的 `DSD` 文本作为提示/条件生成的音频。
- `RP/`：以条目中的 `RP` 文本作为提示/条件生成的音频。

## 当前数据概况（便于核对）

- `list.jsonl`：10 行（10 个 id）。
- `base/{APS,DSD,RP}`：各 10 个 wav。
- `full/{APS,DSD,RP}`：各 10 个 wav。
- `sft/{APS,DSD,RP}`：各 10 个 wav。
- `qwen3tts/{APS,DSD,RP}`：各 10 个 wav。
- `voxinstruct/{APS,DSD,RP}`：各 10 个 wav。

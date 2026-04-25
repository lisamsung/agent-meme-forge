# Example Test Report

本报告记录 `agent-meme-forge` 在本机跑出的端到端样例。前三组使用合成参考图验证处理器；AI 吉祥物样例使用真实 `image_gen` contact sheet 验证“提示词计划 -> 生图 -> 切图 -> 微信打包”链路。最新版本已进一步迁移 `generate2dsprite` 的 motion-sheet 规则，默认推荐每个表情使用 `2x4` 八帧语义动作 sheet。

## Test Environment

- Project path: `/Users/shanxingjun/vibecoding/codex/projects/agent-meme-forge`
- Command family: `python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack`
- Output root: `output/examples/`
- Verification date: 2026-04-25

## Cases

| Case | Mode | Style | Persona | GIF count | Max GIF bytes | Thumb count | Max thumb bytes | Cover/Icon/Banner bytes |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 科研打工人 24 微信包 | `wechat` | `clean-sticker` | `科研打工人` | 24 | 29,427 | 24 | 4,310 | 7,631 / 1,837 / 20,625 |
| 码农 16 微信包 | `wechat` | `pixel-art` | `码农` | 16 | 27,744 | 16 | 4,120 | 7,589 / 1,758 / 20,945 |
| 都市丽人 18 自用包 | `self_use` | `office-cartoon` | `都市丽人` | 18 | 30,295 | 18 | 4,545 | 8,162 / 1,680 / 23,008 |
| AI 吉祥物 24 微信包 | `wechat` | `clean-sticker` | `科研打工人` | 24 | 72,653 | 24 | 17,132 | 30,124 / 2,579 / 29,238 |

## ImageGen Sample

- Plan: `output/examples/ai-research-mascot-plan.json`
- Raw sheet: `output/raw-sheets/ai-research-mascot-sheet.png`
- Split sources: `output/sample-sources/ai-mascot/01.png ... 24.png`
- WeChat package: `output/examples/ai-mascot-24/`
- Published preview assets: `docs/assets/ai-mascot-sheet-preview.jpg` and `docs/assets/ai-mascot-wenxianshan.gif`

The sample subject is an original warm cream-and-coral AI assistant mascot. It is only inspired by familiar AI-assistant aesthetics and explicitly avoids official logos, brand marks, and exact mascot copying.

The published `ai-mascot-wenxianshan.gif` preview has been regenerated from a real motion sheet and contains semantic frames instead of a single static pose bounce.

## Motion-Sheet Upgrade

新版本新增高质量动画路径：

- `plan-pack` 默认输出 `animation.source_layout = 2x4`，也支持 `1x8`。
- 每条 `image_prompts` 都要求 exact grid、same identity、same bounding box、same pixel scale、no edge crossing、transparent PNG background preferred、solid `#FF00FF` fallback。
- `build-pack --source-layout 2x4` 会把每个源图当成一张 8 帧动作 sheet，而不是只对静态图做缩放 bounce。
- `remove_chroma_background()` 已增强近似洋红和边缘红/粉 spill 处理，降低 fallback 去背残留。
- `manifest.json` 为每个条目记录 `animation_source`、`source_layout`、`source_frame_count`。

## Positive Results

- `wechat` 模式可生成 16 和 24 个动态 GIF 包。
- `self_use` 模式可生成 18 个自用包。
- 每个样例都生成了：
  - `named-gifs/*.gif`
  - `wechat-submit/main/*.gif`
  - `wechat-submit/thumbs/*.png`
  - `wechat-submit/cover.png`
  - `wechat-submit/icon.png`
  - `wechat-submit/banner.png`
  - `manifest.json`
  - `manifest.csv`
- 三个样例的主 GIF 均为 `240x240`，小于微信主图 `500KB` 上限。
- 三个样例的缩略图均为 `120x120`，小于 `50KB` 上限。

## Negative Result

Command:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir output/sample-sources/research \
  --output-dir output/examples/invalid-18-wechat \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 18 \
  --mode wechat
```

Result:

```text
exit_code:2
error: WeChat sticker albums must contain 16 or 24 GIFs; use self_use mode for 18.
```

## Takeaways

- 24 个微信包是默认推荐路径，覆盖完整梗库和微信专辑上传需求。
- 16 个微信包适合做更轻量、质量更集中的版本。
- 18 个应定位为自用素材包，不应承诺可直接作为微信表情专辑上传。
- 当前处理器输出体积余量很大，后续真实 AI 图像输入也有压缩空间。

## Regression Fixes

Review 后补充验证：

- 同一输出目录先生成 24 个微信包、再生成 16 个微信包时，`wechat-submit/main/`、`wechat-submit/thumbs/` 和 `named-gifs/` 会清理旧文件，不再留下 `17.gif` 到 `24.gif`。
- 超长中文文案会在最小字号下裁成可容纳的行数，并用省略号结尾，避免文字覆盖角色或越出 240x240 画布。
- GitHub Pages 的中文文档按钮改为 GitHub README 链接，不再解析到站点根目录导致 404。

最新自动化验证：`pytest -q` 共 19 项通过。

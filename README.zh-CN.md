# agent-meme-forge

> **没人用的表情包就是垃圾。** 一个 Codex skill：把一张参考图——或者一句角色概念——变成符合微信表情开放平台规格、聊天里真的会被发出去的动态 GIF 表情包。

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![CI](https://github.com/lisamsung/agent-meme-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/lisamsung/agent-meme-forge/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/lisamsung/agent-meme-forge)](https://github.com/lisamsung/agent-meme-forge/releases/latest)
[![Codex Skill](https://img.shields.io/badge/codex-skill-ff4f64.svg)](skills/generate-meme-gif-pack/SKILL.md)
[![English README](https://img.shields.io/badge/README-English-green.svg)](README.md)
[![Live demo](https://img.shields.io/badge/demo-GitHub%20Pages-2563eb.svg)](https://lisamsung.github.io/agent-meme-forge/)

<p align="center">
  <img src="docs/assets/ai-mascot-shoudao-lixian.gif" alt="HR已读" width="180" />
  <img src="docs/assets/ai-mascot-jiazaizhong.gif" alt="录用快来" width="180" />
  <img src="docs/assets/ai-mascot-wenxianshan.gif" alt="先睡为敬" width="180" />
</p>

<p align="center"><sub>来自 <code>法律硕士毕业求职人</code> 24 张包里的三张：HR 已读不回、求一个 offer 显灵、躺平先睡。都是从 4 张 keypose 干净源图，本地渲染成 16 帧 240×240 GIF。</sub></p>

---

## 为什么有这个项目

市面上"AI 表情包"工具大多在追求"可爱"。但**可爱不会被发**，**能发**才会被发。

每张这个 skill 规划的表情，都必须先过 `sendability_gate`：

1. **复用触发**——一个真实聊天场景里、有人会主动发它的瞬间。
2. **情绪价值**——给对方放松、阴阳怪气、附和、慌乱、安慰、拖延。
3. **创意钩子**——一个想法，而不是一句文字盖在脸上。
4. **视觉笑点**——手机上 240×240，一秒看懂。

只是装饰、只是可爱、只是"氛围感"的表情，会在生图前就被要求重写，而不是事后再砍。

## 它会产出什么

```
你的参考图    ┐
   或文字概念 ├──▶  计划 ──▶  4 个 keypose ──▶  16 帧 GIF  ──▶  微信投稿包
   + 人设+风格 ┘   (JSON)   (每个表情 1 次     (本地渲染、         (24 张、
                            image_gen 调用)     中文文案排版)        manifest、QC 报告)
```

成品长这样：

```
output/my-pack/
├── named-gifs/                # 收到离线.gif、加载中.gif … (转发用)
├── wechat-submit/
│   ├── main/01.gif … 24.gif   # 编号上传序列
│   ├── thumbs/01.png … 24.png # 120×120 缩略图
│   ├── cover.png  icon.png  banner.png
│   └── reward-guide.png       # 接受赞赏时可选
├── preview.html               # 整包浏览器预览
├── manifest.json / .csv       # 完整机读 manifest
└── qc_report.json             # 逐张 QC + 连续性闸门
```

底层做了什么：

- **Plan**——角色卡 + 24 个能发的梗条目 + 每张表情的无文字 `image_gen` 提示词。
- **Render**——4 个 keypose → 16 帧确定性渲染，使用动作模板（`soul_offline`、`loading_loop`、`pretend_understand` 等），本地补特效（灵魂泡泡、loading 点、汗滴、尴尬线）。图片模型不需要画 16 帧连贯动画。
- **QC**——假棋盘格识别、出格检测、bbox 漂移、道具位置/面积突变、单帧道具闪现、脸型/头部漂移、循环首尾跳变、低运动能量护栏。投稿模式走 strict 闸门。
- **Pack**——16 或 24 张 240×240 < 500 KB GIF、缩略图、封面、图标、横幅、双套文件名（编号上传 + 中文转发）、CSV + JSON manifest。
- **Submit（可选）**——Playwright + headed Microsoft Edge 的微信表情开放平台 runbook，覆盖扫码登录、CAPTCHA、实名、驳回处理。

## 快速开始

```bash
# 1. 克隆并安装
git clone https://github.com/lisamsung/agent-meme-forge.git
cd agent-meme-forge
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'

# 2. 交互式做计划
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-wizard

# 3. 生成并 accept-generated 完所有 keypose sheet 之后，
#    打包微信上传文件
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir output/raw-frames/MyPack \
  --output-dir output/my-pack \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 --mode wechat \
  --pack-name 我的表情包 \
  --source-mode keyposes --keypose-layout 2x2 --render-frame-count 16 \
  --quality-mode submission --strict-qc --strict-continuity-qc
```

打开 `output/my-pack/preview.html` 看整包效果，然后把 `wechat-submit/` 上传到微信表情开放平台。

> **提示——先做前 3 张。** 不要一次生成 24 张 keypose。先 `qc-sheet` 验前 3 张，再用 `build-preview --preview-count 3` 看动效，前 3 张能发再继续后面 21 张。技术过关 ≠ 能发，前 3 张不够好就先改文案或动作模板。

## 安装为 Codex skill

```bash
mkdir -p ~/.codex-switcher/skills
cp -R skills/generate-meme-gif-pack ~/.codex-switcher/skills/
# 重启 Codex session
```

之后跟 Codex 说一句"做一个科研打工人的微信表情包"，它会跑 intake、写计划，并跨轮次带你做 keypose 生成和 QC。

## 它怎么工作

这个 skill 有两个不太常见的产品取舍：

**1 · 图片模型每张表情只画 4 个稳定 keypose。**
让扩散模型自由画 16 帧连贯动画，大多数时候会得到跳闪、互不相关的帧。这里改成只让它画一张干净的 `2×2` sheet——*起姿 / 蓄力 / 高光梗 / 回到循环点*——剩下的 16 帧、停顿、蓄力、回弹、首尾闭合都由本地确定性渲染器算出来。动作模板（`soul_offline`、`loading_loop`、`pretend_understand` 等）在本地补漫画特效（灵魂泡泡、loading 点、汗滴），模型不会随手发明也不会随手漏画。

**2 · 中文文案永远不让模型画。**
所有文字由本地处理器排版，字体、字号、裁切规则统一，24 张表情看起来才像一组。视觉提示词强制禁止文字、字幕、对话气泡、UI、logo。

结果：身份更稳定、重生次数更少、微信规格输出可预测。

**最丝滑的路径——密集真帧（推荐）。** 决策 #1 让 keypose 当「任何 provider 都能跑」的安全默认。当图片模型足够强、能在一张 sheet 里画出约 8 张真正不同且一致的连续帧时，`dense_frames` 模式就让它这么画——再由本地一道工序把每帧统一到相同尺寸和头部位置、排好时序、做好首尾闭合。这是**追求最丝滑时的推荐路径**（每个包可能有几张要重生）。详见 **[密集真帧](skills/generate-meme-gif-pack/references/dense-frames.md)**。

## 微信规格默认

| 资源 | 规格 |
|---|---|
| 主图 GIF | `240×240`，循环，< 500 KB（默认目标 < 480 KB） |
| 缩略图 PNG | `120×120`，< 50 KB |
| 专辑图标 | `50×50` 透明背景，< 30 KB |
| 封面 | `240×240` 透明背景，< 80 KB |
| 详情横幅 | `750×400`，不放文字，< 80 KB |
| 包数量 | **16 或 24**（默认 24） |
| 赞赏引导图（可选） | `750×560`，启用 `接受赞赏` 时 |
| 赞赏致谢图（可选） | `750×750`，启用 `接受赞赏` 时 |

**正式投稿前请以微信表情开放平台官方帮助中心当前文档为准**，平台规格会变。

## 仓库结构

```
skills/generate-meme-gif-pack/
├── SKILL.md                 # agent 规则和工作流
├── scripts/meme_pack.py     # plan → accept → qc → preview → build 流水线
└── references/
    ├── personas.md  styles.md  meme-library.md
    ├── prompt-rules.md      # 原图提示词 + sendability gate
    ├── wechat-spec.md       # 输出约束
    └── wechat-platform-upload.md   # 可选 Playwright 投稿 runbook

docs/                        # GitHub Pages 产品页 + 样例素材
tests/                       # pytest 套件（`pytest -q`）
```

## 文档

- [产品页](https://lisamsung.github.io/agent-meme-forge/)
- [Skill 规则和工作流](skills/generate-meme-gif-pack/SKILL.md)
- [密集真帧——追求丝滑的推荐路径](skills/generate-meme-gif-pack/references/dense-frames.md)
- [样例测试报告](docs/example-test-report.md)
- [微信公众号宣传稿](docs/wechat-public-account-draft.md)
- [English README](README.md)
- [版本记录](CHANGELOG.md)
- [发布流程](docs/RELEASING.md)

## 开发与贡献

- 测试：`pytest -q`，覆盖微信数量约束、keypose 计划、动作模板渲染、连续性 QC、道具闪现 / 脸型漂移闸门、sheet 切帧、中文文案排版、完整投稿包结构。
- 已用四组样例端到端验证：24 × `科研打工人`、16 × `码农`、18 × `都市丽人`（自用）、24 × 原创 AI 吉祥物 `2×4` strict-QC 投稿模式。
- 微信平台规格随时可能变化，正式上传前请复核官方帮助中心。

欢迎 issue 和 PR，尤其是新动作模板、新人设库、新本地特效和可复现的
QC 改进。提交较大改动前请先读 [CONTRIBUTING.md](CONTRIBUTING.md)。使用问题请发到
[GitHub Discussions](https://github.com/lisamsung/agent-meme-forge/discussions)，
安全问题请按 [SECURITY.md](SECURITY.md) 的私密渠道报告。

## 肖像与内容审核

如果参考图是真人，请先确认你拥有授权或合法使用权。默认策略是"风格化但认得出本人"，**不是**写实换脸。公开发布时请避开政治、仇恨、低俗、攻击性、医疗承诺、骚扰内容——微信会驳回，这个 skill 也会拦。

## License

项目代码采用 [MIT License](LICENSE)。随项目分发的站酷快乐体采用 SIL Open Font
License 1.1，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

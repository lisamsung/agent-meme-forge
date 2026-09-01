# agent-meme-forge Project Status

## 项目定位

独立公开仓库，提供 Codex skill `generate-meme-gif-pack` 和本地 Python 处理器，用于从参考人物/形象图或文字角色概念生成微信表情开放平台可用的动态 GIF 表情包。

## 当前状态

- **v0.1.0 正式开源版本（2026-09-01）**：补齐 `CHANGELOG.md`、
  `CONTRIBUTING.md`、行为准则、安全与支持策略、Issue/PR 模板、CODEOWNERS、
  多 Python 版本 CI 和可复核的发布流程；GitHub Release 与源码归档以
  `v0.1.0` 标签为准。
- 仓库骨架已建立。
- Skill 文档和 reference 文档已建立。
- `meme_pack.py` 已实现基础处理流程：梗库、motion-sheet prompt 计划、contact sheet 切图、sheet 逐帧读取、motion-sheet QC、组件清理、统一尺度、中文文案排版、GIF 生成、微信投稿包导出、manifest/qc_report 生成。
- 测试覆盖处理器核心行为和 skill 文档完整性。
- 已用四组样例验证：24 个科研打工人微信包、16 个码农微信包、18 个都市丽人自用包、24 个原创 AI 吉祥物 2x4 strict-QC 微信包。
- 已补微信公众号宣传稿：`docs/wechat-public-account-draft.md`。
- 已修复 review 发现的问题：重复构建会清理旧上传文件、超长文案会省略并保持在画布内、GitHub Pages 中文文档链接不再 404。
- 已补强“主动生图”链路：`plan-pack` 生成角色卡和逐条 `image_gen` motion-sheet prompt；`qc-sheet` 先验收前 3 张；`split-sheet` 支持把 4x6 预览图切成 24 个源图；`build-pack --source-layout 2x4 --quality-mode submission --strict-qc` 支持默认 8 帧动作 sheet；透明背景优先，`#FF00FF` 去背兜底，假透明棋盘格直接拒绝。
- 已新增 `plan-wizard` 交互式入口：新手可以选择参考图或文字概念、人设/场景、画面风格、微信/自用数量、质量模式和输出计划路径。
- 已新增公开 demo 资产：`docs/assets/ai-mascot-shoudao-lixian.gif`、`ai-mascot-jiazaizhong.gif`、`ai-mascot-wenxianshan.gif` 和 `ai-mascot-sheet-preview.jpg`。
- GitHub 仓库与 Pages 已发布：`https://github.com/lisamsung/agent-meme-forge` / `https://lisamsung.github.io/agent-meme-forge/`。
- **已新增「密集真帧」路线（`--source-mode dense_frames`，推荐的最丝滑路径，2026-06-28）**：放弃「4 关键姿势 + 本地伪造动作」，改由生图模型在一张 2x4 曝光表里画 8 张真正逐帧不同的连续帧，本地组装。
  - 引擎（`meme_pack.py`）：`normalize_dense_frames` 切片 → 统一尺寸（消除模型 ~5% 逐帧尺寸漂移导致的忽大忽小）→ **头质心横向锚定**（消除大幅不对称动作下 bbox 居中引起的头部摆动，14→0.8px；由「放置对比」闸控制，大型偏心道具自动回退 bbox，适合直立角色）→ 逐帧时序（~11fps + 首帧呼吸）→ 中文文案 → continuity QC → 投稿包；空格子（模型漏帧）直接拒。
  - 生图通道**与厂商解耦**：`scripts/imagegen_client.py`（零依赖 OpenAI 兼容 Images 客户端，端点由 `MEME_IMAGE_*`/`OPENAI_*` 配置）+ `scripts/dense_frames.py`（曝光表/canonical 提示词 + reference 锚定的 `edit` 路径）。
  - 规划链路已接通：`plan-pack/plan-wizard --source-mode dense_frames` 发出曝光表提示词（角色卡 + 可发性闸 + 逐帧表演计划 + 配方），`qc-sheet`/`build-pack` 已支持；非 `{2x4,4x4}` 的 dense 布局在 plan 时即拒（不发出构建接不住的计划）。
  - 已在真实素材验证：法硕研究生（简单）、橘猫打工人多道具大幅甩臂（困难）均 8 帧一致、尺寸稳、头不漂、中文文案干净。每块均经 codex（xhigh）审计。
  - 参考文档：`skills/generate-meme-gif-pack/references/dense-frames.md`。
  - 待续：完整 16/24 真实包压测、4x4 体积截断与循环闭合、本地无法校验逐格身份（生成期 reference 锚定负责）。视频生成→拆帧是未来更贵的可选高级档（成功商业化后再提醒拓展）。

## 开发入口

```bash
git clone https://github.com/lisamsung/agent-meme-forge.git
cd agent-meme-forge
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

## 主要路径

- `skills/generate-meme-gif-pack/SKILL.md`
- `skills/generate-meme-gif-pack/scripts/meme_pack.py`
- `skills/generate-meme-gif-pack/references/`
- `tests/`
- `docs/index.html`

## 待确认

- 微信规格后续应以官方帮助中心的当前版本复核。

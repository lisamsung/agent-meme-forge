# agent-meme-forge Project Status

## 项目定位

独立公开仓库，提供 Codex skill `generate-meme-gif-pack` 和本地 Python 处理器，用于从参考人物/形象图或文字角色概念生成微信表情开放平台可用的动态 GIF 表情包。

## 当前状态

- 仓库骨架已建立。
- Skill 文档和 reference 文档已建立。
- `meme_pack.py` 已实现基础处理流程：梗库、motion-sheet prompt 计划、contact sheet 切图、sheet 逐帧读取、中文文案排版、GIF 生成、微信投稿包导出、manifest 生成。
- 测试覆盖处理器核心行为和 skill 文档完整性。
- 已用四组样例验证：24 个科研打工人微信包、16 个码农微信包、18 个都市丽人自用包、24 个 image_gen AI 吉祥物微信包。
- 已补微信公众号宣传稿：`docs/wechat-public-account-draft.md`。
- 已修复 review 发现的问题：重复构建会清理旧上传文件、超长文案会省略并保持在画布内、GitHub Pages 中文文档链接不再 404。
- 已补强“主动生图”链路：`plan-pack` 生成角色卡和逐条 `image_gen` motion-sheet prompt；`split-sheet` 支持把 4x6 预览图切成 24 个源图；`build-pack --source-layout 2x4` 支持默认 8 帧动作 sheet；透明背景优先，`#FF00FF` 去背兜底。
- GitHub 仓库与 Pages 已发布：`https://github.com/lisamsung/agent-meme-forge` / `https://lisamsung.github.io/agent-meme-forge/`。

## 开发入口

```bash
cd /Users/shanxingjun/vibecoding/codex/projects/agent-meme-forge
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

## 主要路径

- `skills/generate-meme-gif-pack/SKILL.md`
- `skills/generate-meme-gif-pack/scripts/meme_pack.py`
- `skills/generate-meme-gif-pack/references/`
- `tests/`
- `docs/index.html`

## 待确认

- 微信规格后续应以官方帮助中心的当前版本复核。

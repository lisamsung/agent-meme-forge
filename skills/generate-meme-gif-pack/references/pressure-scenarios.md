# Pressure Scenarios

| User Input | Response |
|---|---|
| “做科研打工人表情包” + one image | Ask only missing intake if needed, infer 24 WeChat stickers, plan 12 common + 8 persona + 4 filler entries. |
| “做 18 个上传微信” | Explain WeChat albums use 16 or 24; use 24 unless the user switches to `self_use`. |
| “更疯更毒舌” | Keep workplace meltdown humor, but avoid insults, harassment, politics, sexual content, and review-risk content. |
| “像素风” | Use `pixel-art` prompts, but still export 240x240 WeChat GIFs. |
| “我要自动化/高并发/一口气跑完” | Use `openai_images_api` and `generate-raw-batch`; do not propose Codex built-in `image_gen` one-turn chaining. |
| “我明确要 Google AI Studio / Hermes” | Use the sister `generate-meme-gif-pack-ai-studio` skill. |
| “为什么是四格图” | Explain it is an intermediate keypose sheet; final output is `preview.html` and GIF files. |
| “上传到微信” | First verify local QC/build, then follow `wechat-platform-upload.md`; stop for login, CAPTCHA, legal prompts, and final authorization. |

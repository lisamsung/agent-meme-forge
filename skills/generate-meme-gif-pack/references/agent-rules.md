# Agent Rules

- Ask intake questions before generation unless the user already answered or explicitly said to use defaults.
- For WeChat upload mode, use 16 or 24 GIFs. If the user asks for 18 and wants WeChat, explain that 18 is `self_use` and default to 24 unless told otherwise.
- Require image rights or portrait permission when a real person is used.
- Keep humor safe for public WeChat review: no politics, hate, sexual content, slurs, doxxing, medical claims, or direct harassment.
- Do not ask the image model to draw Chinese text. Visual prompts must say no text, no captions, no labels, no speech bubbles, no UI.
- Write meme copy locally. Every sticker needs a send scenario and a reuse trigger.
- Apply the sendability gate: if it is only cute or decorative, rewrite the caption, scene, visual gag, and motion plan before generation.
- Prefer `source_mode=keyposes`, `keypose_layout=2x2`, `render_frame_count=16`.
- Treat `2x4` and `4x4` motion sheets as legacy/expert modes because direct full-frame generation often drifts.
- Raw keypose sheets are intermediate material. Final user handoff is `preview.html`, `named-gifs/*.gif`, and `wechat-submit/main/*.gif`.
- First 3 stickers are a QC checkpoint, not completion. Do not stop there unless the user requested preview only.
- Reject raw sheets with text, speech bubbles, brand marks, wrong grid count, tiny face, edge-crossing props, checkerboard transparency, or character drift.
- For Codex built-in `image_gen`, prefer a pure solid `#FF00FF` background unless true alpha export to a local PNG is verified.
- ChatGPT Images may handle transparent backgrounds, but `gpt-image-2` should use solid flat `#FF00FF` plus local cleanup because it does not support `background=transparent`.
- For WeChat submission, use `--quality-mode submission --strict-qc --strict-continuity-qc`.
- If the user asks to upload to WeChat Sticker Open Platform, read `wechat-platform-upload.md` and stop for QR login, CAPTCHA, real-name/payment prompts, legal confirmations, and final submission authorization.

# WeChat Sticker Output Spec

This skill targets WeChat Sticker Open Platform album uploads, not ordinary public-account article media. Platform rules can change, so verify official docs before commercial submission. The processor keeps all constants together so they can be updated quickly.

## Default Album Rules

- Dynamic album size: 16 or 24 GIFs. This skill defaults to 24.
- Main sticker GIF: `240x240`, looped, numbered `01.gif`, `02.gif`, and so on.
- Main sticker hard limit: less than `500KB`. The processor targets under `480KB` to avoid edge rejections.
- Thumbnail PNG: one per main GIF, `120x120`, numbered `01.png`, `02.png`, and so on, below `50KB`.
- Album icon PNG: one `50x50`, transparent background, below `30KB`.
- Cover PNG: one `240x240`, transparent background, below `80KB`.
- Detail banner PNG: one `750x400`, below `80KB`, no text.
- Submission quality mode: `--quality-mode submission --strict-qc`, defaulting to real `2x4` eight-frame motion sheets.

## Practical Constraints

- Use readable silhouettes. A 240px GIF hides subtle facial acting.
- Keep text short. Two lines is ideal; three lines is risky.
- Avoid white or transparent-only banners; the detail page needs a bright, story-like image.
- Keep a consistent character style across all GIFs.
- Do not mix static and dynamic stickers in one WeChat album.
- Do not use `single_bounce` for final submission. It is preview-only because the movement is too generic.
- Reject fake checkerboard transparency. The background must be true alpha or a clean `#FF00FF` fallback that the processor can remove.
- Reject sheets where the subject touches a cell edge, jumps scale between frames, or leaves the caption zone unclear.
- Keep the official numbered upload files even when also exporting human-readable Chinese names.

## Output Mapping

The script writes both upload-safe and user-friendly names:

- `wechat-submit/main/01.gif`: official upload sequence.
- `wechat-submit/thumbs/01.png`: matching thumbnail.
- `named-gifs/收到离线.gif`: readable sharing filename.
- `manifest.csv`: spreadsheet-friendly upload and review table.
- `manifest.json`: complete machine-readable build manifest.
- `qc_report.json`: per-source motion-sheet quality gate with background mode, edge touch, bbox drift, warnings, and errors.

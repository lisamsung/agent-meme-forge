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
- Optional reward guide image: one `750x560` JPG, PNG, or GIF when `接受赞赏` is enabled.
- Optional reward thanks image: one `750x750` JPG, PNG, or GIF when `接受赞赏` is enabled.
- Submission quality mode: `--quality-mode submission --strict-qc`. The CLI default is `source_mode=keyposes`, `keypose_layout=2x2`, local 16-frame rendering (robust, any provider). For maximum smoothness the recommended path is `source_mode=dense_frames` (`2x4`/`4x2` real frames, drift-corrected locally; see `references/dense-frames.md`). Raw `2x4`/`4x4` `motion_sheet` is legacy/expert only.

## Platform Metadata Review Pitfalls

- `版权归属` is the copyright attribution subject, not a yes/no originality field. Do not write only `原创`; use the actual rights-holder, platform account, or legal subject name. If the user has not given that name, ask before submitting.
- `角色/内容` should describe the visible subject rather than the drawing style. For a stylized person or photo-derived female character, choose `人物角色 - 女人`; for a male subject choose the matching `人物角色` subtype. Use `动漫/漫画/卡通人物` only for a genuinely original comic/cartoon character.
- If the user asks to accept rewards, enable `接受赞赏` only after preparing all required reward fields: a 5-15 character `赞赏引导语`, a `750x560` `赞赏引导图`, and a `750x750` `赞赏致谢图`.
- When WeChat rejects a submission, the rejection page is the current source of truth. Fix the exact rejected fields, save, confirm the preview metadata changed, and resubmit without regenerating the pack unless the rejection mentions image assets.

## Practical Constraints

- Use readable silhouettes. A 240px GIF hides subtle facial acting.
- Raw `4x4` `motion_sheet` (pre-drawn, no local normalization) drifts and costs more image-generation effort and GIF bytes; use it selectively. For full-frame animation prefer `dense_frames` (recommended for smoothness) or `keyposes` (the safe default).
- Keep text short. Two lines is ideal; three lines is risky.
- Avoid white or transparent-only banners; the detail page needs a bright, story-like image.
- Keep a consistent character style across all GIFs.
- Do not mix static and dynamic stickers in one WeChat album.
- Do not use `single_bounce` for final submission. It is preview-only because the movement is too generic.
- Reject fake checkerboard transparency. The background must be true alpha or a clean `#FF00FF` fallback that the processor can remove.
- Reject sheets where the subject touches a cell edge, jumps scale between frames, or leaves the caption zone unclear. Bigger pose changes are allowed only when the identity, scale, and cell containment remain stable.
- Keep the official numbered upload files even when also exporting human-readable Chinese names.

## Output Mapping

The script writes both upload-safe and user-friendly names:

- `wechat-submit/main/01.gif`: official upload sequence.
- `wechat-submit/thumbs/01.png`: matching thumbnail.
- `named-gifs/收到离线.gif`: readable sharing filename.
- `wechat-submit/reward-guide.png`: optional `750x560` reward guide image for `接受赞赏`.
- `wechat-submit/reward-thanks.png`: optional `750x750` reward thanks image for `接受赞赏`.
- `manifest.csv`: spreadsheet-friendly upload and review table.
- `manifest.json`: complete machine-readable build manifest.
- `qc_report.json`: per-source motion-sheet quality gate with background mode, edge touch, bbox drift, warnings, and errors.

# WeChat Platform Upload Runbook

Use this only after the pack has passed local QC and the user explicitly asks to submit or upload it to WeChat Sticker Open Platform. This is browser automation over the real website, not an unofficial WeChat API.

## Tool Choice

- Preferred tool: Playwright CLI with headed Microsoft Edge.
- Do not use the Codex in-app browser for `sticker.weixin.qq.com` if it is blocked by site permissions.
- Keep a persistent browser profile so QR login survives navigation.

Example:

```bash
/Users/shanxingjun/.codex-switcher/skills/playwright/scripts/playwright_cli.sh open \
  https://sticker.weixin.qq.com \
  --headed \
  --browser msedge \
  --persistent \
  --profile output/playwright/wechat-sticker-profile
```

Stop for user-owned boundaries: QR login, CAPTCHA, real-name verification, payment-account setup, unexpected legal confirmations, or final publish/send actions the user has not authorized.

## Submission Flow

1. Open the platform, ask the user to 扫码登录 if needed, then navigate to `提交作品` -> `表情专辑`.
2. Use `snapshot` before every page-changing click. Element refs are not stable after navigation.
3. Choose `动态表情`.
4. Upload main stickers from `wechat-submit/main/01.gif ... 24.gif`.
5. Fill the 24 `输入含义词` fields from `manifest.csv` `keyword`.
6. Fill basic metadata:
   - 名称: pack name.
   - 介绍: short pack story or usage summary.
   - 版权归属: actual rights-holder, platform account, or legal subject name. Do not write only `原创`.
7. Upload `wechat-submit/banner.png`, `wechat-submit/cover.png`, and `wechat-submit/icon.png`.
8. Fill additional metadata:
   - 类型: usually `卡通表情/其他` for generated sticker-style output.
   - 角色/内容: choose by visible subject, not art style. For a portrait-like female subject, choose `人物角色 - 女人`; use `动漫/漫画/卡通人物` only for a truly original comic/cartoon character.
   - 表情风格: choose 1-2 matching tags.
   - 表情主题: choose the dominant use context.
   - 下载地区: use the user's requested region, commonly `中国大陆`.
9. If the user wants `接受赞赏`, check it and fill the extra fields before saving:
   - `赞赏引导语`: 5-15 Chinese characters.
   - `赞赏引导图`: upload a user-provided or separately prepared image, typically `750x560`.
   - `赞赏致谢图`: upload a user-provided or separately prepared image, typically `750x750`.
   - Stop if these files do not exist. The pack builder does not create reward images automatically.
10. Click `保存`. Confirm the preview metadata shows the corrected copyright, role/content, and reward state.
11. Click `提交` only when the user has explicitly authorized submission. Confirm the result page says `表情提交成功，请耐心等待审核`.

## File Upload Implementation

Use Playwright `setInputFiles`, not OS file-picker automation. Inspect file inputs first because indices can drift:

```bash
/Users/shanxingjun/.codex-switcher/skills/playwright/scripts/playwright_cli.sh run-code \
'async (page) => await page.$$eval("input[type=file]", inputs => inputs.map((i, idx) => ({idx, accept: i.accept, multiple: i.multiple})))'
```

Observed input order on the current platform version:

- `0`: main GIFs, `accept="image/gif"`, `multiple=true`.
- `1`: banner, PNG/JPG.
- `2`: cover, PNG.
- `3`: icon, PNG.
- `4`: reward guide image, PNG/GIF/JPG, only visible after `接受赞赏`.
- `5`: reward thanks image, PNG/GIF/JPG, only visible after `接受赞赏`.
- `6`: optional proof files.

Upload all main GIFs:

```js
const base = "/absolute/path/to/output/my-pack/wechat-submit/main";
const files = Array.from({ length: 24 }, (_, i) =>
  `${base}/${String(i + 1).padStart(2, "0")}.gif`
);
await page.locator("input[type=file]").nth(0).setInputFiles(files);
```

Upload image assets:

```js
const base = "/absolute/path/to/output/my-pack/wechat-submit";
await page.locator("input[type=file]").nth(1).setInputFiles(`${base}/banner.png`);
await page.locator("input[type=file]").nth(2).setInputFiles(`${base}/cover.png`);
await page.locator("input[type=file]").nth(3).setInputFiles(`${base}/icon.png`);
// Only run these after verifying the files exist or the user provided replacements.
await page.locator("input[type=file]").nth(4).setInputFiles(`${base}/reward-guide.png`);
await page.locator("input[type=file]").nth(5).setInputFiles(`${base}/reward-thanks.png`);
```

## 审核驳回 / Rejection Loop

If the platform rejects the pack, open the rejection reason page and treat its wording as authoritative.

- Fix only the rejected fields unless another validation error appears.
- Common rejection: `版权归属` says `请直接填写版权归属主体的名称`. Replace `原创` with the actual subject name.
- Common rejection: role/content says to choose `人物角色 - 女人`. Change only that selector.
- Save first, verify the setting page changed, then resubmit.
- Do not regenerate the sticker GIFs unless the rejection specifically names image quality, content, dimensions, or file format.

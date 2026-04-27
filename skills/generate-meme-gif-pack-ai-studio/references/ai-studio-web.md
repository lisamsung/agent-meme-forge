# Google AI Studio Web Notes

This provider route exists to use Google AI Studio Web membership capacity instead of paid image API calls.

## Model Choice

- Nano Banana Pro: use for final candidate keypose sheets when character consistency and instruction following matter most.
- Nano Banana 2: use for cheaper or faster preview attempts before committing to Pro output.

Naming note: Google API documentation describes Nano Banana Pro as `gemini-3-pro-image-preview` and the fast Nano Banana image model as `gemini-2.5-flash-image`. AI Studio Web labels can differ from API model codes; this skill follows the visible Web UI labels used by the operator.

## Recommended Parameters

- Aspect ratio: `1:1`
- Output format: PNG
- Image size: `2K` or highest stable quality available in the UI
- Background: flat `#00FF00`; switch to `#FF00FF` if green conflicts with the character
- Quantity: one generated image per prompt
- Layout: one `2x2` keypose sheet, exactly four cells

## Operator Contract

The operator may be Hermes or a human. The operator is allowed to use the AI Studio page normally, but must not bypass safety controls, CAPTCHA, login protections, download restrictions, or browser automation blocks.

Save each image into the board's download directory. Prefer exact target filenames such as `01-收到离线-2x2.png`. If AI Studio forces generic names, preserve generation order and use `import-downloads --mode ordered` only after verifying the count.

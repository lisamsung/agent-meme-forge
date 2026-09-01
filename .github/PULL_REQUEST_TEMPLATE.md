## Problem

What concrete problem does this pull request solve? Link the issue when one
exists.

## Change

Describe the observable behavior and the important implementation choices.

## Validation

List the exact commands, fixtures, and visual checks you ran. Distinguish unit
tests from GIF or browser acceptance.

## Checklist

- [ ] The change is scoped to the public skill or deterministic processor.
- [ ] `python -m pytest -q` passes locally.
- [ ] `python -m compileall -q skills/generate-meme-gif-pack/scripts` passes.
- [ ] User-visible changes are recorded in `CHANGELOG.md`.
- [ ] Matching English and Chinese claims are updated together.
- [ ] Changed WeChat requirements include an official source and check date.
- [ ] New assets are rights-safe and their source or generation workflow is stated.
- [ ] No credentials, signed URLs, private portraits, or generated output are included.

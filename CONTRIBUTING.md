# Contributing to agent-meme-forge

Thanks for helping improve the public Codex skill and its deterministic GIF
processor. Contributions should make sticker packs more sendable, more
reproducible, or easier to validate.

## Start in the right place

- Use [GitHub Discussions](https://github.com/lisamsung/agent-meme-forge/discussions)
  for usage questions and early design ideas.
- Open an issue for a reproducible bug or a scoped feature proposal.
- Report security problems privately as described in [SECURITY.md](SECURITY.md).
- Search existing issues before opening a new one.

For a substantial behavior change, open an issue before writing the patch. This
avoids spending time on a direction that conflicts with the skill's core
constraints: sendability, deterministic local rendering, no model-drawn
Chinese text, and explicit QC gates.

## Development setup

Requirements: Git and Python 3.10 or newer.

```bash
git clone https://github.com/lisamsung/agent-meme-forge.git
cd agent-meme-forge
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

The image-generation path may use a configured external provider, but the test
suite must not require paid API calls or real credentials.

## What to change

The public project has three main contribution surfaces:

1. `skills/generate-meme-gif-pack/SKILL.md` and `references/` — agent workflow,
   prompt rules, personas, platform notes, and QC guidance.
2. `skills/generate-meme-gif-pack/scripts/` — deterministic planning, slicing,
   rendering, captioning, QC, and export behavior.
3. `tests/` — executable contracts for the skill documentation and processor.

Keep commercial services, private provider routes, deployment credentials, and
unrelated product code out of this repository.

## Contribution requirements

### Code and processor changes

- Add or update tests for observable behavior.
- Preserve deterministic output unless nondeterminism is the feature under
  review and is documented explicitly.
- Keep the supported baseline at Python 3.10 or update the compatibility claim
  in the same pull request.
- Do not add a runtime dependency when the standard library or an existing
  dependency is sufficient.
- Do not make network calls during the default test suite.

### Skill, prompt, persona, and meme-library changes

Explain the real chat situation the change serves. A new sticker concept should
have a reuse trigger, emotional value, creative hook, and a visual gag readable
at 240 x 240. Decorative variants without a sendability case are not enough.

If a change affects generated sheets, include a small, rights-safe sample or a
written before/after account. Never commit a private reference portrait.

### WeChat platform claims

Platform limits and review rules can change. When changing a claimed WeChat
requirement, link the official source in the pull request and state the date it
was checked. Treat the repository defaults as validated implementation targets,
not a permanent guarantee from WeChat.

### Images, fonts, and generated assets

Only contribute assets you created, assets you are authorized to redistribute,
or assets under a compatible license. Record the source and license in the pull
request. For generated assets, state the generator or workflow and confirm that
the inputs were yours or authorized.

Do not contribute celebrity likenesses, private photos, trademarks used as
characters, or assets copied from existing sticker packs without permission.

## Validation

Run the full local gate before opening a pull request:

```bash
python -m pytest -q
python -m compileall -q skills/generate-meme-gif-pack/scripts
```

For visual or GIF-output changes, also build the smallest representative pack
and inspect its `preview.html` and `qc_report.json`. Report exactly what you
tested; a unit-test pass is not a substitute for visual acceptance.

## Pull requests

- Keep each pull request focused on one concern.
- Use a clear title and explain the problem, the chosen behavior, and the
  evidence that the change works.
- Link the relevant issue when one exists.
- Update `CHANGELOG.md` for user-visible changes.
- Update both English and Chinese documentation when the same product claim
  appears in both.
- Never include API keys, signed URLs, provider responses containing secrets,
  private user images, or generated output directories.

Maintainers may ask for a smaller patch, stronger reproduction steps, or a
rights-safe test fixture before review.

## License

By submitting a contribution, you agree that it may be distributed under the
project's [MIT License](LICENSE).

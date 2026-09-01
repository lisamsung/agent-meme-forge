# Release process

This project uses Semantic Versioning. `pyproject.toml` is the source of the
current version, and `CHANGELOG.md` records user-visible changes.

## Release gate

A release candidate must have:

- a clean commit on `main`;
- a matching version in `pyproject.toml` and `CHANGELOG.md`;
- the full test suite passing on the supported CI versions;
- successful script compilation;
- no credentials, private portraits, signed URLs, or generated output archives;
- visual inspection when rendering, caption, animation, or Pages output changed;
- current documentation for any changed platform constraint.

## Maintainer steps

1. Move completed entries from `Unreleased` into a dated version section.
2. Update the version in `pyproject.toml`.
3. Run:

   ```bash
   python -m pytest -q
   python -m compileall -q skills/generate-meme-gif-pack/scripts
   ```

4. Merge the release pull request only after CI passes.
5. Create and push a signed or annotated `vX.Y.Z` tag on the verified `main`
   commit.
6. Create a GitHub Release from that tag. Use the matching changelog section,
   add upgrade or compatibility notes, and state what was actually validated.
7. Verify the public release page, source archives, README links, and GitHub
   Pages site.

GitHub generates source `.zip` and `.tar.gz` archives from the tag. Do not attach
private test inputs or build outputs. If a future release adds a convenience
artifact, document a reproducible build command and publish its SHA-256 checksum.

## Release notes boundaries

Do not claim current WeChat approval, universal provider compatibility, paid API
validation, or visual acceptance unless those checks were performed for that
exact release candidate. Unit tests, a release tag, and a successful GitHub
workflow are separate pieces of evidence.

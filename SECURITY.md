# Security policy

## Supported versions

Security fixes are applied to the latest published release and the `main`
branch. Older releases are not maintained separately.

## Reporting a vulnerability

Please report a suspected vulnerability through
[GitHub private vulnerability reporting](https://github.com/lisamsung/agent-meme-forge/security/advisories/new).
Do not open a public issue before a fix or mitigation is available.

Include:

- the affected release or commit;
- the smallest reproducible example;
- the security impact and realistic attack path;
- any proposed mitigation;
- whether the report contains private user images or provider data.

Never include live API keys, bearer tokens, signed asset URLs, or images you are
not authorized to share. Replace secrets with unmistakable placeholders and
redact private reference images whenever the issue can be reproduced without
them.

The maintainer will acknowledge a usable report, assess its scope, and coordinate
a disclosure timeline with the reporter. Exact response and remediation times
depend on severity and reproducibility.

## Scope

This policy covers the code and documentation in this repository. Vulnerabilities
in an external image provider, GitHub, Codex, or the WeChat Sticker Open Platform
should also be reported to the relevant vendor. Configuration mistakes involving
third-party credentials may still be relevant here when the repository's code or
documentation caused the unsafe behavior.

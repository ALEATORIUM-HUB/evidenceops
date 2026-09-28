# Security policy

Version 0.1.0 is an early local-file toolkit. Its operations do not modify audited
inputs. Event recording appends to a caller-selected output file. The ledger is
an append-only API; filesystem owners retain the ability to edit it.

Use stable local input trees and dedicated ledger outputs. Do not use this version
as a sandbox for hostile code or as proof of a transactionally consistent filesystem.
See the detailed limitations in [architecture](docs/architecture.md).

## Reporting a vulnerability

Once a public GitHub repository exists and private vulnerability reporting has been
enabled, use its Security tab → Report a vulnerability to submit a private advisory.
For this local-only checkout, contact the repository owner privately using an
existing trusted channel; no hosted reporting endpoint is claimed to exist yet.

Include affected versions, a synthetic reproduction, impact, and a suggested fix
if available. Do not disclose sensitive details publicly during the 90 days after
reporting. Coordinate disclosure with the maintainer; earlier disclosure may be
agreed when a fix is available. Response times are not guaranteed for this early project.

## Release security gate

Before every public push and before a release tag, scan the full Git history and
working tree with Gitleaks, inspect all tracked files for sensitive or proprietary
material, and review the staged diff. Check personal paths, real business fixtures,
authentication material, generated reports, and build artifacts. A clean automated
scan is evidence, not a guarantee; human review is also required.

Never commit private datasets. Examples and tests must remain synthetic.

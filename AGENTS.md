# Instructions for coding agents

These instructions apply throughout this repository.

## Attribution

Include a `Co-Authored-By` trailer in every commit containing substantive work
produced by an AI assistant, including documentation changes.

For ChatGPT or Codex, use:

```text
Co-Authored-By: ChatGPT <noreply@openai.com>
```

For Claude, use:

```text
Co-Authored-By: Claude <noreply@anthropic.com>
```

Claude Code adds its own attribution trailers, which can name the model and link
the session (`Co-Authored-By: Claude <model> <noreply@anthropic.com>` and
`Claude-Session: <URL>`). Keep them exactly as Claude Code writes them.

Only credit assistants that contributed to the commit. Preserve the existing
author and other contributors' trailers. Do not invent a model name or version.
Put trailers in the commit message, separated from the body by a blank line.
Exported Git patches must carry the same attribution in their commit message.

When an authorized change to commit metadata changes its ID, regenerate any
exported patches and update associated references to that commit.

## Working with the maintainer

Answer informational questions without editing files or rewriting commits.
A question about whether a change would be appropriate is not itself a request
to make that change. Carry out explicit implementation requests within their
stated scope.

## Development and validation

Follow [CONTRIBUTING.md](CONTRIBUTING.md). The supported environments and full
test sequence are defined in [.github/workflows/zeyple.yml](.github/workflows/zeyple.yml).
Use the distribution's Python 3 and `python3-gpg` bindings when testing.

- Add regression tests for behavior changes and bug fixes.
- Run `python3 -m pytest tests/` for Python changes.
- Run `pycodestyle --show-pep8 --max-line-length=100 .` for Python style checks.
- For man-page changes, run `mandoc -Tlint -W warning zeyple/zeyple.8` and
  `python3 docs/build-man-html.py > man.html`.
- For packaging changes, commit them, then run `./tools/build-release` and
  `lintian --info --pedantic dist/*.changes`.
- Run `tests/e2e.sh dist/zeyple_*_all.deb` only in a disposable container: it
  installs and removes packages and modifies Postfix configuration, users,
  keys, logs, and mailboxes.
- Documentation-only changes do not require the full integration suite.

For packaging and release work, follow [RELEASING.md](RELEASING.md). Report the
checks actually run and distinguish local preparation from remote publication.

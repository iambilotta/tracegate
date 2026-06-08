# Installing tracegate

tracegate ships as a **single-file binary per OS** (Nuitka, ADR-0001): no Python
environment required. Each ecosystem's installer just fetches that binary, so a Spring,
Laravel, or Next.js dev installs with the package manager they already use.

> Binaries are attached to each [GitHub Release](https://github.com/iambilotta/tracegate/releases)
> by the `release` workflow: `tracegate-linux-x86_64`, `tracegate-macos-arm64`,
> `tracegate-windows-x86_64.exe`.

## Direct download (any OS)

```bash
# Linux x86_64 (adjust the asset name for your OS)
curl -fsSL -o tracegate \
  https://github.com/iambilotta/tracegate/releases/latest/download/tracegate-linux-x86_64
chmod +x tracegate
./tracegate --help
```

## Homebrew (macOS / Linux)

A tap formula downloads the release binary:

```bash
brew install iambilotta/tap/tracegate
```

The formula (`Formula/tracegate.rb`) points at the release asset for the current OS/arch
and installs it as `tracegate`. (Tap published separately; the formula fetches the binary,
it does not build from source.)

## npm / npx (Node ecosystem)

```bash
npx @iambilotta/tracegate --check          # one-off, no install
npm install -g @iambilotta/tracegate       # global
```

The npm package is a thin wrapper whose `postinstall` downloads the matching release
binary for the host platform into the package, and whose `bin` shells out to it. Nothing
is compiled at install time.

## pip / pipx (Python ecosystem)

If you already have Python, install from source — no binary fetch needed:

```bash
pipx install tracegate            # isolated
# or
pip install tracegate
```

This is the secondary channel (ADR-0001): it requires a Python runtime, so it is for
people who already have one. The binary channels above are the zero-dependency default.

## composer (PHP ecosystem)

```bash
composer require --dev iambilotta/tracegate
```

The Composer package's installer script fetches the release binary into `vendor/bin/` so
`./vendor/bin/tracegate` works like any other dev tool.

## Verify

```bash
tracegate --help
tracegate .            # zero-config: detect the stack, generate the catalog
tracegate . --check    # CI drift-gate
```

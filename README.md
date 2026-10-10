# RIOT CI on Woodpecker — proof of concept

This repository demonstrates running **RIOT OS's Murdock CI behaviour on
[Woodpecker CI](https://woodpecker-ci.org)**, reproducing Murdock's job
discovery and execution as closely as possible (full builds, quickbuilds,
merge-queue builds, labels, caching) with Woodpecker pipelines instead of the
`dwq`/disque worker fleet.

The actual PoC lives in [`poc/`](poc/README.md) — **start there**. This top-level
repository only wires the upstream projects together as git submodules so the
PoC can be published without vendoring them.

## Layout

| Path | Role |
| --- | --- |
| [`poc/`](poc/README.md) | the PoC: config extension, dispatcher, compose stack, scripts |
| `RIOT/` | [RIOT-OS/RIOT](https://github.com/RIOT-OS/RIOT) (submodule) — the project being built |
| `murdock/` | [murdock-ng/murdock](https://github.com/murdock-ng/murdock) (submodule) — the CI server the PoC emulates |
| `murdock-scripts/` | [RIOT-OS/murdock-scripts](https://github.com/RIOT-OS/murdock-scripts) (submodule) — Murdock's `build.sh` |
| `murdock-worker/` | [RIOT-OS/murdock-worker](https://github.com/RIOT-OS/murdock-worker) (submodule) — Murdock's worker stack |
| `riotdocker/` | [RIOT-OS/riotdocker](https://github.com/RIOT-OS/riotdocker) (submodule) — RIOT build images |
| `murfrog/` | [AnnsAnns/murfrog](https://github.com/AnnsAnns/murfrog) (submodule) — the Murdock web UI the PoC compares against |

## Getting started

```sh
git clone --recurse-submodules <this-repo> riot-ci-woodpecker
cd riot-ci-woodpecker/poc
# see poc/README.md for prerequisites (Docker, woodpecker-cli, images)
./scripts/poc-up.sh
./scripts/poc-trigger-pr.sh          # quickbuild
./scripts/poc-trigger-mergequeue.sh  # full build
```

Submodules can be fetched/updated later with:

```sh
git submodule update --init --recursive
```

## Notes

- The `RIOT` and `murfrog` submodules currently point at the author's forks
  (`AnnsAnns/*`); switch the URLs in `.gitmodules` to the canonical upstreams if
  you prefer.
- The PoC's own runtime state (`poc/.env.poc`, `poc/.token`, trigger clones,
  generated configs) is git-ignored.

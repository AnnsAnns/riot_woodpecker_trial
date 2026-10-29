# Murdock CI: documentation and local workspace

This repository contains a Starlight documentation site for Murdock, the continuous integration server used by RIOT OS. It also contains a small local stack that runs the Murdock API.

The previous Woodpecker proof of concept is archived and removed from the working tree. See [Archived Woodpecker PoC](#archived-woodpecker-poc) to restore it.

## Layout

| Path | Role |
| --- | --- |
| [`docs/`](docs/README.md) | Astro Starlight documentation for Murdock features and API |
| [`murdock-backend/`](murdock-backend/README.md) | Local Murdock stack and the legacy backend compose file |
| [`patches/`](patches/README.md) | Git patches for submodule fixes |
| `murdock/` | [murdock-ng/murdock](https://github.com/murdock-ng/murdock) (submodule), the Murdock server |
| `RIOT/` | [AnnsAnns/RIOT](https://github.com/AnnsAnns/RIOT) (submodule), RIOT and `.murdock` |
| `murdock-scripts/` | [RIOT-OS/murdock-scripts](https://github.com/RIOT-OS/murdock-scripts) (submodule), RIOT-specific Murdock scripts |
| `murdock-worker/` | [RIOT-OS/murdock-worker](https://github.com/RIOT-OS/murdock-worker) (submodule), legacy worker stack |
| `riotdocker/` | [RIOT-OS/riotdocker](https://github.com/RIOT-OS/riotdocker) (submodule), RIOT build images |
| `murfrog/` | [AnnsAnns/murfrog](https://github.com/AnnsAnns/murfrog) (submodule), Murdock web UI |

## Documentation

```sh
cd docs
npm install
npm run dev      # local preview
npm run build    # static site in docs/dist/
```

## Run Murdock locally

See [`murdock-backend/README.md`](murdock-backend/README.md). The short version:

```sh
cd murdock-backend
mkdir -p data
docker compose up -d
# API:      http://localhost:8000/api
# OpenAPI:  http://localhost:8000/openapi.json
```

For a full RIOT job with the `murfrog` UI, see
[`docs/src/content/docs/getting-started/riot-demo.mdx`](docs/src/content/docs/getting-started/riot-demo.mdx).

## Submodules

```sh
git submodule update --init --recursive
```

The `patches/` directory contains fixes for the `murdock` submodule. Apply,
check, or revert them without changing the submodule source in place:

```sh
./patches/apply.sh check
./patches/apply.sh apply
./patches/apply.sh revert
```

The local RIOT demo does not need these patches. See
[`patches/README.md`](patches/README.md) for the list.

## Archived Woodpecker PoC

The Woodpecker proof of concept is archived at tag `archive/woodpecker-poc`. It is no longer part of the working tree. To inspect or restore it:

```sh
# Inspect in a separate worktree. This does not change the current tree.
git worktree add /tmp/woodpecker-poc archive/woodpecker-poc

# Or restore the files into this tree.
git checkout archive/woodpecker-poc -- poc
```

The PoC runtime state (`.env.poc`, `.token`) was ignored by git and is not part of the tag. `./scripts/poc-up.sh` regenerates it when the files are missing.

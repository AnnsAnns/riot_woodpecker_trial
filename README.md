# Murdock CI: documentation and local workspace

This repository contains a Starlight documentation site for Murdock, the continuous integration server used by RIOT OS. It also contains a small local stack that runs the Murdock API.

The previous Woodpecker proof of concept is archived and removed from the working tree. See [Archived Woodpecker PoC](#archived-woodpecker-poc) to restore it.

## Layout

| Path | Role |
| --- | --- |
| [`docs/`](docs/README.md) | Astro Starlight documentation for Murdock features and API |
| [`murdock-backend/`](murdock-backend/README.md) | Local Murdock stack and the legacy backend compose file |
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

## Submodules

```sh
git submodule update --init --recursive
```

## Archived Woodpecker PoC

The Woodpecker proof of concept is archived at tag `archive/woodpecker-poc`. It is no longer part of the working tree. To inspect or restore it:

```sh
# Inspect in a separate worktree. This does not change the current tree.
git worktree add /tmp/woodpecker-poc archive/woodpecker-poc

# Or restore the files into this tree.
git checkout archive/woodpecker-poc -- poc
```

The PoC runtime state (`.env.poc`, `.token`) was ignored by git and is not part of the tag. `./scripts/poc-up.sh` regenerates it when the files are missing.

---
title: Archived Woodpecker PoC
description: How to inspect or restore the removed Woodpecker proof of concept.
---

The Woodpecker proof of concept was removed from the working tree and archived
at the git tag `archive/woodpecker-poc`. The tag points at the last commit that
contained `poc/`.

Nothing else in this repository depends on it. The Murdock documentation and the
local Murdock stack are independent.

## Inspect without changing this tree

```sh
git worktree add /tmp/woodpecker-poc archive/woodpecker-poc
```

The PoC is then at `/tmp/woodpecker-poc/poc`.

## Restore into this tree

```sh
git checkout archive/woodpecker-poc -- poc
```

This restores the directory but leaves it staged. The PoC had its own
`poc/.gitignore` for runtime state.

## Running it again

The original entry point was:

```sh
cd poc
./scripts/poc-up.sh
```

It starts Forgejo, Redis, the Woodpecker server/agent, and the Murdock-compatible
configuration extension, then logs in and activates the RIOT repository. The stack used
host networking and these ports:

| Service | Address |
| --- | --- |
| Forgejo HTTP | `http://localhost:3000` |
| Forgejo SSH | `localhost:2222` |
| Woodpecker HTTP/UI | `http://localhost:8000` |
| Woodpecker gRPC | `localhost:9000` |
| Configuration extension | `http://localhost:8001/config` |
| Redis | `localhost:6379` |

The PoC required `woodpecker-cli` 3.19.x and the `riotbuild-lite:poc`,
`riotbuild-cached:poc`, and `riot/riotbuild:latest` images.

## Runtime state

`poc/.env.poc` and `poc/.token` were git-ignored and are not in the tag. If
they are missing, `poc-up.sh` regenerates `.env.poc`. The script mints the token during
the Forgejo OAuth login. Forgejo data and the PoC cache live in Docker volumes,
not in the repository.

## Tearing down

```sh
cd poc
./scripts/poc-down.sh      # keep data volumes
./scripts/poc-down.sh -v   # remove data volumes as well
```

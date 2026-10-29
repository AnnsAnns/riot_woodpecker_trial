# Local Murdock backend

This directory contains a working local stack for the murdock-ng API server.

## Start

```sh
mkdir -p data
docker compose up -d
```

Open these addresses:

- Swagger UI: <http://localhost:8000/api>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Jobs API: <http://localhost:8000/jobs>

Stop the stack with:

```sh
docker compose down
# add -v to delete the MongoDB volume and all job history
```

## Services

- `murdock`: the published `murdockng/murdock:latest` image. The `murdock/`
  submodule code is mounted into the image.
- `mongo`: MongoDB 7 for job history.

The image is from 2023. It ships Python 3.10 with `fastapi 0.92.0`,
`pydantic 1.10.5`, and `motor 3.1.1`. These versions match the checked-out
Murdock `main` branch. The API starts, connects to MongoDB, serves `/jobs`, and
exposes the OpenAPI schema.

The image runs as UID 1000. If your user ID is different, change the owner of
`data/` or add a `user:` override to the `murdock` service.

The stack was tested with a real script-mode job. The job ran `scripts/run.sh`,
streamed its output, passed, and appeared in `/jobs` and `/results`.

## Legacy backend file

The original `docker-compose` file was the legacy disque/redis/ssh/vector
backend. It was not a complete Murdock stack. It is preserved as
`docker-compose.legacy.yml`.

That legacy file defined only:

- `disque`: the old job queue,
- `disque_exporter`: metrics for the queue,
- `redis`: the old ccache and test cache,
- `ssh`: the worker SSH bridge,
- `vector`: metrics forwarding.

It did not contain the API server, MongoDB, or a UI. It did not start as-is:

- `disque_exporter` built from the missing `./disque-exporter` directory.
- `ssh` mounted missing `./ssh-host-keys` and `./ssh-slave-keys`.
- `vector` mounted a missing `./vector.toml`.
- The published ports used placeholder IPv6 addresses
  (`[2a01:4f9:...::1]` and `[IPIPIPIP::1]`). Docker rejected the second address
  with `invalid IP address: IPIPIPIP::1`.

The active `docker-compose.yml` file replaces that stack for local use. The legacy
file is still useful as a reference for the old dwq/disque worker design.

## Limits

- The local stack uses dummy GitHub values. Manual jobs and webhooks cannot fetch
  commits. Replace the `GITHUB_*` values with a real repository, GitHub
  App/OAuth credentials, and webhook secret to use them.
- In-process script execution is enabled (`MURDOCK_RUN_IN_DOCKER=0`). Set it to
  `1` and mount the Docker socket if you want Murdock to start job containers.
- The web UI is not included. The API's Swagger UI is at `/api`. You can point
  the separate `murfrog/` UI at this server:

  ```sh
  cd ../murfrog
  VITE_MURDOCK_HTTP_BASE_URL=http://localhost:8000 \
  VITE_MURDOCK_WS_URL=ws://localhost:8000/ws/status \
  npm install && npm run dev
  ```

## Update the server code

The image supplies the Python dependencies. The server code comes from the bind
mount. To run a newer Murdock checkout, update the submodule and restart the
container:

```sh
git -C ../murdock pull
docker compose restart murdock
```

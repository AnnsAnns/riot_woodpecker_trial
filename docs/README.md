# Murdock CI documentation

Starlight site for the Murdock server, its features, RIOT integration, and API.

## Development

```sh
npm install
npm run dev
```

## Build

```sh
npm run build
```

The output is written to `dist/`. The build prints a sitemap warning because no
deployment URL is configured. Set `site` in `astro.config.mjs` when you deploy.

## Update the OpenAPI snapshot

The API reference uses `src/assets/openapi.json`. This file is a snapshot of the schema served by a running Murdock instance.

```sh
# With the local stack running on http://localhost:8000:
npm run update-openapi
```

You can also fetch the production schema:

```sh
curl -fsSL https://ci.riot-os.org/openapi.json -o src/assets/openapi.json
```

## Layout

- `src/content/docs/`: guides and hand-written API pages.
- `src/assets/openapi.json`: OpenAPI 3 snapshot used by `starlight-openapi`.
- `astro.config.mjs`: sidebar and plugin configuration.

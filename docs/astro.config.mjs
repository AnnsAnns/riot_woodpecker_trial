// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightOpenAPI, { openAPISidebarGroups } from 'starlight-openapi';

// https://astro.build/config
export default defineConfig({
  integrations: [
    starlight({
      title: 'Murdock CI',
      description:
        'Features, configuration, and API reference for the Murdock continuous integration server.',
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/murdock-ng/murdock',
        },
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Overview', slug: 'index' },
            'getting-started/architecture',
            'getting-started/deployment',
            'getting-started/local-development',
            'getting-started/riot-demo',
          ],
        },
        {
          label: 'Features',
          items: [
            'features/jobs',
            'features/triggers',
            'features/repository-config',
            'features/tasks-and-execution',
            'features/github-integration',
            'features/notifications',
            'features/results-and-artifacts',
            'features/realtime-and-metrics',
            'features/security',
            'features/riot-ci',
            'features/riot-job-aggregation',
            'features/worker-and-ui',
          ],
        },
        {
          label: 'API Reference',
          items: [
            'api/overview',
            'api/jobs',
            'api/job-details',
            'api/manual-jobs',
            'api/websocket',
            'api/webhooks',
            'api/results-and-metrics',
            'api/models',
          ],
        },
        {
          label: 'Reference',
          items: [
            'reference/environment-variables',
            'reference/job-environment',
            'reference/murdock-yml',
          ],
        },
        {
          label: 'Appendix',
          items: ['appendix/woodpecker-poc'],
        },
        ...openAPISidebarGroups,
      ],
      plugins: [
        starlightOpenAPI([
          {
            base: 'api/openapi',
            schema: './src/assets/openapi.json',
            sidebar: {
              label: 'OpenAPI Operations',
              collapsed: true,
              operations: { badges: true },
            },
          },
        ]),
      ],
    }),
  ],
});

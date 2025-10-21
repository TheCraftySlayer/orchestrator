import { configDefaults, defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default defineConfig(async (configEnv) => {
  const resolvedViteConfig = await (typeof viteConfig === 'function'
    ? viteConfig(configEnv)
    : viteConfig);

  return mergeConfig(resolvedViteConfig, {
    test: {
      environment: 'node',
      exclude: [...configDefaults.exclude, 'e2e/**'],
    },
  });
});

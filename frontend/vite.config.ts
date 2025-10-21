import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    define: {
      __CUSTOM_GPT_API_KEY__: JSON.stringify(env.VITE_CUSTOMGPT_API_KEY || ''),
    }
  };
});

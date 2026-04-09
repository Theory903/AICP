import { defineConfig } from 'tsup';

export default defineConfig({
	clean: false,
	dts: false,
	format: ['esm'],
	target: 'esnext',
	platform: 'node',
	bundle: true,
	splitting: true,
	minify: true,
	outDir: 'dist',
	external: ['@aicp/integration-core', 'zod'],
	entry: ['index.ts'],
});

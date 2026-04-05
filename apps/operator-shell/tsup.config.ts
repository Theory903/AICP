import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/boot/cli.tsx"],
  clean: true,
  dts: true,
  format: ["esm"],
  outDir: "dist",
  sourcemap: true,
  banner: {
    js: "#!/usr/bin/env node"
  }
});

// Compila el frontend a dist/ con esbuild (sin servidor de desarrollo).
import * as esbuild from "esbuild";
import { copyFileSync, cpSync, existsSync, mkdirSync } from "node:fs";

const watch = process.argv.includes("--watch");
mkdirSync("dist/assets", { recursive: true });
copyFileSync("index.html", "dist/index.html");
// Iconos de game-icons.net (CC BY 3.0)
if (existsSync("public/icons")) cpSync("public/icons", "dist/assets/icons", { recursive: true });

const options = {
  entryPoints: ["src/main.jsx"],
  bundle: true,
  minify: !watch,
  sourcemap: watch,
  outfile: "dist/assets/app.js",
  loader: { ".jsx": "jsx" },
  jsx: "automatic",
  define: { "process.env.NODE_ENV": watch ? '"development"' : '"production"' },
  logLevel: "info",
};

if (watch) {
  const ctx = await esbuild.context(options);
  await ctx.watch();
} else {
  await esbuild.build(options);
}

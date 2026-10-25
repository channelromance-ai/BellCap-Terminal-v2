import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { allowed } from "./api/data.js";

// `npm run dev` on your PC: no login, and data comes straight from the
// engine's local output (../data/private, written by `python run.py update`).
// Deployed on Vercel, the real api/ routes handle login and data instead.
const LOCAL_DATA = resolve(import.meta.dirname, "../data/private");

function localData() {
  return {
    name: "bellcap-local-data",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url, "http://localhost");
        if (url.pathname === "/api/login" || url.pathname === "/api/logout") {
          res.setHeader("Content-Type", "application/json");
          return res.end('{"ok":true}');
        }
        if (url.pathname === "/api/news") {
          const { collect } = await import("./api/_feeds.js");
          res.setHeader("Content-Type", "application/json");
          return res.end(JSON.stringify(await collect()));
        }
        if (url.pathname !== "/api/data") return next();
        const path = url.searchParams.get("path");
        if (!allowed(path)) {
          res.statusCode = 400;
          return res.end('{"error":"Unknown file"}');
        }
        try {
          res.setHeader("Content-Type", "application/json");
          res.end(await readFile(resolve(LOCAL_DATA, path)));
        } catch {
          res.statusCode = 404;
          res.end('{"error":"Not found - run: python run.py update"}');
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), localData()],
  build: { outDir: "dist", emptyOutDir: true },
});

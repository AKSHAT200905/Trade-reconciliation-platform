import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const tradeTarget = process.env.TRADE_SERVICE_URL || "http://127.0.0.1:8001";
const reconTarget = process.env.RECON_SERVICE_URL || "http://127.0.0.1:8002";

const proxy = {
  "/api/trades": { target: tradeTarget, changeOrigin: true },
  "/api/recon": { target: reconTarget, changeOrigin: true },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
  test: { environment: "node" },
});

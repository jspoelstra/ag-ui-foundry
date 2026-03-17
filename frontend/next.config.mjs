import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load repo-root .env values as fallback only.
// Next.js still loads frontend/.env* files and those values take precedence.
dotenv.config({
	path: path.resolve(__dirname, "../.env"),
	quiet: true,
});

/** @type {import('next').NextConfig} */
const nextConfig = {};

export default nextConfig;

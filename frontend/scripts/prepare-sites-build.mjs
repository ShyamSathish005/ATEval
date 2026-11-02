#!/usr/bin/env node
import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
const index = path.join(dist, "client", "index.html");
const worker = path.join(root, "worker", "index.js");
const hosting = path.join(root, "site-hosting.json");
const fontLicense = path.join(root, "node_modules", "@fontsource", "poppins", "LICENSE");

for (const file of [index, worker, hosting, fontLicense]) {
  if (!existsSync(file)) throw new Error("Missing Sites build input: " + file);
}

mkdirSync(path.join(dist, "server"), { recursive: true });
mkdirSync(path.join(dist, ".openai"), { recursive: true });
copyFileSync(worker, path.join(dist, "server", "index.js"));
copyFileSync(hosting, path.join(dist, ".openai", "hosting.json"));
const licenses = path.join(dist, "client", "third-party-licenses");
const npmLicenses = path.join(licenses, "npm");
mkdirSync(npmLicenses, { recursive: true });
function copyLicenseFiles(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.name === ".bin" || entry.name === ".cache") continue;
    const source = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      copyLicenseFiles(source);
    } else if (entry.isFile() && /^(license|licence|copying|notice)(\..*)?$/i.test(entry.name)) {
      const relative = path.relative(path.join(root, "node_modules"), source);
      const destination = path.join(npmLicenses, relative);
      mkdirSync(path.dirname(destination), { recursive: true });
      copyFileSync(source, destination);
    }
  }
}
copyLicenseFiles(path.join(root, "node_modules"));
copyFileSync(fontLicense, path.join(licenses, "Poppins-OFL-1.1.txt"));

console.log("Prepared Sites build and copied third-party npm license files.");

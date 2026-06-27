import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const sourceDir = join(root, "node_modules", "@mediapipe", "tasks-vision", "wasm");
const targetDir = join(root, "public", "vendor", "mediapipe", "tasks-vision", "wasm");
const modelPath = join(root, "public", "models", "hand_landmarker.task");

if (!existsSync(sourceDir)) {
  throw new Error(`MediaPipe Tasks wasm package not found: ${sourceDir}`);
}

mkdirSync(targetDir, { recursive: true });
mkdirSync(dirname(modelPath), { recursive: true });

for (const file of readdirSync(sourceDir)) {
  const sourcePath = join(sourceDir, file);
  if (statSync(sourcePath).isFile()) {
    copyFileSync(sourcePath, join(targetDir, file));
  }
}

if (!existsSync(modelPath)) {
  console.warn(`hand_landmarker.task missing: ${modelPath}`);
} else {
  console.log(`hand_landmarker.task found: ${modelPath}`);
}

console.log(`MediaPipe Tasks wasm copied to ${targetDir}`);

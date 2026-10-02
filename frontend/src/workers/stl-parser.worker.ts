/// <reference lib="webworker" />

import { STLLoader } from "three/addons/loaders/STLLoader.js";

const MAX_PREVIEW_TRIANGLES = 250_000;
const MAX_ASCII_PREVIEW_BYTES = 32 * 1024 * 1024;

interface ParsedMeshMessage {
  positions: ArrayBuffer;
  normals: ArrayBuffer | null;
  sourceTriangleCount: number;
  displayedTriangleCount: number;
}

function binaryTriangleCount(buffer: ArrayBuffer): number | null {
  if (buffer.byteLength < 84) return null;
  const count = new DataView(buffer).getUint32(80, true);
  return 84 + count * 50 === buffer.byteLength ? count : null;
}

function parseBinaryPreview(buffer: ArrayBuffer, triangleCount: number): ParsedMeshMessage {
  const stride = Math.max(1, Math.ceil(triangleCount / MAX_PREVIEW_TRIANGLES));
  const displayedTriangleCount = Math.ceil(triangleCount / stride);
  const positions = new Float32Array(displayedTriangleCount * 9);
  const normals = new Float32Array(displayedTriangleCount * 9);
  const view = new DataView(buffer);
  let output = 0;

  for (let triangle = 0; triangle < triangleCount; triangle += stride) {
    const offset = 84 + triangle * 50;
    const ax = view.getFloat32(offset + 12, true);
    const ay = view.getFloat32(offset + 16, true);
    const az = view.getFloat32(offset + 20, true);
    const bx = view.getFloat32(offset + 24, true);
    const by = view.getFloat32(offset + 28, true);
    const bz = view.getFloat32(offset + 32, true);
    const cx = view.getFloat32(offset + 36, true);
    const cy = view.getFloat32(offset + 40, true);
    const cz = view.getFloat32(offset + 44, true);
    positions.set([ax, ay, az, bx, by, bz, cx, cy, cz], output);

    const abx = bx - ax;
    const aby = by - ay;
    const abz = bz - az;
    const acx = cx - ax;
    const acy = cy - ay;
    const acz = cz - az;
    let nx = aby * acz - abz * acy;
    let ny = abz * acx - abx * acz;
    let nz = abx * acy - aby * acx;
    const length = Math.hypot(nx, ny, nz) || 1;
    nx /= length;
    ny /= length;
    nz /= length;
    normals.set([nx, ny, nz, nx, ny, nz, nx, ny, nz], output);
    output += 9;
  }

  return {
    positions: positions.buffer,
    normals: normals.buffer,
    sourceTriangleCount: triangleCount,
    displayedTriangleCount,
  };
}

function parseAsciiPreview(buffer: ArrayBuffer): ParsedMeshMessage {
  if (buffer.byteLength > MAX_ASCII_PREVIEW_BYTES) {
    throw new Error("Büyük ASCII STL önizleme için ikili STL biçimine dönüştürülmelidir.");
  }
  const geometry = new STLLoader().parse(buffer);
  const positionAttribute = geometry.getAttribute("position");
  const source = Float32Array.from(positionAttribute.array);
  const triangleCount = Math.floor(source.length / 9);
  const stride = Math.max(1, Math.ceil(triangleCount / MAX_PREVIEW_TRIANGLES));
  const displayedTriangleCount = Math.ceil(triangleCount / stride);
  const positions = new Float32Array(displayedTriangleCount * 9);
  let output = 0;
  for (let triangle = 0; triangle < triangleCount; triangle += stride) {
    positions.set(source.subarray(triangle * 9, triangle * 9 + 9), output);
    output += 9;
  }
  geometry.dispose();
  return {
    positions: positions.buffer,
    normals: null,
    sourceTriangleCount: triangleCount,
    displayedTriangleCount,
  };
}

self.addEventListener("message", (event: MessageEvent<ArrayBuffer>) => {
  try {
    const triangleCount = binaryTriangleCount(event.data);
    const message = triangleCount === null
      ? parseAsciiPreview(event.data)
      : parseBinaryPreview(event.data, triangleCount);
    const transfer: Transferable[] = [message.positions];
    if (message.normals) transfer.push(message.normals);
    self.postMessage(message, { transfer });
  } catch (error) {
    self.postMessage({
      error: error instanceof Error ? error.message : "STL dosyası ayrıştırılamadı.",
    });
  }
});

export {};

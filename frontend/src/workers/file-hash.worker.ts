/// <reference lib="webworker" />

import { createSHA256 } from "hash-wasm";

const HASH_CHUNK_BYTES = 4 * 1024 * 1024;

self.addEventListener("message", async (event: MessageEvent<File>) => {
  try {
    const file = event.data;
    const hasher = await createSHA256();
    hasher.init();
    for (let offset = 0; offset < file.size; offset += HASH_CHUNK_BYTES) {
      const chunk = await file.slice(offset, offset + HASH_CHUNK_BYTES).arrayBuffer();
      hasher.update(new Uint8Array(chunk));
    }
    self.postMessage({ digest: hasher.digest("hex") });
  } catch (error) {
    self.postMessage({
      error: error instanceof Error ? error.message : "Dosya özeti hesaplanamadı.",
    });
  }
});

export {};

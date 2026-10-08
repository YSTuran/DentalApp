import { act, cleanup, render } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useResumableUpload } from "../hooks/useResumableUpload";
import { ApiError } from "../lib/api";

const apiMocks = vi.hoisted(() => ({
  completeUpload: vi.fn(),
  getUpload: vi.fn(),
  sendUploadChunk: vi.fn(),
  startUpload: vi.fn(),
}));

vi.mock("../lib/cases-api", () => apiMocks);

let worker: FakeWorker;

class FakeWorker {
  terminate = vi.fn();
  postMessage = vi.fn();
  messageListener?: (event: MessageEvent<{ digest?: string }>) => void;
  addEventListener = vi.fn((type: string, listener: (event: MessageEvent<{ digest?: string }>) => void) => {
    if (type === "message") this.messageListener = listener;
  });

  emitDigest(digest: string) {
    this.messageListener?.(new MessageEvent("message", { data: { digest } }));
  }
}

interface UploadProbeProps {
  onReady: (upload: ReturnType<typeof useResumableUpload>["upload"]) => void;
}

function UploadProbe({ onReady }: UploadProbeProps) {
  const { upload } = useResumableUpload("user-1");
  useEffect(() => onReady(upload), [onReady, upload]);
  return null;
}

describe("devam ettirilebilir yükleme", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.stubGlobal("Worker", class {
      constructor() {
        worker = new FakeWorker();
        return worker;
      }
    });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("bileşen kapanınca dosya özeti worker'ını sonlandırır", async () => {
    const captureUpload = vi.fn<UploadProbeProps["onReady"]>();
    const view = render(<UploadProbe onReady={captureUpload} />);
    const upload = captureUpload.mock.calls[0][0];
    let pending!: Promise<unknown>;

    act(() => {
      pending = upload("case-1", new File(["solid demo"], "demo.stl"));
    });
    expect(worker.postMessage).toHaveBeenCalledOnce();

    view.unmount();
    await act(async () => {
      await pending;
    });

    expect(worker.terminate).toHaveBeenCalledOnce();
    expect(apiMocks.startUpload).not.toHaveBeenCalled();
  });

  it("geçici devam oturumu hatasında kayıtlı oturumu silip yenisini açmaz", async () => {
    localStorage.setItem(
      "dentalapp:scan-upload:user-1:case-1",
      JSON.stringify({ uploadId: "upload-1", fingerprint: "digest-1" }),
    );
    apiMocks.getUpload.mockRejectedValue(new ApiError(503, "http_503"));
    const captureUpload = vi.fn<UploadProbeProps["onReady"]>();
    render(<UploadProbe onReady={captureUpload} />);
    const upload = captureUpload.mock.calls[0][0];

    let pending!: Promise<unknown>;
    act(() => {
      pending = upload("case-1", new File(["solid demo"], "demo.stl"));
    });
    worker.emitDigest("digest-1");
    await act(async () => {
      await pending;
    });

    expect(apiMocks.startUpload).not.toHaveBeenCalled();
    expect(localStorage.getItem("dentalapp:scan-upload:user-1:case-1")).not.toBeNull();
  });
});

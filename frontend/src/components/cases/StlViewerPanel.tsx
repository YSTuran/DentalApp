import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

import { getCaseFileBuffer } from "../../lib/cases-api";
import { formatBytes } from "../../lib/case-format";
import { ApiError } from "../../lib/api";
import { hasMeshWarnings, meshReportItems } from "../../lib/mesh-report";
import type { CaseFileVersion } from "../../types/case";
import { MeshStatusBadge } from "./CaseStatusBadge";

interface Props {
  caseId: string;
  files: CaseFileVersion[];
}

interface WorkerSuccess {
  positions: ArrayBuffer;
  normals: ArrayBuffer | null;
  sourceTriangleCount: number;
  displayedTriangleCount: number;
}

interface WorkerFailure {
  error: string;
}

const issueLabels: Record<string, string> = {
  mesh_non_finite_vertices: "Geçersiz koordinatlar",
  mesh_degenerate_faces: "Bozuk üçgenler",
  mesh_duplicate_faces: "Tekrarlanan yüzeyler",
  mesh_open_boundary: "Açık yüzey / delik",
  mesh_non_manifold_edges: "Manifold olmayan kenarlar",
  mesh_inconsistent_winding: "Tutarsız yüzey yönleri",
  mesh_not_closed_volume: "Kapalı hacim oluşturmuyor",
  mesh_self_intersections: "Birbiriyle kesişen yüzeyler",
};

function numberFromReport(report: Record<string, unknown> | null, key: string): number | null {
  const value = report?.[key];
  return typeof value === "number" ? value : null;
}

function booleanFromReport(report: Record<string, unknown> | null, key: string): boolean | null {
  const value = report?.[key];
  return typeof value === "boolean" ? value : null;
}

export function StlViewerPanel({ caseId, files }: Props) {
  const newestFile = [...files].sort((left, right) => (
    new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
  ))[0];
  const [selectedId, setSelectedId] = useState(newestFile?.id ?? "");
  const [wireframe, setWireframe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewNotice, setPreviewNotice] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const materialRef = useRef<THREE.MeshStandardMaterial | null>(null);
  const resetViewRef = useRef<(() => void) | null>(null);
  const wireframeRef = useRef(false);
  const selectedFile = files.find((file) => file.id === selectedId) ?? newestFile;
  const selectedFileId = selectedFile?.id;

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || !selectedFileId) return;

    setLoading(true);
    setError(null);
    setPreviewNotice(null);
    const abortController = new AbortController();
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 10000);
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;

    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x35505a, 2.1));
    const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
    keyLight.position.set(4, 6, 5);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0x9fded5, 1.4);
    fillLight.position.set(-4, 2, -3);
    scene.add(fillLight);

    let mesh: THREE.Mesh | null = null;
    let grid: THREE.GridHelper | null = null;
    let worker: Worker | null = null;
    let frame = 0;

    const resize = () => {
      const width = Math.max(container.clientWidth, 1);
      const height = Math.max(container.clientHeight, 1);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();

    const render = () => {
      controls.update();
      renderer.render(scene, camera);
      frame = window.requestAnimationFrame(render);
    };
    render();

    function fitCamera(radius: number) {
      const safeRadius = Math.max(radius, 0.001);
      camera.near = Math.max(safeRadius / 100, 0.001);
      camera.far = safeRadius * 100;
      camera.position.set(safeRadius * 1.6, safeRadius * 1.15, safeRadius * 1.8);
      camera.updateProjectionMatrix();
      controls.target.set(0, 0, 0);
      controls.minDistance = safeRadius * 0.1;
      controls.maxDistance = safeRadius * 12;
      controls.update();
    }

    getCaseFileBuffer(caseId, selectedFileId, abortController.signal)
      .then((buffer) => {
        if (abortController.signal.aborted) return;
        worker = new Worker(new URL("../../workers/stl-parser.worker.ts", import.meta.url), {
          type: "module",
        });
        worker.addEventListener("message", (event: MessageEvent<WorkerSuccess | WorkerFailure>) => {
          if ("error" in event.data) {
            setError(event.data.error || "STL geometrisi tarayıcıda ayrıştırılamadı.");
            setLoading(false);
            return;
          }

          if (event.data.displayedTriangleCount < event.data.sourceTriangleCount) {
            setPreviewNotice(
              `Akıcı görüntüleme için ${event.data.sourceTriangleCount.toLocaleString("tr-TR")} üçgenden ${event.data.displayedTriangleCount.toLocaleString("tr-TR")} tanesi gösteriliyor.`,
            );
          }

          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute(
            "position",
            new THREE.BufferAttribute(new Float32Array(event.data.positions), 3),
          );
          if (event.data.normals) {
            geometry.setAttribute(
              "normal",
              new THREE.BufferAttribute(new Float32Array(event.data.normals), 3),
            );
          } else {
            geometry.computeVertexNormals();
          }
          geometry.computeBoundingBox();
          geometry.center();
          geometry.computeBoundingSphere();

          const primaryColor = getComputedStyle(document.documentElement)
            .getPropertyValue("--primary")
            .trim() || "#087e70";
          const material = new THREE.MeshStandardMaterial({
            color: primaryColor,
            metalness: 0.08,
            roughness: 0.58,
            side: THREE.DoubleSide,
            wireframe: wireframeRef.current,
          });
          materialRef.current = material;
          mesh = new THREE.Mesh(geometry, material);
          scene.add(mesh);

          const radius = geometry.boundingSphere?.radius ?? 1;
          grid = new THREE.GridHelper(radius * 4, 12, 0x8aa6a1, 0xc9d7d4);
          grid.position.y = -(geometry.boundingBox?.max.y ?? 0) - radius * 0.08;
          const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material];
          gridMaterials.forEach((gridMaterial) => {
            gridMaterial.transparent = true;
            gridMaterial.opacity = 0.35;
          });
          scene.add(grid);
          fitCamera(radius);
          resetViewRef.current = () => fitCamera(radius);
          setLoading(false);
          worker?.terminate();
          worker = null;
        });
        worker.postMessage(buffer, [buffer]);
      })
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError(
          caught instanceof ApiError && caught.detail === "large_ascii_stl_preview_unavailable"
            ? "Bu büyük ASCII STL tarayıcı önizlemesine uygun değil. Dosyayı ikili STL biçimine dönüştürün."
            : "STL dosyası görüntülemek için alınamadı.",
        );
        setLoading(false);
      });

    const themeObserver = new MutationObserver(() => {
      const color = getComputedStyle(document.documentElement).getPropertyValue("--primary").trim();
      if (color && materialRef.current) materialRef.current.color.set(color);
    });
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-mode", "data-palette"],
    });

    return () => {
      abortController.abort();
      worker?.terminate();
      resizeObserver.disconnect();
      themeObserver.disconnect();
      window.cancelAnimationFrame(frame);
      controls.dispose();
      if (mesh) {
        mesh.geometry.dispose();
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        materials.forEach((material) => material.dispose());
      }
      if (grid) {
        grid.geometry.dispose();
        const materials = Array.isArray(grid.material) ? grid.material : [grid.material];
        materials.forEach((material) => material.dispose());
      }
      materialRef.current = null;
      resetViewRef.current = null;
      renderer.dispose();
    };
  }, [caseId, selectedFileId]);

  function toggleWireframe() {
    setWireframe((current) => {
      const next = !current;
      wireframeRef.current = next;
      if (materialRef.current) {
        materialRef.current.wireframe = next;
        materialRef.current.needsUpdate = true;
      }
      return next;
    });
  }

  if (!selectedFile) {
    return (
      <section className="case-panel">
        <p className="card-label">3D ÖNİZLEME</p>
        <h2>Görüntülenecek STL bulunmuyor</h2>
        <p className="panel-description">Bir tarama sürümü yüklendiğinde model burada açılacaktır.</p>
      </section>
    );
  }

  const report = selectedFile.mesh_report;
  const issues = meshReportItems(report, "issues");
  const reviewWarning = hasMeshWarnings(report);
  const vertexCount = numberFromReport(report, "vertex_count");
  const faceCount = numberFromReport(report, "face_count");
  const watertight = booleanFromReport(report, "is_watertight");

  return (
    <section className="case-panel stl-viewer-panel">
      <div className="panel-heading viewer-heading">
        <div><p className="card-label">3D ÖNİZLEME</p><h2>STL inceleyici</h2></div>
        <MeshStatusBadge status={selectedFile.mesh_status} hasWarnings={reviewWarning} />
      </div>
      <div className="viewer-toolbar">
        <label>Sürüm
          <select value={selectedFile.id} onChange={(event) => setSelectedId(event.target.value)}>
            {[...files].reverse().map((file) => (
              <option value={file.id} key={file.id}>
                {file.kind === "scan" ? "Tarama" : "Tasarım"} v{file.version_number} · {formatBytes(file.size_bytes)}
              </option>
            ))}
          </select>
        </label>
        <div>
          <button className={`viewer-tool${wireframe ? " active" : ""}`} type="button" onClick={toggleWireframe}>Tel kafes</button>
          <button className="viewer-tool" type="button" onClick={() => resetViewRef.current?.()}>Görünümü sıfırla</button>
        </div>
      </div>
      <div className="stl-canvas-wrap" ref={containerRef}>
        <canvas ref={canvasRef} aria-label="Etkileşimli STL modeli" />
        {loading && <div className="viewer-state"><span className="viewer-spinner" />Model hazırlanıyor…</div>}
        {error && <div className="viewer-state viewer-error" role="alert">{error}</div>}
        {!loading && !error && <div className="viewer-help">Döndür: sol tuş · Kaydır: sağ tuş · Yakınlaştır: tekerlek</div>}
      </div>
      <div className="mesh-summary">
        <span><strong>{vertexCount?.toLocaleString("tr-TR") ?? "—"}</strong>Köşe</span>
        <span><strong>{faceCount?.toLocaleString("tr-TR") ?? "—"}</strong>Yüzey</span>
        <span><strong>{watertight === null ? "—" : watertight ? "Evet" : "Hayır"}</strong>Kapalı mesh</span>
      </div>
      {previewNotice && <p className="viewer-preview-notice">{previewNotice}</p>}
      {issues.length > 0 && (
        <div className="mesh-issues"><strong>{reviewWarning ? "Yönetici inceleme uyarıları" : "Tespit edilen sorunlar"}</strong>{reviewWarning && <p>Tarama görüntülenebilir; yönetici hekim bu uyarıları onay sırasında değerlendirmelidir.</p>}<ul>{issues.map((issue) => <li key={issue}>{issueLabels[issue] ?? issue}</li>)}</ul></div>
      )}
    </section>
  );
}

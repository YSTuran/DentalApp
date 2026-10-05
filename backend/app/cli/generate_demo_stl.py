from pathlib import Path

import numpy as np
import trimesh

from app.core.config import BACKEND_DIR
from app.services.mesh_validation import inspect_stl

OUTPUT_PATH = BACKEND_DIR.parent / "demo-assets" / "synthetic-dental-arch-watertight.stl"


def _surface_height(angle: float, radius: float) -> float:
    height = 5.0
    radial_profile = np.exp(-((radius - 26.0) / 5.2) ** 4)
    for center in np.linspace(-1.82, 1.82, 14):
        height += 4.2 * np.exp(-((angle - center) / 0.105) ** 4) * radial_profile
    return float(height)


def build_dental_arch() -> trimesh.Trimesh:
    angles = np.linspace(-2.18, 2.18, 97)
    radii = np.linspace(18.0, 34.0, 13)
    columns = len(radii)
    layer_size = len(angles) * columns

    top = [
        [radius * np.cos(angle), radius * np.sin(angle), _surface_height(angle, radius)]
        for angle in angles
        for radius in radii
    ]
    bottom = [
        [radius * np.cos(angle), radius * np.sin(angle), 0.0]
        for angle in angles
        for radius in radii
    ]
    vertices = np.asarray(top + bottom, dtype=np.float64)
    faces: list[list[int]] = []

    def vertex(layer: int, angle_index: int, radius_index: int) -> int:
        return layer * layer_size + angle_index * columns + radius_index

    def quad(a: int, b: int, c: int, d: int) -> None:
        faces.extend(([a, b, c], [a, c, d]))

    for angle_index in range(len(angles) - 1):
        for radius_index in range(len(radii) - 1):
            top_a = vertex(0, angle_index, radius_index)
            top_b = vertex(0, angle_index, radius_index + 1)
            top_c = vertex(0, angle_index + 1, radius_index + 1)
            top_d = vertex(0, angle_index + 1, radius_index)
            quad(top_a, top_b, top_c, top_d)

            bottom_a = vertex(1, angle_index, radius_index)
            bottom_b = vertex(1, angle_index + 1, radius_index)
            bottom_c = vertex(1, angle_index + 1, radius_index + 1)
            bottom_d = vertex(1, angle_index, radius_index + 1)
            quad(bottom_a, bottom_b, bottom_c, bottom_d)

        for radius_index in (0, len(radii) - 1):
            wall = (
                vertex(0, angle_index, radius_index),
                vertex(0, angle_index + 1, radius_index),
                vertex(1, angle_index + 1, radius_index),
                vertex(1, angle_index, radius_index),
            )
            quad(*wall if radius_index == 0 else reversed(wall))

    for angle_index in (0, len(angles) - 1):
        for radius_index in range(len(radii) - 1):
            end = (
                vertex(0, angle_index, radius_index),
                vertex(1, angle_index, radius_index),
                vertex(1, angle_index, radius_index + 1),
                vertex(0, angle_index, radius_index + 1),
            )
            quad(*end if angle_index == 0 else reversed(end))

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)
    if mesh.volume < 0:
        mesh.invert()
    return mesh


def main(output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    build_dental_arch().export(output_path, file_type="stl")
    result = inspect_stl(output_path)
    if result.report["issues"]:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(f"Üretilen demo STL geçersiz: {result.report['issues']}")
    print(f"Demo STL oluşturuldu: {output_path}")


if __name__ == "__main__":
    main()

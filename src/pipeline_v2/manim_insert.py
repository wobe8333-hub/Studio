"""Manim 인서트 엔진 — CH1(경제) / CH2(과학) 전용 차트·수식 장면 (최적화 ②)

두들 배경 위에 Manim 렌더 결과를 투명 레이어로 오버레이.
타채널(CH3~7) 호출 시 즉시 skip.
"""
from __future__ import annotations

import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

MANIM_CHANNELS = {"CH1", "CH2"}
MANIM_OUTPUT_ROOT = Path("runs/pipeline_v2")

if TYPE_CHECKING:
    from src.pipeline_v2.episode_schema import EpisodeMeta


# ── CH1 경제 차트 템플릿 5종 ──────────────────────────────────

CH1_CHART_TEMPLATES = {
    "line": textwrap.dedent("""
        from manim import *
        class LineChart(Scene):
            def construct(self):
                axes = Axes(x_range=[0, 10], y_range=[0, 10])
                graph = axes.plot(lambda x: x**0.8 + 1, color=GOLD)
                self.play(Create(axes), Create(graph))
                self.wait(2)
    """),
    "bar": textwrap.dedent("""
        from manim import *
        class BarChart(Scene):
            def construct(self):
                chart = BarChart(values=[3, 5, 2, 8, 6], bar_names=["A","B","C","D","E"], bar_colors=[GOLD])
                self.play(Create(chart))
                self.wait(2)
    """),
    "pie": textwrap.dedent("""
        from manim import *
        class PieChart(Scene):
            def construct(self):
                sectors = AnnularSector(inner_radius=1, outer_radius=2, angle=PI, color=GOLD)
                self.play(Create(sectors))
                self.wait(2)
    """),
}

# ── CH2 과학 수식/다이어그램 템플릿 ──────────────────────────

CH2_FORMULA_TEMPLATES = {
    "formula": textwrap.dedent("""
        from manim import *
        class Formula(Scene):
            def construct(self):
                eq = MathTex(r"E = mc^2", font_size=72)
                self.play(Write(eq))
                self.wait(2)
    """),
    "diagram": textwrap.dedent("""
        from manim import *
        class AtomDiagram(Scene):
            def construct(self):
                nucleus = Circle(radius=0.5, color=RED).set_fill(RED, 0.8)
                orbit = Circle(radius=1.5, color=BLUE)
                electron = Dot(color=BLUE).move_to(orbit.point_at_angle(0))
                self.play(Create(nucleus), Create(orbit), Create(electron))
                self.play(MoveAlongPath(electron, orbit), run_time=3, rate_func=linear)
    """),
}


def _get_template(channel_id: str, insert_type: str, scene_data: dict) -> str:
    if channel_id == "CH1":
        chart_type = scene_data.get("chart_type", "line")
        return CH1_CHART_TEMPLATES.get(chart_type, CH1_CHART_TEMPLATES["line"])
    elif channel_id == "CH2":
        formula_type = "formula" if insert_type == "formula" else "diagram"
        return CH2_FORMULA_TEMPLATES.get(formula_type, CH2_FORMULA_TEMPLATES["formula"])
    return ""


def _render_manim_scene(template_code: str, output_dir: Path, scene_id: int) -> Path | None:
    """Manim 코드를 임시 파일로 저장 후 CLI 렌더."""
    out_path = output_dir / f"manim_insert_{scene_id:03d}.mp4"

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(template_code)
        script_path = f.name

    class_name = "LineChart"
    for line in template_code.splitlines():
        if "class " in line and "(Scene)" in line:
            class_name = line.split("class ")[1].split("(")[0].strip()
            break

    cmd = [
        "manim", "render",
        "--quality", "l",
        "--output_file", str(out_path),
        script_path, class_name,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.warning(f"Manim 렌더 실패 (scene_{scene_id}): {result.stderr[-200:]}")
        return None
    return out_path


def _overlay_on_doodle(doodle_img: str, manim_video: Path, output_path: Path) -> Path:
    """두들 배경 이미지 + Manim 동영상 오버레이 합성 (multiply 블렌드)."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", doodle_img,
        "-i", str(manim_video),
        "-filter_complex",
        "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:shortest=1[out]",
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-t", "8",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"오버레이 합성 실패: {result.stderr[-200:]}")
        return Path(doodle_img)
    return output_path


def inject_manim_scenes(
    doodle_images: list[str],
    manim_scenes: list[dict],
    storyboard: list[dict],
    meta: "EpisodeMeta",
    out_dir: Path,
) -> list[str]:
    """Manim 인서트 씬을 두들 이미지 목록 안에 끼워넣기.

    타채널은 즉시 원본 반환.
    """
    channel_id = meta.channel_id
    if channel_id not in MANIM_CHANNELS:
        return doodle_images

    if not manim_scenes:
        return doodle_images

    manim_out_dir = out_dir / "manim"
    manim_out_dir.mkdir(parents=True, exist_ok=True)

    result_images = list(doodle_images)
    inserted = 0

    for idx, scene in enumerate(manim_scenes):
        scene_id = scene.get("scene_id", idx)
        insert_type = scene.get("insert_type", "chart")
        template = _get_template(channel_id, insert_type, scene)

        if not template:
            continue

        logger.info(f"Manim 인서트 렌더: {channel_id}/scene_{scene_id} ({insert_type})")
        manim_vid = _render_manim_scene(template, manim_out_dir, scene_id)

        if manim_vid and manim_vid.exists():
            doodle_bg = doodle_images[min(scene_id, len(doodle_images) - 1)] if doodle_images else ""
            overlay_path = manim_out_dir / f"overlay_{scene_id:03d}.mp4"
            if doodle_bg:
                _overlay_on_doodle(doodle_bg, manim_vid, overlay_path)
                insert_pos = min(scene_id, len(result_images))
                result_images.insert(insert_pos, str(overlay_path))
                inserted += 1
        else:
            logger.warning(f"Manim 렌더 결과 없음, scene_{scene_id} 스킵")

    logger.info(f"Manim 인서트 완료: {inserted}개 삽입 ({channel_id})")
    return result_images

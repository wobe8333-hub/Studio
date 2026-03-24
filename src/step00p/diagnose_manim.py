"""
STEP 00-P 오류 정밀 진단 스크립트
실패한 scene_type 1개씩 실행하여 stderr 전문을 출력한다.
"""
import subprocess
import tempfile
import sys
from pathlib import Path

KAS_ROOT = Path(r"C:\Users\조찬우\Desktop\AI_Animation_Stuidio")

MANIM_TEMPLATES = {
    "number_plane": '''
from manim import *
class PilotScene(Scene):
    def construct(self):
        ax = Axes(x_range=[-3,3,1], y_range=[-2,2,1],
                  axis_config={"include_numbers": True})
        self.play(Create(ax))
        self.wait(0.5)
''',
    "bar_chart": '''
from manim import *
class PilotScene(Scene):
    def construct(self):
        chart = BarChart(
            values=[3.2, 1.8, 4.5],
            bar_names=["A","B","C"],
            y_range=[0, 5, 1],
        )
        self.play(Create(chart))
        self.wait(0.5)
''',
    "timeline": '''
from manim import *
class PilotScene(Scene):
    def construct(self):
        line = NumberLine(x_range=[2020,2025,1],
                         length=8, include_numbers=True)
        self.play(Create(line))
        self.wait(0.5)
''',
    "comparison_no_latex": '''
from manim import *
class PilotScene(Scene):
    def construct(self):
        left  = RoundedRectangle(width=3, height=2, color=BLUE).shift(LEFT*2)
        right = RoundedRectangle(width=3, height=2, color=RED).shift(RIGHT*2)
        self.play(Create(left), Create(right))
        self.wait(0.5)
''',
}


def run_test(name: str, code: str) -> None:
    print(f"\n{'='*60}")
    print(f"[TEST] {name}")
    print(f"{'='*60}")
    with tempfile.TemporaryDirectory() as tmpdir:
        scene_file = Path(tmpdir) / "test_scene.py"
        scene_file.write_text(code, encoding="utf-8")
        python_exe = str(Path(sys.executable).resolve())
        proc = subprocess.run(
            [python_exe, "-m", "manim",
             str(scene_file), "PilotScene",
             "-ql", "--disable_caching",
             "--media_dir", tmpdir],
            capture_output=True, text=True,
            timeout=90,
            cwd=str(KAS_ROOT),
        )
        print(f"returncode: {proc.returncode}")
        if proc.returncode == 0:
            print("RESULT: SUCCESS")
        else:
            print("RESULT: FAIL")
            print("\n--- STDOUT (전문) ---")
            print(proc.stdout if proc.stdout else "(없음)")
            print("\n--- STDERR (전문) ---")
            print(proc.stderr if proc.stderr else "(없음)")


if __name__ == "__main__":
    # pdflatex 존재 여부 먼저 확인
    import shutil

    print("=== 사전 진단 ===")
    for tool in ["pdflatex", "latex", "xelatex", "lualatex"]:
        found = shutil.which(tool)
        print(f"  {tool}: {'OK - ' + found if found else 'MISSING'}")
    print(f"  python: {sys.executable}")
    print("  manim: ", end="")
    import manim

    print(manim.__version__)

    print("\n=== scene_type 별 렌더링 테스트 ===")
    for name, code in MANIM_TEMPLATES.items():
        try:
            run_test(name, code)
        except Exception as e:
            print(f"[TEST EXCEPTION] {name}: {e}")

    print("\n=== 진단 완료 ===")


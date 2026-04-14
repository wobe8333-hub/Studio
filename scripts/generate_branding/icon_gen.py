# scripts/generate_branding/icon_gen.py
"""도메인별 두들 아이콘 SVG 생성 — Manim SVGMobject 완벽 호환"""
import sys
import io
import math

from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from svg_helpers import svg_open, svg_close, doodle_path, doodle_circle, doodle_line, doodle_rect, doodle_crown, doodle_star

W = H = 100
C = 50  # 중심


def icon_svg(body, color):
    return svg_open(W, H) + body + svg_close()


# ─── CH1 경제 아이콘 ───
ICONS_CH1 = {
    "money": lambda c: (doodle_rect(15, 30, 70, 45, c, sw=4)
                        + doodle_circle(C, C + 5, 14, c, sw=3)
                        + doodle_line(20, 30, 20, 75, c, sw=2)
                        + doodle_line(80, 30, 80, 75, c, sw=2)),
    "coin": lambda c: (doodle_circle(C, C, 32, c, sw=4)
                       + doodle_circle(C, C, 22, c, sw=2)
                       + doodle_path(f"M {C-6},38 L {C},35 L {C+6},38", c, sw=3)),
    "stock_up": lambda c: (doodle_path(f"M 10,75 L 30,55 L 50,65 L 75,30 L 90,20", c, sw=4)
                           + doodle_path(f"M 75,20 L 90,20 L 90,35", c, sw=3)),
    "stock_down": lambda c: (doodle_path(f"M 10,25 L 30,45 L 50,35 L 75,70 L 90,80", c, sw=4)
                             + doodle_path(f"M 75,80 L 90,80 L 90,65", c, sw=3)),
    "bank": lambda c: (doodle_path(f"M 10,75 L 90,75", c, sw=4)
                       + doodle_path(f"M 10,45 L 90,45", c, sw=3)
                       + doodle_path(f"M {C},15 L 10,45 L 90,45 Z", c, sw=4)
                       + doodle_line(25, 45, 25, 75, c, sw=3)
                       + doodle_line(50, 45, 50, 75, c, sw=3)
                       + doodle_line(75, 45, 75, 75, c, sw=3)),
    "interest": lambda c: (doodle_circle(30, 38, 14, c, sw=4)
                           + doodle_circle(70, 62, 14, c, sw=4)
                           + doodle_path(f"M 15,75 L 85,25", c, sw=3)),
    "exchange": lambda c: (doodle_path(f"M 15,38 L 75,38 L 60,25", c, sw=4)
                           + doodle_path(f"M 85,62 L 25,62 L 40,75", c, sw=4)),
    "piggy": lambda c: (doodle_circle(45, C, 28, c, sw=4)
                        + doodle_circle(72, 40, 12, c, sw=3)
                        + doodle_circle(45, 32, 5, c, sw=2)
                        + doodle_path(f"M 30,75 L 25,88 M 45,78 L 45,92 M 60,75 L 65,88", c, sw=3)
                        + doodle_line(68, C, 80, C, c, sw=3)),
    "card": lambda c: (doodle_rect(10, 28, 80, 45, c, sw=4, rx=6)
                       + doodle_line(10, 42, 90, 42, c, sw=4)
                       + doodle_rect(18, 52, 25, 12, c, sw=2, rx=2)),
    "wallet": lambda c: (doodle_rect(8, 30, 72, 45, c, sw=4, rx=6)
                         + doodle_rect(65, 38, 22, 28, c, sw=3, rx=12)
                         + doodle_circle(76, C + 2, 7, c, sw=2)),
    "calculator": lambda c: (doodle_rect(20, 15, 60, 70, c, sw=4, rx=4)
                             + doodle_rect(28, 23, 44, 18, c, sw=2, rx=2)
                             + "".join(doodle_circle(30 + i * 15, 52, 5, c, sw=2) for i in range(4))
                             + "".join(doodle_circle(30 + i * 15, 67, 5, c, sw=2) for i in range(4))),
    "graph_up": lambda c: (doodle_path(f"M 10,85 L 10,15", c, sw=3)
                           + doodle_path(f"M 10,85 L 92,85", c, sw=3)
                           + doodle_path(f"M 20,70 L 40,50 L 60,60 L 82,25", c, sw=4)
                           + doodle_rect(18, 62, 14, 23, c, sw=2)
                           + doodle_rect(38, 42, 14, 43, c, sw=2)
                           + doodle_rect(58, 52, 14, 33, c, sw=2)
                           + doodle_rect(78, 17, 14, 68, c, sw=2)),
    "graph_down": lambda c: (doodle_path(f"M 10,85 L 10,15", c, sw=3)
                             + doodle_path(f"M 10,85 L 92,85", c, sw=3)
                             + doodle_rect(18, 30, 14, 55, c, sw=2)
                             + doodle_rect(38, 45, 14, 40, c, sw=2)
                             + doodle_rect(58, 55, 14, 30, c, sw=2)
                             + doodle_rect(78, 65, 14, 20, c, sw=2)),
    "dollar": lambda c: (doodle_circle(C, C, 36, c, sw=4)
                         + doodle_path(f"M {C},20 L {C},80", c, sw=3)
                         + doodle_path(f"M {C-14},35 Q {C-18},28 {C},{C-10} Q {C+18},28 {C+14},35 Q {C+18},{C} {C},{C+3} Q {C-18},58 {C-14},65 Q {C-18},72 {C},{C+12}", c, sw=3)),
    "won": lambda c: (doodle_circle(C, C, 36, c, sw=4)
                      + doodle_path(f"M 30,30 L 42,65 L {C},55 L 58,65 L 70,30", c, sw=3)
                      + doodle_line(28, 48, 72, 48, c, sw=2)
                      + doodle_line(28, 58, 72, 58, c, sw=2)),
    "tax": lambda c: (doodle_rect(20, 10, 60, 80, c, sw=4, rx=4)
                      + doodle_line(30, 28, 70, 28, c, sw=3)
                      + doodle_line(30, 40, 70, 40, c, sw=3)
                      + doodle_line(30, 52, 55, 52, c, sw=3)
                      + doodle_circle(68, 62, 10, c, sw=3)
                      + doodle_path(f"M 64,58 L 72,66 M 72,58 L 64,66", c, sw=2)),
    "inflation": lambda c: (doodle_circle(C, 38, 26, c, sw=4)
                            + doodle_path(f"M {C-4},64 L {C-8},85 M {C+4},64 L {C+8},85", c, sw=3)),
    "recession": lambda c: (doodle_path(f"M 10,40 Q 30,20 50,30 Q 70,40 90,30", c, sw=4)
                            + "".join(doodle_line(20 + i * 15, 45, 20 + i * 15, 75, c, sw=3) for i in range(5))),
    "growth": lambda c: (doodle_path(f"M 10,85 Q 30,60 50,55 Q 70,50 90,20", c, sw=4)
                         + doodle_path(f"M 80,20 L 90,20 L 90,30", c, sw=3)
                         + doodle_circle(C, 70, 10, c, sw=3, fill=c)),
    "bond": lambda c: (doodle_rect(15, 15, 70, 70, c, sw=4, rx=4)
                       + doodle_circle(C, C, 18, c, sw=3)
                       + doodle_path(f"M {C-8},{C-4} L {C},{C+8} L {C+12},{C-10}", c, sw=4)),
}

# ─── CH2 과학 아이콘 ───
ICONS_CH2 = {
    "flask": lambda c: (doodle_path(f"M 38,15 L 38,45 L 15,80 Q 12,88 20,90 L 80,90 Q 88,88 85,80 L 62,45 L 62,15 Z", c, sw=4)
                        + doodle_line(32, 15, 68, 15, c, sw=4)
                        + doodle_circle(42, 72, 6, c, sw=2, fill=c)
                        + doodle_circle(58, 62, 4, c, sw=2, fill=c)),
    "microscope": lambda c: (doodle_line(C, 20, C, 65, c, sw=5)
                             + doodle_rect(35, 62, 30, 15, c, sw=4)
                             + doodle_line(20, 77, 80, 77, c, sw=4)
                             + doodle_circle(C, 20, 10, c, sw=3)
                             + doodle_line(38, 40, 62, 40, c, sw=3)),
    "atom": lambda c: (doodle_circle(C, C, 8, c, sw=3, fill=c)
                       + doodle_path(f"M {C-35},{C} Q {C},{C-25} {C+35},{C}", c, sw=3)
                       + doodle_path(f"M {C-35},{C} Q {C},{C+25} {C+35},{C}", c, sw=3)
                       + doodle_path(f"M {C},{C-35} Q {C+25},{C} {C},{C+35}", c, sw=3)
                       + doodle_path(f"M {C},{C-35} Q {C-25},{C} {C},{C+35}", c, sw=3)),
    "dna": lambda c: (doodle_path(f"M 30,10 Q 60,25 30,40 Q 60,55 30,70 Q 60,85 30,90", c, sw=3)
                      + doodle_path(f"M 70,10 Q 40,25 70,40 Q 40,55 70,70 Q 40,85 70,90", c, sw=3)
                      + doodle_line(38, 26, 62, 26, c, sw=2)
                      + doodle_line(38, 52, 62, 52, c, sw=2)
                      + doodle_line(38, 76, 62, 76, c, sw=2)),
    "telescope": lambda c: (doodle_path(f"M 20,75 L 75,35", c, sw=5)
                            + doodle_path(f"M 65,28 L 82,20 L 85,30 L 68,38 Z", c, sw=3)
                            + doodle_circle(25, 78, 6, c, sw=3)
                            + doodle_line(25, 84, C, 84, c, sw=3)),
    "rocket": lambda c: (doodle_path(f"M {C},15 Q {C+20},25 {C+20},55 L {C+10},65 L {C-10},65 Q {C-20},55 {C-20},55 Q {C-20},25 {C},15 Z", c, sw=4)
                         + doodle_circle(C, 42, 10, c, sw=3)
                         + doodle_path(f"M {C-20},55 L {C-30},75 L {C-10},65", c, sw=3)
                         + doodle_path(f"M {C+20},55 L {C+30},75 L {C+10},65", c, sw=3)),
    "lightbulb": lambda c: (doodle_circle(C, 38, 24, c, sw=4)
                            + doodle_path(f"M {C-12},60 Q {C-14},70 {C-10},75 L {C+10},75 Q {C+14},70 {C+12},60", c, sw=3)
                            + doodle_line(C - 8, 78, C + 8, 78, c, sw=3)
                            + doodle_line(C - 6, 83, C + 6, 83, c, sw=3)
                            + doodle_line(C, 10, C, 18, c, sw=2)
                            + doodle_line(20, 20, 26, 26, c, sw=2)
                            + doodle_line(80, 20, 74, 26, c, sw=2)),
    "magnet": lambda c: (doodle_path(f"M 20,70 L 20,40 Q 20,15 {C},15 Q 80,15 80,40 L 80,70", c, sw=5)
                         + doodle_line(12, 70, 28, 70, c, sw=5)
                         + doodle_line(72, 70, 88, 70, c, sw=5)),
    "circuit": lambda c: (doodle_line(10, C, 90, C, c, sw=3)
                          + doodle_rect(38, 38, 24, 24, c, sw=3, rx=2)
                          + doodle_line(C, 10, C, 38, c, sw=2)
                          + doodle_line(C, 62, C, 90, c, sw=2)
                          + doodle_circle(15, C, 5, c, sw=2, fill=c)
                          + doodle_circle(85, C, 5, c, sw=2, fill=c)),
    "graph": lambda c: (doodle_path(f"M 10,85 L 10,15", c, sw=3)
                        + doodle_path(f"M 10,85 L 90,85", c, sw=3)
                        + doodle_path(f"M 20,65 Q 35,45 50,50 Q 65,55 80,25", c, sw=4)),
    "beaker": lambda c: (doodle_path(f"M 35,15 L 35,55 L 15,85 L 85,85 L 65,55 L 65,15 Z", c, sw=4)
                         + doodle_line(28, 15, 72, 15, c, sw=3)
                         + doodle_line(18, 72, 65, 72, c, sw=2)),
    "planet": lambda c: (doodle_circle(C, C, 28, c, sw=4)
                         + doodle_path(f"M 8,{C} Q {C},28 92,{C} Q {C},72 8,{C}", c, sw=3)
                         + doodle_line(12, 38, 88, 38, c, sw=2)),
    "formula": lambda c: (doodle_path(f"M 15,{C} L 30,30 L 45,{C} L 60,30 L 75,{C} L 90,30", c, sw=4)
                          + doodle_path(f"M 20,{C+20} L 80,{C+20}", c, sw=2)),
    "lab_coat": lambda c: (doodle_path(f"M 30,15 L 15,35 L 15,85 L 85,85 L 85,35 L 70,15", c, sw=4)
                           + doodle_path(f"M 30,15 L 38,30 L {C},22 L 62,30 L 70,15", c, sw=3)
                           + doodle_circle(45, 55, 5, c, sw=2, fill=c)
                           + doodle_circle(45, 68, 5, c, sw=2, fill=c)),
    "notebook": lambda c: (doodle_rect(20, 10, 60, 80, c, sw=4, rx=4)
                           + doodle_line(35, 10, 35, 90, c, sw=3)
                           + doodle_line(42, 28, 72, 28, c, sw=2)
                           + doodle_line(42, 40, 72, 40, c, sw=2)
                           + doodle_line(42, 52, 72, 52, c, sw=2)
                           + doodle_line(42, 64, 65, 64, c, sw=2)),
    "fire": lambda c: doodle_path(f"M {C},85 Q 20,70 25,50 Q 20,60 30,55 Q 25,35 {C},20 Q 55,35 65,55 Q 75,60 75,50 Q 80,70 {C},85 Z", c, sw=4),
    "water": lambda c: doodle_path(f"M {C},20 Q 70,50 {C},80 Q 30,50 {C},20 Z", c, sw=4),
    "wind": lambda c: (doodle_path(f"M 10,38 Q 40,28 60,38 Q 75,45 72,55 Q 65,68 48,60 L 10,60", c, sw=4)
                       + doodle_path(f"M 10,{C} Q 55,{C-15} 70,{C}", c, sw=3)),
    "electricity": lambda c: doodle_path(f"M 55,15 L 35,{C} L 55,{C} L 35,85", c, sw=5),
    "virus": lambda c: (doodle_circle(C, C, 22, c, sw=4)
                        + "".join(
                            doodle_line(
                                int(C + 22 * math.cos(math.pi * i / 4)),
                                int(C + 22 * math.sin(math.pi * i / 4)),
                                int(C + 36 * math.cos(math.pi * i / 4)),
                                int(C + 36 * math.sin(math.pi * i / 4)),
                                c, sw=3
                            ) + doodle_circle(
                                int(C + 38 * math.cos(math.pi * i / 4)),
                                int(C + 38 * math.sin(math.pi * i / 4)),
                                4, c, sw=2, fill=c
                            ) for i in range(8)
                        )),
}

# ─── CH3 부동산 아이콘 ───
ICONS_CH3 = {
    "house": lambda c: (doodle_path(f"M {C},15 L 85,50 L 85,85 L 15,85 L 15,50 Z", c, sw=4)
                        + doodle_path(f"M 5,52 L {C},12 L 95,52", c, sw=4)
                        + doodle_rect(38, 58, 24, 27, c, sw=3, rx=2)),
    "apartment": lambda c: (doodle_rect(15, 25, 70, 60, c, sw=4)
                            + "".join(doodle_rect(22 + i * 18, 33, 12, 12, c, sw=2) for i in range(3))
                            + "".join(doodle_rect(22 + i * 18, 52, 12, 12, c, sw=2) for i in range(3))
                            + doodle_line(15, 85, 85, 85, c, sw=4)),
    "building": lambda c: (doodle_rect(20, 15, 60, 70, c, sw=4)
                           + "".join(doodle_rect(25 + i * 14, 22, 10, 10, c, sw=2) for i in range(3))
                           + "".join(doodle_rect(25 + i * 14, 38, 10, 10, c, sw=2) for i in range(3))
                           + "".join(doodle_rect(25 + i * 14, 54, 10, 10, c, sw=2) for i in range(3))
                           + doodle_rect(38, 68, 24, 17, c, sw=2, rx=2)),
    "key": lambda c: (doodle_circle(32, 38, 18, c, sw=4)
                      + doodle_circle(32, 38, 9, c, sw=2)
                      + doodle_line(48, 38, 88, 38, c, sw=4)
                      + doodle_line(75, 38, 75, 52, c, sw=4)
                      + doodle_line(85, 38, 85, 48, c, sw=4)),
    "contract": lambda c: (doodle_rect(15, 10, 70, 80, c, sw=4, rx=3)
                           + doodle_line(25, 28, 75, 28, c, sw=3)
                           + doodle_line(25, 40, 75, 40, c, sw=3)
                           + doodle_line(25, 52, 55, 52, c, sw=3)
                           + doodle_path(f"M 55,62 L 80,75 L 70,85 L 45,72 Z", c, sw=3)),
    "loan": lambda c: (doodle_circle(C, C, 30, c, sw=4)
                       + doodle_path(f"M {C-8},38 L {C},35 L {C+8},38 L {C+8},62 L {C-8},62 Z", c, sw=3)
                       + doodle_line(C - 14, C, C + 14, C, c, sw=3)),
    "interest": lambda c: (doodle_circle(30, 35, 14, c, sw=4)
                           + doodle_circle(70, 65, 14, c, sw=4)
                           + doodle_line(15, 75, 85, 25, c, sw=3)),
    "calculator": lambda c: ICONS_CH1["calculator"](c),
    "chart_up": lambda c: ICONS_CH1["stock_up"](c),
    "chart_down": lambda c: ICONS_CH1["stock_down"](c),
    "location_pin": lambda c: (doodle_circle(C, 35, 22, c, sw=4)
                               + doodle_path(f"M {C-22},35 Q {C-22},70 {C},88 Q {C+22},70 {C+22},35", c, sw=4)
                               + doodle_circle(C, 35, 8, c, sw=2, fill=c)),
    "map": lambda c: (doodle_path(f"M 15,15 L 38,22 L 62,15 L 85,22 L 85,82 L 62,75 L 38,82 L 15,75 Z", c, sw=4)
                      + doodle_line(38, 22, 38, 82, c, sw=3)
                      + doodle_line(62, 15, 62, 75, c, sw=3)),
    "wallet": lambda c: ICONS_CH1["wallet"](c),
    "handshake": lambda c: (doodle_path(f"M 10,{C} L 35,{C-15} L {C},{C-10} L 65,{C-15} L 90,{C}", c, sw=4)
                            + doodle_path(f"M 10,{C} L 35,{C+15} L {C},{C+10} L 65,{C+15} L 90,{C}", c, sw=4)),
    "crown": lambda c: doodle_crown(C, C, 35, c, sw=4),
    "door": lambda c: (doodle_rect(22, 15, 56, 75, c, sw=4, rx=3)
                       + doodle_circle(68, C, 5, c, sw=3, fill=c)
                       + doodle_path(f"M 40,15 Q 50,10 60,15", c, sw=3)),
    "window": lambda c: (doodle_rect(15, 15, 70, 70, c, sw=4, rx=3)
                         + doodle_line(C, 15, C, 85, c, sw=3)
                         + doodle_line(15, C, 85, C, c, sw=3)),
    "garden": lambda c: (doodle_path(f"M {C},75 Q {C-20},55 {C-15},35 Q {C},20 {C+15},35 Q {C+20},55 {C},75", c, sw=4)
                         + doodle_line(C, 75, C, 88, c, sw=4)
                         + doodle_line(15, 88, 85, 88, c, sw=3)),
    "elevator": lambda c: (doodle_rect(20, 10, 60, 80, c, sw=4, rx=2)
                           + doodle_line(C, 10, C, 90, c, sw=3)
                           + doodle_path(f"M {C-10},35 L {C},25 L {C+10},35", c, sw=3)
                           + doodle_path(f"M {C-10},65 L {C},75 L {C+10},65", c, sw=3)),
    "bus": lambda c: (doodle_rect(10, 20, 80, 60, c, sw=4, rx=8)
                      + "".join(doodle_rect(18 + i * 22, 28, 16, 18, c, sw=2, rx=3) for i in range(3))
                      + doodle_circle(28, 84, 10, c, sw=4)
                      + doodle_circle(72, 84, 10, c, sw=4)),
}

# ─── CH4 심리 아이콘 ───
ICONS_CH4 = {k: (lambda c, k=k: doodle_circle(C, C, 30, c, sw=4)) for k in CHANNELS["CH4"]["icons"]}
ICONS_CH4["brain"] = lambda c: (doodle_circle(C - 12, C, 22, c, sw=4)
                                 + doodle_circle(C + 12, C, 22, c, sw=4)
                                 + doodle_line(C, C - 18, C, C + 18, c, sw=2))
ICONS_CH4["heart"] = lambda c: doodle_path(f"M {C},72 Q 10,50 10,35 Q 10,15 {C-15},22 Q {C},28 {C},{C-5} Q {C},28 {C+15},22 Q 90,15 90,35 Q 90,50 {C},72 Z", c, sw=4)
ICONS_CH4["thought_bubble"] = lambda c: (doodle_circle(C, 35, 28, c, sw=4)
                                          + doodle_circle(C - 5, 68, 10, c, sw=3)
                                          + doodle_circle(C - 8, 82, 6, c, sw=2))
ICONS_CH4["stress_cloud"] = lambda c: doodle_path(f"M 20,60 Q 10,50 15,38 Q 12,20 30,22 Q 32,10 {C},12 Q 68,10 72,22 Q 88,18 90,35 Q 95,50 82,60 Z", c, sw=4)
ICONS_CH4["meditation"] = lambda c: (doodle_circle(C, 25, 15, c, sw=4)
                                      + doodle_path(f"M {C-25},65 Q {C-30},40 {C},50 Q {C+30},40 {C+25},65", c, sw=4)
                                      + doodle_line(C - 25, 65, C + 25, 65, c, sw=3))
ICONS_CH4["book"] = lambda c: (doodle_rect(15, 15, 70, 70, c, sw=4, rx=3)
                                + doodle_line(C, 15, C, 85, c, sw=4)
                                + doodle_line(22, 30, 45, 30, c, sw=2)
                                + doodle_line(22, 42, 45, 42, c, sw=2))
ICONS_CH4["mirror"] = lambda c: (doodle_circle(C, 38, 28, c, sw=4)
                                  + doodle_path(f"M {C-8},66 L {C-12},85 L {C+12},85 L {C+8},66", c, sw=3))
ICONS_CH4["eye"] = lambda c: (doodle_path(f"M 10,{C} Q {C},20 90,{C} Q {C},80 10,{C}", c, sw=4)
                               + doodle_circle(C, C, 14, c, sw=3)
                               + doodle_circle(C, C, 6, c, sw=2, fill=c))
ICONS_CH4["growth_arrow"] = lambda c: (doodle_path(f"M 15,80 Q 40,60 65,35", c, sw=4)
                                        + doodle_path(f"M 55,25 L 75,35 L 65,55", c, sw=4))

# ─── CH5 미스터리 아이콘 ───
ICONS_CH5 = {k: (lambda c, k=k: doodle_path(f"M {C},{C-30} Q {C+30},{C-30} {C+30},{C} Q {C+30},{C+30} {C},{C+30} Q {C-30},{C+30} {C-30},{C} Q {C-30},{C-30} {C},{C-30} Z", c, sw=4)) for k in CHANNELS["CH5"]["icons"]}
ICONS_CH5["question_mark"] = lambda c: (doodle_path(f"M {C-12},{C-28} Q {C-16},{C-42} {C},{C-42} Q {C+16},{C-42} {C+16},{C-28} Q {C+16},{C-14} {C},{C-8} L {C},{C+5}", c, sw=5)
                                         + doodle_circle(C, C + 18, 5, c, sw=3, fill=c))
ICONS_CH5["ghost"] = lambda c: (doodle_path(f"M 20,85 L 20,40 Q 20,15 {C},15 Q 80,15 80,40 L 80,85 L 68,72 L {C},85 L 32,72 Z", c, sw=4)
                                 + doodle_circle(38, 48, 7, c, sw=3, fill=c)
                                 + doodle_circle(62, 48, 7, c, sw=3, fill=c))
ICONS_CH5["magnifier"] = lambda c: (doodle_circle(38, 38, 24, c, sw=4) + doodle_line(56, 56, 85, 85, c, sw=6))
ICONS_CH5["moon"] = lambda c: doodle_path(f"M {C+10},18 Q {C-20},20 {C-28},{C} Q {C-20},80 {C+10},82 Q {C-15},70 {C-15},{C} Q {C-15},30 {C+10},18 Z", c, sw=4)
ICONS_CH5["skull"] = lambda c: (doodle_circle(C, 40, 28, c, sw=4)
                                 + doodle_rect(28, 65, 44, 18, c, sw=3, rx=2)
                                 + doodle_circle(C - 10, 40, 8, c, sw=3, fill=c)
                                 + doodle_circle(C + 10, 40, 8, c, sw=3, fill=c))
ICONS_CH5["candle"] = lambda c: (doodle_rect(35, 40, 30, 50, c, sw=4, rx=3)
                                  + doodle_path(f"M {C},15 Q {C+8},28 {C},38 Q {C-8},28 {C},15", c, sw=3))

# ─── CH6 역사 아이콘 ───
ICONS_CH6 = {k: (lambda c, k=k: doodle_rect(15, 15, 70, 70, c, sw=4, rx=6)) for k in CHANNELS["CH6"]["icons"]}
ICONS_CH6["scroll"] = lambda c: (doodle_rect(20, 20, 60, 60, c, sw=4, rx=4)
                                  + doodle_circle(20, C, 12, c, sw=4)
                                  + doodle_circle(80, C, 12, c, sw=4)
                                  + doodle_line(28, 35, 72, 35, c, sw=2)
                                  + doodle_line(28, C, 72, C, c, sw=2)
                                  + doodle_line(28, 65, 60, 65, c, sw=2))
ICONS_CH6["sword"] = lambda c: (doodle_line(C - 35, C + 35, C + 35, C - 35, c, sw=5)
                                  + doodle_path(f"M {C-42},{C+42} L {C-38},{C+38}", c, sw=8)
                                  + doodle_line(C - 8, C + 8, C + 8, C - 8, c, sw=3))
ICONS_CH6["crown"] = lambda c: doodle_crown(C, C, 38, c, sw=4)
ICONS_CH6["castle"] = lambda c: (doodle_rect(15, 38, 70, 47, c, sw=4)
                                  + doodle_rect(15, 25, 14, 18, c, sw=3)
                                  + doodle_rect(43, 25, 14, 18, c, sw=3)
                                  + doodle_rect(71, 25, 14, 18, c, sw=3)
                                  + doodle_rect(38, 58, 24, 27, c, sw=3, rx=2))
ICONS_CH6["hourglass"] = lambda c: (doodle_path(f"M 20,15 L 80,15 L {C},{C} L 80,85 L 20,85 L {C},{C} Z", c, sw=4)
                                     + doodle_line(15, 15, 85, 15, c, sw=4)
                                     + doodle_line(15, 85, 85, 85, c, sw=4))
ICONS_CH6["ship"] = lambda c: (doodle_path(f"M 10,65 L 90,65 Q 80,85 {C},85 Q 20,85 10,65", c, sw=4)
                                + doodle_line(C, 20, C, 65, c, sw=4)
                                + doodle_path(f"M {C},20 L {C+30},45 L {C},50", c, sw=3))
ICONS_CH6["compass_old"] = lambda c: (doodle_circle(C, C, 32, c, sw=4)
                                       + doodle_path(f"M {C},{C-28} L {C+10},{C+10} L {C},{C+28} L {C-10},{C+10} Z", c, sw=3)
                                       + doodle_circle(C, C, 5, c, sw=2, fill=c))
ICONS_CH6["quill"] = lambda c: (doodle_path(f"M 80,15 Q 20,35 35,85", c, sw=3)
                                 + doodle_path(f"M 80,15 Q 90,40 35,85", c, sw=3)
                                 + doodle_line(35, 85, 30, 90, c, sw=3))

# ─── CH7 전쟁사 아이콘 ───
ICONS_CH7 = {k: (lambda c, k=k: doodle_circle(C, C, 30, c, sw=4)) for k in CHANNELS["CH7"]["icons"]}
ICONS_CH7["sword_crossed"] = lambda c: (doodle_line(15, 15, 85, 85, c, sw=5)
                                         + doodle_line(85, 15, 15, 85, c, sw=5))
ICONS_CH7["shield"] = lambda c: doodle_path(f"M {C},15 L 82,30 L 82,{C} Q 82,75 {C},88 Q 18,75 18,{C} L 18,30 Z", c, sw=4)
ICONS_CH7["tank"] = lambda c: (doodle_rect(12, 42, 76, 35, c, sw=4, rx=8)
                                + doodle_rect(22, 28, 56, 18, c, sw=3, rx=4)
                                + doodle_line(60, 28, 85, 18, c, sw=4)
                                + "".join(doodle_circle(20 + i * 15, 78, 8, c, sw=3) for i in range(5)))
ICONS_CH7["medal"] = lambda c: (doodle_circle(C, 55, 28, c, sw=4)
                                 + doodle_star(C, 55, 15, c, sw=2)
                                 + doodle_line(C - 12, 28, C - 8, 8, c, sw=3)
                                 + doodle_line(C + 12, 28, C + 8, 8, c, sw=3)
                                 + doodle_line(C - 8, 8, C + 8, 8, c, sw=3))
ICONS_CH7["helmet"] = lambda c: (doodle_path(f"M 15,58 Q 15,22 {C},18 Q 85,22 85,58 L 85,65 L 15,65 Z", c, sw=4)
                                  + doodle_rect(10, 62, 80, 12, c, sw=3, rx=4))
ICONS_CH7["flag_military"] = lambda c: (doodle_line(20, 15, 20, 85, c, sw=4)
                                         + doodle_path(f"M 20,18 L 75,28 L 75,55 L 20,48 Z", c, sw=3))
ICONS_CH7["cannon"] = lambda c: (doodle_rect(15, C - 10, 55, 22, c, sw=4, rx=6)
                                  + doodle_circle(80, C, 12, c, sw=3)
                                  + doodle_circle(25, C + 16, 12, c, sw=4)
                                  + doodle_circle(48, C + 16, 12, c, sw=4))
ICONS_CH7["plane"] = lambda c: (doodle_path(f"M {C},15 L {C+35},55 L {C+20},55 L {C+20},75 L {C},65 L {C-20},75 L {C-20},55 L {C-35},55 Z", c, sw=4)
                                 + doodle_path(f"M {C+20},65 L {C+35},70 L {C+35},75 L {C+20},72", c, sw=3))
ICONS_CH7["rifle"] = lambda c: (doodle_rect(5, C - 6, 80, 12, c, sw=4, rx=4)
                                 + doodle_line(85, C, 95, C, c, sw=4)
                                 + doodle_rect(15, C + 6, 30, 18, c, sw=3, rx=3))
ICONS_CH7["grenade"] = lambda c: (doodle_circle(C, 55, 25, c, sw=4)
                                   + doodle_rect(C - 10, 22, 20, 16, c, sw=3, rx=3)
                                   + doodle_line(C, 22, C, 12, c, sw=3))
ICONS_CH7["bomb"] = lambda c: (doodle_circle(C, 58, 28, c, sw=4)
                                + doodle_path(f"M {C+10},32 Q {C+25},18 {C+30},10", c, sw=3)
                                + doodle_circle(C + 32, 8, 5, c, sw=2, fill=c))


CHANNEL_ICONS = {
    "CH1": ICONS_CH1,
    "CH2": ICONS_CH2,
    "CH3": ICONS_CH3,
    "CH4": ICONS_CH4,
    "CH5": ICONS_CH5,
    "CH6": ICONS_CH6,
    "CH7": ICONS_CH7,
}


def generate_icons(ch_id: str) -> None:
    cfg = CHANNELS[ch_id]
    color = cfg["main_color"]
    icons_map = CHANNEL_ICONS[ch_id]
    out_dir = CHANNELS_DIR / ch_id / "icons"
    count = 0
    for icon_name in cfg["icons"]:
        fn = icons_map.get(icon_name)
        if fn is None:
            body = doodle_circle(C, C, 30, color, sw=4)
        else:
            body = fn(color)
        content = icon_svg(body, color)
        (out_dir / f"{icon_name}.svg").write_text(content, encoding="utf-8")
        count += 1
    logger.info(f"[OK] {ch_id} 아이콘 {count}종 생성")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for ch_id in CHANNELS:
        generate_icons(ch_id)
    logger.info("7채널 × 20종 아이콘 SVG 생성 완료")

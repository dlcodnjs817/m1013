#!/usr/bin/env python3
"""2026-08-24 랩미팅 PPT — OMX→두산 M1013 전이 (Isaac Sim 시뮬레이션 트랙, 8/20~).

  python3 make_labmeeting_pptx_0824.py
  → /home/kim/m1013/대화록 및 PPT/랩미팅_20260824.pptx

슬라이드 2단 구조:
  위쪽  = 그림·도해·사진 중심 (박사님이 한눈에 볼 시각 자료 — 글 최소화)
  아래쪽 = [이해 노트·설명 대본] 사각형 — 말로 설명할 내용 (발표 때 숨기거나 지워도 됨)
사진/영상은 점선 상자 자리에 발표 전 직접 삽입.
"""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt

NAVY = RGBColor(0x2F, 0x3D, 0x9E)
INK = RGBColor(0x15, 0x18, 0x1D)
GREY = RGBColor(0x62, 0x6B, 0x78)
LINE = RGBColor(0xD8, 0xDC, 0xE3)
RED = RGBColor(0xA9, 0x33, 0x1D)
GREEN = RGBColor(0x1F, 0x6B, 0x4A)
BGSOFT = RGBColor(0xED, 0xEF, 0xF3)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LILAC = RGBColor(0xB9, 0xC2, 0xF0)
AMBER = RGBColor(0x9A, 0x6A, 0x00)
TAN = RGBColor(0xE8, 0xDD, 0xC0)
BLUE = RGBColor(0x5B, 0x6E, 0xE1)

FONT = "맑은 고딕"
MONO = "Consolas"
SW, SH = Cm(33.867), Cm(19.05)
BASE = "/home/kim/m1013"
OUTDIR = os.path.join(BASE, "대화록 및 PPT")
SIMOUT = os.path.join(BASE, "sim_out")
FRAMES = os.path.join(SIMOUT, "frames_straight_ok")

prs = Presentation()
prs.slide_width = SW
prs.slide_height = SH
BLANK = prs.slide_layouts[6]


def _set(run, size=15, bold=False, color=INK, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def slide():
    return prs.slides.add_slide(BLANK)


def bar(s, title, step=None):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Cm(2.0))
    r.fill.solid(); r.fill.fore_color.rgb = NAVY
    r.line.fill.background()
    tf = r.text_frame
    tf.margin_left = Cm(0.9); tf.margin_top = Cm(0.26)
    p = tf.paragraphs[0]
    if step:
        run = p.add_run(); run.text = step + "  "
        _set(run, 15, True, LILAC)
    run = p.add_run(); run.text = title
    _set(run, 21, True, WHITE)
    return r


def textbox(s, x, y, w, h):
    tb = s.shapes.add_textbox(x, y, w, h)
    tb.text_frame.word_wrap = True
    return tb.text_frame


def label(s, x, y, w, txt, size=13, color=INK, bold=True, align=PP_ALIGN.CENTER):
    tf = textbox(s, x, y, w, Cm(0.9))
    p = tf.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = txt
    _set(run, size, bold, color)
    return tf


def keyline(s, txt, w=Cm(32.1)):
    """타이틀 바 바로 아래 한 줄 핵심 설명."""
    tf = textbox(s, Cm(0.9), Cm(2.06), w, Cm(0.6))
    p = tf.paragraphs[0]
    run = p.add_run(); run.text = "▎ " + txt
    _set(run, 14, True, NAVY)
    return tf


def table(s, x, y, w, rows, widths=None, size=12.5, header=True, rh=Cm(0.8)):
    shp = s.shapes.add_table(len(rows), len(rows[0]), x, y, w, rh * len(rows))
    t = shp.table
    if widths:
        total = sum(widths)
        for i, cw in enumerate(widths):
            t.columns[i].width = int(w * cw / total)
    for ri, row in enumerate(rows):
        t.rows[ri].height = rh
        for ci, cell in enumerate(row):
            c = t.cell(ri, ci)
            c.margin_left = Cm(0.16); c.margin_right = Cm(0.16)
            c.margin_top = Cm(0.05); c.margin_bottom = Cm(0.05)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            txt = cell if isinstance(cell, str) else cell[0]
            opt = {} if isinstance(cell, str) else cell[1]
            c.fill.solid()
            c.fill.fore_color.rgb = (NAVY if (header and ri == 0)
                                     else opt.get("bg", WHITE if ri % 2 else BGSOFT))
            p = c.text_frame.paragraphs[0]
            run = p.add_run(); run.text = txt
            _set(run, opt.get("size", size),
                 opt.get("bold", header and ri == 0),
                 WHITE if (header and ri == 0) else opt.get("color", INK),
                 MONO if opt.get("mono") else FONT)
    return t


def foot(s, txt):
    tf = textbox(s, Cm(0.9), SH - Cm(0.72), SW - Cm(1.8), Cm(0.6))
    p = tf.paragraphs[0]
    run = p.add_run(); run.text = txt
    _set(run, 10, False, GREY)


def flowbox(s, x, y, w, h, txt, fill=NAVY, fg=WHITE, size=12.5, bold=True):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = fill
    b.line.color.rgb = LINE; b.line.width = Pt(0.75)
    tf = b.text_frame; tf.word_wrap = True
    tf.margin_left = Cm(0.12); tf.margin_right = Cm(0.12)
    tf.margin_top = Cm(0.08); tf.margin_bottom = Cm(0.08)
    for i, line in enumerate(txt.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = line
        _set(run, size if i == 0 else size - 2, bold if i == 0 else False, fg)
    return b


def arrow(s, x, y, w=Cm(0.7), h=Cm(0.5), color=GREY):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x, y, w, h)
    a.fill.solid(); a.fill.fore_color.rgb = color
    a.line.fill.background()
    return a


def statcard(s, x, y, w, h, before, after, title, good=GREEN):
    """전/후 비교 카드 — 위 작은 회색 '전', 큰 색깔 '후'."""
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = WHITE
    b.line.color.rgb = good; b.line.width = Pt(1.75)
    tf = b.text_frame; tf.word_wrap = True
    tf.margin_top = Cm(0.18); tf.margin_bottom = Cm(0.1)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = title
    _set(run, 13, True, INK)
    p = tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER; p.space_before = Pt(4)
    run = p.add_run(); run.text = before + "  →"
    _set(run, 14, False, GREY)
    p = tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER; p.space_before = Pt(2)
    run = p.add_run(); run.text = after
    _set(run, 22, True, good)
    return b


def bigcard(s, x, y, w, h, big, sub, color=NAVY, bigsize=24):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = WHITE
    b.line.color.rgb = color; b.line.width = Pt(1.75)
    tf = b.text_frame; tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = big
    _set(run, bigsize, True, color)
    p = tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER; p.space_before = Pt(3)
    run = p.add_run(); run.text = sub
    _set(run, 12.5, False, GREY)
    return b


def chip(s, x, y, w, txt, fill=GREEN, h=Cm(0.95), size=13):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = fill
    b.line.fill.background()
    tf = b.text_frame
    tf.margin_top = Cm(0.05); tf.margin_bottom = Cm(0.05)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = txt
    _set(run, size, True, WHITE)
    return b


def panel(s, x, y, w, h, title=None, border=LINE):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = WHITE
    b.line.color.rgb = border; b.line.width = Pt(1.25)
    if title:
        label(s, x, y + Cm(0.12), w, title, 13.5, INK, True)
    return b


def mediabox(s, x, y, w, h, lab, note="발표 전 이 자리에 삽입", icon="▶"):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = BGSOFT
    b.line.color.rgb = NAVY; b.line.width = Pt(1.5)
    try:
        from pptx.enum.line import MSO_LINE
        b.line.dash_style = MSO_LINE.DASH
    except Exception:
        pass
    tf = b.text_frame; tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = icon + "  " + lab
    _set(run, 15, True, NAVY)
    p = tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = note
    _set(run, 11, False, GREY)
    return b


def caption(s, x, y, w, txt, size=11):
    tf = textbox(s, x, y, w, Cm(0.9))
    p = tf.paragraphs[0]
    run = p.add_run(); run.text = txt
    _set(run, size, False, GREY)


def notebox(s, lines, y=Cm(13.35), h=Cm(4.7)):
    """슬라이드 하단 이해 노트 사각형 — 말로 설명할 대본."""
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(0.9), y, Cm(32.1), h)
    b.fill.solid(); b.fill.fore_color.rgb = BGSOFT
    b.line.color.rgb = NAVY; b.line.width = Pt(1.25)
    tf = b.text_frame; tf.word_wrap = True
    tf.margin_left = Cm(0.45); tf.margin_right = Cm(0.45)
    tf.margin_top = Cm(0.2); tf.margin_bottom = Cm(0.12)
    p = tf.paragraphs[0]
    run = p.add_run(); run.text = "이해 노트 · 설명 대본"
    _set(run, 12.5, True, NAVY)
    p.space_after = Pt(4)
    for txt in lines:
        opt = {}
        if isinstance(txt, tuple):
            txt, opt = txt
        p = tf.add_paragraph()
        p.space_after = Pt(3)
        run = p.add_run(); run.text = "–  " + txt
        _set(run, opt.get("size", 12.5), opt.get("bold", False),
             opt.get("color", INK))
    return b


# ═══════════ 1. 표지 ═══════════
s = slide()
r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background()
tf = textbox(s, Cm(2.2), Cm(4.6), Cm(29.5), Cm(8))
p = tf.paragraphs[0]
run = p.add_run(); run.text = "OMX 시연의 두산 M1013 전이"
_set(run, 36, True, WHITE)
p = tf.add_paragraph(); p.space_before = Pt(8)
run = p.add_run()
run.text = "Isaac Sim 시뮬레이션 트랙 — 하루 만에 데이터 변환부터 정책 물리 실행까지"
_set(run, 20, False, LILAC)
p = tf.add_paragraph(); p.space_before = Pt(30)
run = p.add_run()
run.text = ("159/159 변환 (5.7초)   |   ACT 관절오차 0.62~0.67°   |   "
            "35mm 큐브 파지 성공   |   정책 물리 실행 놓기 오차 7.8mm")
_set(run, 15, True, WHITE)
tf2 = textbox(s, Cm(2.2), SH - Cm(1.7), Cm(24), Cm(0.9))
run = tf2.paragraphs[0].add_run()
run.text = "랩미팅 · 2026-08-24 (월) · 이채원 · 한국생산기술연구원 현장실습"
_set(run, 13, False, LILAC)

# ═══════════ 2. 배경 — 방향 전환 ═══════════
s = slide()
bar(s, "배경 — 최종 타깃을 TX90 → 두산 M1013 으로 전환", "01 배경")
keyline(s, "데이터·방법론(초록)은 유지, 로봇 층(남색)만 교체 — 하루 만에 재현", Cm(21.0))
flowbox(s, Cm(0.9), Cm(2.9), Cm(8.2), Cm(2.6),
        "Staubli TX2-90\n기존 타깃 — 방법론 검증 완료\n(8/12~14)", fill=GREY, size=13.5)
arrow(s, Cm(9.35), Cm(3.85), Cm(1.3), Cm(0.7))
flowbox(s, Cm(10.9), Cm(2.9), Cm(9.2), Cm(2.6),
        "두산 M1013 (최종 타깃)\n실기 도착: 9월 중하순\n도착 전 Isaac Sim 선행 검증", fill=NAVY, size=14)
mediabox(s, Cm(22.2), Cm(2.6), Cm(10.8), Cm(6.6), "두산 M1013 사진", icon="📷")
flowbox(s, Cm(0.9), Cm(6.3), Cm(19.2), Cm(2.9),
        "그대로 재사용 (로봇 불변)\nOMX 시연 데이터셋 v5 (159ep) · 오일러 wrap 수정\n오프라인 IK 변환 파이프라인 · ACT 학습 설정",
        fill=GREEN, size=13.5)
flowbox(s, Cm(0.9), Cm(9.7), Cm(19.2), Cm(2.9),
        "M1013 용 신규 제작 (로봇 종속) = 8/20 하루 작업\n기구학 (URDF·IK) · 작업대 배치 오프셋 · 특이점 대책",
        fill=NAVY, size=13.5)
label(s, Cm(22.2), Cm(9.7), Cm(10.8), "재사용 : 신규 = 방법론 전부 : 로봇 껍데기만", 13, GREY, False)
notebox(s, [
    "왜 바꾸나: 실기 투입할 로봇이 TX90 이 아니라 새로 오는 M1013 으로 정해졌다 (약 한 달 뒤 도착). TX90 전용 준비(외부제어 견적, 특이점 회피 배치)는 우선순위를 내렸다.",
    "핵심 아이디어: 시연 데이터(OMX 손끝 궤적)와 방법론은 로봇이 바뀌어도 안 변한다 (초록 상자). 로봇에 붙어 있는 것(팔 구조·관절 계산·작업대 위치)만 다시 만들면 된다 (남색 상자).",
    "그 '다시 만들기'가 8/20 하루 작업의 전부였고, TX90 때 3일 걸린 과정이 하루에 끝났다 — 방법론이 이미 검증돼 있었기 때문.",
    "박사님 제안대로 로봇 도착 전에 Isaac Sim 물리 시뮬레이션에서 미리 전 과정을 검증해 두는 트랙이다.",
])
foot(s, "OMX→M1013 전이 · 랩미팅 2026-08-24")

# ═══════════ 3. 전체 파이프라인 지도 ═══════════
s = slide()
bar(s, "전체 그림 — 8/20 하루에 완주한 6단계", "02 지도")
keyline(s, "OMX 시연 159개를 M1013 관절 언어로 번역 → 배운 정책이 물리 시뮬레이션에서 큐브를 집었다")
y1 = Cm(2.9); h = Cm(3.0); w = Cm(4.85); gap = Cm(0.75)
steps = [
    ("OMX 시연 159ep\nEE pose 데이터셋 v5\n(TX90 때 완성, 재사용)", GREY),
    ("에셋 검증\nm1013.usd + URDF\nFK 리치 1300mm 일치", GREEN),
    ("독립 IK + 배치 스윕\n오프셋 54후보 탐색\n작업대 위치 확정", GREEN),
    ("관절 데이터셋 v6\n159/159 변환 5.7초\n검증 4종 통과", GREEN),
    ("Isaac 물리 검증\n35mm 큐브 파지 성공\n+ ACT 100k 학습", GREEN),
    ("정책 물리 실행\n집기→운반→놓기 완주\n놓기 오차 7.8mm", NAVY),
]
x = Cm(0.9)
for i, (txt, c) in enumerate(steps):
    flowbox(s, x, y1, w, h, txt, fill=c, size=12)
    if i < len(steps) - 1:
        arrow(s, x + w + Cm(0.03), y1 + h / 2 - Cm(0.25), Cm(0.66))
    x += w + gap
cw = Cm(7.5); cy = Cm(7.1); cg = Cm(0.7)
bigcard(s, Cm(0.9), cy, cw, Cm(3.7), "159 / 159", "에피소드 변환 성공", GREEN)
bigcard(s, Cm(0.9) + (cw + cg), cy, cw, Cm(3.7), "5.7초", "전체 변환 시간 (TX90 땐 수십 분)", GREEN)
bigcard(s, Cm(0.9) + (cw + cg) * 2, cy, cw, Cm(3.7), "0.62~0.67°", "정책 관절오차 (TX90 0.93~1.55°)", GREEN)
bigcard(s, Cm(0.9) + (cw + cg) * 3, cy, cw, Cm(3.7), "7.8 mm", "정책 물리 실행 놓기 오차", NAVY)
notebox(s, [
    "각 상자를 풀면: ① 재료(OMX 시연을 TX90 좌표로 이식해 둔 것) ② M1013 3D 모델·수치 확인 ③ 작업대를 로봇 기준 어디에 둘지 + 손끝 위치→관절각 계산기 제작 ④ 159개 시연 전부를 관절 궤적으로 번역 ⑤ 물리 시뮬에서 진짜 집히는지 + 모방학습 ⑥ 학습된 정책의 출력이 물리에서 성공.",
    "'물리 검증'이 중요한 이유: RViz(TX90 때 쓴 도구)는 애니메이션일 뿐 물건이 안 집힌다. Isaac Sim 은 마찰·중력·접촉이 있어 '실제로 집히는가'에 처음 답할 수 있다.",
    "하루에 끝난 이유: 방법론 재사용 + MoveIt 없는 독립 IK 로 변환이 수십 분 → 5.7초가 되어 반복 실험이 자유로워졌기 때문.",
    "지금까지는 open-loop (녹화된 관측으로 추론) — closed-loop (실시간 카메라 관측) 가 다음 단계다.",
], y=Cm(13.55), h=Cm(4.5))
foot(s, "OMX→M1013 전이 · 랩미팅 2026-08-24")

# ═══════════ 4. 에셋 검증 ═══════════
s = slide()
bar(s, "준비 — M1013 에셋 검증", "03 에셋")
keyline(s, "공식 에셋의 수치를 실물 스펙과 대조 — 이후 모든 계산이 딛고 설 토대부터 확보", Cm(21.0))
cw = Cm(20.7); ch = Cm(3.1)
flowbox(s, Cm(0.9), Cm(2.7), cw, ch,
        "✔  두산 공식 Isaac 용 3D 모델 (m1013.usd) 동봉\nURDF 임포트 과정 자체가 불필요 — 로드 검증 완료", fill=GREEN, size=14.5)
flowbox(s, Cm(0.9), Cm(6.15), cw, ch,
        "✔  수치가 실물 스펙과 일치\n관절 리밋 ±360° (J3 ±160°) · FK 수평 리치 1300.5 mm = 카탈로그 1300 mm", fill=GREEN, size=14.5)
flowbox(s, Cm(0.9), Cm(9.6), cw, ch,
        "⚠  함정 파일 배제: m1013_isaac_sim.urdf\n관절 리밋 축소판 (J1 ±120°) + 받침대 0.45 m → 표준 m1013.urdf 사용", fill=RED, size=14.5)
mediabox(s, Cm(22.6), Cm(2.7), Cm(10.4), Cm(10.0), "Isaac Sim 에 로드된 M1013",
         "sim_out 스냅샷 또는 GUI 캡처 삽입", icon="📷")
notebox(s, [
    "USD = Isaac Sim 이 쓰는 3D 모델 형식, URDF = ROS 가 쓰는 로봇 구조 기술 파일. 보통 URDF→USD 변환(임포트)이 한 고비인데, 두산이 공식 USD 를 이미 만들어 둬서 그 고비가 통째로 사라졌다.",
    "FK(순기구학) = 관절각 6개를 넣으면 손끝 위치가 나오는 계산. 이 결과가 카탈로그 스펙(리치 1300mm)과 일치하면 URDF 수치를 신뢰할 수 있다는 뜻 — 이후 모든 계산의 토대라 먼저 확인했다.",
    "함정 파일을 걸러낸 게 중요: 리밋이 좁은 URDF 로 IK 를 풀면 실제론 되는 자세를 '불가능'으로 잘못 판정한다. 링크·조인트 이름 규약이 TX90 과 같아서 기존 파이프라인은 URDF 파일 교체만으로 이식됐다.",
])
foot(s, "산출: doosan-robot2 클론 · FK 스모크 테스트 · Isaac Sim 5.1.0 (RTX 5070 Ti)")

# ═══════════ 5. 독립 IK + 배치 스윕 ═══════════
s = slide()
bar(s, "STEP 1 — 독립 IK 솔버 + 작업대 배치 전수 탐색", "04 IK·배치")
keyline(s, "자체 IK 로 변환이 수십 분 → 5.7초 — 그 반복 속도로 작업대 위치 54후보를 전수 탐색해 확정")
statcard(s, Cm(0.9), Cm(2.75), Cm(9.6), Cm(3.4), "수십 분 (MoveIt)", "5.7초", "159ep 전체 변환 시간")
bigcard(s, Cm(0.9), Cm(6.5), Cm(9.6), Cm(2.9), "1000 / 1000", "IK 셀프테스트 수렴 (오차 ≤0.1mm)", NAVY, 22)
bigcard(s, Cm(0.9), Cm(9.8), Cm(9.6), Cm(2.9), "54 후보", "배치 오프셋 2단계 전수 탐색", NAVY, 22)
# 배치 스윕 도해 (위에서 본 그림)
px, py, pw, ph = Cm(11.3), Cm(2.75), Cm(21.7), Cm(10.0)
panel(s, px, py, pw, ph, "작업대를 로봇 기준 어디에 둘 것인가? — 위에서 본 그림")
base = s.shapes.add_shape(MSO_SHAPE.OVAL, px + Cm(1.6), py + Cm(3.6), Cm(2.6), Cm(2.6))
base.fill.solid(); base.fill.fore_color.rgb = GREY; base.line.fill.background()
label(s, px + Cm(1.1), py + Cm(6.3), Cm(3.6), "M1013 베이스", 12, GREY)
old = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px + Cm(6.9), py + Cm(1.6), Cm(5.6), Cm(3.6))
old.fill.solid(); old.fill.fore_color.rgb = BGSOFT
old.line.color.rgb = GREY; old.line.width = Pt(1.25)
try:
    from pptx.enum.line import MSO_LINE
    old.line.dash_style = MSO_LINE.DASH
except Exception:
    pass
label(s, px + Cm(6.9), py + Cm(3.0), Cm(5.6), "원 위치 (OMX)", 11.5, GREY)
new = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px + Cm(13.6), py + Cm(4.0), Cm(5.6), Cm(3.6))
new.fill.solid(); new.fill.fore_color.rgb = TAN
new.line.color.rgb = GREEN; new.line.width = Pt(2.25)
label(s, px + Cm(13.6), py + Cm(5.3), Cm(5.6), "확정 위치", 12.5, GREEN, True)
ar = arrow(s, px + Cm(11.9), py + Cm(4.6), Cm(2.3), Cm(0.7), NAVY)
ar.rotation = 25
label(s, px + Cm(11.3), py + Cm(7.8), Cm(9.6),
      "d = (+0.05, −0.15, +0.10) m · 53/54 통과", 13.5, NAVY, True)
chip(s, px + Cm(0.9), py + Cm(8.6), Cm(6.6), "손목 특이점 여유 49.7°", GREEN)
chip(s, px + Cm(7.9), py + Cm(8.6), Cm(6.6), "베이스 기둥 여유 0.63 m", GREEN)
chip(s, px + Cm(14.9), py + Cm(8.6), Cm(6.0), "관절 리밋 여유 67.6°", GREEN)
notebox(s, [
    "IK(역기구학) = '손끝을 여기에 두려면 관절 6개를 몇 도로?' 를 푸는 계산. m1013_kin.py 로 ROS·MoveIt 없이 도는 독립 계산기를 만들었다 — 해가 여러 개일 때(팔꿈치 위/아래 등) 이전 프레임과 이어지는 해를 고르는 규약은 TX90 때 만든 걸 이식.",
    "빨라진 효과가 본질: 변환이 5.7초면 '조건 바꿔서 다시 돌려보기'를 하루 종일 반복할 수 있다. 오늘 나온 배치 재탐색·손목 보정 같은 결정이 전부 이 반복 속도 덕에 가능했다.",
    "배치 스윕(오른쪽 그림): 같은 손끝 궤적도 로봇 기준 '어디서' 하느냐에 따라 관절이 편하기도, 특이점에 몰리기도 한다. 54개 후보 위치를 전수 채점(특이점 여유·리밋 여유·자기충돌 기하)해서 초록 위치로 확정.",
    "이 d 는 나중에 실물 작업대(테이프 사각형)를 놓을 때 그대로 쓰는 값 — 시뮬과 실물의 배치가 일치해야 궤적이 유효하다.",
])
foot(s, "산출: m1013_kin.py · sweep_m1013.py · sweep_result_wrist45.json")

# ═══════════ 6. 데이터셋 변환 ═══════════
s = slide()
bar(s, "STEP 2 — v6-M1013 관절 데이터셋 변환", "05 변환")
keyline(s, "손끝 언어(v5)를 관절 언어(v6)로 오프라인에서 미리 번역 — 실행 때 IK 호출 0회")
flowbox(s, Cm(0.9), Cm(3.1), Cm(7.6), Cm(3.6),
        "데이터셋 v5\n손끝 위치의 나열 (EE pose)\n159ep · 76,345 프레임", fill=GREY, size=13.5)
arrow(s, Cm(8.7), Cm(4.55), Cm(1.0), Cm(0.7))
flowbox(s, Cm(9.9), Cm(2.7), Cm(13.4), Cm(4.4),
        "오프라인 IK 번역 (규약)\nTX90 v6 이식: 7프레임 평활 · 6Hz 앵커 IK · state=action[t−1]\n+ 신규 ①: TCP 0.12m — pose 를 '그리퍼 끝' 목표로 해석\n+ 신규 ②: 손목 45° 보정 (다음 장)",
        fill=NAVY, size=13.5)
arrow(s, Cm(23.5), Cm(4.55), Cm(1.0), Cm(0.7))
flowbox(s, Cm(24.7), Cm(3.1), Cm(8.3), Cm(3.6),
        "데이터셋 v6-M1013\n관절각의 나열 (joint)\n실행 시 IK 호출 0회", fill=GREEN, size=13.5)
label(s, Cm(0.9), Cm(7.9), Cm(32.1), "검증 4종 전부 통과", 15, INK, True, PP_ALIGN.LEFT)
cw = Cm(7.5); cy = Cm(8.8); cg = Cm(0.7)
bigcard(s, Cm(0.9), cy, cw, Cm(3.4), "159 / 159", "변환 완전성 (IK 실패 0)", GREEN, 22)
bigcard(s, Cm(0.9) + (cw + cg), cy, cw, Cm(3.4), "≤ 2.94° /fr", "연속성 (임계 30°)", GREEN, 22)
bigcard(s, Cm(0.9) + (cw + cg) * 2, cy, cw, Cm(3.4), "≤ 4.9 mm", "FK 역검증 왕복 오차", GREEN, 22)
bigcard(s, Cm(0.9) + (cw + cg) * 3, cy, cw, Cm(3.4), "0 / 4,770", "다봉성 kNN (단봉 확인)", GREEN, 22)
notebox(s, [
    "하는 일: v5(손끝 위치의 나열)를 에피소드마다 처음부터 끝까지 IK 로 풀어 '관절각의 나열'로 바꾼다. 학습 데이터 자체를 관절 언어로 만들어 두면 실행할 때 IK 를 한 번도 안 풀어도 된다 — TX90 v6 에서 검증한 전략.",
    "TCP: 데이터의 위치는 '그리퍼 끝'인데 IK 는 '플랜지(손목 끝 면)'를 움직인다. 그리퍼 길이 0.12m 만큼 목표를 되당겨 주는 것. OMX 접근이 기울어서(최대 72°) 이걸 무시하면 수평 오차 중앙값 84mm. 실물 그리퍼 확정 시 상수만 바꿔 1분 재변환.",
    "검증 4종: ① 전부 변환됐나 ② 관절이 프레임 사이에 튀지 않나 ③ 관절→손끝 왕복 계산이 원본과 일치하나 ④ 같은 입력에 다른 출력이 섞여(다봉) 학습을 망치지 않나 — 전부 통과.",
])
foot(s, "산출: convert_v6_m1013.py · 데이터셋 dlcodnjs/m1013_act_pick_and_place_v6_joint (76,345 프레임)")

# ═══════════ 7. 트러블슈팅 — 35mm 파지 실패 ═══════════
s = slide()
bar(s, "트러블슈팅 — 35 mm 큐브 파지 실패 12회, 원인 규명", "06 문제")
keyline(s, "실패 원인은 물리 오류가 아니라 접근 기하 — 옆으로 쓸며 진입해 잡기 전에 큐브를 밀어낸다")
bigcard(s, Cm(0.9), Cm(2.75), Cm(6.4), Cm(3.0), "12회 실패", "6cm 가정 → 35mm 실측 교체 후", RED, 22)
bigcard(s, Cm(0.9), Cm(6.15), Cm(6.4), Cm(3.0), "내적 0.13", "이동 방향 · 개구 방향 (거의 수직)", RED, 22)
bigcard(s, Cm(0.9), Cm(9.55), Cm(6.4), Cm(3.0), "0.2 mm", "닫힘 타이밍까지 맞춰도 실패", GREY, 22)
# 실패 기하 도해 (위에서 본 그림)
px, py, pw, ph = Cm(8.1), Cm(2.75), Cm(13.4), Cm(9.8)
panel(s, px, py, pw, ph, "위에서 본 실패 기하 — 패들 옆면이 큐브를 쓸어냄")
pj1 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px + Cm(4.4), py + Cm(1.8), Cm(1.0), Cm(5.6))
pj2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px + Cm(7.6), py + Cm(1.8), Cm(1.0), Cm(5.6))
for pj in (pj1, pj2):
    pj.fill.solid(); pj.fill.fore_color.rgb = GREY; pj.line.fill.background()
label(s, px + Cm(3.6), py + Cm(0.9), Cm(6.0), "그리퍼 패들 2개 (개구 ↔)", 11.5, GREY)
cube = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px + Cm(9.8), py + Cm(3.9), Cm(1.5), Cm(1.5))
cube.fill.solid(); cube.fill.fore_color.rgb = BLUE; cube.line.fill.background()
label(s, px + Cm(9.5), py + Cm(5.5), Cm(2.4), "큐브", 11.5, GREY)
mv = arrow(s, px + Cm(3.2), py + Cm(4.3), Cm(5.4), Cm(0.8), RED)
label(s, px + Cm(1.6), py + Cm(7.7), Cm(11.0), "접근 이동 방향이 개구와 수직 → 잡기 전에 옆면으로 밀어냄", 12.5, RED, True)
label(s, px + Cm(0.6), py + Cm(8.7), Cm(12.4), "실물 OMX 가 됐던 이유: 폼 큐브가 눌리며 슬롯에 '팝인' — 강체 시뮬은 재현 불가", 11.5, GREY, False)
mediabox(s, Cm(22.6), Cm(2.75), Cm(10.4), Cm(4.7), "파지 실패 영상",
         "sim_out/grasp_fail_35mm.mp4", icon="▶")
mediabox(s, Cm(22.6), Cm(7.85), Cm(10.4), Cm(4.7), "실패 근접 영상",
         "sim_out/grasp_fail_35mm_closeup.mp4", icon="▶")
notebox(s, [
    "경위: 첫 물리 재생은 큐브를 6cm 로 어림잡아 성공했는데, 실측하니 35mm. 교체하자 전부 실패했고, 그리퍼 개구 갭 실측 로깅·핑거 끝 궤적 기록·큐브 위치 보정까지 동원해 12회에 걸쳐 원인을 좁혔다.",
    "최종 원인은 물리가 아니라 기하: OMX 시연의 접근이 '옆으로 쓸면서 진입'하는 기울어진 동작이라, 닫히기 전에 패들 옆면이 큐브를 불도저처럼 밀어낸다 (그림). 폼(스펀지) 큐브라 실물에선 됐지만 딱딱한 큐브로는 원리적으로 안 된다.",
    "이 삽질의 가치: 원인을 기하학으로 정확히 규명했기에 다음 장의 해법이 나왔고, 실물 어태치먼트에 '접촉면은 연질(TPU/폼)로' 라는 설계 지침도 얻었다.",
    "발표 팁: 이 장은 '문제', 다음 장이 '해결' — 한 호흡으로 설명.",
])
foot(s, "진단 도구: 갭 실측 로깅 · fingertraj npz · fit_cube_position.py")

# ═══════════ 8. 핵심 결정 — 손목 45° 보정 ═══════════
s = slide()
bar(s, "핵심 결정 — 45° 를 하드웨어가 아니라 손목(IK 목표)에서 상쇄", "07 해결")
keyline(s, "번역 규칙에 회전 보정 하나 → 파지 기하 · 특이점 · 실물 장착의 3개 문제를 동시 해결")
# 왼쪽 패널: 보정 전 (45° 기울어 접근)
px1, py1, pw1, ph1 = Cm(0.9), Cm(2.72), Cm(9.8), Cm(6.6)
panel(s, px1, py1, pw1, ph1, "보정 전 — 45° 기울어 접근", RED)
tb1 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px1 + Cm(0.8), py1 + Cm(4.9), Cm(8.2), Cm(0.7))
tb1.fill.solid(); tb1.fill.fore_color.rgb = TAN; tb1.line.fill.background()
c1 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px1 + Cm(4.4), py1 + Cm(4.1), Cm(0.9), Cm(0.9))
c1.fill.solid(); c1.fill.fore_color.rgb = BLUE; c1.line.fill.background()
a1 = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, px1 + Cm(5.4), py1 + Cm(1.3), Cm(1.3), Cm(2.9))
a1.fill.solid(); a1.fill.fore_color.rgb = RED; a1.line.fill.background()
a1.rotation = 45
label(s, px1 + Cm(0.6), py1 + Cm(5.75), Cm(8.6), "✗  옆으로 쓸며 진입 → 파지 실패", 12.5, RED, True)
# 가운데 화살표
arrow(s, Cm(11.0), Cm(5.5), Cm(1.4), Cm(0.8), NAVY)
label(s, Cm(10.15), Cm(6.4), Cm(3.2), "orient_corr()", 10.5, NAVY, True)
# 오른쪽 패널: 보정 후 (수직 하강)
px2, py2, pw2, ph2 = Cm(12.7), Cm(2.72), Cm(9.8), Cm(6.6)
panel(s, px2, py2, pw2, ph2, "보정 후 — 수직 하강 접근", GREEN)
tb2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px2 + Cm(0.8), py2 + Cm(4.9), Cm(8.2), Cm(0.7))
tb2.fill.solid(); tb2.fill.fore_color.rgb = TAN; tb2.line.fill.background()
c2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px2 + Cm(4.4), py2 + Cm(4.1), Cm(0.9), Cm(0.9))
c2.fill.solid(); c2.fill.fore_color.rgb = BLUE; c2.line.fill.background()
a2 = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, px2 + Cm(4.2), py2 + Cm(1.3), Cm(1.3), Cm(2.6))
a2.fill.solid(); a2.fill.fore_color.rgb = GREEN; a2.line.fill.background()
label(s, px2 + Cm(0.6), py2 + Cm(5.7), Cm(8.6), "✔  위에서 똑바로 내려와 잡음 → 즉시 성공", 12.5, GREEN, True)
# 오른쪽: 실물 함의
flowbox(s, Cm(23.1), Cm(2.72), Cm(9.9), Cm(3.1),
        "하드웨어 대안 (기각)\n45° 꺾인 어태치먼트 제작\n→ 설계·프린팅 필요, 실물도 복잡", fill=GREY, size=12.5)
flowbox(s, Cm(23.1), Cm(6.22), Cm(9.9), Cm(3.1),
        "소프트웨어 보정 (채택)\nIK 목표 자세에 회전 하나 곱함\n→ 실물 그리퍼 표준 일자 장착", fill=GREEN, size=12.5)
# 하단 비교 카드
cy = Cm(9.7); cw = Cm(10.4); cg = Cm(0.45)
statcard(s, Cm(0.9), cy, cw, Cm(3.2), "12회 전부 실패", "즉시 성공 · 5.5mm", "35mm 큐브 파지 (놓기 오차)")
statcard(s, Cm(0.9) + cw + cg, cy, cw, Cm(3.2), "10.5° (특이점 코앞)", "49.7°", "손목 특이점 여유 min|q5|")
statcard(s, Cm(0.9) + (cw + cg) * 2, cy, cw, Cm(3.2), "5.1° /fr", "2.9° /fr", "프레임간 최대 관절 변화")
notebox(s, [
    "원리: 시연 데이터의 자세가 45° 기울어 있으니, IK 에 목표를 줄 때 '그 기욺을 상쇄하는 회전'을 곱해 손목이 항상 수직 아래를 보게 만든다. 데이터는 안 건드리고 번역 규칙만 바꾼 것 — 소프트웨어 한 줄이라 되돌리기도 쉽다.",
    "특이점 부수효과가 왜 큰가: 특이점(joint5 = 0° 근처)에선 관절이 조금만 움직여도 손끝이 크게 튀어 제어가 불안정하다. 기울어진 손목 자세가 하필 내내 그 근처였는데, 수직으로 세우니 여유가 10.5°→49.7° 로 벌어졌다. TX90 내내 싸운 특이점 문제가 공짜로 풀림.",
    "하나의 회전 보정이 세 문제(파지 기하 · 특이점 · 실물 장착 단순화)를 동시 해결 — 이번 작업의 최대 수확.",
], y=Cm(13.55), h=Cm(4.5))
foot(s, "산출: m1013_kin.orient_corr() · 재스윕 sweep_result_wrist45.json · 데이터셋 재생성")

# ═══════════ 9. Isaac 물리 검증 ═══════════
s = slide()
bar(s, "STEP 3 — Isaac Sim 물리 재생: 35 mm 큐브 pick & place 성공", "08 물리 검증")
keyline(s, "학습 전에 '번역된 정답 궤적'부터 물리에서 검증 — 마찰·중력·접촉 위에서 실제로 집힌다")
iw = Cm(10.4); gx = Cm(0.9); gy = Cm(2.72)
s.shapes.add_picture(os.path.join(FRAMES, "0230.png"), gx, gy, width=iw)
s.shapes.add_picture(os.path.join(FRAMES, "0330.png"), gx + iw + Cm(0.45), gy, width=iw)
s.shapes.add_picture(os.path.join(FRAMES, "0380.png"), gx + (iw + Cm(0.45)) * 2, gy, width=iw)
caption(s, Cm(0.9), Cm(8.62), Cm(32),
        "정답 관절 궤적의 물리 재생 (에피소드 0) — 왼쪽부터: 수직 하강 파지 · 들어올려 운반 · 목표 지점에 내려놓기")
cy = Cm(9.6); cw = Cm(6.9); cg = Cm(0.5)
bigcard(s, Cm(0.9), cy, cw, Cm(3.2), "5.5 mm", "ep0 놓기 오차", GREEN, 24)
bigcard(s, Cm(0.9) + cw + cg, cy, cw, Cm(3.2), "6 / 8", "일괄 재생 성공 (오차 2.1~10.8mm)", GREEN, 24)
bigcard(s, Cm(0.9) + (cw + cg) * 2, cy, cw, Cm(3.2), "35 mm · 30 g", "실측 큐브 + LEHR 근사 그리퍼", NAVY, 20)
mediabox(s, Cm(23.1), cy, Cm(9.9), Cm(3.2), "성공 영상", "sim_out/replay_35mm_success.mp4", icon="▶")
notebox(s, [
    "이 재생은 학습 전 단계: '번역해 둔 정답 궤적' 자체가 물리적으로 말이 되는지(진짜 집히는지) 확인하는 것. 이게 안 되면 학습해 봤자 소용없으니 학습보다 먼저 했다.",
    "씬은 직접 구성: 공식 m1013.usd + 테이블 + 35mm/30g 큐브 + 실물 후보(SMC LEHR)를 근사한 평행 2핑거 그리퍼. 그리퍼는 실물 확정 시 치수만 바꾸면 된다.",
    "6/8 의 의미: 변환 파이프라인이 대체로 건강하다는 것. 실패 2건(ep80·158)은 궤적별 편차 문제라 파이프라인 자체의 결함이 아니고, 분석 대상으로 남겨 둠.",
    "부수 발견: v5 의 '테이블 높이'는 상판이 아니라 파지 기준점 높이였다 — 씬 기하를 실측 기반으로 다시 세웠다.",
], y=Cm(13.55), h=Cm(4.5))
foot(s, "산출: prep_replay_ep.py · replay_isaac.py · sim_out/replay_ep*_result.json")

# ═══════════ 10. ACT 학습·평가 ═══════════
s = slide()
bar(s, "STEP 4 — ACT 학습·평가: TX90 대비 전 지표 개선", "09 학습")
keyline(s, "TX90 과 완전히 같은 모델·설정으로 학습 — 지표 차이는 순수하게 데이터 품질의 차이")
flowbox(s, Cm(0.9), Cm(2.75), Cm(32.1), Cm(2.2),
        "같은 모델 · 같은 설정 (ACT, 100k 스텝, 2.8시간) — 달라진 것은 데이터 품질뿐", fill=NAVY, size=15)
cy = Cm(5.6); cw = Cm(10.4); cg = Cm(0.45)
statcard(s, Cm(0.9), cy, cw, Cm(3.6), "0.93~1.55° (TX90)", "0.62~0.67°", "open-loop 관절오차 (3개 ep)")
statcard(s, Cm(0.9) + cw + cg, cy, cw, Cm(3.6), "점프 30.5° → 필터 필요 (TX90)", "최대 4.7°", "청크 경계 연속성 — 필터 불요")
statcard(s, Cm(0.9) + (cw + cg) * 2, cy, cw, Cm(3.6), "RViz 시각화까지 (TX90)", "Isaac 물리 실행", "검증 무대")
label(s, Cm(0.9), Cm(9.7), Cm(32.1),
      "개선 원인: 손목 45° 보정 → 특이점에서 먼 부드러운 궤적 → 배우기 쉬운 액션 분포", 15, NAVY, True)
chip(s, Cm(6.4), Cm(11.0), Cm(9.6), "그리퍼 개폐 일치 95.5~99.7%", GREEN, Cm(1.1), 14)
chip(s, Cm(17.0), Cm(11.0), Cm(9.6), "최종 loss 0.054 (TX90 0.052)", GREY, Cm(1.1), 14)
notebox(s, [
    "ACT = 시연을 모방하는 정책 모델. 카메라 2대 영상 + 현재 관절각을 입력받아 다음 100스텝의 관절각 청크를 출력한다. TX90 때와 완전히 같은 구조·설정으로 학습 — 그래서 지표 차이는 순수하게 데이터 품질 차이다.",
    "open-loop 평가 = 녹화된 관측을 입력해 정책 출력을 정답과 비교하는 것. 관절오차 0.6° 는 '시연을 거의 그대로 재현한다'는 뜻.",
    "청크 경계 점프가 사라진 것이 실기 관점에서 제일 반갑다: TX90 때는 청크가 바뀌는 순간 관절이 30° 튀는 경우가 있어 안전 필터가 필수였는데, 여기선 최대 4.7° 라 자연스럽게 이어진다.",
], y=Cm(13.55), h=Cm(4.5))
foot(s, "산출: 체크포인트 /root/train_m1013_act_v6 · eval_m1013_v6.py")

# ═══════════ 11. 최종 결과 — 정책 물리 실행 ═══════════
s = slide()
bar(s, "최종 결과 — 정책이 만든 궤적이 물리 시뮬레이션에서 과제 완수", "10 결과")
keyline(s, "실물 시연 수집부터 물리 실행까지 전 체인이 시뮬레이션 안에서 닫혔다 — 로봇 도착 전 리스크 소진")
y1 = Cm(2.85); h = Cm(2.6); w = Cm(6.2); gap = Cm(0.5)
chain = [
    ("OMX 시연\n(실물 데모 159개)", GREY),
    ("M1013 관절 데이터셋\n(오프라인 번역)", GREEN),
    ("ACT 정책\n(모방학습 100k)", GREEN),
    ("예측 궤적\n(open-loop 추론)", GREEN),
    ("Isaac 물리 실행\n집기→운반→놓기 ✔", NAVY),
]
x = Cm(0.9)
for i, (txt, c) in enumerate(chain):
    flowbox(s, x, y1, w, h, txt, fill=c, size=12.5)
    if i < len(chain) - 1:
        arrow(s, x + w + Cm(0.02), y1 + h / 2 - Cm(0.25), Cm(0.45))
    x += w + gap
bigcard(s, Cm(0.9), Cm(6.3), Cm(10.4), Cm(4.4), "7.8 mm", "정책 궤적의 놓기 오차\n(정답 재생 5.5mm 와 근접)", NAVY, 30)
flowbox(s, Cm(11.9), Cm(6.3), Cm(10.4), Cm(4.4),
        "전 체인 시뮬 검증 완료\n로봇 도착 전에 궤적·정책 층의\n리스크를 미리 소진\n남은 미지수 = 실기 층 (시각 갭·그리퍼)",
        fill=GREEN, size=13.5)
mediabox(s, Cm(23.1), Cm(6.3), Cm(9.9), Cm(4.4), "정책 실행 영상",
         "정책 궤적 물리 재생 (--pred-npz)", icon="▶")
notebox(s, [
    "'정답 재생'과 '정책 재생'의 차이: 앞 장(STEP 3)은 번역해 둔 정답 궤적을 트는 것이고, 이 장은 학습된 신경망이 스스로 만들어 낸 궤적을 트는 것. 후자가 되어야 '학습이 됐다'고 말할 수 있다.",
    "숫자 감각: 7.8mm 는 35mm 큐브를 목표 지점에 놓는 오차로는 충분히 작다 (큐브 한 변의 1/4 이하). 정답 재생(5.5mm)과의 차이 2.3mm 가 '학습이 더한 오차'다.",
    "아직 open-loop: 정책이 보는 관측은 녹화본이라, 실행 중 큐브를 옮겨도 모른다. 실시간 카메라 관측으로 도는 closed-loop 가 다음 단계 (다다음 장).",
], y=Cm(13.55), h=Cm(4.5))
foot(s, "산출: /root/policy_rollouts/ep000_pred_m1013v6.npz · replay_isaac.py --pred-npz")

# ═══════════ 12. 진행 계획 — 전체 로드맵 ═══════════
s = slide()
bar(s, "진행 계획 — 전체 로드맵", "11 로드맵")
keyline(s, "시뮬 트랙(A)과 실기 준비(B)는 병렬 진행 — 로봇 도착이라는 외부 일정에 묶이는 것은 C 뿐")
y1 = Cm(3.0); h = Cm(2.4); w = Cm(5.1); ov = Cm(0.6)
mile = [
    ("TX90 방법론", "확립", "8/12~14", GREEN),
    ("M1013 전환", "결정", "8/20", GREEN),
    ("시뮬 파이프", "라인 완주", "8/20", GREEN),
    ("산출물", "재확인", "8/21~ (진행 중)", AMBER),
    ("closed-loop", "(시뮬)", "이번 주~ (다음)", RED),
    ("실기 준비", "그리퍼·TCP", "병행", GREY),
    ("로봇 도착", "v7·실기", "9월 중하순~", GREY),
]
x = Cm(0.9)
for i, (l1, l2, dt, c) in enumerate(mile):
    b = s.shapes.add_shape(MSO_SHAPE.CHEVRON, x, y1, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = c
    b.line.color.rgb = WHITE; b.line.width = Pt(1.5)
    tf = b.text_frame; tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Cm(0.5); tf.margin_right = Cm(0.05)
    for j, line in enumerate((l1, l2)):
        p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = line
        _set(run, 11.5, True, WHITE)
    label(s, x + Cm(0.4), y1 + h + Cm(0.08), w - Cm(0.4), dt, 10.5, GREY, False)
    x += w - ov
lg = [("완료", GREEN), ("진행 중", AMBER), ("다음", RED), ("예정", GREY)]
lx = Cm(0.9)
for txt, c in lg:
    chip(s, lx, Cm(6.6), Cm(3.2), txt, c, Cm(0.8), 12)
    lx += Cm(3.6)
flowbox(s, Cm(19.3), Cm(6.5), Cm(13.7), Cm(1.0),
        "최종 목표: 실기 closed-loop — \"큐브를 옮기면 따라온다\"", fill=NAVY, size=13)
y2 = Cm(8.4)
flowbox(s, Cm(0.9), y2, Cm(10.4), Cm(3.6),
        "트랙 A — closed-loop (시뮬)\n손목캠·정면캠 구도 정합\n→ 실시간 관측 제어 → 도메인 갭 측정\n→ (조건부) 혼합학습 A/B", fill=NAVY, size=12.5)
flowbox(s, Cm(11.75), y2, Cm(10.4), Cm(3.6),
        "트랙 B — 실기 준비 (병행)\n그리퍼 확정 → TCP 실측\n→ 재변환 1분 + 재학습 3시간\n→ 어태치먼트 (일자+연질 팁) 설계", fill=GREEN, size=12.5)
flowbox(s, Cm(22.6), y2, Cm(10.4), Cm(3.6),
        "트랙 C — 로봇 도착 후\ndsr ROS2 연동 → v6 궤적 자동 실행\n하며 실기 카메라·엔코더 30~50ep 수집\n→ 이어학습 (v7) → 실기 closed-loop", fill=GREY, size=12.5)
notebox(s, [
    "위 화살표(시간 순서): 초록까지가 지난 열흘, 노랑이 지금(어제 작업 재확인), 빨강이 이번 주, 회색이 로봇 도착 전후. 아래 세 상자는 앞으로의 세 트랙 — A 와 B 는 서로 독립이라 병렬 진행, C 만 로봇 도착이라는 외부 일정에 묶인다.",
    "closed-loop 가 왜 다음인가: 지금 정책의 눈(카메라 영상)은 OMX 리그를 찍은 녹화본이다. 시뮬 카메라를 원본과 같은 구도로 달고 그 렌더를 입력하면, '다른 장면을 봐도 동작이 유지되는가(시각 도메인 갭)'를 로봇 없이 측정할 수 있다.",
    "v7 의 요점: 실기에서 사람이 새로 시연하는 게 아니라, 검증된 궤적을 로봇이 자동 실행하는 동안 실기 카메라·엔코더를 녹화해 이어학습 — 새로 배울 것은 '화면 해석'뿐이라 30~50개면 충분하다고 보는 근거.",
], y=Cm(13.55), h=Cm(4.5))
foot(s, "OMX→M1013 전이 · 랩미팅 2026-08-24")

# ═══════════ 13. 논의 사항 ═══════════
s = slide()
bar(s, "논의드리고 싶은 것", "12 논의")
keyline(s, "우선순위 1순위는 ① 그리퍼 확정 — 나머지는 그와 무관하게 병렬 진행 가능")
cw2 = Cm(15.8); ch2 = Cm(4.9); gx2 = Cm(0.9); gy2 = Cm(2.75); gg = Cm(0.5)


def qcard(s, x, y, num, title, sub):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, cw2, ch2)
    b.fill.solid(); b.fill.fore_color.rgb = WHITE
    b.line.color.rgb = NAVY; b.line.width = Pt(1.75)
    tf = b.text_frame; tf.word_wrap = True
    tf.margin_left = Cm(0.5); tf.margin_right = Cm(0.4); tf.margin_top = Cm(0.35)
    p = tf.paragraphs[0]
    run = p.add_run(); run.text = num + "  " + title
    _set(run, 16.5, True, NAVY)
    for line in sub.split("\n"):
        p = tf.add_paragraph(); p.space_before = Pt(5)
        run = p.add_run(); run.text = line
        _set(run, 12.5, False, INK)
    return b


qcard(s, gx2, gy2, "①", "그리퍼 확정 — SMC LEHR 로 진행?",
      "확정 → TCP 실측 → 재변환 1분 + 재학습 3시간\n어태치먼트 (일자 + 연질 팁) 설계 착수 가능\n두산 연동은 RS485(Modbus) 결선 — 선례 있음")
qcard(s, gx2 + cw2 + gg, gy2, "②", "실물 작업대 — 시뮬 확정값 기준 준비?",
      "로봇 기준 오프셋 (+0.05, −0.15, +0.10) m\n테이블 상판 높이 가정 포함\n실물 설치 시 실측 후 갱신 (재변환 1분)")
qcard(s, gx2, gy2 + ch2 + gg, "③", "closed-loop(시뮬) 우선순위 확인",
      "카메라 구도 정합부터 착수 예정\n시각 도메인 갭 측정 결과가\nv7 수집 규모 (30~50ep 충분 여부) 를 결정")
qcard(s, gx2 + cw2 + gg, gy2 + ch2 + gg, "④", "M1013 도착 일정·설치 환경 공유 요청",
      "PC (PREEMPT_RT) · 카메라 마운트 등\n사전 준비 목록화\n도착일 역산으로 실기 주차 계획 수립")
notebox(s, [
    "우선순위가 가장 높은 것은 ① — 그리퍼가 확정되어야 TCP·어태치먼트·시뮬 그리퍼 치수가 전부 확정되고, 나머지는 그와 무관하게 병렬 진행 가능하다.",
    "④ 는 정보 요청: 도착일이 잡히면 역산해서 실기 주차 계획(dsr 연동 → 궤적 자동 실행 → v7 수집)을 세울 수 있다.",
], y=Cm(13.3), h=Cm(3.2))
foot(s, "OMX→M1013 전이 · 랩미팅 2026-08-24 · 이채원")

out = os.path.join(OUTDIR, "랩미팅_20260824.pptx")
prs.save(out)
print("저장:", out)

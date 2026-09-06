#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-09-06 랩미팅 PPT — 그리퍼 이관 하드웨어: 설계 · 검증 · 발주.

  python make_labmeeting_pptx_0906.py
  → 대화록 및 PPT/랩미팅/랩미팅_20260906.pptx

CAD 라인아트(회색 면 + 검은 특징선)는 img_0906/ 에 사전 렌더된 PNG 사용.
슬라이드 본문은 최소화하고 설명 대본은 PowerPoint 발표자 노트에 넣었다.
"""

import os
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Pt

NAVY  = RGBColor(0x2F, 0x3D, 0x9E)
INK   = RGBColor(0x15, 0x18, 0x1D)
GREY  = RGBColor(0x62, 0x6B, 0x78)
LINE  = RGBColor(0xD8, 0xDC, 0xE3)
RED   = RGBColor(0xA9, 0x33, 0x1D)
GREEN = RGBColor(0x1F, 0x6B, 0x4A)
AMBER = RGBColor(0x9A, 0x6A, 0x00)
BGSOFT= RGBColor(0xED, 0xEF, 0xF3)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT, MONO = "맑은 고딕", "Consolas"
SW, SH = Cm(33.867), Cm(19.05)

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "대화록 및 PPT")
IMG  = os.path.join(DOCS, "img_0906")
SIM  = os.path.join(BASE, "sim_out")
OUT  = os.path.join(DOCS, "랩미팅", "랩미팅_20260906.pptx")

prs = Presentation(); prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]


def _set(run, size=14, bold=False, color=INK, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {}); rPr.append(el)
        el.set("typeface", font)


def slide(title=None, step=None):
    s = prs.slides.add_slide(BLANK)
    if title:
        r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Cm(1.75))
        r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background()
        r.shadow.inherit = False
        tf = r.text_frame; tf.margin_left = Cm(0.95); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; run = p.add_run(); run.text = title
        _set(run, 19, True, WHITE)
        if step:
            tb = tbox(s, SW - Cm(9.4), Cm(0.42), Cm(8.5), Cm(0.95))
            p = tb.paragraphs[0]; p.alignment = PP_ALIGN.RIGHT
            run = p.add_run(); run.text = step
            _set(run, 12, False, RGBColor(0xC5, 0xCC, 0xF2))
    return s


def tbox(s, x, y, w, h):
    b = s.shapes.add_textbox(x, y, w, h)
    tf = b.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def txt(s, x, y, w, h, lines, size=13.5, gap=5):
    """lines: [(문자열, {size,bold,color,mono,bullet})]"""
    tf = tbox(s, x, y, w, h)
    for i, item in enumerate(lines):
        t, o = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(0 if i == 0 else o.get("gap", gap))
        p.line_spacing = o.get("ls", 1.18)
        run = p.add_run(); run.text = t
        _set(run, o.get("size", size), o.get("bold", False),
             o.get("color", INK), MONO if o.get("mono") else FONT)
    return tf


def panel(s, x, y, w, h, fill=None, border=LINE, width=1.0):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = fill or WHITE
    b.line.color.rgb = border; b.line.width = Pt(width)
    b.shadow.inherit = False
    b.adjustments[0] = 0.03
    b.text_frame.text = ""
    return b


def head(s, x, y, w, t, color=NAVY, size=14):
    txt(s, x, y, w, Cm(0.8), [(t, {"size": size, "bold": True, "color": color})])


def table(s, x, y, w, rows, widths=None, size=12, rh=Cm(0.78), header=True):
    shp = s.shapes.add_table(len(rows), len(rows[0]), x, y, w, rh * len(rows))
    t = shp.table
    if widths:
        tot = sum(widths)
        for i, cw in enumerate(widths):
            t.columns[i].width = int(w * cw / tot)
    for ri, row in enumerate(rows):
        t.rows[ri].height = rh
        for ci, cell in enumerate(row):
            c = t.cell(ri, ci)
            c.margin_left = c.margin_right = Cm(0.18)
            c.margin_top = c.margin_bottom = Cm(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            s_, o = (cell, {}) if isinstance(cell, str) else cell
            c.fill.solid()
            c.fill.fore_color.rgb = (NAVY if (header and ri == 0)
                                     else o.get("bg", WHITE if ri % 2 else BGSOFT))
            p = c.text_frame.paragraphs[0]
            p.alignment = o.get("align", PP_ALIGN.LEFT)
            run = p.add_run(); run.text = s_
            _set(run, o.get("size", size), o.get("bold", header and ri == 0),
                 WHITE if (header and ri == 0) else o.get("color", INK),
                 MONO if o.get("mono") else FONT)
    return t


def pic(s, path, x, y, maxw, maxh, caption=None):
    im = Image.open(path); ar = im.width / im.height
    w, h = maxw, int(maxw / ar)
    if h > maxh:
        h, w = maxh, int(maxh * ar)
    left = int(x + (maxw - w) / 2); top = int(y + (maxh - h) / 2)
    s.shapes.add_picture(path, left, top, width=w, height=h)
    if caption:
        tf = tbox(s, x, y + maxh + Cm(0.08), maxw, Cm(0.6))
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = caption
        _set(run, 11, False, GREY)


def foot(s, t):
    tf = tbox(s, Cm(1.0), SH - Cm(0.82), SW - Cm(2.0), Cm(0.6))
    p = tf.paragraphs[0]; run = p.add_run(); run.text = t
    _set(run, 10, False, GREY)


def note(s, t):
    s.notes_slide.notes_text_frame.text = t


def chip(s, x, y, w, t, fill=GREEN, h=Cm(0.92), size=12.5):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = fill
    b.line.fill.background(); b.shadow.inherit = False
    tf = b.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = t
    _set(run, size, True, WHITE)


M = Cm(1.0)                      # 좌우 여백
CW = SW - 2 * M                  # 본문 폭
TOP = Cm(2.35)                   # 제목바 아래

# ═════════════════════════ 1. 표지 ═════════════════════════
s = slide()
r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Cm(6.6))
r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background(); r.shadow.inherit = False
txt(s, M, Cm(1.55), Cm(24), Cm(4),
    [("그리퍼 이관 하드웨어", {"size": 34, "bold": True, "color": WHITE}),
     ("설계 · 검증 · 발주", {"size": 20, "color": RGBColor(0xC5, 0xCC, 0xF2), "gap": 8}),
     ("SMC MHF2-16D2  →  두산 M1013 연결 금구", {"size": 14, "color": RGBColor(0xB9, 0xC2, 0xF0), "gap": 10})])
pic(s, os.path.join(IMG, "r_assembly.png"), Cm(19.5), Cm(7.0), Cm(13.5), Cm(9.6))
txt(s, M, Cm(7.6), Cm(17.5), Cm(9),
    [("이번 세션 요약", {"size": 15, "bold": True, "color": NAVY}),
     ("· 연결 금구 4종 설계 완료 — 어댑터 · 핑거 좌우 · 밸브 브래킷 · 손목캠 브래킷", {"gap": 9}),
     ("· 발주 직전 전수 검증에서 오류 7건 발견 · 전부 정정", {}),
     ("· 어댑터 · 핑거 발주 가능 상태", {"bold": True, "color": GREEN}),
     ("· Isaac 손목캠 정합은 미완 — TCP 반영 후 재정합 필요", {"bold": True, "color": AMBER})])
txt(s, M, Cm(17.2), Cm(20), Cm(1.2), [("2026-09-06 랩미팅", {"size": 12, "color": GREY})])
note(s, "그리퍼를 M1013으로 옮기기 위한 연결 금구 설계와, 발주 직전 검증에서 잡은 오류를 보고합니다. "
        "결론부터 말하면 어댑터와 핑거는 발주 가능하고, Isaac 손목캠 정합만 아직 미완입니다.")

# ═════════════════════════ 2. 배경 ═════════════════════════
s = slide("왜 만드는가 — 부품은 전부 재사용, 연결부만 새로 만든다", "1 / 배경")
panel(s, M, TOP, Cm(15.6), Cm(6.2), BGSOFT)
head(s, M + Cm(0.6), TOP + Cm(0.45), Cm(14), "보유 자산을 그대로 쓴다")
txt(s, M + Cm(0.6), TOP + Cm(1.5), Cm(14.4), Cm(4.4),
    [("· 그리퍼 SMC MHF2-16D2 · 밸브 SY5120 · 콤프 PL-10ST", {}),
     ("  레귤레이터 AW20 · 오토스위치 D-M9N ×2  — 전부 보유", {"color": GREY, "size": 12.5}),
     ("· TX90 에서 쓰던 구성을 그대로 M1013 으로 이관", {"gap": 8}),
     ("· 새로 제작하는 것은 연결 금구뿐", {"bold": True, "color": NAVY, "gap": 8})])
panel(s, M + Cm(16.4), TOP, Cm(15.5), Cm(6.2))
head(s, M + Cm(17.0), TOP + Cm(0.45), Cm(14), "그런데 그냥 못 붙는다", RED)
txt(s, M + Cm(17.0), TOP + Cm(1.5), Cm(14.3), Cm(4.4),
    [("· M1013 툴 플랜지 = ISO 9409-1-50-4-M6  (PCD 50 · 4-M6)", {}),
     ("· 그리퍼 배면 = 4-M5 (±18, ±54) + Ø4 위치결정", {"gap": 6}),
     ("→ 볼트 규격 · 피치 · 센터링 방식이 전부 다름", {"bold": True, "color": RED, "gap": 8}),
     ("· TX90 은 J6 까지 내장 에어가 왔지만 M1013 은 없음", {"gap": 8}),
     ("→ 밸브를 팔이 아니라 툴단에 올린다", {"bold": True, "color": NAVY})])
table(s, M, TOP + Cm(7.0), CW,
      [["설계한 부품", "재질", "질량", "역할", "상태"],
       ["어댑터 플레이트", "AL6061-T6", "295.9 g", "M1013 플랜지 ↔ 그리퍼 배면 변환 · 배선 통로", ("발주 가능", {"color": GREEN, "bold": True})],
       ["핑거 어태치먼트 ×2", "AL6061-T6", "54.9 g/개", "35 mm 폼 큐브 파지면 · 닫힘 갭 33.5 결정", ("발주 가능", {"color": GREEN, "bold": True})],
       ["밸브 브래킷", "PETG", "19 g", "SY5120 을 그리퍼 측면에 고정", ("출력 가능", {"color": GREEN, "bold": True})],
       ["손목캠 브래킷", "PETG", "13.2 g", "손목 카메라 마운트", ("재정합 대기", {"color": AMBER, "bold": True})]],
      widths=[3.4, 2.2, 1.8, 8.2, 2.4], rh=Cm(0.86))
foot(s, "치수 출처 — 두산 설치매뉴얼 v1.7 p.36 (플랜지) / SMC MHF2-16D2 실물 STEP·6면도 (그리퍼)")
note(s, "그리퍼·밸브·콤프는 전부 연구실 보유품이라 새로 살 게 없습니다. 문제는 로봇이 바뀌면서 "
        "플랜지 볼트 패턴이 완전히 달라졌다는 것이고, 그래서 변환 금구가 필요합니다. "
        "추가로 TX90은 팔 안으로 에어가 J6까지 왔는데 M1013은 그게 없어서, 밸브를 툴 끝에 올리기로 했습니다. "
        "그러면 손목을 통과하는 호스가 1가닥이고 응답도 빠릅니다.")

# ═════════════════════════ 3. 어댑터 ═════════════════════════
s = slide("어댑터 — 형상이 이렇게 된 이유 3가지", "2 / 설계")
pic(s, os.path.join(IMG, "r_adapter_robot.png"), M, TOP + Cm(0.3), Cm(15.4), Cm(5.0),
    "로봇 쪽 면 — Ø31.5 h7 스피곳(돌출 4) + Ø20 관통")
pic(s, os.path.join(IMG, "r_adapter_grip.png"), M + Cm(16.2), TOP + Cm(0.3), Cm(15.4), Cm(5.0),
    "그리퍼 쪽 면 — Ø11 카운터보어 ×4 · 다월 Ø4 ×2")
Y = TOP + Cm(6.6)
for i, (t, b, c) in enumerate([
    ("① 스피곳이 튀어나온 이유",
     "플랜지 도면을 다시 읽으니 Ø31.5 는 구멍이고 Ø63 이 보스였다.\n"
     "처음엔 반대로 알고 어댑터에 보어를 팠었다 → 스피곳(돌출)으로 정정.", NAVY),
    ("② 카운터보어가 그리퍼 쪽인 이유",
     "M6 볼트 머리가 그리퍼에 완전히 덮인다. 그래서 그리퍼 쪽 면에서 파고,\n"
     "조립 순서가 「어댑터 → 로봇」 이 먼저로 강제된다.", NAVY),
    ("③ M5 를 바깥(±54)으로 뺀 이유",
     "그리퍼 배면 안쪽 M5(±18)의 홀 가장자리가 스피곳 반경을 0.5 mm 침범.\n"
     "→ 바깥 M5 2개 + 다월 2개(±65) 구성으로 변경. 볼트 베이스라인 36 → 108.", NAVY)]):
    x = M + i * Cm(10.65)
    panel(s, x, Y, Cm(10.2), Cm(4.5))
    head(s, x + Cm(0.5), Y + Cm(0.35), Cm(9.2), t, c, 13)
    txt(s, x + Cm(0.5), Y + Cm(1.35), Cm(9.2), Cm(3.0), [(b, {"size": 12, "ls": 1.3})])
txt(s, M, Y + Cm(4.8), CW, Cm(0.9),
    [("Ø20 중앙 관통 — 튜브·배선이 J6 축과 동축으로 지나가는 통로. 회전이 「감김」이 아니라 「비틀림」이 된다.",
      {"size": 13, "bold": True, "color": NAVY})])
foot(s, "AL6061-T6 · 140 × 70 × 12 · R8 · 착좌면 평면도 0.05 (Ø31.5~Ø63 환형부)")
note(s, "어댑터에서 설명할 건 세 가지입니다. 첫째, 스피곳이 왜 튀어나왔는가 — 처음엔 플랜지 중앙 Ø31.5가 "
        "보스인 줄 알고 어댑터에 구멍을 팠는데, 매뉴얼 도면을 직접 보니 Ø31.5가 구멍이고 Ø63이 보스였습니다. "
        "둘째, 카운터보어가 그리퍼 쪽인 이유는 M6 머리가 그리퍼에 덮이기 때문이고, 이 때문에 조립 순서가 강제됩니다. "
        "셋째, 그리퍼 배면 안쪽 M5를 쓰려니 스피곳과 0.5mm 겹쳐서, 바깥 M5와 다월 조합으로 바꿨습니다.")

# ═════════════════════════ 4. 핑거 ═════════════════════════
s = slide("핑거 — 닫힘 갭 33.5 가 전부, 그런데 하드 스톱이 없다", "3 / 설계")
pic(s, os.path.join(IMG, "r_fingers_closed.png"), M, TOP + Cm(0.2), Cm(14.2), Cm(3.7),
    "완전 닫힘 — 조 안쪽면 간격 33.50 mm (35 mm 큐브를 1.5 mm 압착)")
pic(s, os.path.join(IMG, "r_fingers_open.png"), M, TOP + Cm(4.9), Cm(14.2), Cm(3.7),
    "완전 열림 — 편측 32 mm 이동, 간격 97.50 mm (큐브 여유 62.5 mm)")
X = M + Cm(15.2)
panel(s, X, TOP + Cm(0.2), Cm(16.7), Cm(4.0), BGSOFT)
head(s, X + Cm(0.6), TOP + Cm(0.55), Cm(15), "설계 원칙 — 금속이 갭을 정하고 TPU 는 마찰만")
txt(s, X + Cm(0.6), TOP + Cm(1.55), Cm(15.5), Cm(2.4),
    [("· 닫힘 갭 33.50 = 35 mm 폼 큐브를 1.5 mm 압착", {}),
     ("· TPU 라이너는 1 mm 홈에 면일치로 삽입 → 갭에 영향 없음", {"gap": 6}),
     ("→ 라이너 두께가 바뀌어도 파지 기하가 흔들리지 않는다", {"bold": True, "color": NAVY, "gap": 6})])
panel(s, X, TOP + Cm(4.5), Cm(16.7), Cm(4.3), None, RED, 1.75)
head(s, X + Cm(0.6), TOP + Cm(4.85), Cm(15), "⚠ 하드 스톱이 없다 — 큐브가 유일한 스톱", RED)
txt(s, X + Cm(0.6), TOP + Cm(5.85), Cm(15.5), Cm(2.6),
    [("좌우 조가 33.5 mm 떨어져 있어 서로 닿지 않는다.", {}),
     ("실린더 힘이 그대로 폼에 들어가므로 압력이 실질적 통제 수단.", {"gap": 5}),
     ("0.5 MPa → 90 N   /   0.2 MPa → 36 N   /   0.1 MPa → 18 N",
      {"mono": True, "bold": True, "color": RED, "size": 13, "gap": 7})])
chip(s, X, TOP + Cm(9.1), Cm(16.7), "M5 스피드컨트롤러 2개가 구매 최우선 — 없으면 90 N 으로 수십 ms 만에 닫혀 큐브를 튕겨낸다", RED, Cm(1.0), 12.5)
txt(s, M, TOP + Cm(9.35), Cm(14.2), Cm(1.6),
    [("스트로크 편측 32 (전체 64) · 위치결정 립 39.40 으로 블록 바깥면에 밀착",
      {"size": 12, "color": GREY}),
     ("M4 체결 6.70 / 32.70 · 폭 ±10 — 전부 SMC 실물 CAD 실측", {"size": 12, "color": GREY, "gap": 4})])
foot(s, "AL6061-T6 · 마운트 판 43 × 27 × t8 · 조 폭 30 · 블록 밑면에서 38 돌출 · 좌우 미러 형상")
note(s, "핑거에서 제일 중요한 건 닫힘 갭 33.5mm입니다. 35mm 큐브를 1.5mm 압착하도록 잡았습니다. "
        "설계 원칙은 금속 조 면이 갭을 결정하고 TPU는 마찰만 담당한다는 것 — 라이너를 갈아도 파지 기하가 안 변합니다. "
        "주의할 점은 하드 스톱이 없다는 겁니다. 좌우 조가 서로 안 닿아서 큐브가 유일한 스토퍼이고, "
        "0.5MPa면 90N이 그대로 폼에 들어갑니다. 그래서 스피드컨트롤러가 없으면 배관하면 안 됩니다.")

# ═════════════════════════ 5. 조립 스택 ═════════════════════════
s = slide("조립 스택 — 플랜지 면에서 TCP 83 mm", "4 / 설계")
pic(s, os.path.join(IMG, "r_assembly_side.png"), M, TOP + Cm(0.3), Cm(16.4), Cm(8.4),
    "툴 어셈블리 측면 — 위=로봇 플랜지, 아래=조 끝 (TCP)")
X = M + Cm(17.4)
table(s, X, TOP + Cm(0.4), Cm(14.5),
      [["구간", "플랜지 기준 Z", "비고"],
       ["스피곳", "−4 ~ 0", "플랜지 Ø31.5 보어 안으로"],
       ["어댑터", "0 ~ 12", "AL6061-T6, t12"],
       ["그리퍼 몸체", "12 ~ 40.3", "MHF2-16D2"],
       ["핑거 블록", "40.3 ~ 45", "몸체 아래 4.70 돌출"],
       ["핑거 판 + 조", "45 ~ 83", "조가 블록 밑면에서 38"]],
      widths=[3.0, 3.2, 5.6], rh=Cm(0.82))
Y = TOP + Cm(5.9)
for i, (big, sub, col) in enumerate([("83.00 mm", "TCP (플랜지면 → 조 끝)", NAVY),
                                     ("1.22 kg", "툴 질량", NAVY),
                                     ("33.50 mm", "닫힘 갭", GREEN)]):
    x = X + i * Cm(4.95)
    panel(s, x, Y, Cm(4.6), Cm(2.5), None, col, 1.5)
    txt(s, x + Cm(0.2), Y + Cm(0.35), Cm(4.2), Cm(1.0),
        [(big, {"size": 19, "bold": True, "color": col, "ls": 1.0})])
    tf = tbox(s, x + Cm(0.2), Y + Cm(1.55), Cm(4.2), Cm(0.8))
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = sub; _set(run, 10.5, False, GREY)
    tf2 = s.shapes[-2].text_frame
panel(s, X, Y + Cm(3.0), Cm(14.5), Cm(2.6), None, AMBER, 1.5)
head(s, X + Cm(0.55), Y + Cm(3.3), Cm(13), "⚠ 현재 학습 규약과 어긋난다", AMBER)
txt(s, X + Cm(0.55), Y + Cm(4.2), Cm(13.4), Cm(1.4),
    [("convert_v6_m1013.py 의 TCP = 0.12 → 플랜지-큐브 258.8 mm", {"size": 12, "mono": True}),
     ("실물은 83 mm. 이대로 실기에 올리면 핑거 끝이 큐브보다 175.8 mm 위에 뜬다.",
      {"size": 12, "bold": True, "color": RED, "gap": 4})])
foot(s, "툴 무게중심 (플랜지 기준) X −0.8 / Y +3.6 / Z +25.1 mm · J6 실사용 가동폭 81.8° (159 에피소드 전수 실측)")
note(s, "조립하면 플랜지 면에서 조 끝까지 83mm가 나옵니다. 그런데 지금 학습 데이터 변환 규약은 TCP를 0.12m로 "
        "잡고 있어서 플랜지에서 큐브까지가 258.8mm입니다. 이 차이 175.8mm를 안 고치고 실기에 올리면 "
        "핑거가 큐브 한참 위에서 허공을 잡습니다. 재변환이 모든 후속 작업의 선행 조건입니다.")

# ═════════════════════════ 6. 검증 방법 ═════════════════════════
s = slide("검증 — 문서를 믿지 않고 원본 CAD·도면만 읽었다", "5 / 검증")
panel(s, M, TOP, CW, Cm(2.2), BGSOFT)
txt(s, M + Cm(0.7), TOP + Cm(0.45), CW - Cm(1.4), Cm(1.4),
    [("“요약 · 사진 · 설계 의도에서 추론한 것은 전부 틀렸고, 원본 도면 · CAD · 코드를 직접 읽은 것은 전부 맞았다”",
      {"size": 14.5, "bold": True, "color": NAVY}),
     ("— 지난 세션이 스스로 남긴 교훈. 이번에는 그 세션의 설계 문서까지 2차 자료로 취급하고 전부 다시 뽑았다.",
      {"size": 12.5, "color": GREY, "gap": 6})])
table(s, M, TOP + Cm(2.9), CW,
      [["원본 자료", "읽는 방법", "이렇게 확인한 것"],
       ["STL", "바이너리 파싱 → 삼각형 정점 좌표 직접 계측", "핑거 전 치수 · 닫힘 갭 33.500 · M4 위치 6.700/32.700"],
       ["STEP", "CIRCLE · CYLINDRICAL_SURFACE 추출 + 축 방향별 분류", "어댑터 전 피처 · 그리퍼 배면/측면 나사 위치"],
       ["DXF", "DIMENSION 이 분해돼 있어 도형 좌표에서 역산", "다월 위치 · 핑거 블록 길이 39.40 · 탭 깊이 주기"],
       ["PDF 도면", "벡터 없음(래스터) → 900 DPI 렌더 후 픽셀 계측", "플랜지 보어 깊이 6.4 · 보스 6.5 · 커넥터 위치"]],
      widths=[2.0, 8.0, 9.0], rh=Cm(0.92))
Y = TOP + Cm(7.7)
panel(s, M, Y, Cm(15.6), Cm(3.4), None, GREEN, 1.5)
head(s, M + Cm(0.6), Y + Cm(0.35), Cm(14), "픽셀 계측 스케일 검산", GREEN)
txt(s, M + Cm(0.6), Y + Cm(1.3), Cm(14.4), Cm(1.9),
    [("Ø31.5 한 쌍으로 스케일 산출 → 13.397 px/mm", {"mono": True, "size": 12}),
     ("검산: Ø63 = 63.00 mm   (오차 0.00)", {"mono": True, "size": 12, "bold": True, "color": GREEN, "gap": 4})])
panel(s, M + Cm(16.4), Y, Cm(15.5), Cm(3.4), None, LINE)
head(s, M + Cm(17.0), Y + Cm(0.35), Cm(14), "검증 범위")
txt(s, M + Cm(17.0), Y + Cm(1.3), Cm(14.3), Cm(1.9),
    [("체결 6조인트 · 구멍 정합 7건 · 간섭 6건 · 공압/전기 체인 전 구간", {"size": 12.5}),
     ("모든 수치를 상대 부품 원본과 1:1 대조", {"size": 12.5, "color": GREY, "gap": 4})])
foot(s, "검증 스크립트는 재실행 가능 — 부품이 바뀌면 같은 방법으로 다시 검산할 수 있다")
note(s, "검증 원칙을 먼저 말씀드립니다. 지난 세션 문서가 스스로 '추론한 건 다 틀렸고 원본 읽은 건 다 맞았다'고 "
        "적어놨는데, 이번엔 그 문서마저 2차 자료로 보고 전부 원본에서 다시 뽑았습니다. "
        "특히 두산 매뉴얼 도면은 벡터가 아니라 이미지라서, 900DPI로 렌더해서 픽셀로 쟀습니다. "
        "기지 치수로 스케일을 교정하고 검산했더니 오차 0.00이 나와서 신뢰할 수 있는 값입니다.")

# ═════════════════════════ 7. 오류 7건 ═════════════════════════
s = slide("발주 직전 검증에서 오류 7건 — 전부 정정 완료", "6 / 검증")
table(s, M, TOP, CW,
      [["#", "항목", "잘못된 값", "사실", "그대로 발주했다면"],
       ["1", "DXF Φ6 핀홀", "도면에 “리머 가공” 지시 잔존", "발주서·STEP 은 “가공 말 것”",
        ("착좌면에 불필요한 리머홀", {"color": RED})],
       ["2", "로봇 체결 볼트", "M6×12 + 와셔 t1", "M6×10 무와셔",
        ("머리 0.5 mm 돌출 → 그리퍼 밀착 불가", {"color": RED, "bold": True})],
       ["3", "핑거 체결 볼트", "M4×8", "M4×6",
        ("물림 4.5 > 탭 4.0 → 바닥 침", {"color": RED, "bold": True})],
       ["4", "밸브 체결 볼트", "M3×8", "M3×6 접시머리",
        ("물림 4.0 > 탭 3.5 → 바닥 침", {"color": RED})],
       ["5", "다월 위치", "±63.75", "±65.0",
        ("핀이 그리퍼 배면을 찔러 밀착 불가", {"color": RED, "bold": True})],
       ["6", "밸브 브래킷", "M3 구멍 있다고 가정", "구멍 자체가 없었음",
        ("밸브를 고정할 방법 없음", {"color": RED})],
       ["7", "와셔 규격", "“Φ6 평와셔 t1”", "표준 외경 Ø12 > 카운터보어 Ø11",
        ("애초에 안 들어감", {"color": RED})]],
      widths=[0.7, 3.6, 5.4, 5.4, 6.9], rh=Cm(0.9))
panel(s, M, TOP + Cm(7.6), CW, Cm(3.4), BGSOFT, AMBER, 1.5)
head(s, M + Cm(0.7), TOP + Cm(7.95), Cm(20), "7건 중 5건이 같은 실수 — 상대 부품의 탭 깊이를 확인하지 않았다", AMBER)
txt(s, M + Cm(0.7), TOP + Cm(8.95), CW - Cm(1.4), Cm(2.0),
    [("설계 형상은 CAD 로 검증됐지만, 체결 부품 목록(볼트 길이·와셔·핀)은 검증 대상 밖에 있었다.",
      {"size": 13}),
     ("→ 이번부터 볼트는 「상대 부품 탭 깊이」와 「머리 잠김」을 같이 계산해서 고른다.",
      {"size": 13, "bold": True, "color": NAVY, "gap": 6})])
foot(s, "형상 설계 자체의 오류는 없었다 — 어댑터·핑거의 나머지 치수는 원본과 전수 대조해 전부 일치")
note(s, "발주 직전에 전수 검증을 했더니 7건이 나왔습니다. 중요한 건 형상 설계는 멀쩡했다는 겁니다. "
        "오류는 전부 볼트 길이, 구멍 위치, 문서 간 모순이었습니다. "
        "특히 2·3·5번은 그대로 발주했으면 부품이 아예 안 붙는 것들이었습니다.")

# ═════════════════════════ 8. 볼트 실수 구조 ═════════════════════════
s = slide("볼트 3건이 왜 전부 틀렸나 — 조건 두 개를 같이 봐야 한다", "7 / 검증")
panel(s, M, TOP, Cm(15.0), Cm(5.4), BGSOFT)
txt(s, M + Cm(0.7), TOP + Cm(0.5), Cm(13.8), Cm(4.4),
    [("판 두께 T · 카운터보어 깊이 C · 볼트 길이 L · 상대 탭 깊이 D", {"size": 12.5, "color": GREY}),
     ("나사 물림  E = L − ( T − C )", {"mono": True, "size": 15, "bold": True, "color": NAVY, "gap": 10}),
     ("조건 ①   E < D            바닥 안 침", {"mono": True, "size": 13.5, "gap": 10}),
     ("조건 ②   C ≥ 머리 높이     머리 잠김", {"mono": True, "size": 13.5, "gap": 5}),
     ("두 조건이 동시에 성립하는지 확인하지 않았다.", {"size": 13, "bold": True, "color": RED, "gap": 10})])
table(s, M + Cm(15.8), TOP, Cm(16.1),
      [["", "T", "C", "L", "탭 D", "물림 E", "판정"],
       [("M6 (와셔 없이)", {"size": 11.5}), "12", "6.5", "12", "6", ("6.5", {"color": RED, "bold": True}), ("바닥 침", {"color": RED})],
       [("M6 (와셔 t1)", {"size": 11.5}), "12", "6.5", "12", "6", ("5.5", {"color": GREEN}), ("머리 0.5 돌출", {"color": RED})],
       [("M4×8", {"size": 11.5}), "8", "4.5", "8", "4", ("4.5", {"color": RED, "bold": True}), ("바닥 침", {"color": RED})],
       [("M3×8", {"size": 11.5}), "4", "—", "8", "3.5", ("4.0", {"color": RED, "bold": True}), ("바닥 침", {"color": RED})]],
      widths=[3.6, 1.0, 1.2, 1.0, 1.2, 1.4, 2.6], rh=Cm(0.85), size=12)
txt(s, M + Cm(15.8), TOP + Cm(4.6), Cm(16.1), Cm(1.0),
    [("M6 는 와셔로 ①을 고치면서 ②를 깨뜨렸다 — 와셔 자체도 외경 Ø12 라 Ø11 카운터보어에 안 들어간다.",
      {"size": 12, "color": GREY})])
Y = TOP + Cm(6.4)
head(s, M, Y, Cm(20), "정정 후 — 전 조인트 통과", GREEN, 15)
table(s, M, Y + Cm(0.9), CW,
      [["조인트", "볼트", "통과", "탭", "물림", "머리", "조임", "판정"],
       ["① 로봇 플랜지 ↔ 어댑터", "M6×10 SHCS", "4.5", "6.0", "5.5", "1.5 잠김", "9 N·m", ("✓", {"color": GREEN, "bold": True})],
       ["② 어댑터 ↔ 그리퍼 배면", "M5×20 SHCS", "12.0", "12.0", "8.0", "자유공간", "6 N·m", ("✓", {"color": GREEN, "bold": True})],
       ["③ 그리퍼 블록 ↔ 핑거", "M4×6 SHCS", "3.5", "4.0", "2.5", "0.5 잠김", ("2 N·m", {"color": RED, "bold": True}), ("✓", {"color": GREEN, "bold": True})],
       ["④ 그리퍼 측면 ↔ 브래킷", "M5×8 SHCS", "4.0", "5.5", "4.0", "노출", "4 N·m", ("✓", {"color": GREEN, "bold": True})],
       ["⑤ 브래킷 ↔ SY5120", "M3×6 접시머리", "4.0", "3.5", "2.0", "면일치", "0.8 N·m", ("✓", {"color": GREEN, "bold": True})]],
      widths=[5.6, 4.0, 1.6, 1.6, 1.6, 2.6, 2.0, 1.2], rh=Cm(0.82))
foot(s, "③ 물림 2.5 mm 는 짧지만 실하중은 볼트당 약 66 N (파지 반력 90 N 을 4개가 분담) — 과토크만 주의")
note(s, "볼트 세 건이 왜 전부 틀렸는지 구조를 보면 똑같습니다. 물림 길이와 머리 잠김, 두 조건을 같이 봐야 하는데 "
        "하나만 봤습니다. M6는 특히 와셔를 넣어서 물림 문제를 고치면서 머리가 튀어나오게 만들었고, "
        "그 와셔조차 외경이 커서 카운터보어에 안 들어갑니다. 정정 후에는 전부 통과합니다. "
        "M4는 물림이 2.5mm로 짧아서 2N·m 넘기면 안 됩니다 — 그리퍼 암나사가 상하면 그리퍼를 새로 사야 합니다.")

# ═════════════════════════ 9. Isaac 정합 ═════════════════════════
s = slide("Isaac Sim 정합 — 정면캠은 맞췄고, 손목캠이 미완", "8 / 시뮬레이션")
pic(s, os.path.join(SIM, "cam_match_v1.png"), M, TOP, Cm(11.0), Cm(13.6),
    "REAL (OMX v6 학습 영상)  vs  SIM (M1013 Isaac) — 위 2행 정면캠 / 아래 2행 손목캠")
X = M + Cm(12.2)
panel(s, X, TOP, Cm(19.7), Cm(3.9), None, GREEN, 1.5)
head(s, X + Cm(0.6), TOP + Cm(0.35), Cm(18), "정면캠 — 정합 완료", GREEN)
txt(s, X + Cm(0.6), TOP + Cm(1.3), Cm(18.5), Cm(2.4),
    [("pos (1.20, −0.25, 0.46) · look_at (0.45, −0.15, 0.52) · focal 15 mm (HFOV 69.9°)",
      {"mono": True, "size": 11.5}),
     ("원본 픽셀에서 초기값을 역산하고 후보를 한 번의 Isaac 부팅에 동시 렌더 → 3라운드에 수렴",
      {"size": 12.5, "gap": 6})])
panel(s, X, TOP + Cm(4.3), Cm(19.7), Cm(5.0), None, RED, 1.75)
head(s, X + Cm(0.6), TOP + Cm(4.65), Cm(18), "손목캠 — 정합 미완, 원인은 카메라가 아니라 그리퍼 형상", RED)
txt(s, X + Cm(0.6), TOP + Cm(5.6), Cm(18.5), Cm(3.5),
    [("· Isaac 씬의 그리퍼는 지금 박스 2개 근사 — 실제 형상이 전혀 없다", {"size": 12.5}),
     ("· 손목캠에 그리퍼가 크게 찍히므로 이 근사가 그대로 도메인 갭이 된다", {"size": 12.5, "gap": 5}),
     ("· 기하 모델 자체는 정확: 예측 세로 0.84 vs 기록 실측 0.86", {"size": 12.5, "gap": 5}),
     ("→ 문제는 “카메라를 어디 두느냐” 가 아니라 “무엇이 찍히느냐” 였다",
      {"size": 13, "bold": True, "color": RED, "gap": 7})])
panel(s, X, TOP + Cm(9.7), Cm(19.7), Cm(3.9), BGSOFT)
head(s, X + Cm(0.6), TOP + Cm(10.05), Cm(18), "바꿔 넣을 값 (설계 완료분)")
txt(s, X + Cm(0.6), TOP + Cm(11.0), Cm(18.5), Cm(2.4),
    [("플랜지→조 끝  258.8 → 83 mm    ·    그리퍼 몸체  박스 1개 → 142 × 50 × 33 (z 12~45)",
      {"size": 12, "mono": True}),
     ("조 면 간격 33.5 · 스트로크 편측 32 · 시각 메시는 tool_assembly_flangelocal.stl 을 link_6 에 그대로 부착",
      {"size": 12, "gap": 5})])
foot(s, "물리(collision)는 박스 근사를 유지하는 편이 안정적 — 메시 collision 은 볼록분해 비용이 크고 파지 접촉이 불안정해진다")
note(s, "왼쪽이 실제 학습 영상과 Isaac 렌더를 나란히 놓은 겁니다. 위 두 행이 정면캠인데 구도가 잘 맞았습니다. "
        "아래 두 행이 손목캠인데, 실물은 테이블과 큐브가 보이는 반면 시뮬레이션은 밋밋한 회색 덩어리만 보입니다. "
        "이유는 Isaac 씬의 그리퍼가 박스 두 개짜리 근사이기 때문입니다. 손목캠에는 그리퍼가 화면의 상당 부분을 "
        "차지하는데 그 형상이 아예 없으니 정합이 될 수가 없습니다. 카메라 위치 문제가 아니라 찍히는 물체 문제였습니다. "
        "이번에 실제 CAD가 나왔으니 그걸 넣으면 해결됩니다.")

# ═════════════════════════ 10. TCP 반영 시 손목캠 ═════════════════════════
s = slide("TCP 83 을 반영하면 손목캠은 아예 화면 밖으로 나간다", "9 / 시뮬레이션")
table(s, M, TOP, Cm(17.0),
      [["조건", "플랜지 → 큐브", "이탈각", "화면 세로 위치", "판정"],
       ["현재 규약 (TCP 0.12)", "258.8 mm", "16.0°", "0.84", ("화면 안", {"color": GREEN, "bold": True})],
       [("TCP 83 반영 후", {"bold": True}), ("83 mm", {"bold": True}), ("61.2°", {"bold": True, "color": RED}),
        ("1.80", {"bold": True, "color": RED}), ("화면 밖", {"color": RED, "bold": True})]],
      widths=[5.0, 3.4, 2.4, 3.4, 2.8], rh=Cm(0.95))
panel(s, M, TOP + Cm(3.4), Cm(17.0), Cm(4.2), None, RED, 1.5)
head(s, M + Cm(0.6), TOP + Cm(3.75), Cm(15), "어떤 위치로도 복원 불가", RED)
txt(s, M + Cm(0.6), TOP + Cm(4.7), Cm(15.8), Cm(2.8),
    [("이탈각 16° 를 되찾으려면 카메라가 플랜지 뒤(로봇 내부)에 있어야 한다.", {"size": 12.5}),
     ("측면 60 → z = −126    측면 45 → z = −74    측면 30 → z = −22",
      {"mono": True, "size": 12, "color": RED, "gap": 6}),
     ("→ forward_local = [0,0,1] 폐기. 카메라를 61.2° 틸트해야 한다.",
      {"size": 13, "bold": True, "color": NAVY, "gap": 7})])
panel(s, M, TOP + Cm(8.0), Cm(17.0), Cm(3.4), BGSOFT, AMBER, 1.5)
head(s, M + Cm(0.6), TOP + Cm(8.35), Cm(15), "그래서 손목캠 브래킷은 아직 출력하면 안 된다", AMBER)
txt(s, M + Cm(0.6), TOP + Cm(9.3), Cm(15.8), Cm(2.0),
    [("카메라 패드가 경사면이 되어야 하는데, 각도가 재정합 결과에 달려 있다.", {"size": 12.5}),
     ("확정 시 「팔 + 교체 플레이트」로 분할하면 재출력 양이 줄어든다.", {"size": 12.5, "gap": 5, "color": GREY})])
X = M + Cm(18.0)
panel(s, X, TOP, Cm(13.9), Cm(6.0), None, NAVY, 1.5)
head(s, X + Cm(0.6), TOP + Cm(0.35), Cm(12.5), "카메라 선정의 함정")
txt(s, X + Cm(0.6), TOP + Cm(1.3), Cm(12.7), Cm(4.4),
    [("파지 시 카메라 → 큐브 거리가 65 ~ 90 mm", {"size": 13, "bold": True}),
     ("일반 USB 웹캠의 최단 초점거리는 보통 100 ~ 300 mm", {"size": 12.5, "gap": 6}),
     ("→ 이 거리에서 초점이 안 맞는다", {"size": 13, "bold": True, "color": RED, "gap": 6}),
     ("최단 초점거리 ≤ 65 mm 가 1순위 기준. HFOV ≈ 60°, 640×480 @30fps, USB UVC.",
      {"size": 12, "gap": 8}),
     ("→ M12(S-mount) 보드캠 + 조절식 렌즈. 정면캠은 거리가 멀어 일반 웹캠으로 충분.",
      {"size": 12.5, "bold": True, "color": NAVY, "gap": 6})])
Y = TOP + Cm(6.6)
head(s, X, Y, Cm(13), "확정 순서 — 앞 단계가 끝나야 다음이 정해진다", NAVY, 14)
for i, t in enumerate(["① 재변환  TCP 0.12 → 0.083", "② Isaac 씬 그리퍼 형상 교체",
                       "③ 손목캠 재정합 (틸트 포함)", "④ 카메라 선정 (②③과 병렬 가능)",
                       "⑤ 손목캠 브래킷 확정 · 출력"]):
    yy = Y + Cm(0.95) + i * Cm(0.86)
    b = panel(s, X, yy, Cm(13.9), Cm(0.76), BGSOFT if i % 2 else WHITE)
    txt(s, X + Cm(0.45), yy + Cm(0.16), Cm(13), Cm(0.6), [(t, {"size": 12.5})])
foot(s, "재변환은 재학습 3시간 — 손목캠 재정합·카메라 선정보다 먼저 끝나야 한다")
note(s, "TCP를 83mm로 고치면 손목캠 기하가 완전히 바뀝니다. 지금은 카메라가 큐브를 16도 비껴 보는데, "
        "TCP를 반영하면 61.2도가 되어서 큐브가 화면 밖으로 나갑니다. 카메라를 어디로 옮겨도 복원이 안 됩니다 — "
        "계산해보면 플랜지 뒤쪽, 즉 로봇 내부에 있어야 하거든요. 그래서 카메라를 기울여야 하고, "
        "그러면 브래킷의 카메라 자리가 경사면이 되어야 합니다. 각도가 재정합 결과에 달려 있으니 지금 출력하면 안 됩니다. "
        "그리고 카메라 선정에 함정이 하나 있는데, 파지할 때 카메라와 큐브 거리가 65~90mm라 일반 웹캠은 초점이 안 맞습니다.")

# ═════════════════════════ 11. 남은 과제 ═════════════════════════
s = slide("남은 과제 — 발주 전 2건만 실물로 확인하면 된다", "10 / 다음 단계")
cols = [
    ("발주 · 출력 전", RED, [
        ("① 그리퍼 배면 Ø4 구멍", "개수와 중심에서 거리 (65.0 예상)\n틀리면 어댑터 재가공 → 발주 전에 확인"),
        ("② SY5120 바닥 2-M3", "간격과 방향 (22.6 예상)\n자체 출력이라 언제든 수정 가능"),
        ("③ 핑거 PETG 시제품", "립 걸림 확인 (치수 39.40 은 확정)\n반나절, 알루미늄 발주 전 위험 제거"),
    ]),
    ("조립 · 운용", AMBER, [
        ("M5×20 체결 공간", "어댑터 뒤 반경 54 — 볼 엔드 렌치"),
        ("다월 돌출량 2 mm", "3 mm 넘으면 배면 밀착 방해"),
        ("Tool Weight 1.22 kg", "전원 켜기 전 입력 · 충돌감지 오작동 방지"),
        ("압력 튜닝", "0.1 MPa 부터 올려가며 최소 파지압 탐색"),
        ("1/8 피팅 2개 추가", "필요 5곳 vs 발주 3 + 보유 2 = 여유 0"),
    ]),
    ("시뮬레이션 트랙", NAVY, [
        ("재변환 TCP 0.083", "재학습 3 h · 모든 후속 작업의 선행 조건"),
        ("Isaac 그리퍼 형상 교체", "시각 메시는 이미 준비됨"),
        ("손목캠 재정합 (틸트)", "재변환 후"),
        ("카메라 선정", "M12 보드캠 · 재정합과 병렬 가능"),
        ("클로킹 확정", "Isaac·IK 검토 후 핀홀 1곳 현장 리머"),
    ]),
]
for ci, (title, col, items) in enumerate(cols):
    x = M + ci * Cm(10.65)
    chip(s, x, TOP, Cm(10.2), title, col, Cm(0.95), 14)
    y = TOP + Cm(1.25)
    for t, sub in items:
        h = Cm(2.35) if ci == 0 else Cm(1.75)
        panel(s, x, y, Cm(10.2), h, WHITE)
        txt(s, x + Cm(0.5), y + Cm(0.3), Cm(9.2), Cm(0.7),
            [(t, {"size": 13, "bold": True, "color": col})])
        txt(s, x + Cm(0.5), y + Cm(1.05), Cm(9.2), h - Cm(1.2),
            [(sub, {"size": 11.5, "color": GREY, "ls": 1.25})])
        y += h + Cm(0.28)
panel(s, M, SH - Cm(3.0), CW, Cm(2.0), BGSOFT, GREEN, 1.75)
txt(s, M + Cm(0.8), SH - Cm(2.6), CW - Cm(1.6), Cm(1.3),
    [("어댑터 · 핑거는 발주 가능 상태 — 리드타임이 걸리므로 실물 확인 ① 만 끝내면 바로 발송",
      {"size": 15, "bold": True, "color": GREEN})])
foot(s, "발주 패키지: cad/발주/발주서.md + 어댑터/*.step,*.dxf + 핑거/*.step  ·  세부 기록: 대화록/20260906_그리퍼 연결부 검증 및 발주서 정정.md")
note(s, "정리하면, 발주 전에 실물로 확인할 건 딱 두 가지입니다. 그리퍼 배면의 Ø4 구멍과 밸브 바닥의 M3 구멍인데, "
        "둘 다 물건이 손에 있으니 자로 재면 1~2분입니다. 첫 번째가 틀리면 어댑터를 다시 깎아야 해서 발주 전에 꼭 재야 합니다. "
        "시뮬레이션 쪽은 재변환이 먼저 끝나야 나머지가 순서대로 풀립니다.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
prs.save(OUT)
print(f"저장 완료: {OUT}")
print(f"슬라이드 {len(prs.slides.__iter__.__self__._sldIdLst)} 장")

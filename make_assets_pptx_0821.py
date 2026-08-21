#!/usr/bin/env python3
"""2026-08-21 생성 산출물(사진·영상) 카탈로그 PPT.

  python3 make_assets_pptx_0821.py
  → /home/kim/m1013/대화록 및 PPT/산출물_20260821.pptx
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
RED = RGBColor(0xA9, 0x33, 0x1D)
GREEN = RGBColor(0x1F, 0x6B, 0x4A)
BGSOFT = RGBColor(0xED, 0xEF, 0xF3)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LILAC = RGBColor(0xB9, 0xC2, 0xF0)

FONT = "맑은 고딕"
MONO = "Consolas"
SW, SH = Cm(33.867), Cm(19.05)
BASE = "/home/kim/m1013"
OUTDIR = os.path.join(BASE, "대화록 및 PPT")
SIMOUT = os.path.join(BASE, "sim_out")

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


def bullets(tf, items, size=15):
    first = True
    for it in items:
        lv, txt = it[0], it[1]
        opt = it[2] if len(it) > 2 else {}
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = lv
        p.space_after = Pt(opt.get("after", 6))
        marks = {0: "▪  ", 1: "–  ", 2: "·  "}
        run = p.add_run()
        run.text = ("" if opt.get("nomark") else marks.get(lv, "")) + txt
        _set(run, opt.get("size", size - lv), opt.get("bold", False),
             opt.get("color", INK), MONO if opt.get("mono") else FONT)


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


def caption(s, x, y, w, txt, size=11.5, bold=False, color=GREY):
    tf = textbox(s, x, y, w, Cm(1.2))
    p = tf.paragraphs[0]
    run = p.add_run(); run.text = txt
    _set(run, size, bold, color)


# ═══════════ 1. 표지 ═══════════
s = slide()
r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background()
tf = textbox(s, Cm(2.2), Cm(5.2), Cm(29.5), Cm(7))
p = tf.paragraphs[0]
run = p.add_run(); run.text = "8/21 생성 산출물 카탈로그"
_set(run, 36, True, WHITE)
p = tf.add_paragraph(); p.space_before = Pt(10)
run = p.add_run()
run.text = "Isaac Sim 캡처 사진 4장 · 정책 물리 재생 영상 1편 — 랩미팅(8/24) 자료 삽입용"
_set(run, 19, False, LILAC)
p = tf.add_paragraph(); p.space_before = Pt(28)
run = p.add_run()
run.text = "위치: /home/kim/m1013/sim_out/   |   재생성 도구: capture_m1013.py · frames_to_mp4.py"
_set(run, 14, True, WHITE)
tf2 = textbox(s, Cm(2.2), SH - Cm(1.7), Cm(24), Cm(0.9))
run = tf2.paragraphs[0].add_run()
run.text = "2026-08-21 (금) · 이채원"
_set(run, 13, False, LILAC)

# ═══════════ 2. 로봇 단독 컷 (테이블 없음) ═══════════
s = slide()
bar(s, "사진 ①② — 로봇 단독 (테이블·큐브 없음)", "01 로봇만")
iw = Cm(15.6); ih = iw * 9 / 16  # 8.78
s.shapes.add_picture(os.path.join(SIMOUT, "m1013_only_front.png"), Cm(0.9), Cm(2.4), width=iw)
s.shapes.add_picture(os.path.join(SIMOUT, "m1013_only_side.png"), Cm(17.4), Cm(2.4), width=iw)
caption(s, Cm(0.9), Cm(11.3), iw, "① m1013_only_front.png — 정면 각도, 베이스 바닥판·케이블까지 전신", 12.5, True, INK)
caption(s, Cm(17.4), Cm(11.3), iw, "② m1013_only_side.png — 측면 각도, 링크의 DOOSAN 로고 보임 (추천)", 12.5, True, INK)
tf = textbox(s, Cm(0.9), Cm(12.6), Cm(32), Cm(5.4))
bullets(tf, [
    (0, "무엇: 공식 m1013.usd 를 Isaac Sim 에 로드해 데이터셋 홈 자세로 정착시킨 뒤 캡처 (1920×1080)", {"size": 13.5}),
    (0, "용도: 랩미팅 4장 '에셋 검증' 사진 자리 — 순수하게 \"로봇이 로드됐다\"를 보여주는 컷. 로고 보이는 ② 추천", {"size": 13.5, "bold": True}),
    (1, "2장 '배경'의 M1013 사진 자리에 실물 제품 사진 대신 써도 됨", {"size": 12.5}),
    (0, "재생성: cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/capture_m1013.py --bare", {"size": 12.5, "mono": True}),
    (1, "각도 변경은 capture_m1013.py 의 cam1/cam2 pos(카메라 위치)·tgt(바라보는 점) 수정", {"size": 12}),
])
foot(s, "OMX→M1013 전이 · 산출물 카탈로그 2026-08-21")

# ═══════════ 3. 씬 포함 컷 ═══════════
s = slide()
bar(s, "사진 ③④ — 검증 씬 포함 (로봇 + 테이블 + 큐브)", "02 씬 전체")
s.shapes.add_picture(os.path.join(SIMOUT, "m1013_full_alone.png"), Cm(0.9), Cm(2.4), width=iw)
s.shapes.add_picture(os.path.join(SIMOUT, "m1013_full_scene.png"), Cm(17.4), Cm(2.4), width=iw)
caption(s, Cm(0.9), Cm(11.3), iw, "③ m1013_full_alone.png — 측면에서 본 로봇 전신 + 테이블·큐브 배경", 12.5, True, INK)
caption(s, Cm(17.4), Cm(11.3), iw, "④ m1013_full_scene.png — 정면에서 본 씬 전경 (배치 관계가 한눈에)", 12.5, True, INK)
tf = textbox(s, Cm(0.9), Cm(12.6), Cm(32), Cm(5.4))
bullets(tf, [
    (0, "무엇: 물리 검증에 쓴 씬 그대로 — 테이블(상판 z 0.375m) + 35mm 파란 큐브 + 홈 자세 로봇", {"size": 13.5}),
    (0, "용도: 씬 구성을 설명할 때 (랩미팅 9장 'STEP 3' 보조, 또는 향후 자료의 씬 소개 컷)", {"size": 13.5, "bold": True}),
    (1, "④ 는 로봇-테이블-큐브의 배치 관계(오프셋 d 가 반영된 위치)가 보여서 배치 설명에 적합", {"size": 12.5}),
    (0, "재생성: cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/capture_m1013.py   (--bare 없이)", {"size": 12.5, "mono": True}),
])
foot(s, "OMX→M1013 전이 · 산출물 카탈로그 2026-08-21")

# ═══════════ 4. 정책 물리 재생 영상 ═══════════
s = slide()
bar(s, "영상 — 정책 예측 궤적의 물리 재생 (오늘 신규 생성)", "03 영상")
fw = Cm(10.4)
FR = os.path.join(SIMOUT, "frames_pred_ep0")
s.shapes.add_picture(os.path.join(FR, "0230.png"), Cm(0.9), Cm(2.4), width=fw)
s.shapes.add_picture(os.path.join(FR, "0330.png"), Cm(0.9) + fw + Cm(0.45), Cm(2.4), width=fw)
s.shapes.add_picture(os.path.join(FR, "0380.png"), Cm(0.9) + (fw + Cm(0.45)) * 2, Cm(2.4), width=fw)
caption(s, Cm(0.9), Cm(8.3), Cm(32),
        "replay_pred_ep0.mp4 의 대표 프레임 — 파지 · 운반 · 놓기 (1280×720, 15fps ≈ 실시간, 20초)")
rows = [
    ["항목", "내용"],
    ["파일", ("sim_out/replay_pred_ep0.mp4", {"mono": True, "bold": True})],
    ["내용", "ACT 정책이 예측한 ep0 관절 궤적을 Isaac 물리로 실행 — 집기→운반→놓기 완주"],
    ["결과", ("성공 · 놓기 오차 7.8mm · 관절 추종 1.1° (어제 결과 동일 재현)", {"color": GREEN, "bold": True})],
    ["용도", ("랩미팅 11장 '최종 결과' 의 [정책 실행 영상] 점선 자리에 삽입", {"bold": True})],
]
table(s, Cm(0.9), Cm(9.3), Cm(32.1), rows, widths=[2.6, 17.4], size=12.5, rh=Cm(1.15))
tf = textbox(s, Cm(0.9), Cm(15.4), Cm(32), Cm(2.6))
bullets(tf, [
    (0, "재생성 (2단계): ① 재생+프레임 캡처 → ② mp4 조립", {"size": 13, "bold": True}),
    (1, "./python.sh replay_isaac.py --pred-npz ep000_pred_m1013v6.npz --video --label pred_ep0", {"size": 11.5, "mono": True}),
    (1, "./python.sh frames_to_mp4.py pred_ep0   (경로 생략 — 실제로는 /home/kim/m1013/ 접두)", {"size": 11.5, "mono": True}),
])
foot(s, "OMX→M1013 전이 · 산출물 카탈로그 2026-08-21")

# ═══════════ 5. 랩미팅 삽입 매핑 ═══════════
s = slide()
bar(s, "랩미팅(8/24) 자료 삽입 매핑 — 어느 슬라이드에 무엇을", "04 매핑")
rows = [
    ["랩미팅 슬라이드", "점선 자리", "넣을 파일", "상태"],
    ["2장 배경", "두산 M1013 사진", ("m1013_only_side.png 또는 실물 제품 사진", {"mono": True}),
     ("오늘 생성", {"color": GREEN, "bold": True})],
    ["4장 에셋 검증", "Isaac 에 로드된 M1013", ("m1013_only_side.png (로고 보임)", {"mono": True}),
     ("오늘 생성", {"color": GREEN, "bold": True})],
    ["7장 트러블슈팅", "파지 실패 영상 2편", ("grasp_fail_35mm.mp4 · grasp_fail_35mm_closeup.mp4", {"mono": True}), "기존 (8/20)"],
    ["9장 물리 검증", "성공 영상", ("replay_35mm_success.mp4", {"mono": True}), "기존 (8/20)"],
    ["11장 최종 결과", "정책 실행 영상", ("replay_pred_ep0.mp4", {"mono": True}),
     ("오늘 생성", {"color": GREEN, "bold": True})],
]
table(s, Cm(0.9), Cm(2.7), Cm(32.1), rows, widths=[4.2, 5.0, 12.2, 2.6], size=12.5, rh=Cm(1.4))
tf = textbox(s, Cm(0.9), Cm(11.6), Cm(32), Cm(5.6))
bullets(tf, [
    (0, "모든 파일 위치: /home/kim/m1013/sim_out/  (git 커밋됨 — mp4 포함, 프레임 PNG 폴더는 제외)", {"size": 14}),
    (0, "이것으로 랩미팅 점선 자리 중 실물 사진(2장, 선택)을 빼고 전부 채울 수 있음", {"size": 14, "bold": True}),
    (1, "9장 스냅샷 3장과 11장 대표 프레임은 이미 PPT 에 박혀 있음 — 영상만 끌어다 넣으면 됨", {"size": 13}),
])
foot(s, "OMX→M1013 전이 · 산출물 카탈로그 2026-08-21 · 이채원")

out = os.path.join(OUTDIR, "산출물_20260821.pptx")
prs.save(out)
print("저장:", out)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-09-08 ~ 09-09 정리 PPT — 밸브 CAD 검증 · TCP 정정 · v7 수집 도구.

  python3 make_report_pptx_0909.py
  → 대화록 및 PPT/M1013_20260909.pptx

디자인은 make_labmeeting_pptx_0906.py 체계(남색 바 + flowbox + 지브라 표)를 그대로 계승.
이미지는 대화록 및 PPT/img_0909/ (make 시점에 생성된 차트·렌더·도면 크롭).
"""
import os
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Pt

NAVY  = RGBColor(0x2F, 0x3D, 0x9E); INK = RGBColor(0x15, 0x18, 0x1D); GREY = RGBColor(0x62, 0x6B, 0x78)
LINE  = RGBColor(0xD8, 0xDC, 0xE3); RED = RGBColor(0xA9, 0x33, 0x1D); GREEN = RGBColor(0x1F, 0x6B, 0x4A)
AMBER = RGBColor(0x9A, 0x6A, 0x00); BGSOFT = RGBColor(0xED, 0xEF, 0xF3); WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LILAC = RGBColor(0xC5, 0xCC, 0xF2); NAVY2 = RGBColor(0x5B, 0x6B, 0xD6)
FONT, MONO = "맑은 고딕", "Consolas"
SW, SH = Cm(33.867), Cm(19.05)
BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "대화록 및 PPT"); IMG = os.path.join(DOCS, "img_0909")
OUT = os.path.join(DOCS, "M1013_20260909.pptx")
prs = Presentation(); prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]


def _set(run, size=14, bold=False, color=INK, font=FONT):
    run.font.name = font; run.font.size = Pt(size); run.font.bold = bold; run.font.color.rgb = color
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
        r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background(); r.shadow.inherit = False
        tf = r.text_frame; tf.margin_left = Cm(0.95); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; run = p.add_run(); run.text = title; _set(run, 19, True, WHITE)
        if step:
            tb = tbox(s, SW - Cm(9.4), Cm(0.42), Cm(8.5), Cm(0.95))
            p = tb.paragraphs[0]; p.alignment = PP_ALIGN.RIGHT
            run = p.add_run(); run.text = step; _set(run, 12, False, LILAC)
    return s


def tbox(s, x, y, w, h):
    b = s.shapes.add_textbox(x, y, w, h); tf = b.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def txt(s, x, y, w, h, lines, size=13.5, gap=5):
    tf = tbox(s, x, y, w, h)
    for i, item in enumerate(lines):
        t, o = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(0 if i == 0 else o.get("gap", gap)); p.line_spacing = o.get("ls", 1.18)
        run = p.add_run(); run.text = t
        _set(run, o.get("size", size), o.get("bold", False), o.get("color", INK), MONO if o.get("mono") else FONT)
        if o.get("link"):
            run.hyperlink.address = o["link"]
    return tf


def panel(s, x, y, w, h, fill=None, border=LINE, width=1.0):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = fill or WHITE
    b.line.color.rgb = border; b.line.width = Pt(width); b.shadow.inherit = False
    b.adjustments[0] = 0.03; b.text_frame.text = ""
    return b


def head(s, x, y, w, t, color=NAVY, size=14):
    txt(s, x, y, w, Cm(0.8), [(t, {"size": size, "bold": True, "color": color})])


def table(s, x, y, w, rows, widths=None, size=12, rh=Cm(0.78), header=True):
    shp = s.shapes.add_table(len(rows), len(rows[0]), x, y, w, rh * len(rows)); t = shp.table
    if widths:
        tot = sum(widths)
        for i, cw in enumerate(widths):
            t.columns[i].width = int(w * cw / tot)
    for ri, row in enumerate(rows):
        t.rows[ri].height = rh
        for ci, cell in enumerate(row):
            c = t.cell(ri, ci); c.margin_left = c.margin_right = Cm(0.18); c.margin_top = c.margin_bottom = Cm(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            s_, o = (cell, {}) if isinstance(cell, str) else cell
            c.fill.solid(); c.fill.fore_color.rgb = (NAVY if (header and ri == 0) else o.get("bg", WHITE if ri % 2 else BGSOFT))
            p = c.text_frame.paragraphs[0]; p.alignment = o.get("align", PP_ALIGN.LEFT)
            run = p.add_run(); run.text = s_
            _set(run, o.get("size", size), o.get("bold", header and ri == 0),
                 WHITE if (header and ri == 0) else o.get("color", INK), MONO if o.get("mono") else FONT)
    return t


def pic(s, path, x, y, maxw, maxh, caption=None):
    im = Image.open(path); ar = im.width / im.height
    w, h = maxw, int(maxw / ar)
    if h > maxh:
        h, w = maxh, int(maxh * ar)
    s.shapes.add_picture(path, int(x + (maxw - w) / 2), int(y + (maxh - h) / 2), width=w, height=h)
    if caption:
        tf = tbox(s, x, y + maxh + Cm(0.08), maxw, Cm(0.6)); p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = caption; _set(run, 11, False, GREY)


def foot(s, t):
    tf = tbox(s, Cm(1.0), SH - Cm(0.82), SW - Cm(2.0), Cm(0.6)); p = tf.paragraphs[0]
    run = p.add_run(); run.text = t; _set(run, 10, False, GREY)


def note(s, t):
    s.notes_slide.notes_text_frame.text = t


def chip(s, x, y, w, t, fill=GREEN, h=Cm(0.92), size=12.5):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = fill; b.line.fill.background(); b.shadow.inherit = False
    tf = b.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = t; _set(run, size, True, WHITE)


def flowbox(s, x, y, w, h, t, fill=NAVY, fg=WHITE, size=12, bold=True):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = fill; b.line.color.rgb = LINE; b.line.width = Pt(0.75); b.shadow.inherit = False
    tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Cm(0.1); tf.margin_top = tf.margin_bottom = Cm(0.06)
    for i, line in enumerate(t.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = line; _set(run, size if i == 0 else size - 2, bold if i == 0 else False, fg)
    return b


def arrow(s, x, y, w=Cm(0.7), h=Cm(0.5)):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x, y, w, h); a.fill.solid(); a.fill.fore_color.rgb = GREY; a.line.fill.background()


def flow(s, x, y, items, bw, bh, gap=Cm(0.55), size=12):
    """items: [(text, fill)] 가로 파이프라인."""
    for i, (t, f) in enumerate(items):
        bx = x + i * (bw + gap)
        flowbox(s, bx, y, bw, bh, t, fill=f, size=size)
        if i < len(items) - 1:
            arrow(s, bx + bw + Cm(0.05), y + bh / 2 - Cm(0.25), w=gap - Cm(0.1))


M = Cm(1.0); CW = SW - 2 * M; TOP = Cm(2.35)
P = lambda *a: os.path.join(IMG, *a)

# ═════════════════════════ 1. 표지 ═════════════════════════
s = slide()
r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Cm(6.6)); r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background(); r.shadow.inherit = False
txt(s, M, Cm(1.35), Cm(26), Cm(4.6),
    [("M1013 그리퍼 이관 — 밸브 CAD 검증 · TCP 정정 · v7 수집 도구", {"size": 30, "bold": True, "color": WHITE}),
     ("2026-09-08 ~ 09-09  작업 정리", {"size": 18, "color": LILAC, "gap": 8}),
     ("파이프라인 · 트러블슈팅 · 알고리즘 선택 · 생성 파일 · 현재 상황 · 다음 할 것", {"size": 13, "color": RGBColor(0xB9, 0xC2, 0xF0), "gap": 8})])
pic(s, P("d_grasp.png"), Cm(20.5), Cm(7.1), Cm(12.4), Cm(9.3), "손목캠 파지 순간 (HFOV 85.6°, Isaac 재검증)")
txt(s, M, Cm(7.3), Cm(18.5), Cm(9.6),
    [("이틀 요약", {"size": 15, "bold": True, "color": NAVY}),
     ("· 밸브 SY5120 CAD 확보 → 연결부 설계 미검증 항목 0 (로봇 플랜지까지 원도면 대조)", {"gap": 8}),
     ("· 내 오판 3건을 스스로 잡아 정정 — M3 체결면 · 어댑터 STEP Z 축 · 소음기 지름", {}),
     ("· TCP 상수 0.0675 → 0.0725 정정, 데이터 3세대 정리, 베이스 재학습 (2h45m)", {}),
     ("· 실기 소프트웨어 5종 선작성 — 히스테리시스 · grip-lead · DO 래퍼 · 카메라 · v7 재생수집", {}),
     ("· 검증 도구 버그 발견 (카메라 최대 190 mm 어긋난 채 렌더) → Isaac 없는 순수기하 검증기로 대체", {}),
     ("· 절삭 외주 2건 발주 가능 · 구매목록 확정 · 설치절차서 docx 신설", {"bold": True, "color": GREEN, "gap": 8})])
txt(s, M, Cm(17.4), Cm(20), Cm(1.0), [("근거: cadquery(OpenCASCADE) 커널 실측 · SMC 카탈로그 원도면 · 두산 매뉴얼 V2.12 · Isaac Sim 재검증", {"size": 11, "color": GREY})])
note(s, "9/8~9/9 이틀 작업 정리. 하드웨어 설계는 미검증 항목이 0이 됐고, 소프트웨어는 미착수였던 3종이 전부 코드로 존재하게 됐다. "
        "이 과정에서 내가 만든 오판 3건과 기존 검증 도구의 버그 1건을 잡았다.")

# ═════════════════════════ 2. 파이프라인 — 전체 ═════════════════════════
s = slide("파이프라인 ① — OMX 시연에서 M1013 실기 추론까지", "파이프라인")
Y0 = TOP + Cm(0.5); BW, BH = Cm(4.55), Cm(2.3)
flow(s, M, Y0, [("OMX 시연 데이터\nv4 · 163 ep · 사람 텔레옵", NAVY), ("TX90 변환\nv5 EE → v6 joint", NAVY),
                ("M1013 변환\nconvert_v6_m1013.py\nOFFSET · TCP", NAVY2), ("데이터셋 조립\nassemble_v6_m1013.py", NAVY2),
                ("ACT 베이스 학습\n100K 스텝 · 2h45m", NAVY2), ("v7 실기 수집\nreplay_v6_real.py", AMBER)],
     BW, BH, gap=Cm(0.55), size=11.5)
Y1 = Y0 + BH + Cm(1.2)
flow(s, M + Cm(10.2), Y1, [("이어학습\nv7 30~50 ep", AMBER), ("실기 추론\ngripper_ctl · dsr 래퍼", RED)], BW, BH, size=11.5)
panel(s, M, Y1 + BH + Cm(0.9), CW, Cm(5.3), BGSOFT)
txt(s, M + Cm(0.6), Y1 + BH + Cm(1.25), CW - Cm(1.2), Cm(4.6),
    [("이번 이틀이 건드린 곳", {"size": 14, "bold": True, "color": NAVY}),
     ("▪ M1013 변환 — TCP 상수 0.0675 → 0.0725 (파지점 기하 하한 + 2 mm 여유). 전 궤적이 47.5 mm 밀려 있던 0.12 구본이 기본값이던 것도 정리", {"gap": 7}),
     ("▪ 데이터셋 조립 · 베이스 학습 — 재조립 159 ep / 76,345 프레임 → 재학습 (loss 0.054, 이전과 동일 = 계통 오프셋이었음을 확인)", {}),
     ("▪ v7 실기 수집 — 수집 방식 결정(파지자세 유도 재생) + 도구 5종 전부 코드로 작성", {}),
     ("▪ 실기 추론 — 히스테리시스 · grip-lead · DO 래퍼 (미착수였던 3종)", {}),
     ("▪ 지금 학습된 것 = 「OMX 영상 + M1013 관절」. M1013 영상은 v7 이 채운다 — 그래서 v7 이 필수", {"bold": True, "color": RED, "gap": 7})])
foot(s, "회색 = 이번에 손댄 단계 · 노랑 = 로봇 도착(9/14) 후 · 빨강 = 최종 목표")
note(s, "전체 흐름. OMX에서 사람이 시연한 데이터를 좌표 변환해 M1013 관절 궤적으로 만들고, 그걸로 베이스를 학습한 뒤, 실기에서 v7을 찍어 이어학습한다. "
        "지금 베이스는 영상이 OMX 것이라 실기에서 바로는 못 쓴다.")

# ═════════════════════════ 3. 파이프라인 — 하드웨어 ═════════════════════════
s = slide("파이프라인 ② — 하드웨어 3계통 (기구 · 공압 · 전기)", "파이프라인")
BW, BH = Cm(3.55), Cm(1.75); G = Cm(0.45)
for row, (lab, col, items) in enumerate([
    ("기구", NAVY, ["M1013 플랜지\nISO 9409-1-50-4-M6", "어댑터 AL6061\nM6×10 ×4 · 9 N·m", "MHF2-16D2\n다월 Ø4 ×2 + M5×20", "핑거 좌·우\nM4×6 ×8", "밸브 브래킷 PETG\nM5×8 ×2 · 스페이서 6", "SY5120 밸브\nM3×12 접시 ×2"]),
    ("공압", NAVY2, ["PL-10ST 컴프\n코일호스 15 m", "AW20 레귤레이터\n0.2~0.3 MPa · 1/8", "SY5120 P\n1/8 · Ø4", "A/B → AS1201F-M5-04A\n스피드컨트롤러 ×2", "그리퍼 「S」「O」\nM5 포트 (끝면 X=+71)", "EA/EB → AN110-01\n소음기 ×2 (위로)"]),
    ("전기", AMBER, ["컨트롤러", "팔 내부 배선", "플랜지 X1/X2\nDO 6ch · DI 6ch", "M8 8핀 케이블", "DO ×1 → 밸브\n0=ON (반전 주의)", "DI ×2 ← D-M9N\n오토스위치"])]):
    y = TOP + Cm(0.3) + row * (BH + Cm(1.05))
    chip(s, M, y + Cm(0.42), Cm(1.7), lab, fill=col, h=Cm(0.9))
    flow(s, M + Cm(2.1), y, [(t, col) for t in items], BW, BH, gap=G, size=10.5)
panel(s, M, TOP + Cm(8.9), CW, Cm(4.6), BGSOFT)
txt(s, M + Cm(0.6), TOP + Cm(9.2), CW - Cm(1.2), Cm(4.2),
    [("이번에 확정된 인터페이스 값", {"size": 13.5, "bold": True, "color": NAVY}),
     ("▪ 로봇 플랜지: 4-M6 TAP DP6 @Φ50 · Φ6 H7 REAMER DP6 ×1 @0° · Φ31.5 H7 보어 · Φ63 h7 · 9 N·m  (두산 매뉴얼 p.226 원도면)", {"gap": 5}),
     ("▪ 밸브: 2-M3×0.5 DP3.5 피치 22.6 「For mounting bracket」 — 넓은 옆면 (SMC 카탈로그 p.1-4-15) · 대각 ±18/±5.8 은 2-ø3.2 매니폴드용", {}),
     ("▪ 그리퍼 M5 포트: 본체 끝면 X=+71.0, Y=±13 (간격 26.0), Z=26.6, 탭 깊이 ~5 · 스피드컨트롤러 나사부 3.0 → 바닥 안 침", {}),
     ("▪ 툴 외형 확정: X −71.0 ~ +94.5 · Y −62.3 ~ +46.1 · Z −4 ~ +83 · J6 최대 선회 반경 ≈ 113 mm", {}),
     ("▪ DO/DI 극성이 서로 다르다 — SetToolDigitalOutput 0=ON, GetToolDigitalInput 1=ON  (dsr_msgs2 srv 정의 직접 확인)", {"bold": True, "color": RED})])
foot(s, "M1013 은 팔 내부 공압 배관이 없어 밸브를 툴단에 올린다 — 공기는 밖에서, 전기는 플랜지에서 와서 툴 끝에서 만난다")
note(s, "세 계통이 툴 끝에서 만난다. 이번에 각 인터페이스의 수치가 원도면·CAD 실측으로 전부 확정됐다.")

# ═════════════════════════ 4. 파이프라인 — 그리퍼 제어 ═════════════════════════
s = slide("파이프라인 ③ — 정책 출력이 그리퍼를 움직이기까지 (gripper_ctl.py)", "파이프라인")
BW, BH = Cm(4.3), Cm(2.4)
flow(s, M, TOP + Cm(0.5), [("정책 (ACT)\n30 Hz · 0~1 연속값\n낮을수록 닫힘", NAVY), ("① 히스테리시스\n+ 최소유지 0.5 s\n0.359 / 0.559", NAVY2),
                            ("② grip-lead\n액션 청크 k 프레임 앞보기\n(실측 후 채움)", NAVY2), ("③ ROS2 래퍼\nio/set_tool_digital_output\n0 = ON", NAVY2),
                            ("플랜지 DO → M8\n→ SY5120 솔레노이드", AMBER), ("공기 방향 전환\n→ MHF2 개폐", AMBER)],
     BW, BH, gap=Cm(0.5), size=11)
flow(s, M + Cm(9.7), TOP + Cm(4.0), [("D-M9N 오토스위치 ×2\n열림 · 닫힘 실측", GREEN), ("DI → gripper/closed_real\n정책에 실제 상태 피드백", GREEN)], BW, BH, gap=Cm(0.5), size=11)
panel(s, M, TOP + Cm(7.4), Cm(15.6), Cm(6.0), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(7.7), Cm(14.8), Cm(5.5),
    [("왜 3단계가 한 묶음인가", {"size": 13.5, "bold": True, "color": NAVY}),
     ("▪ 같은 신호 경로의 연속 3단계 — 따로 짜면 인터페이스를 두 번 맞춰야 함", {"gap": 5}),
     ("▪ 래퍼만 있고 히스테리시스가 없으면 첫 실행에서 그리퍼가 상한다 (초당 수십 번 딸깍)", {}),
     ("▪ ①②는 순수 로직 → ROS2 없이 지금 테스트 완료. ③은 뼈대 완료, DO 채널 번호만 실물에서", {}),
     ("▪ grip-lead 값은 실측 필요 → measure_grip_lead.py 로 벤치에서 30분", {"color": AMBER})])
panel(s, M + Cm(16.2), TOP + Cm(7.4), Cm(15.7), Cm(6.0))
txt(s, M + Cm(16.7), TOP + Cm(7.7), Cm(14.8), Cm(5.5),
    [("자체 테스트 결과", {"size": 13.5, "bold": True, "color": GREEN}),
     ("▪ 합성 채터링(±0.03): 단일 임계값 전이 83회/6s = 초당 13.8회 ★ MHF2 한계 초과", {"gap": 5}),
     ("▪ 히스테리시스 + 최소유지: 전이 0회", {"bold": True, "color": GREEN}),
     ("▪ 실제 에피소드 3개: 전이 2회(닫힘1+열림1) 그대로 — 정상 신호를 왜곡하지 않음", {}),
     ("▪ grip-lead: 현재값 0.69(열림)인데 3프레임 뒤 0.23(닫힘) → lead 0.1 s 로 미리 닫음", {})])
foot(s, "MHF2-16D2 최대 60 c.p.m. = 초당 1사이클. 과제는 에피소드당 개폐 1회라 최소유지 0.5 s 로 여유 충분")
note(s, "정책이 뱉는 연속값을 밸브 신호로 바꾸는 경로. 히스테리시스가 없으면 하드웨어가 상하므로 실물 연결 전에 반드시 들어가야 한다.")

# ═════════════════════════ 5. 타임라인 ═════════════════════════
s = slide("이틀 타임라인 — 무엇을 어떤 순서로", "개요")
table(s, M, TOP + Cm(0.2), Cm(15.8),
      [["9/8 (월)", "내용"],
       ["오전", "SY5120 CAD 확보 경로 조사 → PARTcommunity STEP AP214 + 6면도 DXF 수령"],
       ["", "커널 실측 90.8×33×17.1 · 포트 16.2 · 대각 구멍 ±18/±5.8 발견"],
       ["", "★ 「브래킷 22.6 이 틀렸다」 오판 → 카탈로그 원도면으로 정정 (22.6 맞음)"],
       ["오후", "TX90 밸브 사진 → 옆면 접합 추정 · 영수증에서 Ø6 피팅 발견"],
       ["", "설계 감사: 조립순서 누락(M3 갇힘) · 카운터싱크 Ø7.0 · CoG 낡음 · PETG 크리프"],
       ["", "브래킷 재생성 · 발주서 4건 반영 · 설치절차서 docx 신설 (6쪽)"],
       ["", "하단 포트면 ↔ 어댑터 간섭 제기 (전제 미확인으로 보류)"]],
      widths=[1.4, 9.0], size=11, rh=Cm(0.72))
table(s, M + Cm(16.4), TOP + Cm(0.2), Cm(15.5),
      [["9/9 (화)", "내용"],
       ["오전", "TX90 미사용 확정 → 밸브 이관 · 스피드컨트롤러 구매 확정 → 툴 외형 X +94.5"],
       ["", "카메라 U20CAM-720P 확정(정면·손목 동일) → 640×480 은 크롭, HFOV 63.4° 발견"],
       ["", "M3 체결면 논리 확정 → 스페이서 6 mm → ★ 어댑터 STEP Z 뒤집힘 오판 발견·정정"],
       ["", "로봇 플랜지 원도면(p.226) 발견 → 미검증 0 · Ø6×16 핀 추가 · 리머 절차"],
       ["오후", "wristcam_solve 정적 DELTA 버그(190 mm) → wristcam_check.py 순수기하 검증기"],
       ["", "TCP 0.0725 결정 → 재변환 → 데이터 3세대 정리 → 재학습 15:06~17:51"],
       ["", "소프트웨어 3종 + v7 도구 5종 작성 · 작업대 40×50 · 높이 허용 −13~+2"]],
      widths=[1.4, 9.0], size=11, rh=Cm(0.72))
txt(s, M, TOP + Cm(6.6), CW, Cm(1.2), [("★ = 내가 낸 오판을 같은 날 스스로 잡아 정정한 지점. 셋 다 「검증되지 않은 전제로 결론을 냈다」는 같은 패턴이었다.", {"size": 12, "color": RED, "bold": True})])
foot(s, "재학습은 백그라운드에서 돌리고 그 시간에 소프트웨어를 작성했다 — GPU 와 CPU 작업이 겹치지 않음")
note(s, "이틀의 흐름. 하드웨어 검증에서 소프트웨어 작성으로 무게중심이 넘어갔다.")

# ═════════════════════════ 6. 핵심 결론 ═════════════════════════
s = slide("핵심 결론 — 지금 어디까지 왔나", "개요")
for i, (t, lines, col) in enumerate([
    ("하드웨어 설계 — 미검증 0", ["▪ 로봇 플랜지 · 그리퍼 · 밸브 세 인터페이스 전부 원도면/CAD 대조", "▪ 간섭 0 (밸브·피팅·소음기·스피드컨트롤러 포함 16,478 삼각형 전수)", "▪ 볼트 3종 길이 전부 상대 탭 깊이로 검산", "▪ 어댑터·핑거 절삭 발주 가능"], GREEN),
    ("데이터·모델 — 좌표계 정정", ["▪ TCP 0.0725 (파지점). 3세대 섞임 정리", "▪ 재변환 159/159 · 재학습 loss 0.054", "▪ 지금 모델 = OMX 영상 + M1013 관절", "▪ M1013 영상은 v7 이 채운다"], NAVY),
    ("소프트웨어 — 미착수 0", ["▪ gripper_ctl · measure_grip_lead", "▪ camera_uvc_node · replay_v6_real", "▪ m1013_config.yaml · wristcam_check", "▪ 실물에서 채울 상수 3개만 남음"], NAVY2),
    ("남은 병목", ["▪ 절삭 외주가 로봇(9/14)보다 늦음 ★", "▪ 손목캠 브래킷 — 09-11 재설계됨", "▪ 밸브 뗄 때 확인 4건", "▪ 작업대 높이·설치 방식 (도착 후)"], AMBER)]):
    x = M + i * (Cm(7.85) + Cm(0.3))
    panel(s, x, TOP + Cm(0.3), Cm(7.85), Cm(8.6), BGSOFT if i % 2 else WHITE)
    chip(s, x + Cm(0.4), TOP + Cm(0.7), Cm(7.0), t, fill=col, h=Cm(0.95), size=12.5)
    txt(s, x + Cm(0.45), TOP + Cm(2.0), Cm(7.0), Cm(6.4), [(l, {"size": 11.5, "gap": 7}) for l in lines])
table(s, M, TOP + Cm(9.4), CW,
      [["구분", "9/8 시작 시점", "9/9 종료 시점"],
       ["설계 미검증", "로봇 플랜지 4-M6 탭 (메시가 구멍 생략)", ("0 — 매뉴얼 p.226 원도면으로 대조 완료", {"color": GREEN, "bold": True})],
       ["TCP 상수", "0.0675 (판 3 mm 관통, 기하적 불가) · 학습된 모델은 0.12", ("0.0725 · 재변환 · 재학습 완료", {"color": GREEN, "bold": True})],
       ["소프트웨어", "dsr 래퍼 · 히스테리시스 · grip-lead 미착수", ("3종 + v7 도구 전부 코드 존재", {"color": GREEN, "bold": True})],
       ["카메라", "기종 미상, HFOV 90° 가정", ("U20CAM-720P 확정 · 85.6° 재검증 통과", {"color": GREEN, "bold": True})]],
      widths=[2.2, 6.2, 6.2], size=11.5, rh=Cm(0.74))
foot(s, "★ 로봇 도착이 9/20 → 9/14 로 앞당겨져(09-11 갱신) 절삭 외주 리드타임이 새 병목")
note(s, "한 장 요약. 하드웨어는 닫혔고 소프트웨어는 뼈대가 다 있다. 남은 건 부품 도착과 실물 확인.")

# ═════════════════════════ 7. 밸브 CAD 확보 ═════════════════════════
s = slide("밸브 CAD 확보 — CADENAS 모델의 한계와 카탈로그 대조", "1 / 밸브")
pic(s, P("valve_6view.png"), M, TOP + Cm(0.2), Cm(17.5), Cm(9.4), "cad/2_b — CADENAS 6면도 (ezdxf 렌더). 마젠타 = 숨은선")
panel(s, M + Cm(18.2), TOP + Cm(0.2), Cm(13.7), Cm(9.4))
txt(s, M + Cm(18.7), TOP + Cm(0.5), Cm(12.9), Cm(9.0),
    [("입수 경로 (권장 순)", {"size": 13, "bold": True, "color": NAVY}),
     ("1. SMC PARTcommunity (CADENAS) — 형번 조립 후 STEP/DXF, 로그인 무료", {"size": 11.5, "gap": 4}),
     ("2. 한국SMC CAD 다운로드 (같은 엔진)", {"size": 11.5}),
     ("3. MISUMI 상세페이지 — SY5120-5LOZ-01 그대로 검색", {"size": 11.5}),
     ("포맷: 3D는 STEP AP214a (cadquery 바로 읽음), 2D는 DXF 2013 삼각법", {"size": 11.5, "color": GREY}),
     ("커널 실측 (cad/1_b/SY5120-5LOZ-01_V2.stp)", {"size": 13, "bold": True, "color": NAVY, "gap": 9}),
     ("▪ 솔리드 1 · 면 85 · 90.80 × 33.00 × 17.10 mm", {"size": 11.5, "gap": 4}),
     ("▪ A/B 포트 Rc1/8 (Ø8.566 탭) 피치 16.2 · Ø14.8 보스", {"size": 11.5}),
     ("▪ 대각 구멍 Ø5.8 @ X±18.0 / Z±5.8 = 36 × 11.6", {"size": 11.5}),
     ("★ 한계 — 모델이 생략한 것", {"size": 13, "bold": True, "color": RED, "gap": 9}),
     ("▪ 바닥면 P·EA·EB 포트 3개 (바닥 700.7 mm² 에 구멍 0)", {"size": 11.5, "gap": 4}),
     ("▪ 2-M3 브래킷 탭 (카탈로그엔 있음)", {"size": 11.5}),
     ("→ CADENAS 모델은 작은 탭·포트를 생략한다. 치수 근거는 카탈로그 원도면을 원본으로", {"size": 11.5, "bold": True})])
table(s, M, TOP + Cm(10.2), CW,
      [["카탈로그 SY5000 p.1-4-15 표기", "값", "의미"],
       ["2-M3 x 0.5 depth 3.5 (For mounting bracket)", "피치 22.6", "브래킷 체결 — 우리가 쓰는 것"],
       ["2-ø3.2 (For manifold mounting)", "피치 36 · 오프셋 11.6", "매니폴드 장착용 — CAD 에서 본 대각 구멍이 이것"],
       ["1/8 (P, EA, EB port) · 2-ø2.2 die-cast hole", "피치 27.2", "매니폴드 접합면(바닥)의 포트 3개 + 가스켓 핀홀"]],
      widths=[6.0, 3.0, 6.5], size=11, rh=Cm(0.72))
foot(s, "SMC 카탈로그 PDF: content2.smcetech.com/pdf/SY5000.pdf (p.7~9 에 body ported 치수) · CADENAS 라이선스 CC BY-ND 4.0")
note(s, "밸브 CAD를 처음 확보했다. 그런데 CADENAS 모델이 작은 구멍을 생략해서, 그것만 믿고 판단하면 틀린다. 카탈로그 원도면을 같이 봐야 한다.")

# ═════════════════════════ 8. 트러블슈팅 ① ═════════════════════════
s = slide("트러블슈팅 ① — 「브래킷 22.6 이 틀렸다」 오판과 정정", "2 / 밸브")
BW, BH = Cm(5.9), Cm(2.6)
flow(s, M, TOP + Cm(0.4), [("CAD 실측\n대각 Ø5.8 @ ±18/±5.8\n(=36 × 11.6)", NAVY), ("오판\n「이게 체결 구멍이다\n브래킷 22.6 틀림」", RED),
                            ("발주서 확인\n22.6 = 「카탈로그 기록값」\n미확인 항목이었음", AMBER), ("카탈로그 원도면\n2-M3 DP3.5 피치 22.6\n명기 발견", GREEN),
                            ("정정\n대각은 2-ø3.2 매니폴드용\n브래킷 원래 맞음", GREEN)], BW, BH, gap=Cm(0.5), size=11)
panel(s, M, TOP + Cm(3.6), Cm(15.6), Cm(8.9), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(3.9), Cm(14.7), Cm(8.5),
    [("왜 틀렸나", {"size": 13.5, "bold": True, "color": RED}),
     ("▪ CADENAS 모델에 실재하는 유일한 체결용 구멍이 대각 ±18/±5.8 이었고, 「나머지 하나」를 브래킷용으로 오인", {"size": 11.5, "gap": 5}),
     ("▪ 2-M3 탭은 모델에서 생략돼 있었다 — 「없는 것」을 「없다」고 판단", {"size": 11.5}),
     ("▪ 22.6 이 발주서에 「카탈로그 기록값」으로 적혀 있었는데, 그 카탈로그를 안 보고 CAD 를 우선했다", {"size": 11.5}),
     ("어떻게 잡았나", {"size": 13.5, "bold": True, "color": GREEN, "gap": 9}),
     ("▪ 사용자가 「다시 뽑아줘」 했을 때, 좌표를 고치기 전에 SMC 카탈로그 PDF 를 받아 p.1-4-15 를 렌더해 읽음", {"size": 11.5, "gap": 5}),
     ("▪ 「22.6 / 2-M3 x 0.5 depth 3.5 / (For mounting bracket)」 가 그대로 있었다", {"size": 11.5}),
     ("▪ 대각 구멍은 「36 / 2-ø3.2 / (For manifold mounting)」 — 완전히 다른 피처", {"size": 11.5}),
     ("교훈", {"size": 13.5, "bold": True, "color": NAVY, "gap": 9}),
     ("▪ 잘못된 좌표로 브래킷을 다시 뽑았으면 못 쓰는 부품이 될 뻔했다. 「고치기 전에 원본 확인」이 맞았다", {"size": 11.5, "bold": True})])
panel(s, M + Cm(16.2), TOP + Cm(3.6), Cm(15.7), Cm(8.9))
txt(s, M + Cm(16.7), TOP + Cm(3.9), Cm(14.8), Cm(8.5),
    [("이후 확정된 사실 (9/9)", {"size": 13.5, "bold": True, "color": NAVY}),
     ("▪ 2-M3 는 넓은 옆면(90.8×33)에 있다 — 사진 없이 논리로 확정:", {"size": 11.5, "gap": 5}),
     ("   A·B 면은 Ø14.8 보스가 X 0.7~15.5 점유, P·EA·EB 면은 EA 가 X −18.45~−8.75 점유", {"size": 11, "color": GREY}),
     ("   → M3 를 ±11.3 에 둘 자리가 두 좁은 면 어디에도 없다. 포트면으로는 붙일 수 없으니 옆면이 유일", {"size": 11, "color": GREY}),
     ("▪ TX90 실물 사진에서도 두 좁은 면이 전부 포트로 점유·노출 → 옆면 접합 확인", {"size": 11.5}),
     ("▪ M3 탭 깊이 3.5 → M3×6 (물림 2.0) 선정도 유효했음", {"size": 11.5}),
     ("남은 실물 확인", {"size": 13, "bold": True, "color": AMBER, "gap": 9}),
     ("▪ 옆면 어느 높이에 M3 가 있는지 (중앙 가정 ±3 mm 는 결론에 영향 없음)", {"size": 11.5, "gap": 4})])
foot(s, "발주서 「2026-09-07 §8 미확인 항목 #1: 22.6 카탈로그 기록값 → 유지」 가 이 건으로 「원도면 확인 완료」로 닫혔다")
note(s, "첫 번째 오판. CAD에 없는 구멍을 없다고 판단해서 브래킷 좌표를 고치자고 했다. 고치기 전에 카탈로그를 봐서 막았다.")

# ═════════════════════════ 9. 트러블슈팅 ② ═════════════════════════
s = slide("트러블슈팅 ② — 어댑터 STEP 의 Z 축이 뒤집혀 있었다", "3 / 좌표계")
table(s, M, TOP + Cm(0.2), Cm(16.0),
      [["", "adapter_m1013_mhf2.step (자체 좌표)", "tool_assembly_flangelocal.stl (플랜지 로컬 정본)"],
       ["Ø11 카운터보어 DP7.5", "Z 0.0 ~ 7.5  ← 그리퍼 쪽 면이 Z=0", "—"],
       ["Ø31.5 스피곳", "Z 12.0 ~ 16.0  ← 로봇 쪽", "Z −4.0 ~ 0.0"],
       ["판", "Z 0 ~ 12", "Z 0 ~ 12"],
       ["그리퍼 접합면", ("Z = 0", {"color": RED, "bold": True}), ("Z = 12", {"color": GREEN, "bold": True})],
       ["매핑", "", ("Z_assembly = 12 − Z_step", {"mono": True})]],
      widths=[3.2, 5.8, 6.0], size=11, rh=Cm(0.74))
panel(s, M + Cm(16.6), TOP + Cm(0.2), Cm(15.3), Cm(4.7), BGSOFT)
txt(s, M + Cm(17.1), TOP + Cm(0.5), Cm(14.4), Cm(4.3),
    [("이 착오가 만든 오판 2개", {"size": 13.5, "bold": True, "color": RED}),
     ("① 「어댑터 상면 Z=16, 밸브 하단 포트면 Z=15.5 → 축방향 여유 −0.5 mm」", {"size": 11.5, "gap": 5}),
     ("   실제 어댑터 상면 Z=12 → 여유 +3.5 mm  (스페이서 결론은 Y 방향이라 불변)", {"size": 11, "color": GREY}),
     ("② 「브래킷 M5 구멍 Z=32 vs 그리퍼 측면 탭 Z=16+20=36, 4 mm 어긋남」", {"size": 11.5, "gap": 5}),
     ("   실제 12+20 = 32 → 브래킷과 정확히 일치. 09-07 의 「조인트 5종 일치」가 맞았다", {"size": 11, "color": GREY})])
panel(s, M, TOP + Cm(5.4), CW, Cm(7.2))
txt(s, M + Cm(0.5), TOP + Cm(5.7), CW - Cm(1.0), Cm(6.8),
    [("어떻게 잡았나 — 「그리퍼 로컬 Y → 플랜지 Z」 매핑을 독립 피처로 검산", {"size": 13.5, "bold": True, "color": NAVY}),
     ("▪ 그리퍼 STEP 배면 Ø4 다월 (0, −3.3, ±65.0 / −65.5·−64.5 장공) ↔ 어댑터 다월 X=±65.0  → 그리퍼 Z = 플랜지 X 확정", {"size": 11.5, "gap": 5}),
     ("▪ 그리퍼 조 블록 밑면 Y=−33 + 조 38 돌출 = 플랜지 Z 83 (조립체 Z 최대) 이 되려면 접합면이 Z=12 여야 한다 — 16 이면 87", {"size": 11.5}),
     ("▪ 어댑터 STEP 의 카운터보어가 Z 0~7.5 에 있음 = 그리퍼 쪽 면이 Z=0 = 스피곳이 +Z 쪽 → 플랜지 로컬과 뒤집힘 확인", {"size": 11.5}),
     ("▪ 조립체 STL 어댑터 영역 Z 값 {−4, 0, 12, …} 로 스피곳 −4~0 · 판 0~12 재확인", {"size": 11.5}),
     ("교훈 — 메모리에 「함정」으로 기록", {"size": 13, "bold": True, "color": AMBER, "gap": 9}),
     ("▪ 부품 STEP 의 자체 좌표를 조립 좌표로 쓰지 말 것. 플랜지 로컬 정본은 tool_assembly_flangelocal.stl 하나뿐", {"size": 11.5, "gap": 4}),
     ("▪ 「기존 검증(09-07)이 틀렸다」는 결론이 나오면 먼저 내 매핑을 의심할 것 — 두 번 다 내가 틀렸다", {"size": 11.5, "bold": True})])
foot(s, "같은 착오가 하루 사이 두 번 다른 오판을 만들었다. 좌표계 함정은 메모리 m1013-sy5120-valve-cad 에 기록")
note(s, "두 번째 오판. 어댑터 STEP 파일이 자체 좌표에서 Z가 뒤집혀 있는데, 그걸 플랜지 로컬로 착각해 두 가지를 잘못 판단했다.")

# ═════════════════════════ 10. M3 면 확정 + 스페이서 ═════════════════════════
s = slide("밸브 옆면 접합 확정 → 하단 포트면 피팅이 어댑터·손목과 부딪힌다 → 스페이서 6 mm", "4 / 브래킷")
pic(s, P("valve_bracket_section.png"), M, TOP + Cm(0.1), Cm(18.2), Cm(9.9), "플랜지 로컬 Y–Z 단면 개략도 (스페이서 반영 후)")
table(s, M + Cm(18.8), TOP + Cm(0.2), Cm(13.1),
      [["Y 방향 여유 (어댑터 Y ≤ 35)", "스페이서 0", "스페이서 6"],
       ["밸브 접합면 Y", "29.0", "35.0"],
       ["포트 중심선 Y", "37.55", "43.55"],
       ["1/8 피팅 Ø14 안쪽 끝", ("30.55 → 4.45 겹침", {"color": RED}), ("36.55 → +1.55", {"color": GREEN})],
       ["소음기 AN110-01 Ø13 안쪽 끝", ("31.05 → 3.95 겹침", {"color": RED}), ("37.05 → +2.05", {"color": GREEN})]],
      widths=[4.4, 3.0, 3.0], size=11, rh=Cm(0.72))
txt(s, M + Cm(18.8), TOP + Cm(4.2), Cm(13.1), Cm(5.9),
    [("Z 방향은 문제가 아니다 — Y 방향이 문제다", {"size": 12.5, "bold": True, "color": NAVY}),
     ("▪ 옆면 접합 → 밸브 높이 33 이 Z 방향, 브래킷 M3 Z=32 → 포트면 Z 15.5 / 48.5", {"size": 11, "gap": 4}),
     ("▪ 하단면 피팅은 −Z 로 20 mm+ 내려가 어댑터(Z −4~12)를 관통 — 피할 길은 Y 뿐", {"size": 11}),
     ("▪ 대안 검토: 브래킷 M3 를 Z 로 올리기 → 피팅이 여전히 어댑터를 향함 ✗ / 어댑터 모서리 따내기 → 절삭 발주 지연 ✗ / 엘보 피팅 → 부분 완화만 △", {"size": 11}),
     ("▪ 스페이서(+Y)가 유일하게 완전 해결. 자체 출력물이라 비용 0", {"size": 11, "bold": True}),
     ("방향 제약 — 소음기는 위로", {"size": 12.5, "bold": True, "color": RED, "gap": 8}),
     ("▪ 소음기 아래(−Z)로 두면 Z −11.4 까지 내려가 link_6 충돌 메시와 −1.91 / −4.35 mm 충돌 (두산 DAE, translate 보정 후 Z max 0.001 확인)", {"size": 11, "gap": 4}),
     ("▪ 위(+Z)로 두면 Z 48.5→75.4, link_6 (Z≤0) 와 무관. 배기가 어댑터를 안 때리는 부수 이점", {"size": 11})])
foot(s, "09-08 에는 「소음기 Ø17 이라 여유 0.05」 를 근거로 썼으나 CAD 실측 Ø13 — 제약 자체는 유효하되 이유가 link_6 충돌로 바뀜 (정정 ③)")
note(s, "밸브가 옆면으로 붙는 게 확정되면 하단 포트면이 어댑터 바로 위에 온다. 피팅이 어댑터와 스치므로 브래킷에 스페이서를 넣어 Y로 빼냈다.")

# ═════════════════════════ 11. 브래킷 v3 + 조립 순서 ═════════════════════════
s = slide("밸브 브래킷 v3 — 카운터싱크 Ø7.0 · 스페이서 6 · M3×12 · 조립 순서 신설", "5 / 브래킷")
table(s, M, TOP + Cm(0.2), Cm(16.0),
      [["항목", "이전", "v3", "근거"],
       ["카운터싱크 (Y=25 면)", "Ø6.2 깊이 1.4", ("Ø7.0 깊이 1.8", {"bold": True}), "ISO 10642 M3 dk 이론최대 6.72 → 6.2 면 최대 0.26 돌출, 브래킷이 그리퍼에 안 밀착"],
       ["스페이서 패드", "없음", ("X±22 · Z 21~43 · 6 mm", {"bold": True}), "하단 포트 피팅 ↔ 어댑터 Y 여유 확보 (앞 장)"],
       ["M3 나사", "M3×6", ("M3×12 접시머리", {"bold": True}), "통과 4→10 mm. ×6 이면 물림 0, ×14 는 4.0>3.5 바닥 침"],
       ["조임", "0.8 N·m", ("0.5 N·m", {"bold": True}), "물림 2.0 · 다이캐스트 암나사 스트립 여유 1.16→1.86배"],
       ["질량", "18.98 g", "26.19 g", "PETG 1.27 g/cc"],
       ["간섭", "—", ("0 / 16,478", {"color": GREEN, "bold": True}), "밸브 옆면 접합 포락 AABB 전수"]],
      widths=[3.0, 2.4, 3.6, 7.0], size=9.5, rh=Cm(0.9))
panel(s, M + Cm(16.6), TOP + Cm(0.2), Cm(15.3), Cm(5.3), BGSOFT)
txt(s, M + Cm(17.1), TOP + Cm(0.5), Cm(14.4), Cm(4.9),
    [("★ 조립 순서에 밸브 장착 시점이 빠져 있었다", {"size": 13, "bold": True, "color": RED}),
     ("M3 접시머리 머리는 브래킷의 「그리퍼 쪽 면」에 잠긴다. 브래킷을 그리퍼에 먼저 붙이면 머리가 그리퍼 측면과 브래킷 사이에 갇혀 렌치가 못 들어간다 → 밸브를 영영 못 단다.", {"size": 11.5, "gap": 5}),
     ("→ 4번 「밸브 → 브래킷」 신설, 5번 「브래킷 서브어셈블리 → 그리퍼」, 6번 배관 으로 재번호", {"size": 11.5, "bold": True, "gap": 5}),
     ("발주서가 스스로 경고한 「순서 틀리면 볼트에 접근 못 함」 에 정확히 해당하는데 누락돼 있었다", {"size": 11, "color": GREY})])
panel(s, M + Cm(16.6), TOP + Cm(5.8), Cm(15.3), Cm(6.9))
txt(s, M + Cm(17.1), TOP + Cm(6.05), Cm(14.4), Cm(6.6),
    [("걱정거리로 남긴 것", {"size": 12.5, "bold": True, "color": AMBER}),
     ("▪ PETG 크리프 — M3 0.5 N·m 축력 833 N 이 Ø7 원뿔면에 ~20 MPa (압축항복의 2.5배 여유). 지속하중 크리프 → 록타이트 243 또는 0.3 N·m", {"size": 10.5, "gap": 4}),
     ("▪ 무게중심 (−0.8,+3.6,+25.1) 은 09-03 값 — 브래킷 11.3→26.2 g · 밸브 +Y 6 · 공압 부속 +82 g 미반영. +Y 4~8 mm 이동 예상", {"size": 10.5}),
     ("▪ Tool Weight 1.22 → ≈1.30 kg + 카메라. 소음기·피팅은 CAD 체적으로 산정 불가 → 실물 계량", {"size": 10.5}),
     ("▪ 밸브(Z 33)가 판(Z 28)보다 위아래 2.5 mm 오버행 — 기능 무해 · 포트 방향 180° 자유 → P·EA·EB 위 / A·B 아래 명시", {"size": 10.5})])
foot(s, "cad/valve_bracket_sy5120.step / .stl — 면 12개 위상 유지, bbox 136×10×28 · 출력 가능 (구본은 git 에 보존)")
note(s, "브래킷 자체의 변경은 세 가지. 그보다 중요한 건 조립 순서 누락을 잡은 것 — 그대로 조립했으면 밸브를 못 달았다.")

# ═════════════════════════ 12. 로봇 플랜지 ═════════════════════════
s = slide("로봇 플랜지 인터페이스 — 마지막 미검증 항목이 매뉴얼 안에 있었다", "6 / 플랜지")
pic(s, P("flange_p226.png"), M, TOP + Cm(0.1), Cm(17.0), Cm(9.6), "두산 User manual V2.12 p.226 「툴 출력 플랜지, ISO 9409-1-50-4-M6」")
table(s, M + Cm(17.6), TOP + Cm(0.2), Cm(14.3),
      [["항목", "도면", "어댑터 설계", ""],
       ["볼트", "4-M6 TAP DP6 @Φ50 90°", "Ø6.6 관통 ×4 @PCD50 45°", ("✅", {"align": PP_ALIGN.CENTER})],
       ["물림", "탭 깊이 6", "M6×10 → 5.5", ("✅ 0.5", {"align": PP_ALIGN.CENTER})],
       ["위치결정", "Φ6 H7 REAMER DP6 ×1 @0°", "Ø5.8 하도 ×4 @0/90/180/270", ("✅", {"align": PP_ALIGN.CENTER})],
       ["센터링", "Φ31.5 H7 보어", "Ø31.5 h7 스피곳 돌출 4", ("✅", {"align": PP_ALIGN.CENTER})],
       ["접촉면", "Φ63 h7", "140×70 평판", ("✅", {"align": PP_ALIGN.CENTER})],
       ["토크", "권장 9 N·m", "9 N·m", ("✅", {"align": PP_ALIGN.CENTER})]],
      widths=[2.0, 5.2, 5.2, 1.3], size=10.5, rh=Cm(0.72))
txt(s, M + Cm(17.6), TOP + Cm(5.4), Cm(14.3), Cm(5.2),
    [("덤으로 확인된 것", {"size": 12, "bold": True, "color": NAVY}),
     ("▪ 탭 DP6 → M6×12 면 물림 7.5 > 6 바닥 침. 09-06 의 ×10 변경이 독립 근거로 재확인", {"size": 10.5, "gap": 3}),
     ("▪ 메시 교차검증 — 플랜지 면 정점 반경 16.75 (Ø31.5+C1) · 30.5 (Ø63+C1). 볼트 홀만 생략", {"size": 10.5}),
     ("▪ 리머 핀홀 0° 1개 → 어댑터 4방향 하도로 어느 클로킹이든 1곳이 맞음 — 설계 의도 검증", {"size": 10.5}),
     ("▪ Ø6×16 ISO 2338 m6 핀 추가. 리머는 가조립 상태에서 현장 가공 (DO NOT REAM 유지)", {"size": 10.5})])
table(s, M, TOP + Cm(10.6), CW,
      [["방법", "메시 (dsr_description2)", "매뉴얼 p.226 원도면"],
       ["플랜지 면 정점", "반경 16.5 · 17.0 · 30.5 뿐 — 볼트 홀 없음", "4-M6 · Φ6 리머 · Φ31.5 · Φ63 전부 치수 명기"],
       ["결론", "검증 불가 (09-07 「메시가 작은 구멍 생략」)", ("검증 완료 → 어댑터 미검증 항목 0", {"color": GREEN, "bold": True})]],
      widths=[2.4, 6.2, 6.4], size=11, rh=Cm(0.72))
foot(s, "「제공된 CAD 서칭 안 돼?」 라는 질문이 계기 — 메시 4종 재확인 후 로컬 PDF 매뉴얼에서 도면 발견")
note(s, "어댑터의 로봇 쪽 치수는 ISO 규격 텍스트 근거였는데, 두산 매뉴얼 226쪽에 치수 도면이 있었다. 전부 대조해서 미검증 항목이 0이 됐다.")

# ═════════════════════════ 13. 스피드컨트롤러·소음기 ═════════════════════════
s = slide("스피드컨트롤러 · 소음기 CAD 실측 → 툴 외형 확정 · 손목 충돌 검사", "7 / 공압")
table(s, M, TOP + Cm(0.2), Cm(15.8),
      [["AS1201F-M5-04A (cad/speed_2)", "실측", "의미"],
       ["나사 착좌면 기준 돌출", ("23.50 mm", {"bold": True}), "카탈로그 치수 A(unlock) 와 일치"],
       ["나사부 길이", "3.00 mm", "그리퍼 M5 탭 ~5.0 → 바닥 안 침"],
       ["폭 / 튜브방향 전장", "9.40 / 22.00", "육각 9 스펙"],
       ["Ø4 튜브 축 높이", "13.90", "엘보 회전 자유"],
       ["툴 X 최대", ("71.0 + 23.5 = 94.5", {"bold": True, "color": RED}), "종전 ±71 → 비대칭"]],
      widths=[4.6, 3.2, 5.0], size=11, rh=Cm(0.72))
table(s, M + Cm(16.4), TOP + Cm(0.2), Cm(15.5),
      [["AN110-01 (cad/noise_2)", "실측", "의미"],
       ["바디 Ø / 전장", ("Ø13.00 / 34.00", {"bold": True}), "09-08 가정 Ø17 → 정정"],
       ["R1/8 나사", "Ø9.73 · 6.52", "착좌면 기준 돌출 26.90"],
       ["아래로 두면", ("link_6 와 −1.91 / −4.35", {"color": RED, "bold": True}), "충돌 — 위로 둘 것"],
       ["위로 두면", "Z 48.5 → 75.4", "툴 Z 최대 83 이내"],
       ["색", "소결 동합금 = 금속색", "TX90 흰 원통은 수지형(AN10-01)일 가능성"]],
      widths=[3.8, 4.0, 5.4], size=11, rh=Cm(0.72))
panel(s, M, TOP + Cm(5.4), CW, Cm(7.2), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(5.7), CW - Cm(1.0), Cm(6.8),
    [("그리퍼 M5 포트는 옆면이 아니라 끝면이었다 (MHF2 STEP 커널 실측)", {"size": 13.5, "bold": True, "color": NAVY}),
     ("▪ Ø4.13 (M5 탭 드릴) 2개 · 축 Z · (X=±13, Y=−10.6, Z 66→70.6) → 간격 26.0 = 문서와 일치 · 본체 Z=+71.0 끝면에서 뚫림 · 깊이 ~5", {"size": 11.5, "gap": 5}),
     ("▪ 플랜지 로컬 = (X=+71.0, Y=±13, Z=26.6). 밸브 A·B(X 중앙)에서 약 68 mm 튜브가 간다", {"size": 11.5}),
     ("▪ 매핑 검산: 그리퍼 배면 Ø4 다월 (Z=+65.0, −65.5/−64.5 장공) ↔ 어댑터 X=±65 · 측면 M5 (X=±25, Z=±61) ↔ 브래킷 X=±61 — 세 계열 자기일관", {"size": 11.5}),
     ("툴 외형 · 선회 반경 (Isaac 충돌 볼륨 갱신 대상)", {"size": 13.5, "bold": True, "color": RED, "gap": 9}),
     ("▪ X −71.0 ~ +94.5 · Y −62.3 ~ +46.1 · Z −4 ~ +83.  J6 최대 선회 반경 √(94.5²+62.3²) ≈ 113 mm (종전 ≈95)", {"size": 11.5, "gap": 5}),
     ("▪ 스피드컨트롤러 엘보 회전 자유 포락(R 17.2) 으로 조립체 전수 → 겹침 0. 두 피팅 사이 여유 26.0−9.4 = 16.6", {"size": 11.5}),
     ("▪ 툴 조 완전 개방 시 핑거가 X ±75 까지 (닫힘 ±71) — 실사용 개방폭에선 무관", {"size": 11.5, "color": GREY})])
foot(s, "CADENAS STEP 은 질량 산정에 쓰지 말 것 — AN110-01 은 면 8개짜리 단순화 형상 · 링크 SMC AS 카탈로그: content2.smcetech.com/pdf/AS_1F-A_EU.pdf")
note(s, "사용자가 받아온 스피드컨트롤러·소음기 CAD로 추정치를 실측으로 바꿨다. 툴 외형이 +X로 23.5 커지고, 소음기를 아래로 두면 로봇 손목과 실제로 부딪힌다.")

# ═════════════════════════ 14. 카메라 기종 ═════════════════════════
s = slide("카메라 — U20CAM-720P 확정, 640×480 은 크롭이라 화각이 63.4° 로 준다", "8 / 카메라")
pic(s, P("hfov_compare.png"), M, TOP + Cm(0.1), Cm(17.2), Cm(7.0))
panel(s, M + Cm(17.8), TOP + Cm(0.2), Cm(14.1), Cm(6.9), BGSOFT)
txt(s, M + Cm(18.3), TOP + Cm(0.5), Cm(13.2), Cm(6.5),
    [("INNOMAKER U20CAM-720P — 정면·손목 동일 기종", {"size": 13, "bold": True, "color": NAVY}),
     ("▪ 32×32 보드캠 · 나사구멍 Ø2.2 ×4 · M12 렌즈 마운트(교체 가능) · 고정초점 · USB 2.0 UVC", {"size": 11, "gap": 4}),
     ("▪ 네이티브 1280×720 · FOV(D)120° / FOV(H)102°", {"size": 11}),
     ("▪ 「M12 보드캠이 M1013 에 너무 작지 않나」 → 시야는 렌즈가 정하고 캔틸레버 끝이라 가벼운 게 유리. 이미 M12 캠", {"size": 11}),
     ("▪ 「웹캠 vs 보드캠」 논쟁 → OMX 가 이미 보드캠을 쓰고 있었으니 논쟁 종료", {"size": 11}),
     ("★ 08-24 역산값의 불일치가 풀렸다", {"size": 12.5, "bold": True, "color": RED, "gap": 8}),
     ("정면 69.9° / 손목 60.3° 가 서로 달랐던 건 정합 오차. 동일 기종·640×480 크롭이면 63.4° 가 정답 → HFOV 가 자유 파라미터에서 상수로 (7개 → 6개)", {"size": 11, "gap": 4})])
table(s, M, TOP + Cm(7.5), CW,
      [["캡처 방식", "HFOV", "VFOV", "최악 |v| (8ep 중심점)", "판정", "비고"],
       ["1280×720 네이티브 (16:9)", "102.0°", "69.6°", "0.67", "4:3 데이터셋에 못 씀", "v6 정책 입력이 640×480"],
       ["960×720 중앙크롭 → 640×480", ("85.6°", {"bold": True}), "69.6°", ("0.90", {"bold": True}), ("채택", {"color": GREEN, "bold": True}), "센서 세로 720 전부 사용 = 4:3 최대 화각"],
       ["640×480 단순 크롭 (현 OMX 파이프라인 추정)", "63.4°", "49.7°", ("1.35", {"color": RED}), ("불채택", {"color": RED, "bold": True}), "ep050·ep145 에서 파지 직전 큐브 이탈"]],
      widths=[4.6, 1.4, 1.4, 3.0, 2.0, 4.6], size=10.5, rh=Cm(0.72))
txt(s, M, TOP + Cm(10.6), CW, Cm(1.8),
    [("→ v7 수집 파이프라인은 1280×720 캡처 → 960×720 중앙크롭 → 640×480 (camera_uvc_node.py). 09-04 마운트 해가 85.6° 로 그대로 유효 — 렌즈 교체 불필요.", {"size": 12, "bold": True, "color": NAVY}),
     ("파지 거리 114.6 mm 에서 가로 시야 212 mm, 35 mm 큐브 = 106 px. 더 광각은 왜곡만 늘고 픽셀은 줄어든다.", {"size": 11.5, "color": GREY, "gap": 4})])
foot(s, "cameras_v6match.json 에 camera_hardware 블록 추가(참조용, fitted 값은 렌더 코드가 쓰므로 미변경) · inno-maker.com/product/u20cam-720p")
note(s, "카메라 기종이 확정되면서 두 가지가 풀렸다. 08-24 정합값의 불일치가 크롭 때문이었다는 것과, 현재 방식으로는 화각이 부족하다는 것.")

# ═════════════════════════ 15. 트러블슈팅 ③ DELTA ═════════════════════════
s = slide("트러블슈팅 ③ — 검증 도구가 카메라를 190 mm 엉뚱한 곳에 놓고 렌더하고 있었다", "9 / 카메라")
table(s, M, TOP + Cm(0.2), Cm(15.6),
      [["촬영 시점", "카메라 플랜지로컬 (설계 60,−75,5)", "오차"],
       ["a_approach90", "(54.2, −35.2, 195.4)", ("190.4 mm", {"color": RED, "bold": True})],
       ["b_approach45", "(7.6, −54.0, 114.6)", ("109.6 mm", {"color": RED, "bold": True})],
       ["c_close", "(39.5, −71.9, −5.4)", ("20.5 mm", {"color": RED})],
       ["d_grasp", "(60.0, −75.0, 5.0)", ("0.065 mm", {"color": GREEN, "bold": True})]],
      widths=[2.8, 5.4, 2.4], size=11, rh=Cm(0.72))
txt(s, M, TOP + Cm(4.2), Cm(15.6), Cm(3.0),
    [("카메라는 플랜지에 강체로 붙어 있으니 네 값이 같아야 한다. 서보 랙을 의심해 수렴 대기를 넣었지만 값이 그대로 → 원인은 코드", {"size": 11.5, "gap": 4}),
     ("DELTA(link_6 prim ↔ FK 플랜지 보정)를 J[TG] 한 자세에서만 구해 정적으로 사용. USD 아티큘레이션 운동학 ≠ m1013_kin.fk 라 다른 자세에서 어긋남", {"size": 11.5, "mono": False})])
head(s, M + Cm(16.2), TOP + Cm(0.2), Cm(15), "알고리즘 3안 비교 — 무엇을 왜 선택했나")
table(s, M + Cm(16.2), TOP + Cm(1.1), Cm(15.7),
      [["안", "방법", "결과", "채택"],
       ["A 정적 DELTA (기존)", "파지 자세에서 1회 계산 → 고정", ("최대 190 mm 어긋남", {"color": RED}), "✗"],
       ["B 자세별 DELTA 재계산", "shot() 마다 place_cam(q) 로 재산정", ("전 자세 ≤ 0.008 mm", {"color": GREEN}), "✓ 렌더용"],
       ["C 순수 기하 (신규)", "m1013_kin.fk 만으로 투영. USD·DELTA 불필요", ("Isaac 렌더값 재현 · 8ep 608 프레임 수 초", {"color": GREEN, "bold": True}), ("✓ 검증 정본", {"bold": True})]],
      widths=[3.2, 5.2, 4.6, 1.8], size=10, rh=Cm(0.95))
txt(s, M + Cm(16.2), TOP + Cm(5.2), Cm(15.7), Cm(2.2),
    [("C 를 정본으로 삼은 이유 — 카메라가 애초에 플랜지 로컬로 정의돼 있어 DELTA 가 필요 없다. 버그가 원천 차단되고, Isaac 없이 돌아가며, 화각을 인자로 여러 개 스윕할 수 있다. B 는 렌더 그림이 필요할 때만.", {"size": 11.5})])
panel(s, M, TOP + Cm(7.8), CW, Cm(4.9), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(8.05), CW - Cm(1.0), Cm(4.6),
    [("파급 — 09-04 기록의 신뢰도", {"size": 12.5, "bold": True, "color": AMBER}),
     ("▪ 「8 에피소드 최종접근 2초 21/21 통과」 도 정적 DELTA 로 돌렸다면 파지 순간 근처만 유효했을 수 있다. c_close 오차 20 mm 라 최종 2초 안에서 0~20 mm 오염", {"size": 11.5, "gap": 5}),
     ("▪ wristcam_check.py 로 8 에피소드 × 최종 2초 × 큐브 8꼭짓점 (608 프레임) 을 다시 돌려 그 기록을 대체했다 — 결과는 더 좋았다", {"size": 11.5}),
     ("▪ 내가 먼저 「접근 중 큐브가 잘린다」 고 보고한 것도 이 아티팩트(카메라 11 cm 어긋난 렌더)를 보고 한 오판이었다", {"size": 11.5, "color": RED}),
     ("▪ 교훈: 검증 스크립트에는 항상 기하 자기일관성 체크(카메라 플랜지로컬 == 설계값)를 넣을 것. 이번에 카메라오차(mm) 를 매 촬영에 출력하게 함", {"size": 11.5, "bold": True})])
foot(s, "wristcam_solve.py: HFOV 인자화 + place_cam(q) + RGBA 저장 비치명화 · wristcam_check.py 신규 · 메모리 m1013-step5-cameras 에 함정 기록")
note(s, "세 번째는 내 오판이 아니라 기존 도구의 버그. 카메라 위치 출력이 자세마다 달라지는 걸 보고 잡았다. 순수 기하 검증기로 대체해 원천 차단했다.")

# ═════════════════════════ 16. 손목캠 시야 검증 ═════════════════════════
s = slide("손목캠 시야 검증 — HFOV 85.6° 로 파지 정렬 구간 전부 가시", "10 / 카메라")
W4 = Cm(7.6); H4 = Cm(5.7)
for i, (f, cap) in enumerate([("a_approach90.png", "−3.0 s  u −0.05 / v +0.08"), ("b_approach45.png", "−1.5 s  u −0.00 / v +0.07"),
                              ("c_close.png", "닫힘  u +0.04 / v +0.32"), ("d_grasp.png", "파지  u −0.01 / v +0.57")]):
    pic(s, P(f), M + i * (W4 + Cm(0.35)), TOP + Cm(0.1), W4, H4, cap)
table(s, M, TOP + Cm(6.6), Cm(15.6),
      [["파지까지", "보이는 꼭짓점 / 8 (최악 ep145)", "상태"],
       ["−2.00 ~ −0.67 s", ("8/8 전 에피소드", {"color": GREEN, "bold": True}), "정책이 정렬하는 구간 — 완전 가시"],
       ["−0.33 s ~ 파지", "5~6/8", "큐브 아랫면만 프레임 밖 — 조가 이미 감싼 뒤"]],
      widths=[2.8, 4.0, 5.0], size=10.5, rh=Cm(0.85))
txt(s, M, TOP + Cm(9.7), Cm(15.6), Cm(3.0),
    [("판정: 렌즈 교체 불필요. 09-04 마운트 해 (60, −75, 5) / 틸트 38.7° 그대로 유효", {"size": 11.5, "bold": True, "color": GREEN}),
     ("틸트 스윕: +5° 로 여유 10→19% 개선되나 +10° 부터 상단 이탈. 검증된 해를 건드릴 만큼은 아님", {"size": 11, "gap": 4}),
     ("110° 광각이면 꼭짓점까지 전부 담기지만 왜곡 증가 대가 → 불필요", {"size": 11})])
panel(s, M + Cm(16.2), TOP + Cm(6.6), Cm(15.7), Cm(6.0), BGSOFT)
txt(s, M + Cm(16.7), TOP + Cm(6.9), Cm(14.8), Cm(5.6),
    [("wristcam_check.py 사용법", {"size": 12.5, "bold": True, "color": NAVY}),
     ("python3 wristcam_check.py 63.4 85.6 102.0", {"size": 11, "mono": True, "gap": 4}),
     ("▪ replay_ep*.npz 8개 · 최종 2초(60 프레임) + 파지 후 15 · 큐브 중심 또는 8꼭짓점", {"size": 11, "gap": 4}),
     ("▪ 카메라 기저는 wristcam_solve.py 와 같은 규약 (USD −Z 전방 / +Y 상방, up = 파지점을 화면 아래로)", {"size": 11}),
     ("▪ Isaac 렌더값 ep000 파지 (−0.01, +0.57) 을 정확히 재현 → 모델 검증", {"size": 11}),
     ("▪ 09-11 갱신: 손목캠 위치가 그리퍼 중앙 (0, −65, −10)·보드 세로 장착으로 바뀜. 자세 정본은 wristcam_pose.py — 이 장의 수치는 09-09 시점(60,−75,5) 기준", {"size": 11, "color": AMBER, "bold": True})])
foot(s, "sim_out/wristcam_solve/*.png 은 09-09 11:29 재렌더(자세별 DELTA 적용) · 이미지 4장은 img_0909/ 에 복사")
note(s, "고친 도구로 다시 보니 큐브가 3초 전부터 화면 중앙에 있고 파지 순간 하단 중앙으로 내려온다. 설계 의도 그대로.")

# ═════════════════════════ 17. TCP 상수 ═════════════════════════
s = slide("TCP 상수 — JAW_CLEAR 의 물리적 의미로 0.0725 를 정했다", "11 / 데이터")
pic(s, P("tcp_tradeoff.png"), M, TOP + Cm(0.1), Cm(18.0), Cm(9.2))
table(s, M + Cm(18.6), TOP + Cm(0.2), Cm(13.3),
      [["JAW_CLEAR", "TCP", "큐브윗면↔판", "조끝↔상판", "물림", ""],
       ["2.0 (구)", "0.0675", ("−3.0", {"color": RED}), "+2.0", "30", ("판 관통", {"color": RED})],
       ["5.0 (하한)", "0.0705", "0.0", "+5.0", "30", "여유 0"],
       [("7.0", {"bold": True}), ("0.0725", {"bold": True}), "+2.0", "+7.0", "28 (80%)", ("채택", {"color": GREEN, "bold": True})],
       ["10.0", "0.0755", "+5.0", "+10.0", "25 (71%)", "물림 얕음"]],
      widths=[2.2, 1.9, 2.4, 2.2, 2.0, 2.0], size=10.5, rh=Cm(0.7))
txt(s, M + Cm(18.6), TOP + Cm(4.0), Cm(13.3), Cm(5.6),
    [("선택 근거", {"size": 12, "bold": True, "color": NAVY}),
     ("▪ 하한 0.005 는 큐브 윗면이 판에 딱 닿음 → 폼 높이 편차·상판 오차·노이즈를 못 흡수", {"size": 10.5, "gap": 3}),
     ("▪ +2 mm 면 실물 변동 흡수 + 조 물림 80%. 더 키우면 큐브가 조 아래로 빠져 전도 모멘트 증가", {"size": 10.5}),
     ("▪ 하드웨어(조 연장)로는 못 푼다 — 판 밑면이 정하는 값이라 조를 늘려도 불변", {"size": 10.5}),
     ("⚠️ 컨트롤러 TCP 83(플랜지→조 끝)과 별개. 혼용 금지 — 83 에 큐브 중심을 두면 조가 상판 관통", {"size": 10.5, "bold": True, "color": RED, "gap": 5})])
panel(s, M, TOP + Cm(9.9), CW, Cm(2.8), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(10.1), CW - Cm(1.0), Cm(2.5),
    [("실행: convert_v6_m1013.py  JAW_CLEAR 0.002 → 0.007 (근거 주석 6줄) → 재변환 6.5초 → 159/159 OK · fail 0 · FK 4.90→4.89 mm · min|q5| 45.58→45.97° (품질 저하 없음)", {"size": 11.5, "bold": True}),
     ("허용 오차(작업대 높이): 실물 상판이 설계보다 높으면 +2 mm, 낮으면 −13 mm 까지 — 비대칭. 애매하면 낮게", {"size": 11.5, "gap": 4})])
foot(s, "메모리 m1013-tcp-grasp-point 갱신 · JAW_CLEAR = 큐브가 조 끝 아래로 삐져나오는 양 = 조 끝의 상판 여유")
note(s, "TCP는 자유 파라미터가 아니라 툴 기하가 정하는 값. 하한에 2mm 여유를 더한 0.0725를 골랐다.")

# ═════════════════════════ 18. 데이터 3세대 + 재학습 ═════════════════════════
s = slide("데이터 3세대가 섞여 있었다 — 정리 · 재변환 · 재학습", "12 / 데이터")
table(s, M, TOP + Cm(0.2), Cm(16.2),
      [["디렉터리", "tcp_m", "상태", "비고"],
       ["v6_staging (정리 전)", ("0.12", {"color": RED, "bold": True}), "폐기", "구정의 「플랜지→핑거 끝」. 09-04 이전"],
       ["v6_staging_tcp0675", "0.0675", "폐기", "판 3 mm 관통 — 기하적 불가"],
       [("v6_staging (정리 후)", {"bold": True}), ("0.0725", {"bold": True, "color": GREEN}), ("현행", {"color": GREEN, "bold": True}), "= v6_staging_tcp0725"],
       ["v6_staging_tcp012", "0.12", "보존", "원래 v6_staging 이던 것을 개명"]],
      widths=[4.2, 1.6, 1.6, 6.0], size=10.5, rh=Cm(0.72))
panel(s, M, TOP + Cm(4.2), Cm(16.2), Cm(4.0), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(4.5), Cm(15.3), Cm(3.6),
    [("★ 기본값 지뢰", {"size": 12.5, "bold": True, "color": RED}),
     ("assemble_v6_m1013.py(정식 데이터셋 조립) · knn_check_m1013.py · sweep_tcp.py 가 폐기된 0.12 본을 기본값으로 가리키고 있었다. prep_replay_ep.py 만 경고 주석과 함께 _tcp0675 를 봄", {"size": 11, "gap": 4}),
     ("→ v6_staging 을 현행본으로 재생성해 모든 기본값이 옳도록. prep_replay_ep.py 기본값·주석 갱신", {"size": 11, "bold": True})])
table(s, M + Cm(16.8), TOP + Cm(0.2), Cm(15.1),
      [["재학습", "08-20 (TCP 0.12)", "09-09 (TCP 0.0725)"],
       ["데이터셋", "m1013_…_v6_joint (0.12)", "재조립 159 ep / 76,345 프레임"],
       ["시작 ~ 종료", "13:34:48 ~ 16:19:19", "15:06:40 ~ 17:51:50"],
       ["소요", "2h 44m 31s", "2h 45m 10s"],
       ["설정", "ACT · 100K · batch 8 · RTX 5070 Ti", "동일 · 스텝당 0.099 s"],
       ["최종 loss", "0.054", ("0.054", {"bold": True})],
       ["출력", "train_m1013_act_v6 (보존)", "train_m1013_act_v6_tcp0725"]],
      widths=[2.6, 4.6, 4.6], size=10.5, rh=Cm(0.7))
txt(s, M + Cm(16.8), TOP + Cm(5.4), Cm(15.1), Cm(2.8),
    [("loss 가 같다 = TCP 오차는 학습 난이도가 아니라 좌표계 오프셋이었다. 모델은 잘못된 좌표계를 성실히 학습하고 있었다.", {"size": 11.5, "bold": True, "color": NAVY}),
     ("ep0 궤적 비교: 관절 최대 6.98° · 플랜지 위치 전 구간 정확히 47.5 mm = (0.12−0.0725)×1000", {"size": 11, "gap": 4})])
panel(s, M, TOP + Cm(8.7), CW, Cm(3.9))
txt(s, M + Cm(0.5), TOP + Cm(9.0), CW - Cm(1.0), Cm(3.5),
    [("지금 학습된 것의 정체 — 「OMX 영상 + M1013 관절」", {"size": 13, "bold": True, "color": RED}),
     ("videos/…/episode_000000.mp4 → ../omx_act_pick_and_place_v4_162/… 심볼릭 링크. 영상은 OMX 원본, 관절만 변환. robot_type 도 omx_f 로 남아 있고 state/action names 가 EE 이름(x,y,z,rx,ry,rz)인 채 — 실데이터는 관절 (메타 오류, v7 설정에서 정정)", {"size": 11, "gap": 4}),
     ("→ 실기에서 바로 못 쓴다. M1013 화면을 못 알아본다. 오늘 재학습의 목적은 「베이스를 깨끗하게」 — v7 이 47.5 mm 되돌리기와 화면 적응을 동시에 하지 않게", {"size": 11, "bold": True})])
foot(s, "구 자산 전부 보존: v6_staging_tcp012 / _tcp0675 · m1013_…_v6_joint_tcp012_BAK · train_m1013_act_v6 — 언제든 되돌릴 수 있음")
note(s, "v6_staging이 가장 오래된 폐기본이었고 정식 조립 스크립트가 그걸 기본값으로 쓰고 있었다. 정리하고 재학습했다. loss가 같아서 오프셋이었음이 확인됐다.")

# ═════════════════════════ 19. 히스테리시스 알고리즘 ═════════════════════════
s = slide("알고리즘 ① 히스테리시스 + 최소유지 — 대안 4개 중 선택 이유", "13 / 소프트웨어")
pic(s, P("hysteresis.png"), M, TOP + Cm(0.1), Cm(17.6), Cm(9.4))
table(s, M + Cm(18.2), TOP + Cm(0.2), Cm(13.7),
      [["안", "동작", "문제 / 채택"],
       ["단일 임계값 0.459", "g < th → 닫힘", ("경계 떨림 → 초당 13.8회 딸깍 ✗", {"color": RED})],
       ["이동평균 후 임계", "N 프레임 평균", "지연 N/2 프레임 · 경계에선 여전히 떨림 ✗"],
       ["히스테리시스 밴드", "닫힘 <0.359 · 열림 >0.559 · 사이 유지", ("떨림 제거 ✓", {"color": GREEN})],
       [("+ 최소유지 0.5 s", {"bold": True}), "전이 후 0.5 s 잠금", ("사양 60 c.p.m. 보장 ✓ 채택", {"color": GREEN, "bold": True})]],
      widths=[3.2, 4.3, 4.8], size=10.5, rh=Cm(0.78))
txt(s, M + Cm(18.2), TOP + Cm(4.5), Cm(13.7), Cm(5.0),
    [("규약 — 코드에 못박음", {"size": 12.5, "bold": True, "color": NAVY}),
     ("▪ 정책 채널은 낮을수록 닫힘 (닫힘 ~0.23 / 열림 ~0.69, 경계 0.459). run_policy_tx90.py 에서 승계. 처음 설명을 반대로 했다가 소스 확인으로 정정", {"size": 11, "gap": 4}),
     ("▪ 밴드 ±0.10 — 두 군집 간격 0.46 의 절반 이내. 정상 궤적 3 ep 에서 전이 2회 그대로 (왜곡 없음)", {"size": 11}),
     ("▪ 최소유지 0.5 s = 사양 한계(초당 1사이클). 과제는 에피소드당 개폐 1회라 넉넉", {"size": 11}),
     ("▪ GripperGate 는 상태를 들고 있으므로 에피소드마다 reset()", {"size": 11, "mono": False})])
foot(s, "gripper_ctl.py — rclpy 는 run_node() 안에서만 import → 순수 로직은 ROS2 없이 import·테스트 (selftest 통과)")
note(s, "정책 출력이 임계값 근처에서 떨리면 밸브가 초당 수십 번 켜졌다 꺼진다. 켜는 기준과 끄는 기준을 다르게 두고 최소 유지시간을 넣었다.")

# ═════════════════════════ 20. grip-lead + DO ═════════════════════════
s = slide("알고리즘 ② grip-lead (공압 지연 보상) · 두산 DO/DI 극성", "14 / 소프트웨어")
table(s, M, TOP + Cm(0.2), Cm(16.0),
      [["안", "방법", "판정"],
       ["예측 모델", "과거 출력 추세로 미래 추정", "별도 모델 필요 · 오차 · ✗"],
       ["고정 오프셋", "명령을 항상 k 프레임 일찍", "미래를 모르면 불가능 (실시간) ✗"],
       [("액션 청크 앞보기", {"bold": True}), "ACT 가 뱉는 chunk[k] 를 본다", ("실시간에도 미래가 있다 ✓ 채택", {"color": GREEN, "bold": True})]],
      widths=[3.2, 5.0, 4.6], size=10.5, rh=Cm(0.78))
txt(s, M, TOP + Cm(3.6), Cm(16.0), Cm(5.0),
    [("핵심 — ACT 는 한 번에 chunk_size 개 미래 액션을 예측한다. 별도 예측이 필요 없고, k = lead_s × fps 프레임 앞을 읽으면 된다.", {"size": 11.5, "bold": True, "color": NAVY}),
     ("▪ 청크가 없으면(스칼라) 보상 없이 현재값 — 재생 모드 호환", {"size": 11, "gap": 4}),
     ("▪ 값은 실측: measure_grip_lead.py — DO ON → 오토스위치 DI 플립까지 Δt, N 사이클, 평균+1σ 권장값 출력, 2 ms 분해능", {"size": 11}),
     ("▪ 조건: 실사용 압력 0.2~0.3 MPa · 스피드컨트롤러 최종 조임 후. 순서 거꾸로 하면 무효", {"size": 11}),
     ("▪ 안전: 열림으로 시작·종료(finally) · --dry 배선 확인 · 타임아웃 3 s · 5 프레임 초과 시 경고", {"size": 11}),
     ("▪ 「벤치 배관」 = 로봇 없이 작업대에서 공압만 연결한 상태. 압력·속도·방향 확인은 거기서, 지연 실측은 로봇 DO/DI 가 한 컴퓨터라 편함", {"size": 11})])
panel(s, M + Cm(16.6), TOP + Cm(0.2), Cm(15.3), Cm(8.4), BGSOFT)
txt(s, M + Cm(17.1), TOP + Cm(0.5), Cm(14.4), Cm(8.0),
    [("⚠️ 두산 플랜지 I/O 극성 — srv 정의 직접 확인", {"size": 13, "bold": True, "color": RED}),
     ("SetToolDigitalOutput.value   0 = ON,  1 = OFF   ← 반전", {"size": 11.5, "mono": True, "gap": 6}),
     ("GetToolDigitalInput.value    0 = OFF, 1 = ON    ← 정상", {"size": 11.5, "mono": True}),
     ("헷갈리면 밸브가 반대로 동작. DO_ON = 0 상수로 박고 주석", {"size": 11, "gap": 6}),
     ("배관 안전 규약", {"size": 12.5, "bold": True, "color": NAVY, "gap": 9}),
     ("▪ 밸브 A → 그리퍼「S」닫힘 · B → 「O」열림. 솔레노이드 통전 = 닫힘, 무통전 = 스프링 복귀 = 열림", {"size": 11, "gap": 4}),
     ("▪ 정전·비상정지 시 열려서 큐브를 놓는다. 반대로 꽂으면 쥔 채 멈춤 → 그리퍼 끝면 S/O 각인 확인 필수", {"size": 11}),
     ("래퍼 노드 (run_node)", {"size": 12.5, "bold": True, "color": NAVY, "gap": 9}),
     ("policy/gripper (Float32) 구독 → 전이에서만 서비스 호출 → gripper/closed_cmd · closed_real 발행. DO 채널 번호는 결선 후 확정", {"size": 11, "gap": 4})])
foot(s, "DO 돌입전류 ≈42 mA vs 채널 한계 50 mA (여유 16%) — 불안하면 릴레이/MOSFET 개재, 매뉴얼 「전류 제한 없음, 초과 시 영구 손상」 경고 포트")
note(s, "공압은 전기보다 느리다. ACT가 미래 액션을 청크로 주니 그 안에서 앞을 보면 된다. 값은 오토스위치로 실측한다.")

# ═════════════════════════ 21. v7 수집 방식 ═════════════════════════
s = slide("v7 수집 방식 — 4안 비교 → 「파지자세 유도 재생」 선택", "15 / v7")
table(s, M, TOP + Cm(0.2), CW,
      [["안", "내용", "장점", "문제", "판정"],
       ["직접교시", "M1013 을 손으로 끌어 시연", "새 동작 다양성", "두 손이 팔을 잡아 그리퍼 입력 수단(발판) 필요 · 속도 불균일을 정책이 학습 · 30~50회 시연", "보류"],
       ["v6 궤적 재생 (원안)", "v6 궤적 실행 + 실물 영상 기록", "궤적 검증 완료 · 속도 일정", ("큐브를 궤적이 전제한 위치에 mm 단위로 놓아야 함 — 159개 위치 재현 비현실", {"color": RED}), "난점"],
       ["OMX 리더 원격조종", "리더 암을 M1013 에 매핑", "숙련된 장치", "5축 ↔ 6축 매핑, 11일 안에 불가", "✗"],
       ["스페이스마우스 텔레옵", "6DOF 입력 장치", "그리퍼 버튼 내장 · 속도 제어", "장비 10~20만원 · 배송 · 숙련", "△"],
       [("파지자세 유도 재생", {"bold": True}), ("로봇이 파지 자세로 가서 「여기 놓으세요」 → 큐브 놓기 → 시작 자세 복귀 → 재생·기록", {"bold": True}), ("자·장비·발판 불필요 · 오차 원리적 0 · 큐브 위치 다양성 = v6 159개", {"color": GREEN, "bold": True}), "사람 손이 조 사이 → 정지·무압 상태에서만", ("채택", {"color": GREEN, "bold": True})]],
      widths=[2.6, 5.0, 3.6, 5.6, 1.4], size=9.5, rh=Cm(0.95))
panel(s, M, TOP + Cm(7.0), Cm(15.6), Cm(5.7), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(7.25), Cm(14.7), Cm(5.4),
    [("왜 재생이 목적에 더 맞나", {"size": 12.5, "bold": True, "color": NAVY}),
     ("▪ v7 의 진짜 목적: 정책이 OMX 영상으로 학습돼 M1013 화면을 못 알아본다 → 필요한 건 「같은 행동 + 새 영상」 (도메인 적응)", {"size": 11, "gap": 4}),
     ("▪ 직접교시는 행동까지 바꾼다 — 사람 속도·가속 ≠ 정책이 배운 것 → 이어학습에 혼란", {"size": 11}),
     ("▪ 「손목캠에 큐브가 보여야 그쪽으로 가지 않나」 → 맞다. 그래서 큐브 위치가 에피소드마다 달라야 하고, 8 ep 표본만 봐도 파지 위치 산포 93 × 87 mm — (영상, 동작) 쌍이 다양해진다", {"size": 11}),
     ("▪ 시연자가 사람이든 스크립트든 기록되는 건 (영상, 동작) 쌍이고 그 대응만 맞으면 된다 — 큐브를 로봇이 잡을 자리에 놓았으니 정확히 맞는다", {"size": 11})])
panel(s, M + Cm(16.2), TOP + Cm(7.0), Cm(15.7), Cm(5.7))
txt(s, M + Cm(16.7), TOP + Cm(7.25), Cm(14.8), Cm(5.4),
    [("에피소드 1개 절차 (replay_v6_real.py)", {"size": 12, "bold": True, "color": NAVY}),
     ("[기록 OFF] ① 파지 프레임 관절로 MoveJoint (조 열림)", {"size": 11, "mono": True, "gap": 4}),
     ("[기록 OFF] ② 「조 사이에 큐브 놓고 Enter」", {"size": 11, "mono": True}),
     ("[기록 OFF] ③ 시작 자세로 MoveJoint", {"size": 11, "mono": True}),
     ("[기록 ON ] ④ 카운트다운 → MoveSplineJoint(ASYNC) + 그리퍼 시간축 구동 + 명령값 30 Hz 발행", {"size": 11, "mono": True}),
     ("[기록 OFF] ⑤ 큐브 회수", {"size": 11, "mono": True}),
     ("▪ 한계는 v6 위치 분포(9×9 cm) 안. 넓히려면 궤적 워핑(파지 전 오프셋 블렌딩) 또는 그때 직접교시 보강", {"size": 11, "gap": 6}),
     ("▪ 재생 3~5 ep 는 sim/real 영상 나란히 → 도메인 갭 정량화에도 씀", {"size": 11})])
foot(s, "「더 좋은 방법 있어?」 → 재생 방식의 최대 난점(큐브 위치 재현)을 「로봇이 위치를 알려주게」 로 뒤집은 것이 채택안")
note(s, "네 가지를 비교했다. 목적이 화면 적응이라 행동은 그대로 두는 재생이 맞고, 큐브 위치 문제는 로봇이 파지 자세를 먼저 잡아주면 사라진다.")

# ═════════════════════════ 22. v7 도구 체인 ═════════════════════════
s = slide("v7 도구 체인 — 기록기는 새로 짜지 않았다 (physical_ai_server 재사용)", "16 / v7")
BW, BH = Cm(4.9), Cm(2.5)
flow(s, M, TOP + Cm(0.3), [("camera_uvc_node.py ×2\n1280×720 → 960×720\n→ 640×480 compressed", NAVY), ("replay_v6_real.py\n궤적 재생 + 그리퍼\n+ /replay/joint_command", NAVY2),
                            ("gripper_ctl.py --node\npolicy/gripper → DO", NAVY2), ("physical_ai_server\nm1013_config.yaml\nLeRobot v2.1 기록", AMBER),
                            ("v7 데이터셋\naction=명령 · state=실측\ncamera1·2", GREEN), ("이어학습\nact_v6_tcp0725 베이스", GREEN)],
     BW, BH, gap=Cm(0.5), size=10.5)
panel(s, M, TOP + Cm(3.6), Cm(15.6), Cm(9.0), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(3.9), Cm(14.7), Cm(8.6),
    [("발견 — OMX 데이터도 이 기록기로 찍었다", {"size": 12.5, "bold": True, "color": NAVY}),
     ("▪ physical_ai_server/data_processing/lerobot_dataset_wrapper.py · data_manager.py — LeRobotDataset.create 기반 기록 파이프라인 존재", {"size": 11, "gap": 4}),
     ("▪ 로봇 타입 = config/<type>_config.yaml 파일명 → m1013_config.yaml 만 넣으면 UI 목록에 자동", {"size": 11}),
     ("▪ 처음에 기록기를 직접 짜려 했다가 확인 후 중단 — 헛수고 회피", {"size": 11, "color": GREY}),
     ("★ M1013 엔 리더 암이 없다", {"size": 12.5, "bold": True, "color": RED, "gap": 8}),
     ("OMX 는 리더-팔로워: action = 리더 관절, state = 팔로워 실측. 데이터 매니저는 leader_msgs 가 None 이면 action 을 못 만든다.", {"size": 11, "gap": 4}),
     ("→ replay_v6_real.py 가 의도한 관절 목표를 /replay/joint_command (JointState) 로 30 Hz 발행해 리더 역할. action = 명령값 = v6 의 action 정의와 동일, state = /joint_states", {"size": 11, "bold": True}),
     ("   /joint_states 를 양쪽에 쓰면 action == state 가 되어 v6 규약(state[t]=action[t−1])과 어긋난다", {"size": 11, "color": GREY})])
table(s, M + Cm(16.2), TOP + Cm(3.6), Cm(15.7),
      [["제약", "대응"],
       ["MoveSplineJoint 웨이포인트 100개 제한", "600 프레임 → 100 다운샘플, 근사오차 측정 출력 (최대 1.12°, 2° 초과 시 경고)"],
       ["두산 서비스는 도(deg), 데이터는 rad", "변환 지점마다 ⚠️ 주석. 놓치면 57배 이동"],
       ["v7 action 은 실측이 아니라 명령", "스플라인 근사가 원본과 달라도 데이터엔 무관 (실제 동작이 그대로 남음)"],
       ["안전", "시작·종료·예외·Ctrl+C 전부 그리퍼 열림 · MoveStop · --speed 기본 20, 처음 10 권장 · --dry 로 궤적 사전 검증"],
       ["그리퍼 채널", "joint_order 7번째 gripper = 0.0(닫힘)/1.0(열림)"]],
      widths=[4.3, 8.2], size=10.5, rh=Cm(0.98))
foot(s, "카메라 노드는 컨테이너(cv2 4.13 · numpy 1.26)에서 크롭 정확도 검증 — 호스트 cv2 는 numpy 2.x 와 충돌")
note(s, "기록기가 이미 있어서 설정 파일 하나로 끝났다. 대신 리더 암 부재 문제를 재생 스크립트가 명령값을 발행하는 것으로 풀었다.")

# ═════════════════════════ 23. 작업대 ═════════════════════════
s = slide("작업대 — 필요 크기 · 상판 높이 허용오차 · 로봇 설치 방식", "17 / 실기 준비")
table(s, M, TOP + Cm(0.2), Cm(15.6),
      [["159 ep 전수 (베이스 기준)", "x", "y"],
       ["파지 위치 범위", "0.708 ~ 0.908 (200)", "−0.325 ~ −0.200 (125)"],
       ["놓기 위치 범위", "0.657 ~ 0.878 (220)", "−0.278 ~ +0.040 (318)"],
       ["전체", "0.657 ~ 0.908 (251)", "−0.325 ~ +0.040 (365)"],
       [("필요 작업대 (여유 50)", {"bold": True}), ("351 → 40 cm", {"bold": True}), ("465 → 50 cm", {"bold": True})],
       ["권장 중심", "x ≈ 0.78", "y ≈ −0.14"]],
      widths=[4.2, 3.8, 3.8], size=10.5, rh=Cm(0.7))
table(s, M + Cm(16.2), TOP + Cm(0.2), Cm(15.7),
      [["상판 Δ (실물−설계 0.4624)", "큐브윗면↔판", "조끝↔상판", "판정"],
       ["−15", "17.0", "22.0", "물림 13 부족"],
       [("−13", {"bold": True}), "15.0", "20.0", ("OK 낮은 쪽 한계", {"color": GREEN})],
       ["0", "2.0", "7.0", "설계"],
       [("+2", {"bold": True}), "0.0", "5.0", ("OK 높은 쪽 한계", {"color": GREEN})],
       ["+3", ("−1.0", {"color": RED}), "4.0", ("판이 큐브를 누름", {"color": RED})]],
      widths=[4.0, 2.6, 2.6, 3.4], size=10.5, rh=Cm(0.7))
txt(s, M + Cm(16.2), TOP + Cm(4.6), Cm(15.7), Cm(1.4), [("허용 −13 ~ +2 mm — 비대칭. 애매하면 낮게. 측정: 조 끝(플랜지 83)을 상판에 대고 z 읽기, ±2 mm 정밀도", {"size": 11, "bold": True, "color": AMBER})])
table(s, M, TOP + Cm(6.3), CW,
      [["벗어났을 때", "소요", "내용"],
       ["① 작업대 조정 (최선)", "10분", "높으면 로봇 베이스에 심 · 낮으면 상판에 판"],
       ["② OFFSET 재변환", "6.5초", "convert_v6_m1013.py OFFSET[2] += Δ. n_ok 159/159 · min|q5| ≥ 30° 확인"],
       ["③ 베이스 재학습", "2h45m", "v7 수집은 재생이라 ②만으로 됨. 베이스 오차는 이어학습이 교정 → 급하지 않음"]],
      widths=[3.6, 1.6, 9.8], size=10.5, rh=Cm(0.7))
table(s, M, TOP + Cm(9.4), CW,
      [["로봇 설치 (두산: 베이스 Ø9 ×4 M8 20 N·m, 토크 10배·중량 5배 견디는 면)", "min|q5| (IK 20 ep)", "판정"],
       ["상판이 베이스보다 46 cm 위 (설계값)", "58.5°", ("안전 — 재변환·재학습 불필요", {"color": GREEN})],
       ["20 cm 위", "33.0°", "괜찮음"],
       ["베이스가 작업대에 직접 볼트 (같은 평면)", ("11.1°", {"color": RED, "bold": True}), ("손목 특이점 — J4·J6 폭주 위험. 받침대로 20~46 cm 올릴 것", {"color": RED})]],
      widths=[7.0, 2.6, 5.4], size=10.5, rh=Cm(0.7))
foot(s, "설치 방식 3안: 베이스 플레이트+클램프 / 별도 스탠드(권장, 높이를 우리가 정함) / 기존 탭 구멍 활용 — 도착 후 작업대를 보고 결정. 절차서 §7")
note(s, "작업대는 크기보다 위치와 높이가 결정적이다. 높이 허용이 비대칭이고, 로봇을 작업대에 직접 붙이면 손목 특이점에 가까워진다.")

# ═════════════════════════ 24. 생성 파일 ① 코드 ═════════════════════════
s = slide("생성 파일 ① — 코드 (전부 /home/kim/m1013/)", "산출물")
table(s, M, TOP + Cm(0.2), CW,
      [["파일", "역할", "실행 / 검증", "비고"],
       [("gripper_ctl.py", {"mono": True}), "히스테리시스+최소유지 · grip-lead · ROS2 DO/DI 래퍼", "python3 gripper_ctl.py (selftest) / --node", "LEAD_*·DO_INDEX 는 실물에서"],
       [("measure_grip_lead.py", {"mono": True}), "공압 개폐 지연 실측 → LEAD 권장값", "--dry (배선) / -n 20", "실압·조임 후 측정"],
       [("camera_uvc_node.py", {"mono": True}), "U20CAM 1280×720 → 960×720 → 640×480 compressed 발행", "--preview / --dev N --name camera1", "컨테이너에서 실행"],
       [("replay_v6_real.py", {"mono": True}), "v7 수집: 파지자세 유도 → 재생 + 그리퍼 + 명령값 30 Hz", "--dry (궤적 검증) / --episodes", "MoveSplineJoint 100점 · rad→deg"],
       [("m1013_config.yaml", {"mono": True}), "physical_ai_server 기록기 설정 (leader=/replay/joint_command)", "docker cp → config/", "키 구조 OMX 와 일치 검증"],
       [("wristcam_check.py", {"mono": True}), "손목캠 시야 검증 — Isaac 없이 순수 기하", "python3 wristcam_check.py 63.4 85.6", "★ 검증 정본 (09-11 wristcam_pose.py 와 연동)"],
       [("wristcam_solve.py", {"mono": True}), "(수정) HFOV 인자화 · place_cam(q) 자세별 DELTA · 저장 비치명화", "./python.sh … 85.6", "Isaac 렌더용"],
       [("convert_v6_m1013.py", {"mono": True}), "(수정) JAW_CLEAR 0.007 → TCP 0.0725 + 근거 주석", "--out v6_staging", "6.5초"],
       [("prep_replay_ep.py", {"mono": True}), "(수정) 기본 staging → v6_staging + 폐기본 주석", "", ""],
       [("cameras_v6match.json", {"mono": True}), "(추가) camera_hardware 블록 — 기종·크롭별 화각·불일치 기록", "", "fitted 값 미변경"],
       [("make_install_docx_0908.py", {"mono": True}), "설치절차서 docx 생성기 (§0~7)", "python3 make_install_docx_0908.py", "LibreOffice 로 PDF 검수"],
       [("make_report_pptx_0909.py", {"mono": True}), "이 PPT 생성기", "", "img_0909/ 사용"]],
      widths=[3.4, 6.0, 4.0, 3.6], size=10, rh=Cm(0.82))
foot(s, "09-11 갱신: wristcam_pose.py(자세 정본) · 손목캠 브래킷 CAD 생성기 · 3D 뷰어 등이 추가됨 — 본 정리 범위(9/8~9/9) 밖")
note(s, "코드 산출물. 전부 자체 테스트나 건식 실행을 통과했고, 실물에서 채울 상수만 남았다.")

# ═════════════════════════ 25. 생성 파일 ② 문서·CAD·데이터 ═════════════════════════
s = slide("생성 파일 ② — 문서 · CAD · 데이터 · 모델", "산출물")
table(s, M, TOP + Cm(0.2), Cm(16.0),
      [["문서 (cad/발주/ · 대화록 및 PPT/)", "내용"],
       [("M1013_그리퍼_설치절차서_20260908.docx", {"mono": True, "size": 9.5}), "계통도 3종 · 준비물 · 설치 6단계(+5.5 리머) · 컨트롤러 설정 · 확인 항목 · §6 간섭 해결 · §7 작업대"],
       [("구매목록_20260909.md", {"mono": True, "size": 9.5}), "A 절삭 2 · B 볼트 7 · C 공압 4 · D 전기 · E 카메라+케이블 · F 공구 · G 선택 · 안 사도 되는 것 · 체크리스트"],
       [("발주서.md (갱신)", {"mono": True, "size": 9.5}), "볼트 표 3건 정정 · 조립 순서 4번 신설 · 플랜지 검증 블록 · ✅해결 블록 · 공압 확정 블록 · 툴 외형"],
       [("img_0909/ (10장)", {"mono": True, "size": 9.5}), "valve_6view · flange_p226 · valve_bracket_section · hysteresis · tcp_tradeoff · hfov_compare · 손목캠 렌더 4"],
       [("대화록/20260908-09_….md", {"mono": True, "size": 9.5}), "이 PPT 와 함께 생성한 상세 대화록"]],
      widths=[5.2, 8.8], size=10, rh=Cm(0.86))
table(s, M + Cm(16.6), TOP + Cm(0.2), Cm(15.3),
      [["CAD (cad/)", "내용"],
       [("1_b/ · 2_b/", {"mono": True}), "SY5120-5LOZ-01 STEP AP214 + 6면도 DXF (CADENAS, CC BY-ND)"],
       [("speed_1/ · speed_2/", {"mono": True}), "AS1201F-M5-04A DXF + STEP"],
       [("noise_1/ · noise_2/", {"mono": True}), "AN110-01 DXF + STEP"],
       [("valve_bracket_sy5120.step/.stl", {"mono": True}), "v3 — 카운터싱크 Ø7.0 · 스페이서 6 · 26.19 g · 출력 가능"],
       [("wristcam_bracket.*", {"mono": True}), ("09-09 시점 출력 금지 → 09-11 재설계됨", {"color": AMBER})]],
      widths=[5.0, 7.8], size=10, rh=Cm(0.78))
table(s, M + Cm(16.6), TOP + Cm(5.4), Cm(15.3),
      [["데이터 · 모델 (컨테이너 physical_ai_server)", "내용"],
       [("v6_staging (=_tcp0725)", {"mono": True}), "현행 변환본 TCP 0.0725 · _tcp0675 · _tcp012 보존"],
       [("m1013_act_pick_and_place_v6_joint", {"mono": True}), "재조립 159 ep / 76,345 프레임 · 구본 _tcp012_BAK"],
       [("/root/train_m1013_act_v6_tcp0725", {"mono": True}), "ACT 100K · loss 0.054 · 체크포인트 10개 · 구 train_m1013_act_v6 보존"],
       [("/workspace/v6_staging_m1013", {"mono": True}), "조립용 반입본 (docker cp)"]],
      widths=[5.0, 7.8], size=10, rh=Cm(0.78))
txt(s, M, TOP + Cm(6.6), Cm(16.0), Cm(5.6),
    [("메모리 (세션 간 지식)", {"size": 12.5, "bold": True, "color": NAVY}),
     ("▪ m1013-sy5120-valve-cad — M3 옆면 확정 · 스페이서 · 어댑터 STEP Z 뒤집힘 함정", {"size": 10.5, "gap": 3}),
     ("▪ m1013-gripper-connection-verified — 로봇 플랜지까지 검증 완료, 미검증 0", {"size": 10.5}),
     ("▪ m1013-step5-cameras — U20CAM 확정 · 85.6° · DELTA 버그 · wristcam_check", {"size": 10.5}),
     ("▪ m1013-tcp-grasp-point — 0.0725 · 3세대 정리 · 기본값 지뢰", {"size": 10.5}),
     ("별도 세션 산출물 (같은 날, 본 대화 밖)", {"size": 12, "bold": True, "color": GREY, "gap": 8}),
     ("▪ M1013_연구방향_20260909.docx · 업무보고_20260909.md", {"size": 10.5, "gap": 3})])
foot(s, "구본 파일은 하나도 삭제하지 않았다 — git · _BAK · _tcp012 로 전부 되돌릴 수 있음")
note(s, "문서, CAD, 데이터, 모델 산출물 목록. 무엇이 무엇인지 여기서 찾으면 된다.")

# ═════════════════════════ 26. 현재 상황 ═════════════════════════
s = slide("현재 상황 — 어디까지 왔나 (09-09 종료 + 09-11 갱신 반영)", "현황")
for i, (t, col, lines) in enumerate([
    ("완료", GREEN, ["어댑터·핑거 설계 (미검증 0)", "밸브 브래킷 v3 (출력 가능)", "TCP 0.0725 · 재변환 · 재학습", "카메라 기종·화각·크롭 파이프라인", "소프트웨어 3종 + v7 도구 5종", "구매목록 · 설치절차서 · 발주서"]),
    ("진행 / 대기", AMBER, ["절삭 외주 2건 — 발주 필요 ★", "재고품 B~F 주문", "밸브 뗄 때 확인 4건 (소음기 각인 · S/O 각인 · 튜브 굵기 · 코일호스 끝단)", "손목캠 브래킷 — 09-11 재설계·위치 변경 (0,−65,−10)", "작업대 규격·높이 (도착 후)"]),
    ("미착수", RED, ["v7 수집 실행 (로봇 필요)", "grip-lead 실측 (벤치)", "Isaac 씬 툴 외형 갱신 (X −71~+94.5, 밸브 포함 STL)", "Tool Weight·CoG 재산정 (손목캠 확정 후)", "DO 릴레이 개재 결정", "시뮬 정면캠 재정합 — 후순위로 뺌"])]):
    x = M + i * (Cm(10.5) + Cm(0.3))
    panel(s, x, TOP + Cm(0.3), Cm(10.5), Cm(8.3), BGSOFT if i == 1 else WHITE)
    chip(s, x + Cm(0.4), TOP + Cm(0.7), Cm(9.7), t, fill=col, h=Cm(0.95))
    txt(s, x + Cm(0.45), TOP + Cm(2.0), Cm(9.7), Cm(6.3), [("▪ " + l, {"size": 11, "gap": 6}) for l in lines])
panel(s, M, TOP + Cm(9.0), CW, Cm(3.5))
txt(s, M + Cm(0.5), TOP + Cm(9.3), CW - Cm(1.0), Cm(3.1),
    [("★ 09-11 갱신 (이 정리 범위 밖이지만 현재 상태에 영향)", {"size": 12.5, "bold": True, "color": RED}),
     ("▪ 로봇 도착 9/20 → 9/14 로 앞당겨짐. 절삭 외주 금구가 로봇보다 늦는 것이 새 병목 — 발주가 급하다", {"size": 11.5, "gap": 4}),
     ("▪ 손목캠 위치가 (60,−75,5) → 그리퍼 중앙 (0,−65,−10), 보드 세로 장착으로 변경. 자세 정본 wristcam_pose.py. 어댑터 clearance 확대·손목캠 브래킷 재설계·3D 뷰어 추가", {"size": 11.5}),
     ("▪ 따라서 본 PPT 의 손목캠 좌표(60,−75,5)·브래킷 「출력 금지」 서술은 09-09 시점 기록 — 최신은 git 6649bcc 이후 참조", {"size": 11.5, "color": GREY})])
foot(s, "메모리 m1013-robot-arrival-plan · m1013-step5-cameras 최신본 기준")
note(s, "완료·진행·미착수 3열. 09-11에 로봇 도착일과 손목캠 위치가 바뀌었으니 그 부분은 최신 자료를 봐야 한다.")

# ═════════════════════════ 27. 다음 할 것 + 고려사항 ═════════════════════════
s = slide("다음 할 것 · 고려해야 할 것", "다음")
table(s, M, TOP + Cm(0.2), Cm(16.2),
      [["시점", "할 것", "막는 것"],
       ["지금", "어댑터·핑거 절삭 발주 (cad/발주/어댑터, 핑거 STEP+DXF+발주서 본문)", "없음 ★ 리드타임"],
       ["지금", "구매목록 A~F 주문 · 밸브 브래킷 PETG 출력", "없음"],
       ["부품 도착", "벤치 배관 → 압력·방향·스피드컨트롤러 조임 → measure_grip_lead → LEAD 값 반영", "부품"],
       ["로봇 도착 (9/14)", "작업대 규격·높이 측정 → 허용 −13~+2 확인 → 설치 방식 결정 → 어댑터 가조립 → Ø6 현장 리머", "로봇"],
       ["도착 후", "저속 1 ep 재생(--speed 10) → v7 30~50 ep → 이어학습 → 실기 추론", "위 전부"]],
      widths=[2.2, 8.6, 2.6], size=10.5, rh=Cm(0.86))
panel(s, M + Cm(16.8), TOP + Cm(0.2), Cm(15.1), Cm(12.3), BGSOFT)
txt(s, M + Cm(17.3), TOP + Cm(0.5), Cm(14.2), Cm(11.9),
    [("고려해야 할 것", {"size": 13, "bold": True, "color": AMBER}),
     ("▪ 절삭 외주가 로봇보다 늦으면 → 핑거는 PETG 시제품으로 먼저 끼워 v7 을 찍을 수 있는지 검토 (강성·마모 리스크). 어댑터는 대체 불가", {"size": 11, "gap": 5}),
     ("▪ 클로킹은 X1/X2 커넥터가 어댑터 짧은 변(±Y)으로 오게 — 긴 변 쪽이면 반경 41.5 커넥터가 판 밑 28 mm 에 묻혀 M8 케이블 굽힘이 빠듯", {"size": 11}),
     ("▪ 작업대 높이가 설계보다 높으면 +2 mm 밖에 여유가 없다 — 애매하면 낮게. 로봇을 작업대에 직접 볼트하면 min|q5| 11° 로 손목 폭주 위험", {"size": 11}),
     ("▪ v7 ② 단계에서 사람 손이 조 사이 — 정지 확인·무압·원격 시작. 처음엔 --speed 10 한 에피소드", {"size": 11}),
     ("▪ PETG 브래킷 크리프 → 록타이트 243 또는 M3 0.3 N·m. 인쇄 방향은 축력이 압축이 되는 쪽(문제 없음)", {"size": 11}),
     ("▪ DO 돌입 42 mA/50 mA — 릴레이 개재 여부를 결선 전에 결정", {"size": 11}),
     ("▪ 손목캠은 09-11 위치 기준으로 wristcam_check 재실행 필요 (본 PPT 수치는 09-09 위치)", {"size": 11}),
     ("▪ Tool Weight ≈1.30 kg + 카메라, CoG +Y 이동 — 조립 후 실측·컨트롤러 갱신", {"size": 11}),
     ("▪ 데이터셋 메타(robot_type omx_f, state names EE) 는 v7 설정에서 정정 — 학습엔 무해하나 오독 유발", {"size": 11}),
     ("▪ 이어학습 베이스는 train_m1013_act_v6_tcp0725. 구 train_m1013_act_v6 (0.12) 를 쓰면 47.5 mm 편향", {"size": 11, "bold": True})])
foot(s, "진짜 병목 순서: 절삭 발주 → 로봇 도착 → 작업대 확정 → v7. 소프트웨어는 더 이상 병목이 아니다")
note(s, "지금 당장은 발주. 부품과 로봇이 오면 벤치 → 설치 → v7 순서. 고려사항은 전부 문서에 반영돼 있다.")

# ═════════════════════════ 28. 링크 ═════════════════════════
s = slide("링크 · 참조", "참조")
L = [("SMC PARTcommunity (CADENAS) — SY5120·AS1201F·AN110 CAD 입수처", "https://smc.partcommunity.com/"),
     ("SMC SY3000/5000/7000/9000 Body Ported 카탈로그 PDF — p.7~9 SY5000 치수, 2-M3 22.6 · 2-ø3.2 36×11.6", "https://content2.smcetech.com/pdf/SY5000.pdf"),
     ("SMC AS 시리즈 엘보 스피드컨트롤러 카탈로그 — AS1201F-M5-04A 치수 A 23.5", "https://content2.smcetech.com/pdf/AS_1F-A_EU.pdf"),
     ("MISUMI SY5120-5LOZ-01 (한국) — CAD 다운로드 대안", "https://kr.misumi-ec.com/vona2/detail/221300029672/?HissuCode=SY5120-5LOZ-01"),
     ("INNOMAKER U20CAM-720P — 32×32 · Ø2.2 ×4 · M12 · FOV D120/H102", "https://www.inno-maker.com/product/u20cam-720p/"),
     ("ISO 10642 M3 접시머리 치수 (dk 이론최대 6.72) — 카운터싱크 Ø7.0 근거", "https://fullerfasteners.com/tech/iso-10642-specifications-hex-socket-countersunk-head-screws/"),
     ("AS1201F-M5-04 가격 — RS Korea ₩16,394/개", "https://us.rs-online.com/product/smc-corporation/sy5120-5loz-01t/70073782/"),
     ("tx90 GitHub (비공개) — run_policy_tx90.py 그리퍼 규약 원본", "https://github.com/dlcodnjs817/tx90")]
for i, (t, u) in enumerate(L):
    y = TOP + Cm(0.3) + i * Cm(0.95)
    txt(s, M, y, CW, Cm(0.9), [(t, {"size": 11.5}), (u, {"size": 10, "color": NAVY2, "mono": True, "link": u, "gap": 1})], gap=1)
panel(s, M, TOP + Cm(8.2), CW, Cm(4.3), BGSOFT)
txt(s, M + Cm(0.5), TOP + Cm(8.5), CW - Cm(1.0), Cm(3.9),
    [("로컬 참조 (/home/kim/m1013/)", {"size": 12.5, "bold": True, "color": NAVY}),
     ("Doosan_Robotics_User_Manual_V2.12_v2.12_KR(MH-Series).pdf — p.100 베이스 고정 · p.217 로봇 고정·베이스 도면 · p.226 툴 플랜지 치수 도면 ★", {"size": 11, "mono": True, "gap": 4}),
     ("doosan-robot2/dsr_msgs2/srv/io/SetToolDigitalOutput.srv · GetToolDigitalInput.srv — DO/DI 극성 원본", {"size": 11, "mono": True}),
     ("doosan-robot2/dsr_description2/meshes/m1013_collision/MF1013_6_0.dae — link_6 (translate −0.712,−1.363,−26.185 적용 시 Z max = 0 = 플랜지 면)", {"size": 11, "mono": True}),
     ("physical_ai_tools/physical_ai_server/config/omx_f_config.yaml — 기록기 설정 원형 · data_processing/data_manager.py — state/action 조립 로직", {"size": 11, "mono": True}),
     ("대화록: 대화록 및 PPT/대화록/20260908-09_*.md · 이전: 20260906_*.md · 20260907_*.md", {"size": 11, "mono": True})])
foot(s, "PPT 생성: make_report_pptx_0909.py · 이미지: 대화록 및 PPT/img_0909/")
note(s, "외부 링크와 로컬 파일 참조.")

prs.save(OUT)
print("저장:", OUT, "| 슬라이드", len(prs.slides))

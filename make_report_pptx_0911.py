#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-09-11 정리 PPT — 손목캠 브래킷 재설계 · 어셈블리 재검증 · Isaac 시연 생성 파이프라인 구축.

  python3 make_report_pptx_0911.py  →  대화록 및 PPT/M1013_20260911.pptx

파이프라인 개요 → 항목별 과정·트러블슈팅 → 알고리즘 선택 근거 → 생성 파일 → 현황 → 다음 할 일.
상세 설명은 발표자 노트에.
"""
import os
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Pt

NAVY = RGBColor(0x2F, 0x3D, 0x9E); INK = RGBColor(0x15, 0x18, 0x1D); GREY = RGBColor(0x62, 0x6B, 0x78)
LINE = RGBColor(0xD8, 0xDC, 0xE3); RED = RGBColor(0xA9, 0x33, 0x1D); GREEN = RGBColor(0x1F, 0x6B, 0x4A)
AMBER = RGBColor(0x9A, 0x6A, 0x00); BGSOFT = RGBColor(0xED, 0xEF, 0xF3); WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ORANGE = RGBColor(0xE0, 0x7A, 0x2E); TEAL = RGBColor(0x2E, 0x8B, 0x8B); LNAVY = RGBColor(0x5B, 0x69, 0xC2)
FONT, MONO = "맑은 고딕", "Consolas"
SW, SH = Cm(33.867), Cm(19.05)
BASE = os.path.dirname(os.path.abspath(__file__)); DOCS = os.path.join(BASE, "대화록 및 PPT"); IMG = os.path.join(DOCS, "img_0911")
OUT = os.path.join(DOCS, "M1013_20260911.pptx")
prs = Presentation(); prs.slide_width, prs.slide_height = SW, SH; BLANK = prs.slide_layouts[6]
ART = "https://claude.ai/code/artifact/de6b7321-be57-4b7a-b8dd-f64fa34dc429"


def _set(run, size=14, bold=False, color=INK, font=FONT):
    run.font.name = font; run.font.size = Pt(size); run.font.bold = bold; run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None: el = rPr.makeelement(qn(tag), {}); rPr.append(el)
        el.set("typeface", font)


def slide(title=None, step=None):
    s = prs.slides.add_slide(BLANK)
    if title:
        r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Cm(1.75)); r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background(); r.shadow.inherit = False
        tf = r.text_frame; tf.margin_left = Cm(0.95); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        run = tf.paragraphs[0].add_run(); run.text = title; _set(run, 19, True, WHITE)
        if step:
            tb = tbox(s, SW - Cm(11), Cm(0.42), Cm(10.1), Cm(0.95)); p = tb.paragraphs[0]; p.alignment = PP_ALIGN.RIGHT
            run = p.add_run(); run.text = step; _set(run, 12, False, RGBColor(0xC5, 0xCC, 0xF2))
    return s


def tbox(s, x, y, w, h):
    b = s.shapes.add_textbox(x, y, w, h); tf = b.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; return tf


def txt(s, x, y, w, h, lines, size=13, gap=4):
    tf = tbox(s, x, y, w, h)
    for i, item in enumerate(lines):
        t, o = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.space_before = Pt(0 if i == 0 else o.get("gap", gap)); p.line_spacing = o.get("ls", 1.15)
        run = p.add_run(); run.text = t; _set(run, o.get("size", size), o.get("bold", False), o.get("color", INK), MONO if o.get("mono") else FONT)
    return tf


def panel(s, x, y, w, h, fill=None, border=LINE, width=1.0):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h); b.fill.solid(); b.fill.fore_color.rgb = fill or WHITE
    b.line.color.rgb = border; b.line.width = Pt(width); b.shadow.inherit = False; b.adjustments[0] = 0.03; b.text_frame.text = ""; return b


def head(s, x, y, w, t, color=NAVY, size=14):
    txt(s, x, y, w, Cm(0.8), [(t, {"size": size, "bold": True, "color": color})])


def table(s, x, y, w, rows, widths=None, size=11, rh=Cm(0.72), header=True):
    shp = s.shapes.add_table(len(rows), len(rows[0]), x, y, w, rh * len(rows)); t = shp.table
    if widths:
        tot = sum(widths)
        for i, cw in enumerate(widths): t.columns[i].width = int(w * cw / tot)
    for ri, row in enumerate(rows):
        t.rows[ri].height = rh
        for ci, cell in enumerate(row):
            c = t.cell(ri, ci); c.margin_left = c.margin_right = Cm(0.15); c.margin_top = c.margin_bottom = Cm(0.03); c.vertical_anchor = MSO_ANCHOR.MIDDLE
            s_, o = (cell, {}) if isinstance(cell, str) else cell
            c.fill.solid(); c.fill.fore_color.rgb = NAVY if (header and ri == 0) else o.get("bg", WHITE if ri % 2 else BGSOFT)
            p = c.text_frame.paragraphs[0]; p.alignment = o.get("align", PP_ALIGN.LEFT)
            run = p.add_run(); run.text = s_
            _set(run, o.get("size", size), o.get("bold", header and ri == 0), WHITE if (header and ri == 0) else o.get("color", INK), MONO if o.get("mono") else FONT)
    return t


def pic(s, path, x, y, maxw, maxh, caption=None):
    im = Image.open(path); ar = im.width / im.height; w, h = maxw, int(maxw / ar)
    if h > maxh: h, w = maxh, int(maxh * ar)
    s.shapes.add_picture(path, int(x + (maxw - w) / 2), int(y + (maxh - h) / 2), width=w, height=h)
    if caption:
        tf = tbox(s, x, y + maxh + Cm(0.08), maxw, Cm(0.6)); p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = caption; _set(run, 10.5, False, GREY)


def foot(s, t):
    tf = tbox(s, Cm(1.0), SH - Cm(0.82), SW - Cm(2.0), Cm(0.6)); run = tf.paragraphs[0].add_run(); run.text = t; _set(run, 10, False, GREY)


def note(s, t): s.notes_slide.notes_text_frame.text = t


def chip(s, x, y, w, t, fill=GREEN, h=Cm(0.85), size=12):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h); b.fill.solid(); b.fill.fore_color.rgb = fill; b.line.fill.background(); b.shadow.inherit = False
    tf = b.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = t; _set(run, size, True, WHITE)


def flowbox(s, x, y, w, h, t, fill=NAVY, fg=WHITE, size=11.5, bold=True):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h); b.fill.solid(); b.fill.fore_color.rgb = fill
    b.line.color.rgb = LINE; b.line.width = Pt(0.75); b.shadow.inherit = False; b.adjustments[0] = 0.08
    tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Cm(0.1); tf.margin_top = tf.margin_bottom = Cm(0.05)
    for i, line in enumerate(t.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = line; _set(run, size if i == 0 else size - 2, bold if i == 0 else False, fg)
    return b


def arrow(s, x, y, w=Cm(0.7), h=Cm(0.5), down=False):
    a = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW if down else MSO_SHAPE.RIGHT_ARROW, x, y, w, h); a.fill.solid(); a.fill.fore_color.rgb = GREY; a.line.fill.background()


def flow(s, x, y, items, bw, bh, gap=Cm(0.55), fills=None, size=11.5):
    """가로 플로우: items 문자열 리스트. 반환 = 마지막 x"""
    for i, t in enumerate(items):
        fl = (fills[i] if fills else NAVY)
        flowbox(s, x, y, bw, bh, t, fill=fl, fg=WHITE if fl not in (BGSOFT, WHITE) else INK, size=size)
        if i < len(items) - 1: arrow(s, x + bw + Cm(0.05), y + bh / 2 - Cm(0.25), gap - Cm(0.1))
        x += bw + gap
    return x


M = Cm(1.0); CW = SW - 2 * M; TOP = Cm(2.35)
IM = lambda n: os.path.join(IMG, n)

# ═══════════ 1. 표지 ═══════════
s = slide(); r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH); r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background()
txt(s, Cm(2.2), Cm(4.6), Cm(29), Cm(2.4), [("M1013 손목캠 재설계 · 어셈블리 재검증 · Isaac 시연 생성 파이프라인", {"size": 30, "bold": True, "color": WHITE})])
txt(s, Cm(2.2), Cm(8.4), Cm(29), Cm(4), [("2026-09-11 작업 정리 — 과정 · 트러블슈팅 · 알고리즘 선택 근거 · 산출물 · 현황 · 다음 단계", {"size": 16, "color": RGBColor(0xC5, 0xCC, 0xF2)}),
    ("저장소 /home/kim/m1013 (브랜치 wristcam-bracket-redesign, 커밋 8bf468a → 8b0b054)  ·  로봇 도착 2026-09-14(월)", {"size": 13, "color": RGBColor(0xC5, 0xCC, 0xF2), "gap": 14})])
note(s, "오늘 하루 작업 전체 정리. 발표자 노트에 상세 설명과 근거 수치를 넣었다.")

# ═══════════ 2. 한 장 요약 ═══════════
s = slide("오늘 한 장 요약", "01 / 개요")
rows = [["영역", "시작 상태", "끝 상태", "핵심 수치"],
        ["손목캠 브래킷", "09-03 판 — 카메라 미선정 시절 임의 패드, 09-04 해와 불일치", "그리퍼 중앙 (0,−65,−10) · 보드 세로 장착 · 스탠드오프 실측 19 반영 → 출력 가능", "시야 여유 0.59 · 브래킷 화면 침범 0 · 간섭 0"],
        ["툴 어셈블리 검증", "09-07 판 STL, 핑거·밸브 브래킷 수정 이후 미갱신, 재생성 스크립트 없음", "make_tool_assembly.py — 최신 4부품 불리언 전 쌍 0", "관통 1건(675 mm³) 발견·수정"],
        ["Isaac 렌더", "GPU 드라이버 불일치로 불가", "실제 툴 메시 부착 손목캠 실사 12장, 로봇 자세 0.3 mm 이내", "함정 4개 잡음(상판 충돌체 등)"],
        ["학습 데이터", "OMX 시연 159개(영상은 OMX 리그 것)", "Isaac 스크립트 전문가 시연 생성기 — 큐브 위치·yaw 무작위, 6~13 s/에피소드", "1,000개 생성 중 → 학습 → 평가 자동"],
        ["닫힌 루프 평가", "없음 (08-24 미완)", "act_server ↔ Isaac 브릿지, 기하 파지 판정, 오라클 100%", "v6 정책 기준선 0% (도메인 갭)"],
        ["구매·문서", "카메라가 '이관'처럼 읽힘, M2 누락", "구매목록 E-1·B-8·G-2, 발주서·설치절차서 갱신, 카메라 매뉴얼 반영", "절삭 외주 2건 발주 대기"]]
table(s, M, TOP, CW, rows, widths=[2.2, 5.2, 6.4, 3.8], size=10.5, rh=Cm(1.55))
foot(s, "노란 항목 = 사용자 결정 대기: 절삭 외주 발주(오늘) · 작업대 높이(월요일 실측)")
note(s, "오늘은 크게 세 갈래였다. (1) 하드웨어: 손목캠 브래킷을 전면 재설계하고 4부품 전체를 최신 상태로 재검증. (2) 시뮬: Isaac 실사 렌더를 살리면서 잠복 버그 여러 개를 잡음. (3) 학습: 사용자 선택으로 'Isaac 시연 대량 생성 → ACT' 파이프라인을 처음부터 끝까지 구축해 밤새 돌아가게 함.")

# ═══════════ 3. 파이프라인 ① 데이터·학습 ═══════════
s = slide("파이프라인 ① 데이터 → 정책 — 오늘 추가된 갈래", "02 / 파이프라인")
head(s, M, TOP, CW, "기존 갈래 (8/20~9/9) — 사람 시연을 기하로 옮김")
y = TOP + Cm(0.9); bw, bh = Cm(4.6), Cm(1.55)
flow(s, M, y, ["OMX 사람 시연\n159 ep · 30 Hz", "v5 EE pose\nFK (omx_f.urdf)", "기하 변환\n오프셋·45° 보정·IK", "v6 M1013 관절\n영상은 OMX 리그 것", "ACT 학습\n100k 스텝", "정책 v6"], bw, bh, fills=[GREY, GREY, GREY, GREY, GREY, GREY])
head(s, M, y + Cm(2.2), CW, "오늘 추가 — Isaac 안에서 시연을 만든다 (사용자 ①안 선택)", color=ORANGE)
y2 = y + Cm(3.1)
flow(s, M, y2, ["큐브 무작위\n위치 ×1.5 · yaw 0~90°", "스크립트 전문가\nmin-jerk + IK 시드체인", "Isaac 렌더 2대\n실제 툴·손목캠 기하", "v8 데이터셋\nLeRobot v2.1 형식", "ACT 학습\n동일 설정", "닫힌 루프 평가\nIsaac ↔ act_server"], bw, bh, fills=[ORANGE, ORANGE, ORANGE, ORANGE, NAVY, NAVY])
head(s, M, y2 + Cm(2.2), CW, "월요일 이후 — 실기로 잇는다", color=GREEN)
y3 = y2 + Cm(3.1)
flow(s, M, y3, ["로봇 설치·실측\n작업대 높이", "재변환·재생성\n6 s / 1.8 h", "v6 궤적 재생 수집\nreplay_v6_real.py", "v7 실기 30~50 ep", "이어학습\nscratch / OMX / Isaac", "데이터 효율 곡선"], bw, bh, fills=[GREEN, GREEN, GREEN, GREEN, GREEN, GREEN])
txt(s, M, y3 + Cm(2.0), CW, Cm(1.2), [("회색 = 기존 · 주황 = 오늘 구축 · 초록 = 다음 주. 연구방향 문서(09-09)의 '데이터 효율 곡선'에 Isaac 사전학습 축이 추가된다.", {"size": 11, "color": GREY})])
note(s, "핵심 차이: 기존 갈래의 정책은 OMX 리그 카메라 영상으로 학습됐고 관절만 M1013이다. 오늘 갈래는 실제 M1013·툴·손목캠 기하로 렌더한 영상으로 학습하므로 실물 카메라 뷰에 훨씬 가깝다. 변환(FK/IK)은 학습이 아니라 순수 기하다.")

# ═══════════ 4. 파이프라인 ② 하드웨어 검증 체인 ═══════════
s = slide("파이프라인 ② 하드웨어 설계 검증 체인 — 위치를 바꾸면 이 순서로 돌린다", "02 / 파이프라인")
y = TOP + Cm(0.3); bw, bh = Cm(4.55), Cm(1.75)
flow(s, M, y, ["wristcam_pose.py\n카메라 자세 단일 소스", "make_wristcam_bracket.py\n브래킷 STEP/STL 생성", "make_tool_assembly.py\n4부품 불리언 간섭", "wristcam_check.py\n큐브 궤적 시야 여유", "wristcam_occlusion.py\n브래킷 화면 침범·손목 간격", "wristcam_preview / render\n소프트웨어·Isaac 렌더"], bw, bh, fills=[ORANGE, NAVY, NAVY, NAVY, NAVY, NAVY])
rows = [["단계", "무엇을 판정하나", "판정 기준", "오늘 결과"],
        ["형상 감사 (cadquery)", "STEP 을 커널로 열어 치수·구멍 위치", "도면·SMC CAD·두산 매뉴얼과 일치", "어댑터·핑거·밸브 브래킷 전부 일치"],
        ["불리언 간섭", "부품 쌍마다 intersect().Volume()", "0.000 mm³ (정점 거리는 보조 지표)", "손목캠↔어댑터 675 mm³ 관통 발견 → 무릎 추가 → 0"],
        ["시야 여유", "8 ep × 파지 전 2 s 큐브 투영 |u|,|v| 최대", "< 1.0 (가장자리), 렌즈오차 ±12 mm 포함", "0.59 / 강건 0.63"],
        ["화면 침범", "브래킷 정점 투영 vs 큐브 궤적 거리", "브래킷이 큐브 궤적과 안 겹침", "정점 0개 화면 안"],
        ["렌더 확인", "실제 메시로 카메라가 보는 화면", "큐브 보이고 브래킷 안 가림", "SW 프리뷰 12장 + Isaac 실사 12장 일치"]]
table(s, M, y + Cm(2.4), CW, rows, widths=[3.2, 5.6, 5.2, 6.0], size=10.5, rh=Cm(1.05))
foot(s, "교훈: 간섭은 반드시 불리언으로. 정점 최근접 거리는 큰 평판(어댑터)에서 관통을 놓쳤다.")
note(s, "이 체인이 오늘 만들어진 이유: 09-07까지는 STEP/STL만 있고 생성 스크립트가 없어서, 부품이 바뀌면 검증을 처음부터 손으로 다시 해야 했다. 지금은 wristcam_pose.py 한 곳만 고치고 다섯 스크립트를 순서대로 돌리면 된다.")

# ═══════════ 5. 파이프라인 ③ 시연 생성·평가 루프 ═══════════
s = slide("파이프라인 ③ Isaac 시연 생성 · 학습 · 평가 루프 (밤새 자동 실행 중)", "02 / 파이프라인")
y = TOP + Cm(0.3); bw, bh = Cm(5.6), Cm(1.8)
flow(s, M, y, ["gen_isaac_demos.py (Isaac)\n전문가 궤적 + weld + 렌더 2대", "HF 캐시 dlcodnjs/m1013_isaac_v8\nparquet + h264 mp4 + meta", "lerobot train (컨테이너)\n--policy.type=act 100k", "act_server.py (컨테이너)\nlocalhost:5555", "eval_isaac_closedloop.py (Isaac)\n기하 파지 판정"], bw, bh, fills=[ORANGE, NAVY, NAVY, TEAL, TEAL], size=11)
panel(s, M, y + Cm(2.5), Cm(15.6), Cm(6.6))
txt(s, M + Cm(0.4), y + Cm(2.7), Cm(14.8), Cm(6.2), [("run_v8_pipeline.sh — 체인", {"bold": True, "color": NAVY}),
    "1. 생성기 PID 종료 대기 (1,000 ep, seed 1, table_z 0.4624)", "2. info.json 에피소드 수 확인 (≥100)", "3. 컨테이너에서 ACT 학습 → /root/train_m1013_act_isaac_v8 (v6 와 동일 설정)",
    "4. 평가 3종 각 30 ep: Isaac 정책 (v6 분포) · Isaac 정책 (1.5배 영역) · v6 정책 기준선", "5. 결과 → sim_out/eval_*/results.json + 에피소드별 그림",
    ("로그: sim_out/v8_pipeline.log · gen_v8.log", {"mono": True, "size": 10.5, "color": GREY})], size=11.5)
panel(s, M + Cm(16.2), y + Cm(2.5), CW - Cm(16.2), Cm(6.6))
txt(s, M + Cm(16.6), y + Cm(2.7), CW - Cm(17), Cm(6.2), [("규약 (v6 와 동일 — 학습 스크립트 무수정)", {"bold": True, "color": NAVY}),
    "observation.state[7] = action[t−1] (완전 추종 가정)", "action[7] = 관절 6 + 그리퍼 (열림 0.69 / 닫힘 −0.02, 임계 0.459, 5프레임 램프)",
    "camera1 = 손목캠 (세로 장착 원본 방향), camera2 = 정면캠", "640×480 30 fps, libx264 yuv420p (컨테이너 ffmpeg 파이프)",
    "큐브: 닫힘 순간 플랜지에 weld, 열림에 상판으로 스냅", ("컨테이너 lerobot 0.2.0 로더로 읽힘 확인", {"color": GREEN})], size=11.5)
foot(s, "생성 속도 6~13 s/에피소드 (GPU 공유 여부에 따라) · 학습 ~2.8 h · 평가 3종 ~1 h")
note(s, "평가는 weld를 쓰지 않는다. 정책이 큐브를 빗나가 닫아도 성공으로 찍히면 안 되므로, 닫힘 순간 큐브 중심이 플랜지 로컬 |x|≤12, |y|≤15, |z−TCP|≤20 mm 안에 있을 때만 잡힌 것으로 본다.")

# ═══════════ 6. 타임라인 ═══════════
s = slide("오늘 타임라인", "02 / 파이프라인")
rows = [["시각", "작업", "결과 / 발견"],
        ["오전", "손목캠 브래킷 감사 → 09-04 위치 여유 0.898, 렌즈 오차 +10 mm 면 이탈", "재배치 결정 (35,−45,0)"],
        ["", "A-프레임 설계 (베이스판이 큐브 가림) · 어댑터 관통 675 mm³ 발견 → 무릎", "브래킷 v2 · 어셈블리 재생성 스크립트"],
        ["", "4부품 감사, 구매목록 E-1(카메라)·B-8(M2) 추가, replay npz tcp 0.0675 낡음 발견 → 재생성", "정정 궤적에서 0.647 유지"],
        ["점심", "재부팅 (GPU 드라이버 불일치 해소) → Isaac 렌더 트러블슈팅 6건", "실사 12장, 로봇 0.3 mm 이내"],
        ["오후", "사용자 지적 '삐뚤어짐' → 롤 분석 → 그리퍼 중앙 배치 + 세로 장착", "여유 0.63, 브래킷 침범 0"],
        ["", "3D 뷰어(three.js + Isaac 턴테이블 폴백), 작업대 높이 분석(1 cm당 1°)", "한 면 배치 불가 → 월요일 실측"],
        ["", "Isaac 시연 생성기 · 평가 브릿지 구축, 그리퍼 램프 버그 발견 → 119 ep 폐기·재생성", "오라클 100%, v6 기준선 0%"],
        ["저녁", "카메라 매뉴얼 반영(왜곡·60 Hz·수동 노출·by-id), 스탠드오프 실측 19 mm 반영", "브래킷 출력 가능"]]
table(s, M, TOP, CW, rows, widths=[1.3, 10.5, 5.5], size=10.5, rh=Cm(1.2))
note(s, "시간 순서. 오후 중반의 '삐뚤어짐' 지적이 손목캠 설계를 한 번 더 바꾼 계기였고, 결과적으로 더 좋아졌다.")

# ═══════════ 7. 손목캠 A ═══════════
s = slide("손목캠 브래킷 ① 문제 발견 — 위치가 카메라와 안 맞고, 여유가 렌즈 오차에 취약", "03 / 손목캠")
panel(s, M, TOP, Cm(15.5), Cm(6.2)); txt(s, M + Cm(0.4), TOP + Cm(0.2), Cm(14.8), Cm(5.8), [("발견 1 — 구 브래킷(09-03)은 카메라 미선정 시절 임의 패드", {"bold": True, "color": RED}),
    "패드 광심 (−39.3, −45.3, +44) · 광축 +Z  vs  09-04 확정 (60, −75, +5) · 틸트 38.7°", "X 부호까지 반대, Z 39 mm 차이. 체결부(M5 @ ±61, z=32)만 유효", ("→ 팔 전부 새로 설계", {"bold": True}),
    ("발견 2 — 09-04 위치의 시야 여유가 얇다", {"bold": True, "color": RED, "gap": 10}),
    "공칭 0.898 (1.00 = 화면 가장자리). M12 렌즈 광심 위치(스탠드오프)를 모르는데, 그 오차가 정확히 광축 방향 = Z 민감축", "+10 mm 오차 → 1.08 이탈. '출력 금지'가 맞았다"], size=11.5)
rows = [["광축 방향 이동 (mm)", "−20", "−10", "0", "+5", "+10", "+15"], ["09-04 위치 여유", "0.74", "0.81", "0.90", "0.95", "1.01 ❌", "1.07 ❌"]]
table(s, M, TOP + Cm(6.6), Cm(15.5), rows, size=10.5, rh=Cm(0.7))
panel(s, M + Cm(16), TOP, CW - Cm(16), Cm(8.3)); txt(s, M + Cm(16.4), TOP + Cm(0.2), CW - Cm(16.8), Cm(7.9), [("알고리즘 — 제작 가능 영역 전수 탐색", {"bold": True, "color": NAVY}),
    "지표: 8 에피소드 × 파지 전 2 s 큐브 투영의 max(|u|,|v|)", "강건 지표: 광축 ±12 mm 이동 5점 중 최악값 (렌즈 오차 흡수)", "제약: 툴 STL 정점 거리 ≥ 20 mm, 플랜지 뒤는 손목 하우징 r 44.5 밖",
    "격자: X 20~65 · Y −35~−65 · Z 0~16 (5 mm 간격)", ("결과 상위: (35,−45,0) 0.66 / (30,−45,0) 0.65 / 09-04 값 1.03", {"bold": True}),
    ("대안 검토: 좌표하강 최적화 → (68,−52,−10) 0.50 이 나왔으나 z=−10 이 플랜지 뒤·툴 20 mm 이내라 제작 불가 → 제약 격자로 전환", {"size": 10.5, "color": GREY, "gap": 8}),
    ("근거: v7 을 새로 찍으므로 OMX 구도 재현 불필요(09-20 계획 메모)", {"size": 10.5, "color": GREY})], size=11.5)
foot(s, "cam_basis(gz) 인자는 m 단위 TCP(0.0725). 72.5/1000 과 헷갈려 한 번 틀린 기저로 판단했다 → 검증 스크립트마다 단위 명시")
note(s, "격자 탐색을 택한 이유: 목적함수가 비연속(에피소드별 최악값)이고 제약(툴·손목 간격, 제작 가능성)이 복잡해 무제약 최적화는 만들 수 없는 점을 찾아왔다. 격자는 5 mm 해상도로 충분했고 계산도 수십 초였다.")

# ═══════════ 8. 손목캠 B ═══════════
s = slide("손목캠 브래킷 ② 자기 카메라를 가리는 브래킷, 그리고 놓친 관통", "03 / 손목캠")
panel(s, M, TOP, Cm(16), Cm(7.4)); txt(s, M + Cm(0.4), TOP + Cm(0.2), Cm(15.3), Cm(7), [("설계 제약 — 카메라가 아래에서 그리퍼를 올려다본다", {"bold": True, "color": RED}),
    "체결부(그리퍼 −Y 측면 2-M5, z=32)가 시선 위에 있다", "기존식 좌우 관통 베이스판: 판 중앙(x=0,y=−27,z=32)이 화면 (−0.19,−0.28) → 큐브 궤적과 0.17 겹침",
    ("해법: 가운데를 비운 A-프레임", {"bold": True}), "+X 이어→패드 경로 전 구간 화면 밖/카메라 뒤 · −X 스트럿만 모서리 스침(큐브와 0.75)",
    ("트러블슈팅 — 어댑터 관통 675 mm³", {"bold": True, "color": RED, "gap": 10}),
    "정점 최근접 거리로는 '14.0 mm 여유'. 솔리드 불리언은 관통. 어댑터가 140×70 평판이라 정점이 드물어 스트럿이 면 한가운데를 뚫어도 어느 정점과도 안 가까웠다",
    "스트럿 축은 Y=−35 밖(2.9 mm)이지만 단면 반폭 7 이 z=12 에서 y=−30.9 까지 들어옴", ("→ 무릎 (±57, −50, 18) 으로 Y 를 먼저 빼고 하강. 여유 1.76 → 6.82 mm (2 g 추가)", {"bold": True})], size=11.5)
rows = [["무릎 (Y, Z, X)", "질량 g", "어댑터 여유 mm"], ["없음", "40.8", "관통 675 mm³"], ["(−45, 16, 55)", "44.6", "1.76"], ["(−48, 16, 55)", "45.5", "4.47"], ["(−50, 18, 57) ✅", "46.6", "6.82"]]
table(s, M + Cm(16.5), TOP, CW - Cm(16.5), rows, size=10.5, rh=Cm(0.68))
txt(s, M + Cm(16.5), TOP + Cm(3.9), CW - Cm(16.5), Cm(3.5), [("부수 버그", {"bold": True, "color": AMBER}), "패드 케이블 구멍이 스트럿 모서리를 31.8 mm³ 떼어내 솔리드 2개로 갈라짐 → 최대 솔리드만 남기고 1% 초과 시 중단하도록 생성기에 가드"], size=11)
foot(s, "교훈: 간섭 판정은 intersect().Volume() 으로. 거리 기반은 보조 지표일 뿐 (09-07 '정규식 말고 cadquery' 교훈과 같은 계열)")
note(s, "무릎 스윕 결과 표. 최근접이 면이 아니라 어댑터 능선과 스트럿 모서리 사이 대각선이라 손계산(3.97)보다 실거리(1.76)가 작았다. 그래서 BRepExtrema 솔리드 간 실거리로 다시 재고 무릎을 더 뺐다.")

# ═══════════ 9. 손목캠 C 중앙 배치 ═══════════
s = slide("손목캠 브래킷 ③ 최종 — 그리퍼 중앙 배치 + 보드 세로 장착", "03 / 손목캠")
panel(s, M, TOP, Cm(15.2), Cm(5.3)); txt(s, M + Cm(0.4), TOP + Cm(0.2), Cm(14.5), Cm(5), [("사용자 지적: '삐뚤어져 있다', '그리퍼 중앙이 좋겠다'", {"bold": True, "color": NAVY}),
    "맞는 지적 — (35,−45,0)은 X 로 35 치우치고 광축에 대각 성분이 있어 그리퍼 모서리가 화면을 사선으로 갈랐다",
    ("롤(화면 회전)을 따로 재보니 그 기울임이 여유를 사고 있었다", {"bold": True}), "같은 위치, 화면 바로 세움(가로) → 0.947. 큐브가 아래(+Z)에서 올라오는 움직임이 4:3 의 짧은 축(세로)에 실리기 때문",
    ("해법: 보드를 90° 돌려 세로(포트레이트)로 달면 긴 축에 실린다 — 정사각 기판이라 공짜", {"bold": True, "color": GREEN})], size=11.5)
rows = [["배치 · 롤", "틸트", "공칭", "렌즈오차 ±12 포함", "툴 간격"], ["(35,−45,0) 09-04 대각 롤", "38.7°", "0.614", "0.647", "27.2"], ["(35,−45,0) 가로", "38.7°", "0.899", "0.947 △", "27.2"],
        ["(0,−60,−10) 세로, h=140", "21.8°", "0.595", "0.630", "33.6"], [("(0,−65,−10) 세로, h=140 ✅ 최종", {"bold": True}), "23.4°", "0.591", "0.63", "26.4 / 손목 14.8"]]
table(s, M, TOP + Cm(5.6), Cm(15.2), rows, widths=[5.2, 1.6, 1.6, 3.2, 2.6], size=10.5, rh=Cm(0.68))
pic(s, IM("wristcam_isaac_sheet.png"), M + Cm(15.7), TOP, CW - Cm(15.7), Cm(9.2), "Isaac 실사 — 3 에피소드 × 접근→파지 (표시용 90° 회전). 양 핑거 아래 중앙 대칭, 큐브 정면 진입")
txt(s, M, TOP + Cm(9.6), Cm(15.2), Cm(2.4), [("최종: 브래킷 화면 침범 0 정점 (이전 좌상단 모서리) · 큐브 궤적 u ±0.54 대칭 · A-프레임 좌우 대칭 · 47.3 g · 스탠드오프 실측 19 mm 반영", {"size": 11, "bold": True}),
    ("wristcam_pose.py 를 단일 소스로 만들어 생성기·검증기·프리뷰·렌더가 전부 import — 위치 변경 시 한 곳만 고침", {"size": 10.5, "color": GREY})])
note(s, "파지점을 정확히 조준하면 09-04 롤 규약(up = -(v-(v·f)f))이 0/0 이 돼 NaN 이 나오는 함정이 있었다. 중앙 배치엔 ROLL='Z' (화면 가로 = 툴축)를 쓴다. 광심 (0,−65,−10)은 플랜지 면 10 mm 뒤인데 손목 하우징이 r 44.5 뿐이고 link_5 는 z=−63.5 부터라 빈 공간이다.")

# ═══════════ 10. 검증 3단계 이미지 ═══════════
s = slide("손목캠 ④ 세 단계가 같은 결론 — 기하 · 소프트웨어 렌더 · Isaac 실사", "03 / 손목캠")
w3 = (CW - Cm(1.0)) / 3
pic(s, IM("preview_sw_ep130_c_pre.png"), M, TOP, w3, Cm(7.2), "wristcam_preview.py — numpy z-버퍼 (GPU 불필요). 브래킷 주황, 툴 회색, 상판 베이지")
pic(s, IM("render_isaac_ep130_c_pre.png"), M + w3 + Cm(0.5), TOP, w3, Cm(7.2), "wristcam_render.py — Isaac RTX, 실제 툴 메시 부착 (같은 프레임)")
pic(s, IM("render_isaac_ep130_d_grasp.png"), M + 2 * (w3 + Cm(0.5)), TOP, w3, Cm(7.2), "파지 순간 — 큐브가 핑거 사이, 조가 일부만 가림")
rows = [["단계", "도구", "무엇을 확인", "결과"], ["기하", "wristcam_check.py · wristcam_occlusion.py", "큐브 중심 투영 여유 · 브래킷 정점 투영", "최악 0.59 · 침범 0"],
        ["소프트웨어 렌더", "wristcam_preview.py", "실제 메시로 화면 구성 (색 구분)", "브래킷 화면 밖, 큐브 뚜렷"], ["Isaac 실사", "wristcam_render.py", "RTX 렌더 + 로봇 물리 자세 검산", "카메라·툴·로봇 0.3 mm 이내, 구도 일치"]]
table(s, M, TOP + Cm(8.2), CW, rows, widths=[2.2, 5.5, 5.5, 4.5], size=10.5, rh=Cm(0.72))
foot(s, "'파먹은' 것처럼 보이는 파지 그림 = 닫힘 갭 33.5 < 큐브 35 (TPU 라이너 1 mm 가 흡수하는 설계 간섭 0.75) + 물리 없는 렌더 + 궤적 잔차 1.2 mm. 설계 문제 아님")
note(s, "세 단계가 독립적으로 같은 결론을 내야 믿을 수 있다. 특히 Isaac 실사는 로봇 자세 검산이 없으면 아무 의미가 없다는 걸 오늘 배웠다(다음 장).")

# ═══════════ 11. 어셈블리 재검증 ═══════════
s = slide("툴 어셈블리 재검증 — 낡은 STL 을 버리고 재생성기를 만들다", "04 / 어셈블리")
panel(s, M, TOP, Cm(16.2), Cm(6.4)); txt(s, M + Cm(0.4), TOP + Cm(0.2), Cm(15.5), Cm(6), [("문제", {"bold": True, "color": RED}),
    "tool_assembly_flangelocal.stl 이 09-07 14:55 판. 그 뒤 핑거 수정(09-07 17:17, 43.0→41.8)·밸브 브래킷 재생성(09-09, 스페이서 6)이 있었는데 미갱신. 만든 스크립트도 없음",
    "→ 09-07 의 '불리언 전부 0' 검증은 현재 부품 조합에 대한 것이 아니었다",
    ("해법 — make_tool_assembly.py", {"bold": True, "color": GREEN, "gap": 8}), "SMC 원본·어댑터·핑거 STEP 의 좌표 매핑을 역산해 스크립트로 고정. 검산 7종 자동 확인 후 쌍별 불리언",
    ("어댑터 (x,−y,12−z) · 그리퍼 (z,−x,12−y) · 핑거 (x,−y,53−z) · 브래킷은 이미 플랜지 로컬", {"mono": True, "size": 10.5})], size=11.5)
rows = [["검산", "값", "기대"], ["어댑터 스피곳 끝 / 판 상면 Z", "−4.00 / 12.00", "−4 / 12"], ["그리퍼 옆면 |Y| / 기준면 Z", "25.00 / 12.00", "25 / 12"], ["배면에서 20 → 측면 M5 Z", "32.00", "32"], ["핑거 조 끝 Z", "83.00", "83"], ["완전 닫힘 좌우 판 간격", "2.40", "2.40"]]
table(s, M + Cm(16.7), TOP, CW - Cm(16.7), rows, size=10.5, rh=Cm(0.66))
rows = [["부품 쌍", "간섭 mm³"], ["어댑터 ↔ 그리퍼 몸체", "0.0000"], ["어댑터 ↔ 손목캠 브래킷", "0.0000 (수정 전 675.1)"], ["그리퍼 몸체 ↔ 밸브 / 손목캠 브래킷", "0.0000 / 0.0000"], ["그리퍼 조 ↔ 핑거 좌·우", "0.0000"], ["조1 ↔ 조2 (블록만)", "0.0000"]]
table(s, M + Cm(16.7), TOP + Cm(4.4), CW - Cm(16.7), rows, size=10.5, rh=Cm(0.66))
txt(s, M, TOP + Cm(6.8), Cm(16.2), Cm(4.8), [("함정: CADENAS 그리퍼 조 솔리드는 몸체 안 가이드 레일까지 한 덩어리 → 두 조를 닫힘 위치로 옮기면 모델 안에서 레일끼리 164 mm³ 겹침(실물은 엇갈려 들어감). Z ≥ 40.3 으로 잘라 블록만 검증", {"size": 11}),
    ("4부품 감사 결과: 어댑터·핑거·밸브 브래킷 형상은 도면과 전 항목 일치. 발주 폴더 사본은 최신본과 동일(STEP 헤더 타임스탬프만 차이). 남은 관리 항목: 핑거·밸브 브래킷 생성 스크립트 없음, 핑거 DXF 없음(공차는 발주서 본문)", {"size": 11, "gap": 8}),
    ("의도된 보류: 어댑터 Φ6 핀홀은 Ø5.8 파일럿 4곳(0/90/180/270°)만 뚫고 클로킹 확정 후 1곳만 현장 리머. 리머는 지름 0.2 mm 만 깎으므로 파일럿 위치가 곧 최종 위치 → CNC 셋업에서 지금 뚫어야 함. 핀 미사용 시 회전 유격 ±0.69°(핑거 끝 ±0.52 mm) — 상수 보정 가능", {"size": 10.5, "color": GREY, "gap": 8})])
note(s, "재생성기가 생긴 뒤로는 부품이 바뀔 때마다 6~10초에 전 쌍 재검증이 된다. 손목캠 브래킷 위치를 두 번 바꾸는 동안 매번 여기서 통과시켰다.")

# ═══════════ 12. Isaac 렌더 트러블슈팅 ═══════════
s = slide("Isaac 렌더 트러블슈팅 — 증상 · 원인 · 해결 (6건)", "05 / Isaac")
rows = [["증상", "원인", "해결", "재발 방지"],
        ["렌더 자체 불가", "GPU 드라이버 불일치: 커널 580.173.02 vs NVML 580.178 (재부팅 전 패키지 업데이트)", "재부팅", "nvidia-smi 로 먼저 확인"],
        ["카메라 배치 타입 오류", "Camera 프림에 quatd orient op 이 이미 있어 AddOrientOp(float) 충돌", "MakeMatrixXform() 로 행렬 덮어쓰기 (Gf 는 행벡터 규약 → T.T)", "진단 스크립트로 A/B/C 규약 확인"],
        ["첫 프레임 빈 배열", "재부팅 직후 셰이더 컴파일이 수백 프레임", "초기 워밍업 루프(최대 600) 한 번", "—"],
        ["검산이 항상 0 (동어반복)", "l6 @ inv(l6) @ X == X — 아무것도 검증 안 함", "프림에서 실제 자세를 읽어 fk 와 비교 (카메라·툴·로봇 3종)", "검산은 반드시 독립 경로로"],
        ["큐브 뒤 정체불명 원통", "렌더용 상판(1.4×1.8, x 0.005~)이 충돌체라 로봇 어깨 관통 → joint_2 −0.4 rad 에 못 박힘, link_6 가 fk 에서 95~858 mm 어긋남. 카메라·툴은 운동학이라 제자리 → 처진 팔의 손목이 화면에", "상판·벽·큐브를 VisualCuboid 로 (물리는 로봇만). 드라이브 명령 매 스텝 재적용. 카메라를 link_6 자식 대신 월드 프림으로 fk 에 직접", "로봇 link_6 위치를 검산에 포함"],
        ["흰색 클리핑", "sun 3000 / dome 900", "1200 / 350", "—"]]
table(s, M, TOP, CW, rows, widths=[2.6, 6.2, 5.6, 2.8], size=10, rh=Cm(1.5))
foot(s, "5번은 09-09 wristcam_solve.py 렌더에도 있었을 가능성이 높다 — 같은 상판·같은 아티큘레이션이고 그 검산은 DELTA 가 어긋남을 흡수하는 구조였다")
note(s, "원통 정체를 찾는 데 링크별 숨기기, 깊이 역투영, 마커 테스트, 자세 추종 테스트를 거쳤다. 결정적이었던 건 '캡처 순간 로봇 link_6 가 어디 있나'를 처음으로 찍어본 것. 그 전 검산은 카메라·툴만 봤다.")

# ═══════════ 13. 데이터 정합 발견 ═══════════
s = slide("데이터 정합 — 오늘 발견한 낡은 값 2건", "05 / Isaac")
panel(s, M, TOP, Cm(15.8), Cm(8.8)); txt(s, M + Cm(0.4), TOP + Cm(0.2), Cm(15.1), Cm(8.4), [("① replay_ep*.npz 8개가 tcp = 0.0675 (수정 전)", {"bold": True, "color": RED}),
    "09-07 판. convert_v6_m1013.TCP 는 09-09 부터 0.0725 인데 npz 를 재생성하지 않았다", "→ 오늘 카메라 분석 전부가 수정 전 궤적 위에서 돌았다",
    ("조치: prep_replay_ep.py 로 8개 재생성 후 재검증", {"bold": True}), "(35,−45,0): 0.647 → 0.635 (유지) · 구 위치 (60,−75,5): 1.034 → 0.938 — '이탈'이 아니라 아슬아슬한 통과였음을 정정",
    ("교훈: npz 는 파생물. 상수를 고치면 재생성 여부를 확인할 것", {"color": GREY, "size": 10.5}),
    ("② 정면캠이 상판 안에 묻혀 있었다", {"bold": True, "color": RED, "gap": 12}),
    "cameras_v6match.json 정면캠 z=0.46 은 옛 상판(0.3746)에 맞춘 값. 09-04 에 상판을 0.4624 로 올린 뒤 재검토 안 됨(메모리에 '미해결'로 남아 있던 항목)",
    "시연 생성 프리뷰에서 에피소드 일부 정면캠이 검게 → 발견", ("조치: 상판 상승분 +0.0878 만큼 정면캠도 올려 상판 대비 구도 보존. 실제 위치는 월요일 배치 때 확정", {"bold": True})], size=11.5)
panel(s, M + Cm(16.3), TOP, CW - Cm(16.3), Cm(8.8)); txt(s, M + Cm(16.7), TOP + Cm(0.2), CW - Cm(17.1), Cm(8.4), [("검증 정정 목록", {"bold": True, "color": NAVY}),
    "· cam_basis 단위 실수(72.5/1000) → 틀린 기저로 판단한 것 1건, 재계산으로 결론 유지", "· 정점 거리 '14 mm 여유' → 불리언 관통 675 mm³", "· '구 위치 이탈' → 정정 궤적에서 0.938 통과",
    "· Isaac 검산 0.0000 → 동어반복, 실제 오차 최대 858 mm", ("전부 이 문서에 남김. 밤 결과를 믿으려면 어디가 틀렸었는지가 기록돼야 한다", {"color": GREY, "size": 10.5, "gap": 8})], size=11)
note(s, "정정 궤적에서 구 위치가 살아났다고 해서 재배치가 무의미해진 건 아니다. 여유 6% 대 35%.")

# ═══════════ 14. 작업대 높이 ═══════════
s = slide("작업대 높이 — 베이스와 한 면에 두면 손목 특이점을 지난다 (월요일 실측 후 결정)", "06 / 배치")
rows = [["상판(큐브면)이 베이스 위", "최악 min|q5|", "중앙값", "프레임당 최대 Δq", "판정"],
        ["2 cm (한 면)", "5.2°", "24.2°", "11.3° (초당 330°)", "❌"], ["12 cm", "10.7°", "33.7°", "5.7°", "❌"], ["22 cm", "19.5°", "43.4°", "4.1°", "❌"],
        ["32 cm", "29.6°", "53.2°", "3.5°", "△"], ["38 cm (TX90 리그)", "35.9°", "59.5°", "3.2°", "✅"], ["48 cm (현재 시뮬)", "46.0°", "—", "3.0°", "✅"]]
table(s, M, TOP, Cm(17), rows, widths=[4.6, 2.6, 2.2, 3.6, 1.4], size=11, rh=Cm(0.72))
panel(s, M + Cm(17.5), TOP, CW - Cm(17.5), Cm(9.5)); txt(s, M + Cm(17.9), TOP + Cm(0.2), CW - Cm(18.3), Cm(9.1), [("왜", {"bold": True, "color": NAVY}),
    "45° 손목 보정은 OMX 의 기운 접근을 '수직으로 펴는' 것. 베이스 높이 물체를 위에서 똑바로 집으려면 팔뚝이 거의 수직 → 손목이 펴져(q5→0) 특이점",
    "접근을 기울여 피하는 건 핑거 끝이 상판 위 7 mm 뿐이라 불가", "작업영역을 20 cm 멀리 두면 8°까지만 회복",
    ("결론", {"bold": True, "color": NAVY, "gap": 10}), "특이점 여유 ≈ 상판 높이 1 cm 당 1°", ("로봇 베이스가 작업면보다 35~48 cm 아래여야 한다", {"bold": True}),
    "예: 바닥 베이스판 + 45 cm 작업대, 또는 30 cm 받침 + 75 cm 책상",
    ("현재 시뮬 가정 46 cm 는 TX90 리그(38) + 8/20 스윕 +10 을 물려받은 것 — 실험실 배치를 보고 정한 게 아님", {"size": 10.5, "color": GREY, "gap": 8})], size=11.5)
txt(s, M, TOP + Cm(5.6), Cm(17), Cm(3.5), [("159 에피소드 전체를 높이별로 재변환해 잰 값 (IK 는 전 높이 159/159 성공, 문제는 특이점 여유만)", {"size": 11, "color": GREY}),
    ("사용자 결정: 월요일 로봇 설치 후 작업대 위치 보고 실측 → 그 값으로 OFFSET 맞춰 재변환(6 s) + 시연 재생성(1.8 h) + 재학습(2.8 h)", {"size": 11.5, "bold": True, "gap": 8})])
note(s, "생성기·평가기 모두 --table_z 가 CLI 파라미터라 실측값이 오면 바로 재생성된다. 그래서 오늘 현재 높이로 파이프라인을 완성해도 낭비가 없다.")

# ═══════════ 15. 3D 뷰어 ═══════════
s = slide("3D 뷰어 — 로봇 + 설계 부품 전부, 부품별 켜고 끄기", "07 / 산출물")
pic(s, IM("viewer_webgl.png"), M, TOP, Cm(19), Cm(9.8), "three.js 실시간 뷰 (WebGL). 프리셋: 전체 / 툴 정면 / 브래킷 측면 / 아래에서 / 손목캠 시점")
pic(s, IM("turntable_tool.jpg"), M + Cm(19.5), TOP, CW - Cm(19.5), Cm(4.7), "WebGL 없는 화면(VS Code 패널) 폴백 — Isaac 턴테이블 96장")
txt(s, M + Cm(19.5), TOP + Cm(5.4), CW - Cm(19.5), Cm(5), [("링크", {"bold": True, "color": NAVY}), (ART, {"mono": True, "size": 9.5}),
    ("파일: sim_out/scene3d/m1013_tool_assembly.html (6.1 MB, 크롬에서 직접 열림)", {"size": 10.5, "gap": 6}),
    ("export_scene3d.py → scene.json (부품별 정점/삼각형, ep130 파지 자세) → build_scene3d_html.py", {"size": 10.5, "color": GREY}),
    ("함정: 로봇 DAE 한 파일에 지오메트리가 여럿(액센트 2_1·2_2·4_1) — 위치 배열 하나에 삼각형을 다 연결하면 화면만 한 파란 삼각형이 됨 → 지오메트리 단위로 짝지어 파싱", {"size": 10.5, "color": GREY, "gap": 6})])
foot(s, "색: 어댑터·핑거 금속 회색 · 그리퍼 진회색 · 밸브 브래킷 청록 · 손목캠 브래킷 주황 · 카메라 초록/검정 · 손목캠 시야 프러스텀 주황선")
note(s, "VS Code 사이드 패널은 WebGL 이 없어 처음엔 검게 나왔다. 진단 문구를 넣어 원인을 확인한 뒤, Isaac 으로 24방위×2고도×2세트 턴테이블을 찍어 폴백으로 넣었다.")

# ═══════════ 16. 학습 방식 3안 ═══════════
s = slide("알고리즘 선택 ① 'Isaac 에서 실시간으로 보고 반응하는 학습' — 세 방식 비교", "08 / 알고리즘")
rows = [["방식", "원리", "장점", "단점 / 왜 안 골랐나", "선택"],
        ["① Isaac 시연 대량 생성 → ACT (모방)", "큐브 무작위 배치, IK 전문가가 집는 장면을 렌더해 시연 수천 개. 기존 ACT 파이프라인 그대로", "파이프라인·형식·학습 스크립트 재사용. 큐브 yaw 를 무작위화해 OMX 의 yaw 결손을 직접 메움. 09-09 연구방향의 '최유력 대안'", "렌더↔실물 화질 차이 → domain randomization 으로 완화. 전문가가 '정답'이라 다양성은 잡음으로 넣어야 함", "✅ 사용자 선택"],
        ["② 강화학습 (Isaac Lab)", "카메라 관측으로 시행착오", "진짜 즉석 반응. 시연 불필요", "픽셀 RL 파지는 GPU 수십~수백 시간, 보통 상태 기반 RL 후 비전 증류. 9/14 일정 불가", "—"],
        ["③ 비주얼 서보 (학습 없음)", "손목캠 색 검출 → IK 추종", "확실히 동작", "연구 주제(모방학습·데이터 효율)와 무관", "—"]]
table(s, M, TOP, CW, rows, widths=[3.4, 4.6, 4.8, 5.4, 1.6], size=10.5, rh=Cm(1.9))
txt(s, M, TOP + Cm(8.2), CW, Cm(2.5), [("현재 ACT 정책은 추론 때 닫힌 루프다 — 청크(100프레임)마다 카메라를 다시 보고 반응한다. 문제는 배운 범위(시연 159개, 집는 영역 20×12 cm)이지 구조가 아니다. ①은 그 범위를 Isaac 으로 넓히는 것", {"size": 11.5}),
    ("결과로 얻는 것: 데이터 효율 곡선에 'Isaac 사전학습' 축 → 'Isaac 시연이 실기 데모 몇 개 값어치인가'를 정량화", {"size": 11.5, "bold": True, "gap": 6})])
note(s, "학습한 모델의 정체도 이때 정리했다: OMX→M1013 변환은 학습이 아니라 기하(FK→EE→IK). 학습은 ACT(이미지+관절→관절 청크). v6 의 영상은 OMX 리그 것이라 도메인 갭의 원천.")

# ═══════════ 17. 전문가 알고리즘 ═══════════
s = slide("알고리즘 선택 ② 스크립트 전문가 — 무엇을 어떻게 흉내 내나", "08 / 알고리즘")
panel(s, M, TOP, Cm(16.5), Cm(9.6)); txt(s, M + Cm(0.4), TOP + Cm(0.2), Cm(15.8), Cm(9.2), [("궤적 생성 (isaac_expert.py)", {"bold": True, "color": NAVY}),
    "웨이포인트 8개: 시작 → 큐브 위 6~11 cm → 하강(TCP=큐브 중심) → [닫힘 0.45 s] → 들기 → 놓을 곳 위 → 하강 → [열림] → 후퇴",
    "구간마다 최소저크(min-jerk) 시간 프로파일, 자세는 slerp, 30 Hz 프레임마다 IK", "IK: m1013_kin.solve — 적응감쇠 DLS + 직전 해 시드 + 2π 접기 + 브랜치(>90°) 거부 + 섭동 재시도 (convert_v6 와 동일). 실패·Δq>6° 면 에피소드 폐기",
    ("파지 자세", {"bold": True, "color": NAVY, "gap": 8}), "플랜지 z = 수직(45° 보정과 동일 규약), x 축 yaw = 큐브 yaw 의 90° 배수 중 v6 관습(158.8°)에 가장 가까운 것",
    ("사람 흉내 (v6 실측 분포에서)", {"bold": True, "color": NAVY, "gap": 8}), "손목 기울기 N(0, 6°) ← v6 파지 시 수직 이탈 중앙값 9° · 웨이포인트 지터 ±1 cm(위)/±3 mm(파지) · 저주파 흔들림 ≤4 mm · 속도 ×0.85~1.3 · 그리퍼 5프레임 램프 ← v6 실측",
    ("왜 잡음을 넣나: 깨끗한 궤적만 배운 정책은 실기에서 약하다. 시연 다양성을 데이터 분포에서 가져왔다", {"size": 10.5, "color": GREY, "gap": 6})], size=11)
rows = [["무작위화", "범위", "정책이…"], ["큐브 집는/놓는 위치", "v6 영역 ×1.5", "읽어야"], ["큐브 yaw", "0~90° 균일", "읽어야 (OMX 결손)"], ["시작 자세", "v6 시작 159개 + N(0,1°)", "읽어야"],
        ["조명 방향·세기", "sun 700~2000, ±70°/±40°", "무시해야"], ["상판 색 · 큐브 색조", "회색~베이지 · 파랑 계열", "무시해야"], ["카메라 지터", "손목 ±3 mm/±2°, 정면 ±1 cm", "무시해야 (조립 오차)"]]
table(s, M + Cm(17), TOP, CW - Cm(17), rows, widths=[3.2, 3.8, 2.6], size=10.5, rh=Cm(0.7))
txt(s, M + Cm(17), TOP + Cm(5.4), CW - Cm(17), Cm(4), [("domain randomization: '읽어야 할 것'은 넓게, '무시해야 할 것'은 흔들어서", {"size": 11, "bold": True}), ("dry 검증 12/12 · 평균 392 프레임(13 s, v6 평균 16 s)", {"size": 10.5, "color": GREY, "gap": 6})])
note(s, "IK 를 앵커 6 Hz 대신 매 프레임 푼 이유: 전문가 궤적은 카르테시안으로 매끄럽게 만들어졌으므로 직전 해를 시드로 하면 프레임당 수 ms 로 충분히 빠르고 보간 오차가 없다.")

# ═══════════ 18. weld vs 접촉물리, 형식 ═══════════
s = slide("알고리즘 선택 ③ weld vs 접촉 물리 · 프레임 선택 · 기록 형식", "08 / 알고리즘")
rows = [["결정", "채택", "대안", "이유"],
        ["시연 생성 시 파지", "weld — 닫힘 순간 큐브를 플랜지에 운동학 고정, 열림에 상판으로 스냅", "접촉 물리 (핑거 충돌 메시·마찰·조 힘 튜닝)", "시연엔 성공 장면만 필요. 영상·관절에 차이 없음. 접촉은 미끄러짐·튕김으로 실패 시연이 섞이고 튜닝에 시간이 감"],
        ["평가 시 파지 판정", "기하 — 닫힘 순간 큐브 중심이 |x|≤12, |y|≤15, |z−TCP|≤20 mm", "weld / 접촉 물리", "weld 는 빗나가 닫아도 성공으로 찍힘. 접촉 물리는 8/20 셋업 재사용 가능하나 우선 기하로 엄격하게"],
        ["렌더 프레임 선택", "TCP–큐브 3D 거리 (≥300 / ≥180 / ≥110 / 최소)", "t_close ± 고정 오프셋 · 플랜지로컬 Z 성분", "고정 오프셋은 이미 큐브를 든 뒤(큐브가 집는 위치에 고정된 렌더에서 오판). Z 성분만 보면 팔이 지나가다 같은 높이인 엉뚱한 프레임"],
        ["Isaac 카메라 배치", "월드 프림, fk(q) @ T_cam_fl 직접", "link_6 자식 + DELTA 보정 (09-09 방식)", "DELTA 는 렌더된 마지막 USD 자세라 물리 직후 낡은 값. 팔이 흔들리면 4회 재시도해도 9 mm 어긋남. 월드 프림이면 보정 자체가 없음"],
        ["데이터셋 형식", "v6 와 동일 LeRobot v2.1, HF 캐시에 직접 기록", "새 형식 / 변환 스크립트", "학습 스크립트 무수정. 컨테이너 ffmpeg 파이프로 코덱까지 동일(h264 yuv420p)"],
        ["큐브 상판 색 등 렌더", "VisualCuboid (물리 없음)", "FixedCuboid/DynamicCuboid", "충돌체 상판이 로봇 어깨를 막는 사고. 물리는 로봇만 필요"]]
table(s, M, TOP, CW, rows, widths=[2.8, 5.2, 4.0, 7.2], size=10, rh=Cm(1.55))
note(s, "weld 는 '용접' — 두 물체를 붙여버리는 것. 시연 생성엔 weld, 평가엔 기하 판정 또는 접촉 물리라는 분리가 핵심이다.")

# ═══════════ 19. 평가 브릿지 + 검증 ═══════════
s = slide("닫힌 루프 평가 브릿지 — 구조와 검증 2종", "09 / 평가")
y = TOP + Cm(0.2); bw, bh = Cm(5.0), Cm(1.6)
flow(s, M, y, ["Isaac (호스트)\n손목캠·정면캠 렌더 + state", "TCP 127.0.0.1:5555\n[길이][pickle]", "act_server.py (컨테이너)\nACTPolicy.select_action", "action[7]\n관절 6 + 그리퍼", "Isaac\nstep_robot + 기하 파지 판정"], bw, bh, fills=[TEAL, GREY, NAVY, GREY, TEAL], size=11)
panel(s, M, y + Cm(2.2), Cm(16), Cm(6.8)); txt(s, M + Cm(0.4), y + Cm(2.4), Cm(15.3), Cm(6.4), [("검증 1 — 브릿지 규약 (컨테이너 안)", {"bold": True, "color": NAVY}),
    "v6 정책에 자기 학습 데이터 프레임을 서버와 같은 전처리(uint8 HWC → /255 CHW)로 넣어 정답 행동과 비교", ("ep130 601 프레임: 관절 오차 평균 0.45°, 중앙값 0.26°, 최대 2.82° — 8/20 기록 0.62°와 동급 ✅", {"bold": True}),
    ("검증 2 — 평가기 자체 (--oracle)", {"bold": True, "color": NAVY, "gap": 10}), "정책 대신 스크립트 전문가로 루프를 돌림. 파지 판정·weld·놓기 로직이 맞으면 ~100%",
    ("첫 실행: 파지 8/8, 들기 1/8, 에피소드가 파지 20프레임 뒤 종료 → 버그 발견 (다음 장)", {"color": RED}), ("수정 후: 파지 8/8, 들기 8/8, 닫힘 순간 TCP–큐브 0.5~5 mm ✅", {"bold": True, "color": GREEN})], size=11.5)
panel(s, M + Cm(16.5), y + Cm(2.2), CW - Cm(16.5), Cm(6.8)); txt(s, M + Cm(16.9), y + Cm(2.4), CW - Cm(17.3), Cm(6.4), [("지표", {"bold": True, "color": NAVY}),
    "파지율 · 들기율(잡고 5 cm 상승) · 놓기율(들어서 집는 자리 8 cm 이상 떨어진 곳에 내려놓음)", "TCP–큐브 최소거리 · 프레임당 최대 Δq · 스텝 수",
    ("출력", {"bold": True, "color": NAVY, "gap": 8}), "sim_out/<tag>/results.json + 에피소드별 4프레임 그림(시작·파지·놓기·끝)", ("속도 17 행동/s (생성기와 GPU 공유 중)", {"size": 10.5, "color": GREY, "gap": 6})], size=11)
foot(s, "두 검증이 통과했으니 v6 정책의 0% 는 브릿지 버그가 아니라 화면 차이(OMX 리그 영상 ↔ Isaac 렌더)로 확정")
note(s, "검증 1 이 없으면 '서버 전처리가 틀려서 0%' 가능성을 못 지운다. 검증 2 가 없으면 '평가기가 틀려서 0%' 를 못 지운다. 둘 다 있어야 밤 결과를 해석할 수 있다.")

# ═══════════ 20. 그리퍼 램프 버그 ═══════════
s = slide("트러블슈팅 — 전문가 그리퍼 채널 버그 (오라클이 잡음, 생성 데이터 119개 폐기)", "09 / 평가")
panel(s, M, TOP, Cm(16.2), Cm(8.6)); txt(s, M + Cm(0.4), TOP + Cm(0.2), Cm(15.5), Cm(8.2), [("증상", {"bold": True, "color": RED}), "오라클 첫 실행: 파지 100% 인데 들기 12%, 에피소드가 t_grasp+20 에서 끝남",
    ("원인", {"bold": True, "color": RED, "gap": 8}), "정지 구간(15프레임)을 '바꾸기 전' 그리퍼 값으로 먼저 채우고 램프를 앞 5프레임에 덮어써서:",
    ("수정 전  0.69 → 0.55 0.41 0.26 0.12 −0.02 → 0.69 0.69 0.69 … (10프레임) → −0.02 …", {"mono": True, "size": 10.5}), "임계 0.459 규약으로 읽으면 닫힘→열림→닫힘. 평가기가 두 번째 전이를 '놓기'로 처리",
    ("더 중요: 생성 중이던 v8 데이터 119개에 같은 패턴이 들어가 있었다 — 정책이 그걸 배웠으면 밤 결과가 엉망", {"bold": True}),
    ("수정", {"bold": True, "color": GREEN, "gap": 8}), "상태를 먼저 바꾸고 정지 프레임 전부를 새 상태로 채움. 램프는 앞 5프레임", ("수정 후  0.69 → 0.55 0.41 0.26 0.12 −0.02 −0.02 −0.02 …   (열림 전이 횟수 1)", {"mono": True, "size": 10.5}),
    "생성기·체인 중단 → 부분 데이터셋 삭제(합성 데이터만, 원본 무손상) → 전문가를 isaac_expert.py 로 빼서 생성기·평가기 공용 → 재시작 15:10"], size=11)
txt(s, M + Cm(16.7), TOP, CW - Cm(16.7), Cm(8.6), [("규약 자체는 변경 없음", {"bold": True, "color": NAVY}), "값 > 0.459 열림, < 0.459 닫힘 (v6: 열림 0.69, 닫힘 −0.02)", "실물 gripper_ctl.py 는 히스테리시스 0.359/0.559 + 최소유지 0.5 s 라 밸브까진 안 갔겠지만, 정책은 데이터 패턴을 그대로 배운다",
    ("일정 영향: 완료 예상 21시 → 22시 30분", {"color": AMBER, "gap": 10})], size=11)
note(s, "검증 도구(오라클)를 먼저 만든 덕에 데이터 버그를 학습 전에 잡았다. 순서가 반대였으면 밤새 돌린 학습이 통째로 무효였다.")

# ═══════════ 21. 기준선 ═══════════
s = slide("기준선 — 기존 v6 정책은 Isaac 에서 0% (예상된 결과)", "09 / 평가")
pic(s, IM("eval_v6_ep002.jpg"), M, TOP, Cm(20), Cm(7.5), "v6 정책 ep02 — 시작(좌) · 끝(우). 큐브 근처까지 가서 맴돌기만 하고 하강하지 않음. 최소거리 50.6 mm")
pic(s, IM("eval_oracle_ep002.jpg"), M, TOP + Cm(8.3), Cm(20), Cm(3.0), "오라클(전문가) ep02 — 시작 · 파지 · 놓기 · 끝. 파지 ✅ 들기 ✅ 놓기 ✅")
panel(s, M + Cm(20.5), TOP, CW - Cm(20.5), Cm(11.3)); txt(s, M + Cm(20.9), TOP + Cm(0.2), CW - Cm(21.3), Cm(10.9), [("v6 정책 (OMX 영상 학습) · 3 ep", {"bold": True, "color": NAVY}), "파지 0% · 최소거리 50~164 mm · maxΔq 5° (움직이긴 함)",
    ("해석", {"bold": True, "color": NAVY, "gap": 8}), "학습 때 본 화면 = OMX 리그 실제 카메라. 평가 화면 = Isaac 렌더. 처음 보는 화면이라 큐브를 못 찾고 평균 동작만 재생",
    "'정책이 나쁘다'가 아니라 '화면이 다르다'", ("밤 결과 해석 기준", {"bold": True, "color": NAVY, "gap": 8}), "Isaac 학습 모델은 같은 화면으로 배우고 평가받음 → 이 0% 를 넘어야 함",
    ("만약 그것도 0% 면: ① loss 가 0.05 수준까지 내려갔나 → ② 학습 데이터 1 ep 열린 루프 재생(검증 1 과 동일) → ③ 닫힌 루프에서 어디서 갈라지나(접근·하강·닫힘 타이밍)", {"size": 10.5, "color": GREY, "gap": 6})], size=11)
note(s, "기준선이 0% 인 것 자체가 결과다: OMX 영상으로 배운 정책은 M1013 카메라 뷰에 그대로 못 옮긴다는 뜻이고, 그게 Isaac 갈래를 만드는 이유다.")

# ═══════════ 22. 카메라 매뉴얼 ═══════════
s = slide("카메라 매뉴얼(U20CAM-720P) 반영 — 노드 4건 + 스탠드오프 실측", "10 / 카메라")
rows = [["매뉴얼 항목", "값", "영향", "반영 (camera_uvc_node.py)"],
        ["TV 왜곡", "< −17% (배럴)", "Isaac 렌더는 핀홀 → 실물 프레임 기하가 다름. ①안 sim-to-real 의 필수 조건", "cam_calibrate.py 체커보드 → cam_calib_<name>.npz → 크롭 전 cv2.remap 언디스토션"],
        ["전원 주파수", "매뉴얼 기본 50 Hz", "한국 60 Hz. 형광등 밴딩 플리커가 데이터에 들어감", "power_line_frequency=2 명시"],
        ["자동 노출·WB", "기본 자동", "프레임마다 색이 흔들림 = 도메인 잡음", "수동 고정 (값은 현장 조명에서 조정)"],
        ["같은 기종 2대", "/dev/videoN 부팅마다 변동", "손목·정면 뒤바뀜 위험", "--dev 에 /dev/v4l/by-id 경로"],
        ["해상도", "1280×720 최대 (960×720 없음)", "960 크롭 파이프라인이 맞음 (HFOV 85.6°)", "변경 없음"],
        ["렌즈", "f=2.79 mm F2.2, M12, 시트 간격 18", "광심 위치 미공개 (제품페이지·GitHub 404)", "사용자 실측: 기판 앞면→렌즈 끝 22 mm → 광심 ≈ 19 mm → 브래킷 반영"],
        ["기타", "롤링셔터 · 피그테일 1 m · 트리거 없음", "30 Hz 궤적 속도에선 무시 · 연장 3~5 m 산정 확인", "—"]]
table(s, M, TOP, CW, rows, widths=[2.4, 3.6, 5.6, 5.8], size=10.5, rh=Cm(1.15))
foot(s, "매뉴얼 원본: docs/U20CAM-720P UserManual-v1.0.pdf · 스탠드오프 19 반영 후 브래킷: 간섭 0, 어댑터 4.86, 손목 14.8 mm, 47.3 g → 출력 가능")
note(s, "LENS_STANDOFF 는 아침엔 차단 항목(구 위치는 +10 mm 면 이탈)이었지만 중앙 배치 후 ±12 mm 를 견디게 돼 '출력 전 확인' 수준이 됐고, 사용자 실측 22 mm 로 확정했다.")

# ═══════════ 23. 알고리즘 총괄 ═══════════
s = slide("알고리즘 선택 총괄 — 적용 / 대안 / 선택 이유", "08 / 알고리즘")
rows = [["문제", "적용", "검토한 대안", "선택 이유"],
        ["카메라 위치 탐색", "제약 격자 + 강건 지표(광축 ±12 mm 최악)", "좌표하강 최적화", "최적화는 제작 불가 지점(z<0, 툴 근접)으로 감. 목적함수 비연속"],
        ["카메라 롤", "세로(포트레이트), 화면 가로=툴축", "09-04 파지점-하단 롤 · 가로", "큐브 접근 움직임을 4:3 긴 축에 실어야 여유 확보. 09-04 롤은 파지점 정조준 시 0/0"],
        ["브래킷 구조", "A-프레임 + 무릎", "관통 베이스판", "판 중앙이 큐브 궤적과 0.17 겹침"],
        ["간섭 판정", "솔리드 불리언 intersect().Volume()", "정점 최근접 거리", "평판에서 관통을 놓침 (14 mm 여유 → 675 mm³)"],
        ["어셈블리 좌표", "원본 STEP 매핑 역산 + 검산 7종 자동", "STL 수동 조립", "재현성. 부품 바뀔 때마다 10 s 재검증"],
        ["시연 데이터", "Isaac 스크립트 전문가 + weld", "RL · 비주얼 서보 · 접촉 물리", "일정·연구 주제·성공 시연 보장"],
        ["궤적 보간", "min-jerk + slerp + 매 프레임 IK 시드체인", "6 Hz 앵커 + 관절 보간(convert_v6)", "카르테시안 경로가 매끄러워 시드체인이 충분, 보간 오차 없음"],
        ["평가 파지", "기하 판정", "weld · 접촉 물리", "빗나간 닫힘을 성공으로 안 찍음"],
        ["Isaac 카메라 배치", "월드 프림 fk 직접", "link_6 자식 + DELTA", "DELTA 는 낡은 USD 자세, 팔 흔들림에 취약"],
        ["3D 뷰어", "three.js + Isaac 턴테이블 폴백", "JS 소프트웨어 렌더러", "WebGL 없는 화면에서도 보여야 함, 품질"]]
table(s, M, TOP, CW, rows, widths=[2.6, 4.6, 3.8, 6.4], size=10, rh=Cm(1.0))
note(s, "IK 자체(적응감쇠 DLS + 시드체인)는 8/20 에 정해진 기존 알고리즘을 그대로 썼다.")

# ═══════════ 24~25. 생성 파일 ═══════════
s = slide("생성 파일 ① 스크립트 (전부 /home/kim/m1013, 커밋됨)", "11 / 파일")
rows = [["파일", "역할", "실행"],
        ["wristcam_pose.py", "손목캠 자세 단일 소스 (CAM_POS·AIM·ROLL·HFOV, basis(), project())", "import 전용 · python3 wristcam_pose.py 로 확인"],
        ["cad/make_wristcam_bracket.py", "손목캠 브래킷 STEP/STL 생성기 (A-프레임·무릎·장공·너트 채널·부스러기 가드). LENS_STANDOFF=19", "python3 cad/make_wristcam_bracket.py"],
        ["cad/make_tool_assembly.py", "4부품+그리퍼 좌표 매핑·검산 7종·쌍별 불리언·어셈블리 STL 2종 출력", "python3 cad/make_tool_assembly.py (exit 0 = 통과)"],
        ["wristcam_check.py", "큐브 궤적 시야 여유 (기존, wristcam_pose 로 물림)", "python3 wristcam_check.py [HFOV]"],
        ["wristcam_occlusion.py", "브래킷 정점 화면 침범 + 로봇 손목 간격", "python3 wristcam_occlusion.py"],
        ["wristcam_preview.py", "손목캠 시점 numpy 소프트웨어 렌더 (GPU 불필요, 색 구분)", "python3 wristcam_preview.py"],
        ["wristcam_render.py", "Isaac 실사 렌더 — 실제 툴 메시, 월드 프림 카메라, 프림 기반 검산, --norobot/--notool", "isaacsim/python.sh wristcam_render.py"],
        ["export_scene3d.py · build_scene3d_html.py · isaac_turntable.py", "3D 뷰어: 부품별 메시 JSON → three.js HTML(+턴테이블 폴백) · Isaac 96장", "순서대로 실행"],
        ["isaac_scene.py", "Isaac 씬 공용 모듈 (로봇 물리, 시각 전용 상판·큐브, 카메라 2대, DR)", "import 전용"],
        ["isaac_expert.py", "스크립트 전문가 (궤적·그리퍼·사람 흉내·샘플러)", "import 전용"],
        ["gen_isaac_demos.py", "시연 생성 → HF 캐시 LeRobot v2.1 (--n --out --table_z --ws_scale --no_dr --preview --dry)", "isaacsim/python.sh gen_isaac_demos.py --n 1000 --out m1013_isaac_v8"],
        ["act_server.py · eval_isaac_closedloop.py", "컨테이너 ACT 추론 서버 · Isaac 닫힌 루프 평가 (--oracle 검증 모드)", "isaacsim/python.sh eval_isaac_closedloop.py --ckpt … --n 30"],
        ["run_v8_pipeline.sh", "생성 대기 → 학습 → 평가 3종 체인", "nohup bash run_v8_pipeline.sh <PID>"],
        ["camera_uvc_node.py · cam_calibrate.py", "실물 카메라 노드(60 Hz·수동 노출·by-id·언디스토션) · 체커보드 캘리브레이션", "로봇 도착 후"],
        ["make_report_pptx_0911.py", "이 PPT", "python3 make_report_pptx_0911.py"]]
table(s, M, TOP, CW, rows, widths=[5.2, 8.2, 4.0], size=9.5, rh=Cm(0.72))

s = slide("생성 파일 ② CAD · 데이터 · 이미지 · 문서", "11 / 파일")
rows = [["경로", "내용", "상태"],
        ["cad/wristcam_bracket_v2.step / .stl", "손목캠 브래킷 최종 (구 wristcam_bracket.* 삭제)", "출력 가능 47.3 g"],
        ["cad/tool_assembly_flangelocal.stl · tool_assembly_nowrist.stl", "최신 4부품 어셈블리 (플랜지 로컬) · 손목캠 제외판", "재생성됨"],
        ["cad/valve_bracket_sy5120.stl · finger_left/right.stl", "밸브 브래킷 · 핑거 (PETG 시제품용)", "출력 가능 (변경 없음)"],
        ["replay_ep{000,020,050,080,110,130,145,158}.npz", "카메라 검증용 8 에피소드 — tcp 0.0725 로 재생성", "갱신"],
        ["sim_out/v6_start_q.npy", "v6 시작 자세 159개 (전문가 샘플러)", "신규"],
        ["sim_out/wristcam_render/*.png · contact_sheet.png", "Isaac 손목캠 실사 12장 + 한 판", "최종 배치"],
        ["sim_out/wristcam_preview/*.png", "소프트웨어 렌더 12장", "최종 배치"],
        ["sim_out/scene3d/ (scene.json · m1013_tool_assembly.html · turn/*.jpg)", "3D 뷰어 데이터·HTML·턴테이블 96장", "게시됨"],
        ["sim_out/eval_v6_smoke/ · eval_oracle/", "평가 스모크(v6 3 ep) · 오라클(8 ep) results.json + 그림", "완료"],
        ["sim_out/gen_v8.log · v8_pipeline.log · gen_preview.jpg", "생성·체인 로그 · 시험 생성 프리뷰", "진행 중"],
        ["HF 캐시 dlcodnjs/m1013_isaac_v8 (컨테이너 /root/.cache/huggingface/lerobot/…)", "생성 중인 1,000 ep 데이터셋 (data/videos/meta/preview)", "생성 중"],
        ["cad/발주/구매목록_20260909.md · 발주서.md · make_install_docx_0908.py", "E-1 카메라 명시, B-8 M2, G-2 록타이트, 브래킷 상태·스탠드오프·매뉴얼 요점 반영", "갱신"],
        ["docs/U20CAM-720P UserManual-v1.0.pdf", "카메라 매뉴얼 원본", "신규"],
        ["대화록 및 PPT/img_0911/ · M1013_20260911.pptx", "이 PPT 와 이미지", "신규"]]
table(s, M, TOP, CW, rows, widths=[7.2, 7.4, 2.8], size=9.5, rh=Cm(0.72))
foot(s, "메모리(다음 세션용): ~/.claude/…/memory/m1013-step5-cameras.md · m1013-isaac-demo-generation.md · m1013-robot-arrival-plan.md 에 오늘 결정·함정 기록")

# ═══════════ 26. 링크 ═══════════
s = slide("링크 · 경로", "11 / 파일")
rows = [["항목", "링크 / 경로"],
        ["3D 뷰어 (아티팩트)", ART], ["3D 뷰어 (파일)", "/home/kim/m1013/sim_out/scene3d/m1013_tool_assembly.html"],
        ["저장소", "/home/kim/m1013 · 브랜치 wristcam-bracket-redesign (main 미병합) · GitHub dlcodnjs/tx90 은 별도"],
        ["카메라 제품 페이지", "https://www.inno-maker.com/product/u20cam-720p/"], ["카메라 SW 매뉴얼", "https://www.inno-maker.com/wp-content/uploads/2023/11/UVC-SW-Manual.pdf"],
        ["파이프라인 로그", "/home/kim/m1013/sim_out/v8_pipeline.log · gen_v8.log"], ["학습 출력 (컨테이너)", "/root/train_m1013_act_isaac_v8 · 로그 /root/train_m1013_act_isaac_v8.log"],
        ["기존 정책", "/root/train_m1013_act_v6_tcp0725/checkpoints/last/pretrained_model"], ["두산 매뉴얼", "/home/kim/m1013/Doosan_Robotics_User_Manual_V2.12_v2.12_KR(MH-Series).pdf (플랜지 도면 p.226)"],
        ["연구방향 문서", "대화록 및 PPT/M1013_연구방향_20260909.docx"], ["설치 절차서", "대화록 및 PPT/M1013_그리퍼_설치절차서_20260908.docx (make_install_docx_0908.py 로 재생성)"]]
table(s, M, TOP, CW, rows, widths=[4, 13.4], size=10.5, rh=Cm(0.78))

# ═══════════ 27. 현재 진행 상황 ═══════════
s = slide("현재 진행 상황 (2026-09-11 저녁 기준)", "12 / 현황")
rows = [["시각(예상)", "단계", "상태"], ["15:10", "시연 생성 1,000 ep (m1013_isaac_v8, seed 1, table_z 0.4624)", "🟠 진행 중 — 246/1000, 6~13 s/ep"],
        ["~18:45", "ACT 학습 100k 스텝 (컨테이너, v6 와 동일 설정)", "⏳ 자동 시작"], ["~21:30", "평가 3종 각 30 ep (Isaac v6분포 · Isaac 1.5배 · v6 기준선)", "⏳ 자동"], ["~22:30", "완료 → sim_out/eval_*/results.json", "확인: grep 요약 sim_out/eval_*.log"]]
table(s, M, TOP, Cm(19), rows, widths=[2.2, 10, 6.8], size=11, rh=Cm(0.85))
rows = [["하드웨어", "상태"], ["어댑터 · 핑거 (AL6061 절삭)", "🔴 발주 대기 — 오늘 안에"], ["밸브 브래킷 · 손목캠 브래킷 (PETG)", "✅ 출력 가능 — 그리퍼에 끼워 확인 권장"],
        ["핑거 PETG 시제품", "권장 — 알루미늄 전 립·M4·갭 확인"], ["재고품 B~F (M2 포함)", "🟠 이번 주 주문"], ["카메라 U20CAM-720P 1(+1)", "🟠 이번 주 주문"], ["작업대 높이", "🟡 월요일 실측 후 결정"]]
table(s, M + Cm(19.5), TOP, CW - Cm(19.5), rows, size=10.5, rh=Cm(0.72))
txt(s, M, TOP + Cm(5.2), Cm(19), Cm(5.5), [("확인된 것", {"bold": True, "color": GREEN}), "· 4부품 CAD 검증 완료(간섭 0) · 손목캠 3단계 검증 일치 · 브릿지 규약 0.45° · 평가기 오라클 100% · 데이터셋 형식 로더 통과",
    ("확인 안 된 것 (솔직하게)", {"bold": True, "color": AMBER, "gap": 8}), "· 실물에 맞춰본 부품 없음 (그리퍼는 손에 있으니 브래킷·핑거 PETG 로 주말에 확인 가능) · 어댑터↔로봇 플랜지는 월요일 · Isaac 학습 정책의 성공률(밤) · 정면캠 실제 위치"], size=11)
note(s, "생성 속도가 13 s/ep 로 느려진 구간은 평가기·오라클이 GPU 를 같이 쓰던 때다. 이후 회복되면 22시 전 완료.")

# ═══════════ 28. 고려사항 ═══════════
s = slide("고려해야 할 것 · 리스크", "13 / 고려")
rows = [["항목", "무엇이 문제될 수 있나", "대응"],
        ["Isaac 정책도 0% 일 가능성", "렌더 다양성 부족, 전문가 궤적이 너무 일정, 그리퍼 타이밍", "① loss 확인 → ② 학습 데이터 열린 루프 재생 → ③ 닫힌 루프 갈라지는 지점. 도구 전부 있음"],
        ["sim → real 화면 차이", "렌더 재질·조명 vs 실물, 배럴 왜곡 −17%", "DR 강화(텍스처·배경), 실물 언디스토션(cam_calibrate), v7 이어학습이 본래 목적"],
        ["작업대 높이", "한 면 배치면 특이점 5° — 데이터셋 전체 재변환·재생성·재학습(약 5 h)", "베이스가 작업면보다 35~48 cm 아래. 월요일 실측값으로 파라미터만 교체"],
        ["정면캠 위치", "옛 상판 기준 fit, 오늘은 +8.8 cm 만 올림", "실물 배치 후 cameras_v6match.json 재정합"],
        ["전문가 vs 사람 시연 분포", "전문가는 항상 성공·항상 같은 전략 → 정책이 복구 동작을 못 배움", "실패-복구 시연 추가, 노이즈 확대, v7 실기로 보완"],
        ["PETG 브래킷 크리프", "케이블 장력으로 몇 주에 걸쳐 카메라 위치 이동", "케이블은 그리퍼 몸체에 고정. 구도 확정 후 2피스 알루미늄으로"],
        ["밸브 M3 물림 2 mm", "탭 깊이 3.5 의 한계, 과토크 시 암나사 손상", "0.5 N·m 토크 드라이버, 록타이트 243(G-2)"],
        ["Φ6 클로킹 핀 미사용", "재장착 시 툴 롤 ±0.69° 재현 불가", "한 번 달면 상수 보정. 필요 시 현장 리머(F-1)"],
        ["핑거·밸브 브래킷 생성 스크립트 없음", "수정 시 처음부터 재작도", "필요 시 cadquery 생성기 작성"],
        ["HF 캐시·workspace root 소유", "호스트에서 쓰기 실패", "docker exec 로 mkdir + chmod a+rwX (생성기에 내장)"]]
table(s, M, TOP, CW, rows, widths=[3.6, 6.4, 7.4], size=10, rh=Cm(1.02))

# ═══════════ 29. 다음 할 일 ═══════════
s = slide("다음에 어디부터 — 오늘 밤 · 월요일 · 그 다음", "14 / 다음")
w3 = (CW - Cm(1.0)) / 3
for i, (t, col, lines) in enumerate([
    ("오늘 밤 ~ 주말", AMBER, ["🔴 절삭 외주 2건 발주 (STEP+DXF+발주서 본문)", "재고품 B~F + 카메라 주문", "PETG 출력: 밸브 브래킷 · 손목캠 브래킷 · 핑거 시제품 → 그리퍼에 끼워 확인 (M5 122, 립, M4, 갭 2.4)",
        "22:30 결과 확인: sim_out/eval_isaac_v8/results.json", "0% 면 ①②③ 진단 (21번 슬라이드)", "성공률 나오면 1.5배 영역 결과로 일반화 판단"]),
    ("월요일 (9/14) 로봇 도착", GREEN, ["설치 · 작업대 높이 실측 → 알려주기", "table_z 갱신 → 재변환(6 s) → 시연 재생성(1.8 h) → 재학습(2.8 h)", "어댑터 플랜지 결합 확인 (M6×10, 9 N·m, 핀홀 DO NOT REAM)",
        "카메라 캘리브레이션 (cam_calibrate.py, 체커보드) → 언디스토션", "손목캠 실물 구도 확인 (장공 ±3 mm · 소프트웨어 크롭으로 미세 조정)", "정면캠 실제 위치 정합", "밸브 탈거 시 확인 4항목 (소음기 각인·튜브 굵기·코일호스·S/O 각인)"]),
    ("그 다음 주", NAVY, ["배선 → measure_grip_lead.py 로 지연 실측 → gripper_ctl LEAD 확정", "replay_v6_real.py --dry → 저속 1 ep → v7 실기 30~50 ep", "이어학습 4종: scratch / OMX / Isaac / Isaac+OMX → 데이터 효율 곡선",
        "손목캠 구도 확정 후 2피스 알루미늄 브래킷 설계·발주", "DR 강화(텍스처·배경), 실패-복구 시연", "closed-loop 평가에 접촉 물리 옵션(8/20 셋업 재사용)"])]):
    x = M + i * (w3 + Cm(0.5)); chip(s, x, TOP, w3, t, fill=col); panel(s, x, TOP + Cm(1.1), w3, Cm(10.2))
    txt(s, x + Cm(0.35), TOP + Cm(1.3), w3 - Cm(0.7), Cm(9.8), [("· " + l, {"size": 11}) for l in lines], gap=6)
foot(s, "위치를 바꾸면: wristcam_pose.py → make_wristcam_bracket → make_tool_assembly → wristcam_check → wristcam_occlusion → preview/render 순")
note(s, "가장 먼저: 절삭 외주 발주. 리드타임이 있는 유일한 항목이고 오늘이 지나면 하루 밀린다.")

prs.save(OUT)
print("저장:", OUT, "슬라이드", len(prs.slides._sldIdLst), "장")

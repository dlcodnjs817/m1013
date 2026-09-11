#!/usr/bin/env python3
"""2026-09-11 학회 논문 구성 PPT (KSMTE 2026 추계).

디자인: make_report_pptx_0814.py 의 체계 계승 (남색 바+스텝 칩, flowbox 파이프라인,
지브라 테이블, 푸터). 실행: python3 make_report_pptx_0820.py
출력: 대화록 및 PPT/OMX_M1013_작업정리_20260820.pptx
"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
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

FONT = "맑은 고딕"
MONO = "Consolas"
SW, SH = Cm(33.867), Cm(19.05)
OUT = "/home/kim/m1013/대화록 및 PPT/M1013_학회논문_구성_20260911.pptx"
FIG = "/home/kim/m1013/paper_figs"
IMG = "/home/kim/m1013/대화록 및 PPT"
SIM = "/home/kim/m1013/sim_out"

prs = Presentation()
prs.slide_width = SW
prs.slide_height = SH
BLANK = prs.slide_layouts[6]


def _set(run, size=14, bold=False, color=INK, font=FONT):
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
    tf.margin_left = Cm(0.9); tf.margin_top = Cm(0.28)
    p = tf.paragraphs[0]
    if step:
        run = p.add_run(); run.text = step + "  "
        _set(run, 15, True, LILAC)
    run = p.add_run(); run.text = title
    _set(run, 21, True, WHITE)


def textbox(s, x, y, w, h):
    tb = s.shapes.add_textbox(x, y, w, h)
    tb.text_frame.word_wrap = True
    return tb.text_frame


def bullets(tf, items, size=14):
    first = True
    for it in items:
        lv, txt = it[0], it[1]
        opt = it[2] if len(it) > 2 else {}
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = lv
        p.space_after = Pt(opt.get("after", 5))
        marks = {0: "▪  ", 1: "–  ", 2: "·  "}
        run = p.add_run()
        run.text = ("" if opt.get("nomark") else marks.get(lv, "")) + txt
        _set(run, opt.get("size", size - lv), opt.get("bold", False),
             opt.get("color", INK), MONO if opt.get("mono") else FONT)
        if opt.get("link"):
            run.hyperlink.address = opt["link"]
            run.font.color.rgb = NAVY


def table(s, x, y, w, rows, widths=None, size=11.5, header=True, rh=Cm(0.72)):
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
            c.margin_left = Cm(0.15); c.margin_right = Cm(0.15)
            c.margin_top = Cm(0.04); c.margin_bottom = Cm(0.04)
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
    tf = textbox(s, Cm(0.9), SH - Cm(1.0), SW - Cm(1.8), Cm(0.7))
    p = tf.paragraphs[0]
    run = p.add_run(); run.text = txt
    _set(run, 10, False, GREY)


def flowbox(s, x, y, w, h, txt, fill=NAVY, fg=WHITE, size=12, bold=True):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid(); b.fill.fore_color.rgb = fill
    b.line.color.rgb = LINE; b.line.width = Pt(0.75)
    tf = b.text_frame; tf.word_wrap = True
    tf.margin_left = Cm(0.1); tf.margin_right = Cm(0.1)
    tf.margin_top = Cm(0.06); tf.margin_bottom = Cm(0.06)
    for i, line in enumerate(txt.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run(); run.text = line
        _set(run, size if i == 0 else size - 2, bold if i == 0 else False, fg)
    return b


def arrow(s, x, y, w=Cm(0.7)):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x, y, w, Cm(0.5))
    a.fill.solid(); a.fill.fore_color.rgb = GREY
    a.line.fill.background()


def pic(s, path, x, y, h):
    if os.path.exists(path):
        s.shapes.add_picture(path, x, y, height=h)


def pic_w(s, path, x, y, w):
    if os.path.exists(path):
        s.shapes.add_picture(path, x, y, width=w)


# ═══════════ 1. 표지 ═══════════
s = slide()
r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
r.fill.solid(); r.fill.fore_color.rgb = NAVY; r.line.fill.background()
tf = textbox(s, Cm(2.2), Cm(4.2), Cm(29.5), Cm(11))
p = tf.paragraphs[0]
run = p.add_run(); run.text = "5축 시연 데이터의 6축 협동로봇 전이를 위한\n행동 다양체 분석과 EE pose 재타겟팅의 비용 정량화"
_set(run, 28, True, WHITE)
p = tf.add_paragraph(); p.space_before = Pt(10)
run = p.add_run()
run.text = "Action-Manifold Analysis and the Cost of EE-Pose Retargeting for Transferring\n5-DOF Demonstrations to a 6-DOF Collaborative Robot"
_set(run, 15, False, LILAC)
p = tf.add_paragraph(); p.space_before = Pt(24)
run = p.add_run()
run.text = "2026 한국생산제조학회 추계학술대회 (12. 9 ~ 12. 12, 쉐라톤 제주) — 논문 구성안"
_set(run, 14, False, LILAC)
p = tf.add_paragraph(); p.space_before = Pt(4)
run = p.add_run()
run.text = "2026-09-11  ·  이채원 (한국생산기술연구원 현장실습)"
_set(run, 13, False, LILAC)

# ═══════════ 2. 한 장 요약 ═══════════
s = slide()
bar(s, "논문 한 장 요약")
tf = textbox(s, Cm(0.9), Cm(2.4), Cm(32), Cm(8.2))
bullets(tf, [
    (0, "문제: 저가 5축 암(OMX)으로 찍은 모방학습 데모를 6축 협동로봇(Doosan M1013)에 쓰고 싶다 — 축 수가 다르다", {"bold": True}),
    (0, "기존: 이종 로봇을 최대 DOF 패딩 + 마스킹 + embodiment 토큰으로 처리 = '차원(dimension)' 문제로 취급 (OXE·Octo·OpenVLA·CrossFormer·HPT)"),
    (0, "재정의: EE pose 로 올리면 차원은 이미 7D↔7D 로 같다. 진짜 격차는 소스 도달집합이 SE(3)의 5차원 부분다양체라는 것 — 축이 '없는' 게 아니라 '있는데 종속'", {"bold": True, "color": GREEN}),
    (1, "닫힌형 구속식 1개:  atan2(p_y, p_x) = atan2((Re₁)_y, (Re₁)_x) = q₁   → 78,009 프레임 전수로 검증 (잔차 RMS 0.21°)"),
    (0, "비용: EE pose 공통 표현은 IK 재타겟팅 비용(특이점·연속성·작업영역)을 낳는다 → 5개 지표로 정량 보고 (표준 표현인데 아무도 비용을 안 적음)"),
    (0, "정합·검증: 손목캠 기하 설계(HFOV 85.6°) + Isaac Sim 물리 재생 + 검증셋 분리 ACT (진행 중)"),
    (0, "주장 범위: '전이가 된다'가 아니라 '무엇이 진짜 격차이고 그 격차를 넘는 비용이 얼마인가' — 실물 데이터 효율 곡선은 향후 연구", {"color": RED}),
], 14)
table(s, Cm(0.9), Cm(11.0), Cm(32), [
    ["구속식 잔차", "6D 유효랭크", "yaw 스팬", "재타겟팅", "특이점 여유", "Δq / 역검증", "Isaac 재생"],
    ["0.00° (항등) / 0.21°", "2.70 / 6", "16.5° (리밋 ±180°)", "159/159, 분지 0", "min|q5| 45.97°", "2.95°/fr · 4.89 mm", "3/3 성공, 1.6~7.5 mm"],
], size=12)
tf = textbox(s, Cm(0.9), Cm(13.3), Cm(32), Cm(3.5))
bullets(tf, [
    (0, "기여 ① 구속식 유도·검증   ② 재타겟팅 비용 지표 5종 정의·측정   ③ 관측공간 기하 정합 절차   ④ 시뮬 검증 + 실물 데이터 효율 실험 설계", {"bold": True, "color": NAVY}),
], 13.5)
foot(s, "KSMTE 2026 추계 · 논문 구성안 · 결과 없는 판 (실물 결과가 나오면 6절만 교체)")

# ═══════════ 3. 배경과 문제 재정의 ═══════════
s = slide()
bar(s, "배경 — 축 수 불일치를 어떻게 볼 것인가", "1. 서론")
tf = textbox(s, Cm(0.9), Cm(2.4), Cm(32), Cm(2.2))
bullets(tf, [
    (0, "OMX·SO-100 계열 저가 암으로 데모 수집이 보편화 → 협동로봇 현장 적용 시 데모를 다시 찍는 비용이 문제"),
    (0, "소스 OMX: 5R (yaw–pitch–pitch–pitch–roll) + 그리퍼 · 타깃 M1013: 6R + MHF2-16D2 · 태스크 pick & place · 163 ep / 78,009 fr · 2뷰 640×480 30 fps"),
], 13.5)
X0, X1 = Cm(0.9), Cm(17.3); W2 = Cm(15.6)
flowbox(s, X0, Cm(5.0), W2, Cm(1.3), "기존 접근 — 차원 문제", fill=GREY, size=14)
flowbox(s, X1, Cm(5.0), W2, Cm(1.3), "본 연구 — 다양체 문제", fill=NAVY, size=14)
tf = textbox(s, X0, Cm(6.5), W2, Cm(8))
bullets(tf, [
    (0, "이종 로봇 행동을 최대 DOF 로 패딩하고 없는 축은 마스킹"),
    (0, "embodiment 토큰·형상 토큰으로 '어느 로봇인지'를 입력"),
    (0, "검증된 세팅은 전부 full-DOF ↔ full-DOF (Franka 7, UR5e 6, WidowX 6, Google Robot)"),
    (0, "ZETA(2609.02546) — 가장 통제된 연구. appearance/gripper/arm/full 4분류. DOF 결손 소스는 명시적으로 미수행"),
    (0, "→ '없는 축'을 다루는 방법. 5축→6축에서 무엇이 얼마나 부족한지를 적지 못함", {"color": RED, "bold": True}),
], 13)
tf = textbox(s, X1, Cm(6.5), W2, Cm(8))
bullets(tf, [
    (0, "EE pose [p, r, g] ∈ ℝ⁷ 로 올리면 OMX 도 M1013 도 7D — 차원 문제는 여기서 사라짐"),
    (0, "남는 것: 5축 소스가 SE(3) 안에서 도달할 수 있는 집합의 모양"),
    (0, "joint2~4 축이 모두 arm plane Π(q₁)의 법선에 평행, joint5(roll) 축은 평면 안 → EE 위치 p 와 툴 x축 Re₁ 이 둘 다 Π(q₁) 위"),
    (0, "식 (1)  atan2(p_y, p_x) = atan2((Re₁)_y, (Re₁)_x) = q₁ → 여차원 1, 즉 5차원 부분다양체 𝓜 ⊂ SE(3)", {"bold": True}),
    (0, "→ 축이 없는 게 아니라 있는데 종속. 마스킹으로는 표현조차 되지 않음", {"color": GREEN, "bold": True}),
], 13)
foot(s, "핵심 문장: '차원은 같다. 다양체가 다르다.'")

# ═══════════ 4. 기존 연구 지형 ═══════════
s = slide()
bar(s, "기존 연구 지형 — 무엇이 이미 되어 있는가", "2. 관련 연구")
table(s, Cm(0.9), Cm(2.5), Cm(32), [
    ["계열", "대표 연구", "축 불일치 처리", "본 연구와의 관계"],
    ["대규모 이종 사전학습", "Open X-Embodiment / RT-X, Octo, OpenVLA, CrossFormer, HPT", "최대 DOF 패딩 + 마스킹 + embodiment 토큰", "소스·타깃 모두 full-DOF. DOF 결손 소스 없음"],
    ["형상 정보 주입", "Embedding Morphology into Transformers (2603.00182)", "kinematic 토큰 + 토폴로지 어텐션 + FiLM", "형상을 '입력'으로 넣지만 도달집합 결손은 안 다룸"],
    ["통제 실험", "ZETA (2609.02546)", "EEF-Delta 가 절대좌표 대비 +15%p", "가장 가까움. DOF 결손·데이터효율곡선 명시적 미수행"],
    ["데이터 효율", "Data Analogies (2603.06450)", "소스 다양성↑ → 타깃 성공률 곡선", "'타깃 데모 N개 등가' 환산은 없음"],
    ["시각 갭 완화", "RoVi-Aug, Mirage, Cloak (2606.22836)", "로봇 외형·시점 augmentation / EE 마스킹", "시각을 '가림'. 우리는 타깃 리그를 소스에 맞춰 '설계'"],
    ["저가 로봇 IL", "SmolVLA, SO-100/101, LeRobot", "저가 암 위에서 학습·평가", "저가 데모가 협동로봇에 값어치를 하는지는 미답"],
    ["행동공간 통일", "Unify Actions in Camera Frame, PointAction, Latent Action Diffusion", "카메라 프레임·3D 점·잠재 행동", "통일 표현의 '대가'(IK 특이점·작업영역)는 미보고"],
], widths=[2.2, 4.2, 4.0, 4.6], size=11, rh=Cm(1.35))
tf = textbox(s, Cm(0.9), Cm(14.0), Cm(32), Cm(2.5))
bullets(tf, [
    (0, "공통 결론: DOF 결손 소스와 재타겟팅 비용을 함께 다룬 연구가 없다 — 이 빈자리가 본 논문의 자리", {"bold": True, "color": NAVY}),
], 14)
foot(s, "2절은 반 페이지. 각 계열 두 줄 + 위 마지막 문장")

# ═══════════ 5. 차별점 ═══════════
s = slide()
bar(s, "기존 연구와 다른 점 — 6가지, 성립 조건별", "차별점")
table(s, Cm(0.9), Cm(2.5), Cm(32), [
    ["#", "차별점", "성립 조건"],
    ["1", "'축 개수 불일치'가 아니라 행동 다양체의 구속으로 재정의 — 기존은 패딩·마스킹으로 차원 문제, 우리는 7D↔7D 로 차원 같고 축이 있는데 종속", ("지금 데이터로 성립", {"color": GREEN, "bold": True})],
    ["3", "EE pose 공통 행동공간의 청구서 (IK 특이점 여유 45.97°, Δq 2.95°/fr, 역검증 ≤4.89 mm) 정량 보고 — 표준 표현인데 아무도 비용을 안 적음", ("지금 데이터로 성립", {"color": GREEN, "bold": True})],
    ["4", "관측공간 정합을 기하로 설계 — HFOV 63.4° 불합격 / 85.6° 합격 판정, 최종 마운트 (0,−65,−10)·틸트 21.8°", ("지금 데이터로 성립", {"color": GREEN, "bold": True})],
    ["2", "결손이 스칼라라 성능을 결손 크기의 함수로 측정 가능 — ZETA 도 명시적으로 미수행", ("실물 결과 필요", {"color": NAVY})],
    ["6", "'OMX 159 ep = M1013 실물 데모 N개 등가' 지표", ("실물 결과 필요", {"color": NAVY})],
    ["5", "형상 격차 vs 도메인 격차 2×2 분리", ("Isaac 데모 추가 → 후속 논문", {"color": GREY})],
], widths=[0.5, 12.5, 3.0], size=12, rh=Cm(1.5))
tf = textbox(s, Cm(0.9), Cm(13.8), Cm(32), Cm(2.5))
bullets(tf, [
    (0, "결과가 마감에 못 미치면 1·3·4 로 분석·시스템 논문이 그대로 성립 — 물러날 자리가 있는 구조", {"bold": True, "color": NAVY}),
    (0, "실물 결과(v7 수집·이어학습)가 10월 중순까지 나오면 2·6 을 6절에 얹어 결과 있는 판으로 승격"),
], 13.5)
foot(s, "지도교수님 지시 '기존 연구와 다른 점' 에 대한 답")

# ═══════════ 6. 3절 — 구속식 ═══════════
s = slide()
bar(s, "행동 다양체 — 구속식은 근사가 아니라 항등식", "3절")
pic_w(s, f"{FIG}/fig1_constraint.png", Cm(0.9), Cm(2.4), Cm(20.5))
tf = textbox(s, Cm(22.0), Cm(2.4), Cm(11), Cm(13))
bullets(tf, [
    (0, "그림 1 — 163 ep / 78,009 프레임 전수, omx_f.urdf FK", {"bold": True, "color": NAVY}),
    (1, "az(Re₁) − q₁ = 0.00000° — 정확한 항등식. EE 방위 성분의 원천은 q₁ 뿐"),
    (1, "az(p) − q₁ = RMS 0.21° / max 0.51° — 횡오프셋 0.66 mm 환산, 기구 오프셋"),
    (1, "→ az(Re₁) = az(p): SE(3) 위 닫힌형 홀로노믹 구속 1개"),
    (0, "의미", {"bold": True, "color": NAVY}),
    (1, "7D 표현 중 실질 자유도 6 (pose 5 + grip 1)"),
    (1, "'yaw 를 독립 사용하는 조작' 사례가 소스에 원천 부재 → 타깃 데모가 채워야 할 것이 정확히 특정됨"),
    (0, "09-09 문서의 'yaw ≈ atan2(y,x)' 는 근사 서술 — 논문에는 이 정확한 형태로", {"color": RED}),
], 12.5)
foot(s, "재현: tx90/action_manifold_analysis.py (~1분) · 그림: tx90/make_paper_figs.py")

# ═══════════ 7. 3절 — 커버리지 ═══════════
s = slide()
bar(s, "커버리지 — 결손은 두 층위다", "3절")
pic_w(s, f"{FIG}/fig2_coverage.png", Cm(0.9), Cm(2.4), Cm(20.5))
tf = textbox(s, Cm(22.0), Cm(2.4), Cm(11), Cm(13))
bullets(tf, [
    (0, "그림 2 (a) — 6D pose 유효랭크 2.70 / 6", {"bold": True, "color": NAVY}),
    (1, "설명비율 63.5 / 19.6 / 14.3 / 2.0 / 0.4 / 0.1 % — 4번째 축부터 급감"),
    (0, "그림 2 (b) — 데이터가 실제로 차지한 각도 범위", {"bold": True, "color": NAVY}),
    (1, "joint1(yaw) 스팬 16.5° vs 가동 360°"),
    (1, "joint5(roll) 73.7°, 툴 z 고도각 70.3°"),
    (0, "해석 — 결손 2층위", {"bold": True, "color": GREEN}),
    (1, "① 기구적 결손: 식 (1), 1차원 — 어떤 데이터를 찍어도 못 채움"),
    (1, "② 데이터 분포 결손: 기구 한계보다 훨씬 좁음 — 수집으로 채울 수 있음"),
    (1, "→ 타깃 데모 수집 시 yaw 다양성을 의도적으로 포함해야 하는 근거 (7절)"),
], 12.5)
foot(s, "논문 3.5절 · 표 1 잔차 3종 + 이 두 그림")

# ═══════════ 8. 4절 — 파이프라인 ═══════════
s = slide()
bar(s, "EE pose 재타겟팅 파이프라인 — 비용 지표 5종을 정의한다", "4절")
X = [Cm(0.9), Cm(5.5), Cm(10.1), Cm(14.7), Cm(19.3), Cm(23.9), Cm(28.5)]
W = Cm(4.3)
flows = ["OMX 데모\n5축 joint → FK", "EE pose 7D\n7MA 평활 · 6 Hz 앵커", "작업대 오프셋\n+ TCP 0.0725 파지점", "손목 45° 보정\n(특이점 여유↑)",
         "DLS IK\nλ∝오차 · 시드 · 분지거부", "M1013 관절\nstate = action[t−1]", "검증 4종\nIK/연속/FK/kNN"]
for i, txt in enumerate(flows):
    flowbox(s, X[i], Cm(2.6), W, Cm(2.4), txt, fill=NAVY if i not in (0, 6) else GREY, size=11.5)
    if i < 6:
        arrow(s, X[i] + W + Cm(0.03), Cm(3.55), Cm(0.5))
tf = textbox(s, Cm(0.9), Cm(5.4), Cm(15.5), Cm(6))
bullets(tf, [
    (0, "작업대 배치 스윕 — 54 후보 → 채점(min|q5|, j3 여유, maxΔq) → 5 → 기하검사 → OFFSET (+0.05, −0.15, +0.10)"),
    (0, "TCP 미보정 시 접근 틸트 44° × 0.12 m = 수평 84 mm 오차 → 보정 필요성의 수치"),
    (0, "손목 45° 보정: 그리퍼를 일자로 다는 결정 하나가 특이점 여유 10° → 50° 와 파지 실패를 동시 해결"),
], 13)
table(s, Cm(17.0), Cm(5.4), Cm(15.9), [
    ["비용 지표 (제안)", "정의", "159 ep 결과"],
    ["(a) 특이점 여유", "min |q5| — 손목 특이점까지 거리", "45.97°"],
    ["(b) 관절 연속성", "프레임 간 max Δq", "2.95°"],
    ["(c) 재타겟팅 정확도", "FK 역검증 위치 / 각도 오차", "4.89 mm / 1.03°"],
    ["(d) 해 안정성", "IK 실패 · 분지 점프 수", "0 / 0"],
    ["(e) 작업영역 축소율", "특이점 회피 후 사용 가능 영역 / 전체", "manipulability 맵 (도착 후)"],
], widths=[3.2, 5.0, 3.2], size=11.5)
tf = textbox(s, Cm(0.9), Cm(11.4), Cm(32), Cm(4))
bullets(tf, [
    (0, "왜 '비용'을 보고하나 — EE-pose / EEF-delta 공통 행동공간은 사실상 표준(ZETA: 절대좌표 대비 +15%p)인데, 정책 출력 pose 를 타깃 관절로 되돌릴 때의 대가를 정량 보고한 사례가 없다", {"bold": True}),
    (0, "협동로봇 맥락: 사람과 같은 공간에서 저속 운용이 전제 → 특이점 근방 관절속도 발산은 정확도가 아니라 안전 요건. 여유 45.97° 는 그 수치", {"color": RED}),
], 13)
foot(s, "논문 4.1~4.5절 · 표 2 = 위 표 · 변환 5.7 s (m1013_kin.py 독립 DLS, MoveIt 불사용)")

# ═══════════ 9. 4절 — 비용 분포 ═══════════
s = slide()
bar(s, "재타겟팅 비용 — 에피소드별 분포", "4절")
pic_w(s, f"{FIG}/fig3_retarget_cost.png", Cm(0.9), Cm(2.5), Cm(32))
tf = textbox(s, Cm(0.9), Cm(12.6), Cm(32), Cm(4.5))
bullets(tf, [
    (0, "그림 3 — 159 에피소드 전부. 최악값(빨간 선)이 곧 표 2 의 수치. 분포 자체가 '이 파이프라인이 어디까지 안전한가'의 근거"),
    (0, "(a) 손목 특이점 여유는 최악 46°, 대부분 60~85° — 손목 45° 보정 전에는 10° 대였음"),
    (0, "(b) 관절 연속성 최악 2.95°/frame(30 Hz) — 실기 MoveSplineJoint 재생에 안전한 범위 · (c) 역검증 오차는 앵커 6 Hz 보간에서 나오는 값, 파지 허용오차(조 스트로크 32 mm) 대비 충분"),
], 13)
foot(s, "출처: m1013/v6_staging/report.json (TCP 0.0725 재변환본)")

# ═══════════ 10. 5절 — 관측공간 정합 ═══════════
s = slide()
bar(s, "관측공간 정합 — 타깃 리그를 기하로 설계한다", "5절")
tf = textbox(s, Cm(0.9), Cm(2.4), Cm(19), Cm(13))
bullets(tf, [
    (0, "원칙: 구도를 먼저 못 박아야 남는 차이가 '순수 시각 도메인 갭'으로 귀속된다. 구도 불일치와 도메인 갭이 섞이면 실패 원인 분리가 불가능", {"bold": True}),
    (0, "기존(RoVi-Aug·Mirage·Cloak)은 로봇 외형·시점을 augmentation 이나 마스킹으로 '가림'. 우리는 반대로 타깃 손목캠을 정량 판정으로 '설계'"),
    (0, "손목캠 기하 결정 (09-11 확정)", {"bold": True, "color": NAVY}),
    (1, "카메라 U20CAM-720P (정면·손목 동일 기종, OMX 리그와 같음) · 1280×720 → 960×720 중앙 크롭 → 640×480 · HFOV 85.6°"),
    (1, "광심 플랜지 로컬 (0, −65, −10) mm · 툴축 위 Z=140 조준 · 틸트 21.8° · 보드 세로 장착"),
    (1, "판정 기준: 파지 정렬구간(2.0~0.7 s 전) 큐브 8꼭짓점 가시 + 렌즈 스탠드오프 ±12 mm 오차 포함 여유 0.63 (1.0 = 화면 가장자리)"),
    (0, "화각 요구조건", {"bold": True, "color": NAVY}),
    (1, "센서 640×480 크롭(HFOV 63.4°)은 8 ep 중 2 ep 에서 파지 직전 큐브 이탈 → 불합격. 85.6° 는 8/8 → 채택"),
    (1, "※ 이 판정은 구 마운트 기준 — 최종 마운트로 wristcam_check.py 재실행 후 논문 수치 확정 (수 초)", {"color": RED}),
    (0, "정면캠: OMX 리그 것을 그대로 이관 → 도메인 갭 최소 · 검증기 wristcam_check.py 는 Isaac 없이 FK 만으로 투영"),
], 12.5)
pic_w(s, f"{SIM}/wristcam_solve/d_grasp.png", Cm(20.6), Cm(2.6), Cm(12.3))
pic_w(s, f"{IMG}/img_0906/r_assembly.png", Cm(23.0), Cm(11.6), Cm(7.6))
tf = textbox(s, Cm(20.6), Cm(11.9), Cm(1.5), Cm(0.6))
foot(s, "우: 손목캠 파지 순간 렌더(09-04 마운트) · 툴 어셈블리 CAD (어댑터+MHF2-16D2+핑거, cadquery 커널 검증 완료)")

# ═══════════ 11. 6절 — 시뮬 검증 ═══════════
s = slide()
bar(s, "시뮬레이션 검증 — 파이프라인이 실제로 돈다", "6절")
table(s, Cm(0.9), Cm(2.5), Cm(15.5), [
    ["Isaac 재생 (GT 궤적)", "ep0", "ep50", "ep130"],
    ["성공", "✓", "✓", "✓"],
    ["배치 오차 (mm)", "7.5", "1.6", "5.2"],
    ["추종 오차 max (°)", "1.85", "1.34", "3.14"],
], widths=[3.2, 1.5, 1.5, 1.5], size=12)
tf = textbox(s, Cm(0.9), Cm(6.2), Cm(15.5), Cm(6))
bullets(tf, [
    (0, "Isaac Sim 5.1 · m1013.usd · 실물 그리퍼 기하(npz) · 상판 0.4624 · TCP 0.0725 · PhysX 60 Hz position drive"),
    (0, "이건 정답 궤적 재생 — 재타겟팅 결과가 물리적으로 파지·운반·배치 가능함을 보임 (모델과 무관)"),
    (0, "정책이 등장하려면 → 오른쪽", {"bold": True, "color": NAVY}),
], 13)
table(s, Cm(17.3), Cm(2.5), Cm(15.6), [
    ["검증셋 분리 ACT (진행 중)", "값"],
    ["분할", "seed 0 무작위 · 학습 139 / 검증 20 ep"],
    ["설정", "09-09 전체 학습과 동일 (ACT, 100k, batch 8) — 차이는 held-out 유무뿐"],
    ["평가", "held-out 20 vs train-ref 20 — 관절오차 mean/median/max · 그리퍼 일치 · 출력 연속성"],
    ["참조", "전체 159 ep 학습 모델을 같은 held-out 에 → '본 데이터' 기준선"],
    ["상태", ("09-11 15:00 시작 · ~19:00 완료 예정", {"color": NAVY, "bold": True})],
], widths=[3.0, 8.0], size=11.5, rh=Cm(1.1))
tf = textbox(s, Cm(17.3), Cm(9.6), Cm(15.6), Cm(5))
bullets(tf, [
    (0, "이게 들어가면 주장이 한 단계 올라간다: '재타겟팅 데이터로 학습한 정책이 타깃 기구학에서 실행 가능'"),
    (0, "held-out 정책 출력 npz → Isaac 재생까지 이어짐 (표 3 두 번째 줄)"),
    (0, "기존 0.62~0.67° open-loop 오차는 159 ep 전부 학습한 값 — 논문에 못 씀", {"color": RED}),
    (0, "정규화 통계는 데이터셋 전체 meta 사용(held-out 포함) — 논문에 한 줄 명시"),
], 12.5)
foot(s, "논문 6절 · 표 3 · lerobot 0.2.0 episodes 서브셋 IndexError 패치 (lerobot_dataset.py, 백업 .orig_20260911)")

# ═══════════ 12. 논문 구성 ═══════════
s = slide()
bar(s, "논문 구성 — 절별 내용과 그림·표", "구성")
table(s, Cm(0.9), Cm(2.5), Cm(32), [
    ["절", "내용", "그림·표"],
    ["1 서론", "저가 암 IL 보편화 vs 협동로봇 재수집 비용 · 기존은 '없는 축' · 우리는 '있는데 종속' · 기여 ①~④", "—"],
    ["2 관련 연구", "5계열 각 두 줄 · 공통 결론: DOF 결손 소스·재타겟팅 비용 미답", "—"],
    ["3 행동 다양체 분석", "세팅 · 공통 표현 · 식(1) 유도 · 실데이터 검증 · 커버리지(결손 2층위) · 함의", "표 1 · 그림 1 · 그림 2"],
    ["4 재타겟팅과 비용", "파이프라인 · 배치 스윕 · 비용 지표 5종 정의 · 결과 · 협동로봇 안전 맥락", "표 2 · 그림 3 (+스윕 맵)"],
    ["5 관측공간 정합", "원칙 · 손목캠 기하 결정 · 화각 요구조건 · 정면캠 이관", "그림 4 접근 구간 가시성 (재실행)"],
    ["6 시뮬 검증", "Isaac 재생 3 ep · 검증셋 분리 ACT held-out 평가 · 정책 출력 재생", "표 3"],
    ["7 한계·향후", "제한 작업영역 · 접촉 물리 · 실물 미검증 / 실물 데이터 효율 곡선 · yaw 평가군 · 등가 데모 수 · 2×2", "—"],
    ["8 결론", "3문장", "—"],
], widths=[2.6, 10.0, 3.4], size=11.5, rh=Cm(1.15))
tf = textbox(s, Cm(0.9), Cm(13.4), Cm(32), Cm(3))
bullets(tf, [
    (0, "그림 1·2·3 은 이미 제작 완료 (paper_figs/) · 그림 4 는 최종 마운트로 재실행 · 표 3 은 학습 완료 후 채움"),
    (0, "결과 있는 판으로 승격 시: 6절에 실물 데이터 효율 곡선(scratch / 비전만 / 전체 × 데모 10/30/60/120)과 'OMX 159 ep = N개 등가' 추가, 제목을 '…모방학습 전이: 행동 다양체 구속 관점의 정량 평가' 로 교체"),
], 13)
foot(s, "결과 없는 판이 정본. 2·3·4·5절은 어느 판이든 그대로 — 지금 쓰기 시작해도 버리는 게 없음")

# ═══════════ 13. 일정·리스크·한계 ═══════════
s = slide()
bar(s, "일정 · 리스크 · 한계", "계획")
table(s, Cm(0.9), Cm(2.5), Cm(17), [
    ["시점", "내용"],
    ["09-14 (월)", "M1013 도착 + 절삭 외주 2건 발주 (발주서·STEP·DXF 준비 완료)"],
    ["09-14 ~ 입고", "배선 · ROS2 · 카메라 노드 · manipulability 실측 · 작업대 확정 · 저속 궤적 재생 (그리퍼 없이 가능)"],
    ["09-21 ~ 09-28", "금구 입고 → Φ6 H7 현장 리머 → 그리퍼 장착 → grip-lead 실측"],
    ["~10-05", "v7 실기 수집 30~50 ep (yaw 다양성 포함 · 평가군 2종 분리)"],
    ["~10-19", "이어학습 3종 × 데모 수 4단계 + 평가"],
    ["10월 말~11월 초", ("초록 마감 — 홈페이지 미공지, 확인 필요", {"color": RED, "bold": True})],
    ["12-09 ~ 12-12", "학술대회 발표 (쉐라톤 제주)"],
], widths=[3.2, 9.0], size=11.5, rh=Cm(1.05))
tf = textbox(s, Cm(18.8), Cm(2.5), Cm(14.2), Cm(13))
bullets(tf, [
    (0, "리스크", {"bold": True, "color": RED}),
    (1, "절삭 외주 납기 — 유일한 크리티컬 패스. 발주 시 '영업일 며칠'로 회신받고 급행 가능 여부 확인"),
    (1, "초록 마감일 미확인 — 결과 판 / 분석 판을 가르는 유일한 변수"),
    (1, "손목캠 브래킷 LENS_STANDOFF 미실측 (OMX 리그 동일 기종으로 실측)"),
    (0, "논문의 한계 (7절에 정직하게)", {"bold": True, "color": NAVY}),
    (1, "EE pose 공통 표현의 대가 = IK 특이점 → 제한 작업영역 내 결과임을 명시"),
    (1, "접촉 물리 재현도(파지 미끄러짐·변형)는 실물 대비 낮음"),
    (1, "실물 미검증 — 결과 없는 판에서는 '전이가 된다'를 주장하지 않음"),
    (0, "지금 할 것", {"bold": True, "color": GREEN}),
    (1, "학회 초록 마감·원고 형식 확인 · 절삭 납기 확인 · split 학습 완료 후 평가 · wristcam_check 재실행 · 09-09 문서 구속식 정정"),
], 12.5)
foot(s, "M1013 = 협동로봇 (ISO/TS 15066). '산업용' 이라 쓰지 말 것")

prs.save(OUT)
print("saved:", OUT, os.path.getsize(OUT), "bytes,", len(prs.slides), "slides")

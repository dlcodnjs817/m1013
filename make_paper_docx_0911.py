# -*- coding: utf-8 -*-
"""KSMTE 2026 추계학술대회 논문 초안 (결과 없는 판) — 2단 편집 docx 생성.

실행: python3 make_paper_docx_0911.py
출력: 대화록 및 PPT/논문초안_KSMTE2026_20260911.docx
[  ] 표시는 학습 완료·확인 후 채울 자리.
"""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FIG = "/home/kim/m1013/paper_figs"
OUT = "/home/kim/m1013/대화록 및 PPT/논문초안_KSMTE2026_20260911.docx"
FONT_KO = "맑은 고딕"
FONT_EN = "Times New Roman"

doc = Document()
st = doc.styles["Normal"]
st.font.name = FONT_EN
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_KO)
st.font.size = Pt(9.5)
st.paragraph_format.space_after = Pt(0)
st.paragraph_format.line_spacing = 1.15

sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.0)
sec.left_margin = sec.right_margin = Cm(1.8)


def set_cols(section, n, space_cm=0.7):
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols"); sectPr.append(cols)
    cols.set(qn("w:num"), str(n)); cols.set(qn("w:space"), str(int(space_cm * 567)))


def run(p, text, size=9.5, bold=False, italic=False, color=None):
    r = p.add_run(text)
    r.font.name = FONT_EN
    r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_KO)
    r.font.size = Pt(size); r.bold = bold; r.italic = italic
    if color: r.font.color.rgb = color
    return r


def para(text="", size=9.5, align=None, before=0, after=0, indent=True, bold=False, italic=False):
    p = doc.add_paragraph()
    if align: p.alignment = align
    p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after)
    if indent: p.paragraph_format.first_line_indent = Cm(0.5)
    if text: run(p, text, size, bold, italic)
    return p


def h1(text):
    p = para(text, 10.5, before=8, after=3, indent=False, bold=True); return p


def h2(text):
    p = para(text, 9.5, before=5, after=2, indent=False, bold=True); return p


def eq(text, label):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3); p.paragraph_format.space_after = Pt(3)
    run(p, text, 9.5, italic=True); run(p, f"        ({label})", 9.5)


def caption(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(6)
    run(p, text, 8.5)


def figure(path, cap, width_cm=8.0):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    if os.path.exists(path):
        p.add_run().add_picture(path, width=Cm(width_cm))
    caption(cap)


def table(cap, headers, rows, widths):
    caption(cap)
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW"); tblPr.append(tblW)
    tblW.set(qn("w:type"), "dxa"); tblW.set(qn("w:w"), str(int(sum(widths) * 567)))
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run(p, h, 8.5, bold=True)
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            p = cells[i].paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i else WD_ALIGN_PARAGRAPH.LEFT
            run(p, v, 8.5)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


# =====================================================================
# 제목 블록 (1단)
# =====================================================================
p = para("5축 시연 데이터의 6축 협동로봇 전이를 위한 행동 다양체 분석과\nEE pose 재타겟팅의 비용 정량화",
         14, WD_ALIGN_PARAGRAPH.CENTER, after=4, indent=False, bold=True)
p = para("Action-Manifold Analysis and the Cost of End-Effector-Pose Retargeting\nfor Transferring 5-DOF Demonstrations to a 6-DOF Collaborative Robot",
         11, WD_ALIGN_PARAGRAPH.CENTER, after=8, indent=False)
p = para("이채원*, [지도교수명]†", 10, WD_ALIGN_PARAGRAPH.CENTER, after=1, indent=False)
p = para("*한국생산기술연구원 [부서명], †[소속]", 9, WD_ALIGN_PARAGRAPH.CENTER, after=10, indent=False)

p = para("", indent=False, after=2); run(p, "Abstract", 9.5, bold=True)
p = para(indent=False, after=4)
run(p, ("Demonstrations collected on low-cost 5-DOF arms are attractive as pre-training data for 6-DOF collaborative robots, "
        "but the mismatch in joint count is usually handled as a dimension problem, i.e., by padding and masking action vectors. "
        "We show that, once actions are expressed as end-effector (EE) poses, both robots share a 7-D action space and the real gap "
        "is geometric: the reachable set of a 5R yaw–pitch–pitch–pitch–roll chain is a 5-dimensional submanifold of SE(3) defined by a "
        "single closed-form holonomic constraint, the azimuth of the tool x-axis equals the azimuth of the EE position. "
        "We verify this identity on 78,009 frames of OpenMANIPULATOR-X demonstrations (residual RMS 0.21°) and show that the data "
        "occupies an even narrower region (effective rank 2.70/6, yaw span 16.5°). We then quantify the price of the EE-pose common "
        "action space when retargeting to a Doosan M1013 through damped-least-squares IK—wrist-singularity margin, per-frame joint "
        "continuity, forward-kinematics re-check error, branch jumps, and workspace reduction—and report 159/159 episodes retargeted "
        "with min|q5| = 45.97°, max Δq = 2.95°/frame and ≤ 4.89 mm error. A geometric procedure for matching the wrist-camera "
        "observation space and physics replay in Isaac Sim complete the pipeline. Real-robot data-efficiency experiments are left as future work."), 9)
p = para(indent=False, after=10)
run(p, "Key Words: ", 9, bold=True)
run(p, "Cross-embodiment transfer(이종형상 전이), Imitation learning(모방학습), Action manifold(행동 다양체), "
       "Inverse-kinematics retargeting(역기구학 재타겟팅), Collaborative robot(협동로봇), Kinematic singularity(기구학적 특이점)", 9)

# =====================================================================
# 본문 (2단)
# =====================================================================
body = doc.add_section(WD_SECTION.CONTINUOUS)
set_cols(body, 2)

h1("1. 서 론")
para("OpenMANIPULATOR-X(이하 OMX), SO-100 계열과 같은 저가 소형 매니퓰레이터로 모방학습 시연을 수집하는 일이 보편화되었다[11,12]. "
     "그러나 생산 현장에 투입되는 로봇은 대개 6축 협동로봇이며, 로봇이 바뀔 때마다 시연을 다시 수집하는 비용이 저가 시연 자산의 "
     "재활용을 가로막는다. 본 연구는 5축 OMX에서 수집한 pick-and-place 시연을 6축 협동로봇 Doosan M1013으로 옮기는 문제를 다룬다.")
para("기존의 이종형상(cross-embodiment) 연구는 로봇 간 행동 차원의 차이를 최대 자유도 패딩·마스킹과 embodiment 토큰으로 처리한다[1-5]. "
     "이 접근은 '없는 축'을 다루는 방법이며, 검증된 사례는 대부분 소스와 목표가 모두 6~7축 full-DOF 인 경우이다[6]. "
     "본 연구가 다루는 5축→6축은 축이 없는 것이 아니라, 있으되 다른 축에 종속된 경우다. 엔드이펙터(EE) pose 로 행동을 표현하면 두 로봇의 "
     "행동 차원은 7로 같아지지만, 5축 체인이 SE(3) 안에서 도달할 수 있는 집합은 5차원 부분다양체에 그친다. 이 결손은 패딩이나 마스킹으로는 "
     "표현조차 되지 않는다.")
para("본 논문의 기여는 다음과 같다. (1) 5R 체인의 도달집합을 정의하는 닫힌형 구속식을 유도하고 78,009 프레임의 실데이터로 검증하였다. "
     "(2) EE pose 공통 행동공간이 수반하는 역기구학(IK) 재타겟팅 비용을 5개 지표로 정의하고 159 에피소드 전체에 대해 측정하였다. "
     "(3) 이종형상 전이의 전제조건으로 관측공간 정합을 두고, 손목 카메라의 위치·자세·화각을 기하 판정으로 결정하는 절차를 제시하였다. "
     "(4) 시뮬레이션 물리 재생으로 파이프라인의 실행 가능성을 확인하고, 실물 데이터 효율 실험을 설계하였다.")

h1("2. 관련 연구")
para("대규모 이종 로봇 데이터 사전학습(Open X-Embodiment[1], Octo[2], OpenVLA[3], CrossFormer[4], HPT[5])은 로봇별 행동 벡터를 "
     "고정 길이 슬롯에 패딩하고 마스크로 유효 항목을 표시하는 방식으로 자유도 차이를 흡수한다. 형상 정보를 kinematic 토큰과 "
     "토폴로지 어텐션으로 주입하는 시도도 있다[13]. 이들은 형상을 입력으로 다루지만 소스 도달집합의 결손 자체를 분석하지는 않는다.")
para("ZETA[6]는 appearance/gripper/arm/full 네 종류의 형상 변화에 대해 zero-shot 전이를 통제 실험하였고, EE 기준 상대 행동 표현이 "
     "절대 좌표 대비 약 15%p 우수함을 보고하였다. 그러나 자유도가 결손된 소스와 데이터 효율 곡선은 다루지 않았다. "
     "Data Analogies[7]는 소스 다양성에 따른 목표 로봇 성공률 곡선을 제시하나 목표 시연 등가 수로 환산하지는 않는다. "
     "RoVi-Aug[8], Mirage[9], Cloak[10]은 로봇 외형과 시점을 증강 또는 마스킹으로 가려 시각 격차를 줄인다. 본 연구는 반대로 목표 리그를 "
     "소스 관측 분포에 맞춰 설계한다. 행동공간을 카메라 프레임이나 잠재 행동으로 통일하는 연구[14]도 통일 표현의 대가, 즉 IK 특이점과 "
     "작업영역 제한은 보고하지 않는다. 저가 로봇 모방학습[11,12]은 급증했으나 그 시연이 협동로봇에 어느 정도 값어치를 하는지는 답이 없다.")

h1("3. 문제 정의와 행동 다양체 분석")
h2("3.1 실험 구성")
para("소스 로봇은 OMX(5R: yaw–pitch–pitch–pitch–roll)와 1자유도 그리퍼, 목표 로봇은 Doosan M1013(6R)과 SMC MHF2-16D2 평행 그리퍼다. "
     "과제는 파란 큐브를 집어 지정 구역에 놓는 pick-and-place 이며, 소스 시연은 163 에피소드 78,009 프레임(30 fps), 손목 카메라와 정면 "
     "카메라 각 640×480 영상을 포함한다. 학습에는 유효성 검사를 통과한 159 에피소드 76,345 프레임을 사용한다.")
h2("3.2 공통 행동 표현")
para("관절 시퀀스를 URDF 순기구학(FK)으로 변환하여 행동을 a = [p, r, g] ∈ ℝ⁷ (위치 3, 회전 3, 그리퍼 1)로 표현한다. "
     "이 시점에서 관절 개수는 표현에서 사라지며, OMX와 M1013의 행동 차원은 동일하다. 정책 출력 pose 는 IK 로 목표 로봇 관절값으로 되돌린다.")
h2("3.3 5축 체인의 도달집합 구속")
para("OMX의 joint1은 베이스 z축 회전(q₁)이고 joint2~4의 회전축은 모두 q₁이 정의하는 arm plane Π(q₁)의 법선 n(q₁) = [−sin q₁, cos q₁, 0]ᵀ 에 "
     "평행하며, joint5(roll)의 축은 Π(q₁) 안에 놓인다. 따라서 링크에 횡방향 오프셋이 없는 한 EE 위치 p 와 툴 x축 Re₁ 은 모두 Π(q₁) 위에 있고, 다음이 성립한다.")
eq("atan2(p_y, p_x) = atan2((Re₁)_y, (Re₁)_x) = q₁", "1")
para("즉 5축 체인의 도달집합은 식 (1)의 좌변과 중변이 같다는 하나의 홀로노믹 구속을 만족하는 집합")
eq("𝓜 = {(p, R) ∈ SE(3) : n(atan2(p_y, p_x))ᵀ R e₁ = 0}", "2")
para("이며, SE(3)의 여차원 1, 즉 5차원 부분다양체다. 7차원 행동 벡터 중 실질 자유도는 6(pose 5 + 그리퍼 1)이다. "
     "이는 근사가 아니라 체인 구조에서 나오는 항등식이므로, 어떤 시연을 추가로 수집해도 채워지지 않는 '기구적 결손'이다.", indent=False)
h2("3.4 실데이터 검증")
para("163 에피소드 78,009 프레임 전체에 대해 FK 로 p, R 을 계산하고 식 (1)의 세 항 사이의 잔차를 측정하였다(Table 1, Fig. 1). "
     "툴 x축 방위각과 q₁의 차는 수치 정밀도 수준(0.00000°)으로 정확히 일치하고, 위치 방위각과 q₁의 차는 RMS 0.21°, 최대 0.51°로 "
     "수평 반경 0.28~0.33 m 에서 횡오프셋 0.66 mm 에 해당한다. 이는 링크 기구 오프셋에서 나오는 값이며, 구속식이 실데이터에서 성립함을 보인다.")
table("Table 1  Residuals of the constraint (163 episodes, 78,009 frames)",
      ["항", "RMS [deg]", "max [deg]"],
      [["az(Re₁) − q₁", "0.00000", "0.00000"],
       ["az(p) − q₁", "0.20953", "0.50766"],
       ["az(Re₁) − az(p)", "0.20953", "0.50766"]],
      [3.4, 2.2, 2.2])
figure(f"{FIG}/fig1_col.png",
       "Fig. 1  Constraint check: (a) tool-x azimuth vs. position azimuth, 8,000 of 78,009 frames; (b) residual histogram.")
h2("3.5 데이터 커버리지")
para("기구적 결손과 별개로, 시연 데이터가 실제로 차지하는 영역은 기구 한계보다 훨씬 좁다(Fig. 2). 위치를 특성길이 0.1 m 로 무차원화한 "
     "6차원 pose 분포의 엔트로피 유효랭크는 2.70/6 이며, 주성분 설명비율은 63.5/19.6/14.3/2.0/0.4/0.1%로 4번째 성분부터 급감한다. "
     "joint1(yaw)이 차지한 범위는 16.5°(가동 범위 360°), joint5(roll)는 73.7°, 툴 z축 고도각은 13.6~83.9°다. "
     "따라서 결손은 두 층위다. 식 (1)의 기구적 결손(1차원)은 수집으로 채울 수 없고, 데이터 분포 결손은 목표 로봇 시연 수집 시 yaw 다양성을 "
     "의도적으로 포함하면 채울 수 있다. 소스에 'yaw 를 독립적으로 사용하는 조작' 사례가 원천적으로 없다는 점이 5축→6축 전이의 진짜 격차이며, "
     "이는 목표 로봇 시연이 무엇을 보완해야 하는지를 정확히 특정한다.")
figure(f"{FIG}/fig2_col.png",
       "Fig. 2  Coverage of the source data: (a) singular-value spectrum of the 6-D pose distribution; (b) occupied range vs. range of motion.")

h1("4. EE pose 재타겟팅 파이프라인과 비용")
h2("4.1 파이프라인")
para("소스 EE pose 시퀀스는 7점 이동평균으로 평활한 뒤 6 Hz 앵커를 추출하고, 작업대 배치 오프셋과 파지점 기준 TCP(0.0725 m) 보정, "
     "손목 45° 보정을 적용한 후 감쇠최소제곱(DLS) IK[16]로 M1013 관절값을 구한다. 감쇠계수는 잔차에 비례시켜 특이점 근방에서 관절속도 발산을 "
     "억제하고, 직전 프레임 해를 시드로 사용하며, 팔꿈치 위/아래 등 다른 분지(branch)로 점프한 해는 거부하고 섭동 후 재시도한다. "
     "앵커 사이는 선형 보간하여 30 Hz 로 복원하고, 관측 상태는 완전 추종을 가정해 state = action[t−1] 로 정의한다. "
     "TCP 를 보정하지 않으면 접근 틸트 44°에서 그리퍼 길이 0.12 m 가 수평 84 mm 오차로 나타나므로 보정은 필수다. "
     "손목 45° 보정은 그리퍼를 플랜지에 일자로 장착하는 결정에 해당하며, 손목 특이점 여유를 약 10°에서 50° 수준으로 끌어올린다.")
h2("4.2 작업대 배치")
para("두 로봇의 작업공간 스케일이 다르므로(OMX 리치 약 0.3 m, M1013 1.3 m) 작업대 위치를 별도로 정해야 한다. 54개 후보 오프셋에 대해 "
     "손목 특이점 여유 min|q₅|, joint3 리밋 여유, 프레임 간 최대 관절 변화 maxΔq 를 채점하여 5개로 압축한 뒤 기하 자기충돌 검사를 거쳐 "
     "OFFSET = (+0.05, −0.15, +0.10) m 를 확정하였다.")
h2("4.3 비용 지표")
para("EE pose 공통 표현은 관절공간 제어에는 없는 특이점 문제를 새로 떠안는다. 협동로봇은 사람과 공간을 공유하며 운용되므로[15] 특이점 "
     "근방의 관절속도 발산은 정확도가 아니라 안전 요건이다. 본 연구는 다음 다섯 지표로 재타겟팅 비용을 정의한다. "
     "(a) 특이점 여유 min|q₅|, (b) 프레임 간 최대 관절 변화 maxΔq, (c) 재타겟팅 결과의 FK 역검증 위치·각도 오차, (d) IK 실패 및 분지 점프 수, "
     "(e) 특이점 회피 후 사용 가능한 작업영역의 비율.")
h2("4.4 결과")
para("159 에피소드 전체가 실패와 분지 점프 없이 변환되었다(Table 2, Fig. 3). 최악 에피소드의 특이점 여유는 45.97°, 프레임 간 최대 관절 변화는 "
     "2.95°(30 Hz), FK 역검증 오차는 4.89 mm / 1.03° 이다. 역검증 오차는 6 Hz 앵커 보간에서 발생하는 값으로, 그리퍼 조 스트로크(32 mm)에 "
     "비해 충분히 작다. 변환 소요 시간은 5.7 s 이다. 지표 (e)는 manipulability 지수[17] 맵으로 로봇 도착 후 산출한다.")
table("Table 2  Retargeting cost over 159 episodes",
      ["지표", "정의", "결과"],
      [["(a) 특이점 여유", "min|q₅|", "45.97°"],
       ["(b) 관절 연속성", "max Δq / frame", "2.95°"],
       ["(c) 재타겟팅 정확도", "FK 역검증 위치 / 각도", "4.89 mm / 1.03°"],
       ["(d) 해 안정성", "IK 실패 / 분지 점프", "0 / 0"],
       ["(e) 작업영역 축소율", "사용 가능 영역 / 전체", "[도착 후]"]],
      [2.8, 3.0, 2.0])
figure(f"{FIG}/fig3_col.png",
       "Fig. 3  Per-episode distribution of the retargeting cost: (a) wrist-singularity margin, (b) joint continuity, (c) FK re-check error.")

h1("5. 관측공간 정합")
para("이종형상 전이에서 카메라 구도가 다르면 정책 실패의 원인을 구도 불일치와 시각 도메인 격차로 분리할 수 없다. 따라서 목표 리그의 카메라를 "
     "소스 관측 분포에 맞추는 것을 전이의 전제조건으로 둔다. 정면 카메라는 소스 리그의 동일 기종(U20CAM-720P)을 이관하여 사용한다.")
para("손목 카메라는 그리퍼 형상이 다르므로 소스 구도를 그대로 복제할 수 없다. 대신 '파지 정렬 구간(파지 2.0~0.7 s 전) 동안 큐브의 8개 꼭짓점이 "
     "모두 화면 안에 있을 것'을 판정 기준으로 두고, FK 만으로 큐브를 카메라에 투영하는 순수 기하 검증기로 제작 가능한 장착 위치를 전수 탐색하였다. "
     "렌즈 스탠드오프 미실측 오차 ±12 mm 를 포함한 여유(1.0 = 화면 가장자리)로 후보를 비교하여 플랜지 로컬 광심 (0, −65, −10) mm, 툴축 위 "
     "140 mm 지점 조준(틸트 21.8°), 보드 세로 장착을 확정하였다(여유 0.63). 화각은 센서 640×480 크롭(HFOV 63.4°)에서는 8 에피소드 중 2개에서 "
     "파지 직전 큐브가 이탈하여 불합격이었고, 1280×720 → 960×720 중앙 크롭(HFOV 85.6°)에서 8/8 통과하여 후자를 채택하였다. "
     "[최종 마운트 기준 재실행 수치로 갱신]")

h1("6. 시뮬레이션 검증")
para("재타겟팅 결과가 물리적으로 실행 가능한지 Isaac Sim 5.1 에서 검증하였다. M1013 USD 모델에 실물 그리퍼 기하(핑거 연장 38 mm, 조 간격 "
     "33.5~97.5 mm)를 부착하고 상판 높이 0.4624 m, 35 mm 큐브로 씬을 구성하였으며, PhysX 60 Hz position drive 로 30 Hz 관절 궤적을 재생하였다. "
     "에피소드 0, 50, 130 모두 큐브를 집어 운반·배치하는 데 성공하였고 배치 오차는 7.5, 1.6, 5.2 mm 였다(Table 3).")
para("정책 수준의 검증을 위해 159 에피소드를 무작위로 학습 139 / 검증 20 으로 나누어 ACT[12] 정책(100k steps, batch 8)을 학습하고, "
     "검증 에피소드에 대한 open-loop 관절 오차, 그리퍼 개폐 일치율, 출력 연속성을 학습 에피소드와 같은 잣대로 측정한다. "
     "정규화 통계는 데이터셋 전체 메타를 사용한다. [학습 완료 후 기입: held-out 관절오차 __°, 그리퍼 일치 __%, 정책 출력 Isaac 재생 __/__]")
table("Table 3  Physics replay in Isaac Sim",
      ["", "ep 0", "ep 50", "ep 130"],
      [["재타겟팅 궤적 재생 성공", "○", "○", "○"],
       ["배치 오차 [mm]", "7.5", "1.6", "5.2"],
       ["추종 오차 max [deg]", "1.85", "1.34", "3.14"],
       ["held-out 정책 출력 재생", "[ ]", "[ ]", "[ ]"]],
      [3.6, 1.4, 1.4, 1.4])

h1("7. 한계 및 향후 연구")
para("본 연구의 결과는 특이점 회피가 보장된 제한 작업영역 내의 값이며 전 작업공간에 대한 성능이 아니다. 이는 EE pose 공통 표현을 채택한 대가이고, "
     "본 논문은 '축 불일치를 해소하면 전이가 된다'가 아니라 '축 불일치를 EE pose 로 해소할 때 어떤 비용이 발생하며 그 비용이 얼마인가'까지를 주장한다. "
     "시뮬레이션의 접촉 물리(파지 시 미끄러짐·변형) 재현도는 실물보다 낮으며, 실물 로봇에서의 전이 성능은 아직 검증되지 않았다.")
para("향후 실물 M1013 에서 다음을 수행한다. (1) 목표 로봇 시연 수(10/30/60/120)에 대한 성공률 곡선을 scratch, 비전 인코더만 전이, 전체 전이의 세 조건으로 "
     "측정하여 'OMX 159 에피소드 = M1013 실물 시연 N개' 등가 지표를 도출한다. (2) yaw 가 필요한 과제군과 불필요한 과제군을 분리 평가하여 식 (1)의 "
     "결손이 성능에 미치는 비용을 결손 크기의 함수로 측정한다. (3) Isaac Sim 내 M1013 자체 시연(형상 같음·도메인 다름)과 OMX 실물 시연(형상 다름·도메인 같음)을 "
     "같은 평가군에서 비교하여 형상 격차와 도메인 격차를 분리한다.")

h1("8. 결 론")
para("5축 시연 데이터를 6축 협동로봇으로 옮길 때 축 개수 차이는 EE pose 표현으로 해소되며, 남는 격차는 소스 도달집합이 닫힌형 구속식 하나로 정의되는 "
     "SE(3)의 5차원 부분다양체라는 점임을 78,009 프레임 실데이터로 보였다. EE pose 공통 표현이 수반하는 IK 재타겟팅 비용을 5개 지표로 정의하고 "
     "159 에피소드 전체에서 특이점 여유 45.97°, 관절 연속성 2.95°/frame, 역검증 오차 4.89 mm 로 측정하였으며, 관측공간 정합 절차와 시뮬레이션 물리 재생으로 "
     "파이프라인의 실행 가능성을 확인하였다. 이 결과는 저가 시연 자산을 협동로봇에 재활용할 때 무엇이 진짜 격차이고 그 격차를 넘는 비용이 얼마인지를 "
     "정량적으로 제시한다.")

h1("참고문헌")
refs = [
    "Open X-Embodiment Collaboration, \"Open X-Embodiment: Robotic Learning Datasets and RT-X Models,\" Proc. IEEE ICRA, 2024.",
    "Octo Model Team, \"Octo: An Open-Source Generalist Robot Policy,\" Proc. RSS, 2024.",
    "M. J. Kim et al., \"OpenVLA: An Open-Source Vision-Language-Action Model,\" Proc. CoRL, 2024.",
    "R. Doshi et al., \"Scaling Cross-Embodied Learning: One Policy for Manipulation, Navigation, Locomotion and Aviation,\" Proc. CoRL, 2024.",
    "L. Wang et al., \"Scaling Proprioceptive-Visual Learning with Heterogeneous Pre-trained Transformers,\" Proc. NeurIPS, 2024.",
    "[저자 확인], \"ZETA: A Controlled Study of Zero-Shot Cross-Embodiment VLA Transfer for Tabletop Manipulation,\" arXiv:2609.02546, 2026.",
    "[저자 확인], \"Data Analogies Enable Efficient Cross-Embodiment Transfer,\" arXiv:2603.06450, 2026.",
    "L. Y. Chen et al., \"RoVi-Aug: Robot and Viewpoint Augmentation for Cross-Embodiment Robot Learning,\" Proc. CoRL, 2024.",
    "L. Y. Chen et al., \"Mirage: Cross-Embodiment Zero-Shot Policy Transfer with Cross-Painting,\" Proc. RSS, 2024.",
    "[저자 확인], \"Cloak: Zero-Shot Cross-Embodiment Manipulation by Masking the End-Effector from the VLA,\" arXiv:2606.22836, 2026.",
    "M. Shukor et al., \"SmolVLA: A Vision-Language-Action Model for Affordable and Efficient Robotics,\" arXiv:2506.01844, 2025.",
    "T. Z. Zhao et al., \"Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware,\" Proc. RSS, 2023.",
    "[저자 확인], \"Embedding Morphology into Transformers for Cross-Robot Policy Learning,\" arXiv:2603.00182, 2026.",
    "[저자 확인], \"Unify Robot Actions in Camera Frame,\" arXiv:2511.17001, 2025.",
    "ISO/TS 15066:2016, Robots and robotic devices — Collaborative robots, ISO, 2016.",
    "Y. Nakamura and H. Hanafusa, \"Inverse Kinematic Solutions with Singularity Robustness for Robot Manipulator Control,\" ASME J. Dyn. Syst. Meas. Control, Vol. 108, No. 3, pp. 163-171, 1986.",
    "T. Yoshikawa, \"Manipulability of Robotic Mechanisms,\" Int. J. Robotics Research, Vol. 4, No. 2, pp. 3-9, 1985.",
]
for i, r in enumerate(refs, 1):
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(0.6); p.paragraph_format.first_line_indent = Cm(-0.6)
    p.paragraph_format.space_after = Pt(1)
    run(p, f"[{i}] {r}", 8.5)

doc.save(OUT)
print("saved:", OUT, os.path.getsize(OUT), "bytes")

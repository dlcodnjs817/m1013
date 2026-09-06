// ============================================================
//  어댑터 플레이트  DOOSAN M1013 플랜지 <-> SMC MHF2-16D2
//  AL6061-T6  140 x 70 x 12   약 295.9 g
//  좌표: 원점 = 플랜지 축, +X = 그리퍼 장축(=조 이동방향=핀 방향)
//        z=0 그리퍼측 면,  z=12 로봇측 면
//  출처: 두산 설치매뉴얼 v1.7 p.36 / SMC MHF2 카탈로그 5-96
// ============================================================
$fn = 128;

L=140; W=70; T=12; RC=8;         // 외형
SPG_D=31.5; SPG_H=4;             // 스피곳 (플랜지 Φ31.5 H7 에 삽입)
BORE=20;                         // 중앙 관통 (튜브·배선)
PCD=50; M6_D=6.6; CB_D=11; CB_H=7.5;
PIN_PILOT_D=5.8;                 // 핀홀 하도 4곳 (0/90/180/270°) — 드릴만, 리머는 현장
M5_D=5.5; M5_X=54;
DW_D=4;   DW_X=65.0;  DW_H=6;    // 다월 압입 (Φ4x8 핀 → 2mm 돌출. 위치 ±65.0 = SMC 6면도 도형 실측)

module plate() {
  hull() for (sx=[1,-1], sy=[1,-1])
    translate([sx*(L/2-RC), sy*(W/2-RC), 0]) cylinder(h=T, r=RC);
}

difference() {
  union() {
    plate();
    translate([0,0,T]) cylinder(h=SPG_H, d=SPG_D);        // 스피곳
  }
  translate([0,0,-1]) cylinder(h=T+SPG_H+2, d=BORE);      // 중앙 관통

  // 로봇 체결 M6 : 관통 + 그리퍼측 카운터보어
  for (a=[45,135,225,315]) rotate([0,0,a]) translate([PCD/2,0,0]) {
    translate([0,0,-1])  cylinder(h=T+2,  d=M6_D);
    translate([0,0,-0.01]) cylinder(h=CB_H, d=CB_D);
  }
  // 핀홀 하도 (관통) — 클로킹 확정 후 1곳만 Φ6 H7 리머
  for (a=[0,90,180,270]) rotate([0,0,a]) translate([PCD/2,0,-1]) cylinder(h=T+2, d=PIN_PILOT_D);
  // 그리퍼 체결 M5 (관통)
  for (sx=[1,-1]) translate([sx*M5_X,0,-1]) cylinder(h=T+2, d=M5_D);
  // 다월 압입홀 (그리퍼측에서 DW_H 깊이)
  for (sx=[1,-1]) translate([sx*DW_X,0,-0.01]) cylinder(h=DW_H, d=DW_D);
}

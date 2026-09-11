#!/usr/bin/env python3
"""2026-09-11 오후 세션(학습 2개 설명 · 전원 차단 대비) 대화를 마크다운으로 추출.

  python3 export_project_md_0911.py
  → ~/m1013/대화록 및 PPT/20260911_학습설명_전원차단대비.md
"""

import glob
import json
import os

PROJ = os.path.expanduser("~/.claude/projects/-home-kim-tx90")
OUT = os.path.expanduser("~/m1013/대화록 및 PPT/20260911_학습설명_전원차단대비.md")

SINCE = "2026-09-10T15:00"     # KST 2026-09-11 00:00 (UTC 기준)
MAX_RESULT = 2500
MAX_INPUT = 1200

# (세션 id 앞 8자, 제목) — 시작 시각 순
SESSIONS = [
    ("298fa89c", "동시 학습 2개(검증셋 분리 · Isaac v8) 설명 · 진행 상황 · "
                 "18:00 전원 차단 대비(자동 정리 + 월요일 재개 스크립트)"),
]

SKIP_CONTAINS = [
    "채팅방 내용 md",            # 이 추출 요청 자체
]
SKIP_EXACT = {"아", "+", ""}

MARKERS = ("[Request interrupted", "<local-command-caveat", "<command-name>",
           "<system-reminder>", "<ide_opened_file", "[Image:",
           "<local-command-stdout", "<task-notification",
           "Approach this as the design lead")


def blocks(content):
    if isinstance(content, str):
        return [("text", content)]
    if not isinstance(content, list):
        return []
    out = []
    for b in content:
        if isinstance(b, dict):
            t = b.get("type")
            if t == "text":
                out.append(("text", b.get("text", "")))
            elif t == "tool_use":
                out.append(("tool_use", b))
            elif t == "tool_result":
                out.append(("tool_result", b))
    return out


def flatten(payload):
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        parts = []
        for b in payload:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    parts.append(b.get("text", ""))
                elif b.get("type") == "image":
                    parts.append("[이미지]")
            elif isinstance(b, str):
                parts.append(b)
        return "\n".join(parts)
    return "" if payload is None else str(payload)


def clip(s, n):
    s = (s or "").rstrip()
    return s if len(s) <= n else s[:n] + f"\n… (이하 {len(s)-n:,}자 생략)"


def export_session(path, md):
    recs = []
    for line in open(path):
        line = line.strip()
        if line:
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    names = {}
    for r in recs:
        msg = r.get("message")
        if isinstance(msg, dict):
            for kind, b in blocks(msg.get("content")):
                if kind == "tool_use":
                    names[b.get("id")] = b.get("name", "?")

    keep = False
    n_user = n_asst = n_tool = n_skip = 0

    for r in recs:
        if r.get("timestamp", "") < SINCE:
            continue
        # 응답 도중 끼워 넣은 사용자 메시지(queued_command)는 별도 레코드로 남는다
        att = r.get("attachment")
        if isinstance(att, dict) and att.get("type") == "queued_command":
            txt = flatten(att.get("prompt")).strip()
            if txt:
                n_user += 1
                md += ["## 👤 사용자 (응답 도중 추가)", "", txt, ""]
            continue
        if r.get("type") not in ("user", "assistant"):
            continue
        msg = r.get("message")
        if not isinstance(msg, dict):
            continue

        for kind, b in blocks(msg.get("content")):
            if kind == "text":
                txt = (b or "").strip()
                if not txt:
                    continue
                if r["type"] == "user":
                    if any(txt.startswith(m) or m in txt[:120] for m in MARKERS):
                        continue
                    if txt in SKIP_EXACT or any(p in txt for p in SKIP_CONTAINS):
                        keep = False
                        n_skip += 1
                        continue
                    keep = True
                    n_user += 1
                    md += ["## 👤 사용자", "", txt, ""]
                elif keep:
                    n_asst += 1
                    md += ["## 🤖 Claude", "", txt, ""]

            elif kind == "tool_use" and keep:
                n_tool += 1
                inp = json.dumps(b.get("input", {}), ensure_ascii=False, indent=2)
                md += [f"**🔧 {b.get('name','?')}**", "",
                       "```json", clip(inp, MAX_INPUT), "```", ""]

            elif kind == "tool_result" and keep:
                nm = names.get(b.get("tool_use_id"), "결과")
                body = clip(flatten(b.get("content")), MAX_RESULT)
                if body.strip():
                    md += [f"<details><summary>▸ {nm} 출력</summary>", "",
                           "```", body, "```", "", "</details>", ""]

    return n_user, n_asst, n_tool, n_skip


def main():
    md = ["# M1013 — 학습 2개 설명 · 전원 차단 대비 대화록 (2026-09-11)", ""]
    md += ["9/11 오후 세션 하나의 기록입니다. "
           "도구 호출·출력은 접힌 상태로 포함.",
           "", "---", ""]

    tot = [0, 0, 0, 0]
    for sid, title in SESSIONS:
        hits = [p for p in glob.glob(os.path.join(PROJ, "*.jsonl")) if sid in p]
        if not hits:
            print(f"경고: 세션 {sid} 없음 — 건너뜀")
            continue
        md += [f"# ⏱ {title}", "", "---", ""]
        stats = export_session(hits[0], md)
        tot = [a + b for a, b in zip(tot, stats)]
        print(f"{sid}: 사용자 {stats[0]} · Claude {stats[1]} · 도구 {stats[2]}"
              f" | 제외 {stats[3]}")

    text = "\n".join(md)
    with open(OUT, "w") as f:
        f.write(text)
    print(f"\n저장: {OUT}")
    print(f"  {len(text):,}자 / {text.count(chr(10)):,}줄")
    print(f"  합계: 사용자 {tot[0]} · Claude {tot[1]} · 도구 {tot[2]}"
          f" | 제외 구간 {tot[3]}")


if __name__ == "__main__":
    main()

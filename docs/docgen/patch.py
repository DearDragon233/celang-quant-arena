"""把 body.part.js 拼入 generate.js 并替换标题/配色/封面配置。"""
import re

src = open("generate.js", encoding="utf-8").read()
body = open("body.part.js", encoding="utf-8").read()

# 1) 配色 DM-1 → IG-1（金融墨金）
src = src.replace("调色板 DM-1 Deep Cyan（科技类报告）", "调色板 IG-1 Ink Gold（金融类报告）")
src = src.replace('bg: "162235", accent: "37DCF2",', 'bg: "1A1A1A", accent: "C9A84C",')
src = src.replace(
    'headerBg: "1B6B7A", headerText: "FFFFFF", accentLine: "1B6B7A", innerLine: "C8DDE2", surface: "EDF3F5"',
    'headerBg: "C9A84C", headerText: "1A1A1A", accentLine: "C9A84C", innerLine: "DDD5C0", surface: "F5F2E8"',
)
src = src.replace('primary: "0A1628", secondary: "6878A0",', 'primary: "1A1A1A", secondary: "8A7B55",')

# 2) 系统名称与标题
src = src.replace("教务选课管理系统", "模拟炒股与量化回测系统")

# 3) 替换正文
start = src.index("// ---------- 正文内容 ----------")
end = src.index("// ---------- 组装文档 ----------")
src = src[:start] + body + src[end:]

# 4) 封面配置
src = src.replace('subtitle: "Vue 3 + Element Plus + FastAPI + SQLite 前后端分离实践",',
                  'subtitle: "Vue 3 + Element Plus + FastAPI + SQLite 的模拟盘与量化回测实践",')
src = src.replace('englishLabel: "ACADEMIC REGISTRATION SYSTEM",',
                  'englishLabel: "QUANT PAPER TRADING PLATFORM",')
src = src.replace('"系统类型：管理信息系统（教务选课，双端 + 抢课机制）",',
                  '"系统类型：管理信息系统（模拟炒股 + 自配量化回测，双端）",')
src = src.replace('footerLeft: "EDU-REGISTRATION SYSTEM",', 'footerLeft: "QUANT PAPER TRADING SYSTEM",')

open("generate.js", "w", encoding="utf-8").write(src)
print("patched, length:", len(src))

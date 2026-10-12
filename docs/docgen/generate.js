/* 模拟炒股与量化回测系统开发文档生成脚本（docx-js） */
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, PageBreak, Header, Footer, PageNumber, NumberFormat, SectionType,
  AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType,
  TableOfContents, TableLayoutType,
} = require("docx");
const fs = require("fs");
const path = require("path");

// ---------- 调色板 IG-1 Ink Gold（金融类报告） ----------
const P = {
  bg: "1A1A1A", accent: "C9A84C",
  cover: { titleColor: "FFFFFF", subtitleColor: "B0B8C0", metaColor: "90989F", footerColor: "687078" },
  table: { headerBg: "C9A84C", headerText: "1A1A1A", accentLine: "C9A84C", innerLine: "DDD5C0", surface: "F5F2E8" },
  primary: "1A1A1A", secondary: "8A7B55",
};

const NB = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: NB, bottom: NB, left: NB, right: NB };
const allNoBorders = { top: NB, bottom: NB, left: NB, right: NB, insideHorizontal: NB, insideVertical: NB };

// ---------- 封面标题布局辅助（技能标准实现） ----------
function splitTitleLines(title, charsPerLine) {
  if (title.length <= charsPerLine) return [title];
  const breakAfter = new Set([..."，。、；：！？", ..."的与和及之在于为", ..."-_—–·/", ..." \t"]);
  const lines = [];
  let remaining = title;
  while (remaining.length > charsPerLine) {
    let breakAt = -1;
    for (let i = charsPerLine; i >= Math.floor(charsPerLine * 0.6); i--) {
      if (i < remaining.length && breakAfter.has(remaining[i - 1])) { breakAt = i; break; }
    }
    if (breakAt === -1) {
      const limit = Math.min(remaining.length, Math.ceil(charsPerLine * 1.3));
      for (let i = charsPerLine + 1; i < limit; i++) {
        if (breakAfter.has(remaining[i - 1])) { breakAt = i; break; }
      }
    }
    if (breakAt === -1) {
      breakAt = charsPerLine;
      const prevChar = remaining[breakAt - 1], nextChar = remaining[breakAt];
      if (prevChar && nextChar && !breakAfter.has(prevChar) && !breakAfter.has(nextChar) &&
          /[\u4e00-\u9fff]/.test(prevChar) && /[\u4e00-\u9fff]/.test(nextChar)) breakAt -= 1;
    }
    lines.push(remaining.slice(0, breakAt).trim());
    remaining = remaining.slice(breakAt).trim();
  }
  if (remaining) lines.push(remaining);
  if (lines.length > 1 && lines[lines.length - 1].length <= 2) {
    const last = lines.pop();
    lines[lines.length - 1] += last;
  }
  return lines;
}

function calcTitleLayout(title, maxWidthTwips, preferredPt = 40, minPt = 24) {
  const charsPerLine = (pt) => Math.floor(maxWidthTwips / (pt * 20));
  let titlePt = preferredPt, lines;
  while (titlePt >= minPt) {
    const cpl = charsPerLine(titlePt);
    if (cpl < 2) { titlePt -= 2; continue; }
    lines = splitTitleLines(title, cpl);
    if (lines.length <= 3) break;
    titlePt -= 2;
  }
  if (!lines || lines.length > 3) {
    lines = splitTitleLines(title, charsPerLine(minPt));
    titlePt = minPt;
  }
  return { titlePt, titleLines: lines };
}

function calcCoverSpacing(params) {
  const { titleLineCount = 1, titlePt = 36, hasSubtitle = false, hasEnglishLabel = false,
    metaLineCount = 0, fixedHeight = 800, pageHeight = 16838, marginTop = 0, marginBottom = 0 } = params;
  const SAFETY = 1200;
  const usableHeight = pageHeight - marginTop - marginBottom - SAFETY;
  const titleHeight = titleLineCount * (titlePt * 23 + 200);
  const subtitleHeight = hasSubtitle ? (12 * 23 + 600) : 0;
  const englishLabelHeight = hasEnglishLabel ? (9 * 23 + 600) : 0;
  const metaHeight = metaLineCount * (10 * 23 + 100);
  const implicitParaHeight = 3 * 300;
  const contentHeight = titleHeight + subtitleHeight + englishLabelHeight + metaHeight + fixedHeight + implicitParaHeight;
  const safeRemaining = Math.max(usableHeight - contentHeight, 400);
  const FOOTER_MIN = 800;
  const rawTop = Math.floor(safeRemaining * 0.45);
  const rawBottom = Math.floor(safeRemaining * 0.45);
  const bottomSpacing = Math.max(rawBottom, FOOTER_MIN);
  const topSpacing = Math.max(rawTop - Math.max(0, FOOTER_MIN - rawBottom), 400);
  return { topSpacing, midSpacing: Math.max(safeRemaining - topSpacing - bottomSpacing, 0), bottomSpacing };
}

// ---------- 封面 R1（左对齐纯段落） ----------
function buildCoverR1(config) {
  const padL = 1200, padR = 800;
  const availableWidth = 11906 - padL - padR - 300;
  const { titlePt, titleLines } = calcTitleLayout(config.title, availableWidth, 40, 24);
  const titleSize = titlePt * 2;
  const spacing = calcCoverSpacing({
    titleLineCount: titleLines.length, titlePt,
    hasSubtitle: !!config.subtitle, hasEnglishLabel: !!config.englishLabel,
    metaLineCount: (config.metaLines || []).length, fixedHeight: 400,
  });
  const accentLeft = { style: BorderStyle.SINGLE, size: 8, color: P.accent, space: 12 };
  const children = [];
  children.push(new Paragraph({ spacing: { before: spacing.topSpacing } }));
  if (config.englishLabel) {
    children.push(new Paragraph({
      indent: { left: padL, right: padR }, spacing: { after: 500 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: P.accent, space: 8 } },
      children: [new TextRun({ text: config.englishLabel.split("").join("  "), size: 18, color: P.accent,
        font: { ascii: "Calibri", eastAsia: "SimHei" }, characterSpacing: 40 })],
    }));
  }
  for (let i = 0; i < titleLines.length; i++) {
    children.push(new Paragraph({
      indent: { left: padL },
      spacing: { after: i < titleLines.length - 1 ? 100 : 300, line: Math.ceil(titlePt * 23), lineRule: "atLeast" },
      children: [new TextRun({ text: titleLines[i], size: titleSize, bold: true,
        color: P.cover.titleColor, font: { eastAsia: "SimHei", ascii: "Arial" } })],
    }));
  }
  if (config.subtitle) {
    children.push(new Paragraph({
      indent: { left: padL }, spacing: { after: 800 },
      children: [new TextRun({ text: config.subtitle, size: 24, color: P.cover.subtitleColor,
        font: { eastAsia: "Microsoft YaHei", ascii: "Arial" } })],
    }));
  }
  for (const line of (config.metaLines || [])) {
    children.push(new Paragraph({
      indent: { left: padL + 200 }, spacing: { after: 80 },
      border: { left: accentLeft },
      children: [new TextRun({ text: line, size: 24, color: P.cover.metaColor,
        font: { eastAsia: "Microsoft YaHei", ascii: "Arial" } })],
    }));
  }
  children.push(new Paragraph({ spacing: { before: spacing.bottomSpacing } }));
  children.push(new Paragraph({
    indent: { left: padL, right: padR },
    border: { top: { style: BorderStyle.SINGLE, size: 2, color: P.accent, space: 8 } },
    spacing: { before: 200 },
    children: [
      new TextRun({ text: config.footerLeft || "", size: 16, color: P.cover.footerColor, font: { ascii: "Arial", eastAsia: "Microsoft YaHei" } }),
      new TextRun({ text: "                                        " }),
      new TextRun({ text: config.footerRight || "", size: 16, color: P.cover.footerColor, font: { ascii: "Arial", eastAsia: "Microsoft YaHei" } }),
    ],
  }));
  return [new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    borders: allNoBorders,
    rows: [new TableRow({
      height: { value: 16838, rule: "exact" },
      children: [new TableCell({
        shading: { type: ShadingType.CLEAR, fill: P.bg }, borders: noBorders, verticalAlign: "top",
        children,
      })],
    })],
  })];
}

// ---------- 正文构件 ----------
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160, line: 312 },
    children: [new TextRun({ text, bold: true, size: 32, color: P.primary, font: { ascii: "Calibri", eastAsia: "SimHei" } })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120, line: 312 },
    children: [new TextRun({ text, bold: true, size: 28, color: P.primary, font: { ascii: "Calibri", eastAsia: "SimHei" } })],
  });
}
function body(text, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: 420 },
    spacing: { line: 312, after: opts.after ?? 0 },
    children: [new TextRun({ text, size: 24, color: "000000", font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
  });
}
function codeLine(text) {
  return new Paragraph({
    spacing: { line: 280 },
    indent: { left: 600 },
    shading: { type: ShadingType.CLEAR, fill: "F4F7F8" },
    children: [new TextRun({ text, size: 19, color: "1B4B5A", font: { ascii: "Consolas", eastAsia: "Microsoft YaHei" } })],
  });
}
function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 80, after: 240 },
    children: [new TextRun({ text, size: 18, color: P.secondary, font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
  });
}
function tableTitle(text) {
  return new Paragraph({
    keepNext: true, spacing: { before: 160, after: 80 },
    children: [new TextRun({ text, bold: true, size: 21, color: P.primary, font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
  });
}
function figure(imgPath, captionText, widthPx = 560) {
  const buf = fs.readFileSync(imgPath);
  const height = Math.round(widthPx * 900 / 1440);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 120 },
      children: [new ImageRun({ data: buf, transformation: { width: widthPx, height }, type: "png" })],
    }),
    caption(captionText),
  ];
}
function cell(text, opts = {}) {
  return new TableCell({
    children: [new Paragraph({
      spacing: { line: 276 },
      children: [new TextRun({
        text: String(text), size: 20, bold: !!opts.bold,
        color: opts.color || "000000",
        font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" },
      })],
    })],
    shading: opts.fill ? { type: ShadingType.CLEAR, fill: opts.fill } : undefined,
    margins: { top: 60, bottom: 60, left: 120, right: 120 },
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
    verticalAlign: "center",
  });
}
function makeTable(headers, rows, widths) {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: P.table.accentLine },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: P.table.accentLine },
      left: NB, right: NB,
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: P.table.innerLine },
      insideVertical: NB,
    },
    rows: [
      new TableRow({
        tableHeader: true, cantSplit: true,
        children: headers.map((t, i) => cell(t, { bold: true, color: P.table.headerText, fill: P.table.headerBg, width: widths?.[i] })),
      }),
      ...rows.map((r, ri) => new TableRow({
        cantSplit: true,
        children: r.map((t, i) => cell(t, { width: widths?.[i], fill: ri % 2 === 1 ? P.table.surface : undefined })),
      })),
    ],
  });
}

const IMG = (name) => path.join(__dirname, "..", "img", name);
const pgSize = { width: 11906, height: 16838 };
const pgMargin = { top: 1440, bottom: 1440, left: 1701, right: 1417 };

function pageNumFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" })],
    })],
  });
}
function docHeader() {
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "D8E0E8", space: 4 } },
      children: [new TextRun({ text: "策澜量化竞技场 · 模拟炒股与量化回测系统开发文档", size: 18, color: "98A2AE",
        font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
    })],
  });
}

// ---------- 正文内容 ----------
const bodyChildren = [];

bodyChildren.push(h1("一、项目概述"));
bodyChildren.push(h2("1.1 项目背景"));
bodyChildren.push(body("本系统名为「策澜量化竞技场」，面向大学生模拟炒股大赛场景设计。参赛选手以 100 万元虚拟资金在真实市场行情下进行模拟交易，系统按实时价格撮合并实时排名；同时平台引入两组特色能力：NPC 竞技场让八位风格迥异的传奇交易者机器人在真实行情上自动对战，形成赛博斗蛐蛐式的观摩与对比体验；财经快讯自动追踪昨日收盘以来的全部市场消息并进行利好/利空情绪分析；平台采用『年度常驻账户 + 管理员发布限时比赛』的双层账户体系，选手既有一年场长期成绩，也可报名进入特定时期的模拟盘比赛。区别于传统模拟盘逐笔人工下单的模式，本系统的核心创新是内置「策略决策树」顾问：由系统对全部标的持续计算技术信号，自动生成 长期操作、短期操作、交易技巧 三大分支的决策建议（含建议仓位、参考入场价、止损纪律、止盈目标与信号依据），选手只需在决策树中选择符合自己风格的策略并一键执行，实现从『人工盯盘下单』到『策略驱动交易』的转变。"));
bodyChildren.push(h2("1.2 系统目标"));
bodyChildren.push(body("系统目标包括：一是接入真实行情数据源，覆盖 A 股与美股两个市场的实时报价与历史日K，数据获取具备主备双源与自动降级能力；二是提供专业的行情浏览与模拟交易体验，包括K线蜡烛图、均线系统、双市场交易规则（A股整手与美股按股）、手续费模型与资产曲线；三是构建策略决策树顾问，将双均线、MACD、RSI、布林带、海龟突破、动量趋势等量化信号融合为环境判定与可执行决策卡；四是提供量化回测引擎，六种策略均可对任一标的的历史区间回测并输出年化、回撤、夏普等专业指标；五是提供大赛运营能力，包括实时排行榜、赛程设置与全局成交监管；六是提供 NPC 竞技场与财经快讯（含利好利空情绪分析）两大特色模块；七是提供多账户比赛体系，年度场长跑与限时赛并存，比赛资金独立核算；八是全链路性能优化，保证行情页面秒级打开。"));
bodyChildren.push(h2("1.3 用户角色"));
bodyChildren.push(makeTable(
  ["角色", "使用端", "主要功能"],
  [
    ["参赛选手", "用户端", "行情中心（A股+美股K线）、模拟交易、策略决策树（长线/短线/技巧建议与一键执行）、量化回测、资产总览、大赛排行"],
    ["大赛组委会", "管理端", "运营看板、选手管理、股票池停复牌、全局成交监管、赛程设置"],
  ],
  [14, 12, 74]
));

bodyChildren.push(h1("二、技术选型"));
bodyChildren.push(h2("2.1 选型总览"));
bodyChildren.push(makeTable(
  ["层次", "技术", "说明"],
  [
    ["前端", "Vue 3 + Vite + Element Plus(dark) + ECharts", "暗色交易终端风格，K线蜡烛图与净值曲线"],
    ["后端", "FastAPI (Python) + SQLAlchemy 2.0", "五层路由：认证/行情/交易/量化/管理 + 决策树/大赛"],
    ["数据库", "SQLite（WAL 模式）", "日K缓存、持仓、成交、策略、回测存档与赛程设置"],
    ["行情主源", "东方财富公开行情接口", "A股与美股实时报价（批量、8秒缓存）与日K数据"],
    ["行情备源", "腾讯行情接口", "主源连接被拒时自动重试并切换，美股自动匹配交易所后缀"],
    ["认证", "JWT (PyJWT) + PBKDF2 密码哈希", "前后端双重角色隔离"],
    ["回测引擎", "自研逐日撮合引擎", "六种经典策略，防未来函数设计，策略来源均已标注"],
  ],
  [14, 30, 56]
));
bodyChildren.push(h2("2.2 选型理由"));
bodyChildren.push(body("行情数据全部来自真实数据源：主源为东方财富公开行情接口（同时覆盖A股与美股的实时报价和前复权日K），实测发现其存在间歇性断连，因此实现三次重试退避，并在K线拉取失败时自动切换到腾讯行情接口（美股标的自动尝试 .OQ 纳斯达克 / .N 纽交所后缀），实时报价亦有腾讯备用解析。日K数据落库缓存，回测与决策树优先读缓存，仅在缓存缺失或落后于数据源时增量补拉，既保证离线演示能力又控制对数据源的请求频率。界面采用暗色交易终端风格并启用 Element Plus 暗色变量，配合红涨绿跌语义色，贴近专业行情软件的使用习惯。"));

bodyChildren.push(h1("三、系统架构设计"));
bodyChildren.push(h2("3.1 总体架构"));
bodyChildren.push(body("前后端分离单体架构。前端 Vue 3 单页应用按角色划分管理端与用户端；后端按 auth、market、trade、quant、admin 五组业务路由加 advisor（策略决策树）、competition（大赛）两个特色路由组织，数据访问层新增独立的 datasource 模块统一封装行情主备源的请求、重试、解析与缓存。日K数据以（股票，日期）建立联合索引存储于 daily_bars 表，作为回测与决策树的本地数据底座。"));
bodyChildren.push(h2("3.2 工程目录结构"));
bodyChildren.push(codeLine("quant-system/"));
bodyChildren.push(codeLine("├── backend/app/"));
bodyChildren.push(codeLine("│   ├── datasource.py    # 行情主备源：EM + 腾讯，重试/缓存/降级"));
bodyChildren.push(codeLine("│   ├── engine.py        # 指标库 + 六策略信号 + 回测引擎"));
bodyChildren.push(codeLine("│   ├── security.py      # JWT / PBKDF2 / RBAC 依赖"));
bodyChildren.push(codeLine("│   └── routers/"));
bodyChildren.push(codeLine("│       ├── market.py    # 实时行情 + 日K（缓存增量刷新）"));
bodyChildren.push(codeLine("│       ├── trade.py     # 模拟交易（双市场规则/费用模型）"));
bodyChildren.push(codeLine("│       ├── advisor.py   # 策略决策树（信号事实→评分→三分支）"));
bodyChildren.push(codeLine("│       ├── quant.py     # 策略配置与回测"));
bodyChildren.push(codeLine("│       ├── competition.py # 排行榜（批量实时估值）"));
bodyChildren.push(codeLine("│       └── admin.py     # 看板/用户/股票池/成交/赛程设置"));
bodyChildren.push(codeLine("└── frontend/src/views/  # portal 六页 + admin 五页"));

bodyChildren.push(h1("四、数据库设计"));
bodyChildren.push(body("共 8 张表：users（含学校字段）、stocks（含 market 与 em_secid 数据源标识）、daily_bars（真实日K缓存）、positions、orders、strategies、backtest_runs 与 settings（大赛键值设置）。持仓以（用户，股票）唯一约束；回测指标、净值曲线与买卖点以 JSON 序列化存档便于复看。"));
bodyChildren.push(tableTitle("表 1 标的与行情"));
bodyChildren.push(makeTable(
  ["表", "关键字段", "说明"],
  [
    ["stocks", "symbol / market(CN/US) / em_secid / is_active", "股票池，em_secid 为数据源标识（如 1.600519、105.AAPL）"],
    ["daily_bars", "stock_id / date / OHLC / volume / amount", "真实日K缓存，(stock_id, date) 联合索引"],
  ],
  [18, 44, 38]
));
bodyChildren.push(tableTitle("表 2 交易与量化"));
bodyChildren.push(makeTable(
  ["表", "关键字段", "说明"],
  [
    ["positions", "user_id + stock_id 唯一 / qty / avg_cost", "摊薄成本持仓"],
    ["orders", "side / price(实时价) / qty / amount / fee", "成交流水，费用单列"],
    ["strategies", "kind / params(JSON) / 区间 / initial_cash", "六种策略的参数化配置"],
    ["backtest_runs", "metrics / equity / trades (JSON)", "回测结果存档，可随时复看"],
    ["settings", "key / value", "大赛名称、赛季、起止日期"],
  ],
  [18, 44, 38]
));

bodyChildren.push(h1("五、功能模块设计"));
bodyChildren.push(h2("5.1 用户端（参赛选手）"));
bodyChildren.push(makeTable(
  ["模块", "功能点"],
  [
    ["行情中心", "24 只真实标的（A股16 + 美股8）实时涨跌排序、市场标签、K线抽屉：蜡烛图 + MA5/10/20 + 成交量 + 缩放平移，60/120/250 日切换，缓存落后自动增量补拉"],
    ["模拟交易", "双市场规则（A股整手/美股按股）、实时价成交、费用模型（万三佣金最低5元 + 卖出印花税）、全仓/清仓、持仓浮动盈亏、决策树带标的直达"],
    ["场内分析", "四大指数实时卡（上证/深成/创业板/沪深300）、池内涨跌家数与上涨占比、实时涨幅榜/跌幅榜、距 60 日高点强度榜（临近新高/中位/深度回调）、快讯情绪联动，15 秒自动刷新"],
    ["持仓分析", "账户汇总（总资产/累计盈亏/当日盈亏/第一大重仓占比）、持仓分布饼图、持仓明细逐票附决策树评级与今日涨跌，支持比赛账户切换，15 秒刷新"],
    ["收益分析", "资产曲线 vs 沪深300 基准、每日收益红绿柱、回撤序列、月度收益表与单日极值统计，支持比赛账户切换"],
    ["策略决策树", "大盘环境判定（沪深300/纳指QQQ 的 MA20/MA60 状态与20日涨跌）、全标的信号雷达（评分/评级/RSI/动量）、三分支决策卡：长期操作（分批建仓+趋势持有）、短期操作（金叉买入/超卖低吸/逢高兑现）、交易技巧（ATR自适应网格 + 仓位止损纪律）；每张决策卡含建议仓位、参考入场、止损止盈、信号依据与置信度，支持一键去执行"],
    ["量化回测", "六种策略（来源标注）参数化回测、指标报告（总收益/年化/最大回撤/夏普/胜率）、策略净值 vs 买入持有基准、K线买卖点标注、策略与回测历史管理"],
    ["资产总览", "总资产/可用/市值/浮盈卡片、以 100 万为基准线的资产走势（逐日重放 + 实时终值）、最近成交"],
    ["大赛排行", "比赛窗口（进行中比赛卡片、一键报名、我的比赛收益）+ 年度场/单场比赛排行切换（金银铜牌、收益率条、我的高亮）"],
    ["NPC竞技场", "八位职业风格各异的机器人交易者（退休老股民/私募经理/游资敢死队/量化研究员/华尔街交易员/定投学生/海龟传人/技术博主）基于真实行情按各自策略自动对战，卡片展示净值曲线、最新操作与决策理由，可查看完整操作流水，并提供我与最强 NPC 的成绩对比"],
    ["财经快讯", "自动追踪昨日收盘以来的全部市场消息：双源合并去重、A股/美股标签筛选、利好利空情绪分析（逐条标注 + 市场情绪温度计）、60 秒自动刷新"],
  ],
  [16, 84]
));
bodyChildren.push(h2("5.2 管理端（组委会）"));
bodyChildren.push(makeTable(
  ["模块", "功能点"],
  [
    ["运营看板", "选手/在市股票/成交笔数/总成交额统计、热门股票TOP8、最新成交动态"],
    ["用户管理", "学校与资产一览、重置密码、禁用启用"],
    ["股票池管理", "双市场标的实时价一览、停复牌、备注"],
    ["全局成交", "按选手/方向筛选的全市场成交流水"],
    ["赛程设置", "大赛名称、赛季、起止日期，实时同步用户端"],
    ["比赛发布", "创建限时模拟盘比赛（名称/说明/初始资金/起止时间），发布、下架与删除管理，实时统计报名人数"],
  ],
  [16, 84]
));

bodyChildren.push(h1("六、核心机制设计"));
bodyChildren.push(h2("6.1 真实行情接入与降级"));
bodyChildren.push(body("行情主源为东方财富公开行情接口：实时报价一次请求可批量携带全部标的 secid（A股 1./0. 前缀、美股 105/106/107 前缀），服务端保留 8 秒缓存以控制频率；日K为前复权数据。实测主源存在间歇性断连（连接被远端直接关闭），故请求层实现三次指数退避重试；仍失败时K线自动切换腾讯行情接口（美股自动尝试 .OQ / .N 交易所后缀），实时报价切换腾讯 qt.gtimg.cn 批量接口并按 GBK 解析。日K落库后本地缓存，行情中心仅在缓存最后日期落后于数据源时增量补拉，保证断网环境下历史数据仍可离线回测。"));
bodyChildren.push(h2("6.2 策略决策树顾问（系统核心创新）"));
bodyChildren.push(body("决策树顾问将『看盘—分析—决策』的完整链路自动化，分三步生成：第一步信号事实采集，对每只标的计算均线状态（多头/空头/纠缠）、RSI、MACD 柱与金叉死叉、布林位置、量比、20日动量、60日高低点距离与 ATR；第二步评分与评级，按信号加权得到 0-100 分并映射为 强势可做多 / 回调低吸 / 持有观察 / 回避减仓 四档；第三步结合大盘环境（沪深300 与纳指 QQQ 的 MA20/MA60 相对位置）构建决策树，分为长期操作（评分达标标的的分批建仓卡：首笔 20% 仓位、回踩 MA10 加仓、2倍ATR 止损、60日高点止盈参照）、短期操作（金叉买入、超卖低吸、超买兑现三类信号卡：轻仓试错、-5% 纪律止损、+10%~15% 目标）与交易技巧（基于 ATR 的自适应网格方案、仓位与止损纪律）三大分支。每张决策卡都附带触发信号依据与置信度评分，选手点击「去执行」直接携带标的跳转交易面板完成下单，实现『系统给策略、选手做选择、一键落地』的闭环。"));
bodyChildren.push(h2("6.3 模拟交易与双市场规则"));
bodyChildren.push(body("成交价取实时行情（数据源异常时回退最近日线收盘并提示）。A股按 100 股整手交易，美股按 1 股起交易；费用模型为万三佣金最低 5 元，A股卖出额外收取 0.05% 印花税。持仓成本采用摊薄成本法，买入更新 avg_cost =（原成本 x 原数量 + 成交额）/ 新数量。资产曲线从初始资金 100 万逐日重放全部成交，持仓按最近交易日收盘价向前取齐估值，并在末端追加以实时价计算的当日点，保证曲线终点与顶栏总资产精确一致（实测 5 账户误差 ≤ 0.05 元）。"));
bodyChildren.push(h2("6.4 量化回测引擎与策略库"));
bodyChildren.push(body("回测引擎采用「当日收盘确认信号、次日开盘成交」的防未来函数设计。策略库共六种，均在界面标注来源：双均线交叉（Backtrader 社区经典）、MACD 趋势（Gerald Appel）、RSI 均值回复（Wilder）、布林带均值回复（John Bollinger）、海龟突破（海龟交易法则 / ABU 量化 AbuFactorBuyBreak：突破前 20 日高点入场、跌破前 10 日低点离场）、动量趋势（Qlib Alpha158 动量因子思路：20 日动量为正且站上 MA20 持有）。指标输出含总收益、年化（244 交易日）、最大回撤（峰谷法）、夏普比率（无风险 3%）、胜率等，并绘制策略净值与买入持有基准对比。"));
bodyChildren.push(h2("6.5 大赛排行榜与权限"));
bodyChildren.push(body("排行榜按总收益率（总资产/100 万 - 1）实时排序，总资产 = 可用资金 + 持仓实时市值，全部持仓的估值通过一次批量行情请求完成以控制数据源压力，实测 5 选手全量估值 3 秒内返回。JWT 认证下前后端双重角色隔离：选手与管理员的页面路由、接口权限互相隔离，越权访问返回 403。"));
bodyChildren.push(h2("6.6 NPC 竞技场引擎"));
bodyChildren.push(body("NPC 竞技场将量化策略人格化：八位 NPC 分别对应 退休老股民（布林带均值回复、低仓位）、私募基金经理（双均线趋势重仓）、游资打板敢死队（5 日动量快进快出、全仓梭哈）、量化研究员（MACD 多因子）、华尔街归国交易员（美股 20 日动量）、佛系定投大学生（每五日定投、破位避险）、海龟派传人（20/10 突破系统）、技术分析博主（RSI 超卖博弈），各自绑定不同真实标的。引擎复用回测的信号生成器逐日重放：信号在收盘确认、次日开盘按人物仓位比例成交，买卖自动生成带指标依据的人性化决策理由（如『5日动量 +1.7%，强势跟进』），并逐日记录净值曲线。重放具备幂等性：每当数据源出现新交易日，竞技场请求会自动触发重放更新战绩，实现『每个交易日收盘后自动更新』的对战体验。页面同时给出『我的成绩 vs 最强 NPC』对比，强化赛博斗蛐蛐的竞技氛围。"));
bodyChildren.push(h2("6.7 财经快讯双源聚合"));
bodyChildren.push(body("快讯模块并行抓取东方财富 7×24 财经商讯与新浪财经滚动新闻两个真实数据源，按标题指纹去重合并后按时间倒序输出，服务端保留 5 分钟缓存以控制请求频率。支持 since_close 参数：以昨日 15:00（A股收盘）为分界，精确回答『昨日收盘以来发生了什么』；前端按关键词自动为新闻打上 A股/美股 标签并支持分类筛选，60 秒自动刷新。"));
bodyChildren.push(body("在此之上内置关键词规则情绪分析引擎：内置利好词表（降准、降息、回购、增持、超预期、创新高等 20 词）与利空词表（减持、退市、制裁、立案、暴跌等 19 词）并分别加权，对每条快讯的标题与摘要打分，得到 利好/利空/中性 三档倾向、情绪分值与命中关键词，页面逐条彩色标注并汇总为『市场情绪温度计』（净情绪值 +3 以上判定偏暖、-3 以下判定偏冷）。规则引擎纯本地运行、毫秒级响应且不依赖大模型服务，适合课堂演示与离线场景。"));
bodyChildren.push(body("实时性保障机制：日K内存缓存由按天失效改为 60 秒 TTL，K线接口增量刷新时强制绕过内存缓存，确保盘中当日未完成K线及时进入本地库；决策树计算前对全部标做一轮增量行情刷新，使评分基于最新价格；行情中心与模拟交易页面前端 10~15 秒轮询，配合行情 stale-while-revalidate 策略，开盘时段的价格变动在数秒内即可反映到列表、持仓浮盈亏与当日盈亏。"));
bodyChildren.push(h2("6.8 多账户比赛体系"));
bodyChildren.push(body("账户分为两层：年度场为选手常驻账户（初始 100 万，长期有效，构成年度排行）；管理员可随时发布限时比赛（名称、说明、初始资金、起止时间），选手在比赛窗口一键报名后获得独立的比赛资金账户。持仓与成交表通过 contest_id 字段（0=年度场）实现账户级隔离，同一选手在年度场与各比赛中的资金、持仓、收益互不影响；交易接口在比赛账户下会校验报名状态与比赛时间窗口（未报名 403、窗口外 400）。排行榜相应分为年度场排行与单场比赛排行，均按总收益率实时排序，比赛结束后成绩封存。"));

bodyChildren.push(h1("七、接口设计"));
bodyChildren.push(makeTable(
  ["方法", "路径", "说明", "权限"],
  [
    ["POST", "/api/auth/login", "登录", "公开"],
    ["GET", "/api/market/stocks | /kline/{id}", "实时行情列表 / 真实日K（自动增量刷新）", "登录"],
    ["GET", "/api/advisor/tree", "决策树：大盘环境 + 信号雷达 + 三分支决策卡", "登录"],
    ["GET/POST", "/api/trade/account | /buy | /sell", "账户与资产曲线 / 实时价买卖", "选手"],
    ["GET/POST/DELETE", "/api/quant/strategies | /backtest", "策略配置与回测", "选手"],
    ["GET", "/api/competition/leaderboard | /info", "实时排行榜与赛程", "登录"],
    ["GET", "/api/npc/arena | /npc/{id}", "NPC 竞技场战绩与单人操作流水", "登录"],
    ["GET", "/api/analysis/market | /portfolio | /pnl", "场内分析 / 持仓分析（含决策树评级）/ 收益分析", "登录"],
    ["GET", "/api/contests/window", "比赛窗口（进行中比赛 + 我的报名状态）", "登录"],
    ["POST", "/api/contests/{id}/join", "报名比赛，获得独立资金账户", "登录"],
    ["GET", "/api/contests/{id}/leaderboard", "单场比赛实时排行", "登录"],
    ["GET/POST/PUT/DELETE", "/api/admin/contests", "比赛发布与管理", "管理员"],
    ["GET", "/api/news/list", "财经快讯（双源合并，支持昨日收盘过滤）", "登录"],
    ["GET/PUT", "/api/admin/users / stocks / orders / settings", "选手、股票池、成交与赛程管理", "管理员"],
    ["GET", "/api/admin/dashboard", "运营看板", "管理员"],
  ],
  [16, 34, 34, 16]
));

bodyChildren.push(h1("八、系统测试"));
bodyChildren.push(h2("8.1 真实数据与规则测试"));
bodyChildren.push(makeTable(
  ["测试项", "预期", "实测结果"],
  [
    ["A股实时行情", "与市场一致", "贵州茅台 1263.00（+0.57%）、平安银行 11.59（-1.61%）等 16 只实时返回"],
    ["美股实时行情", "与市场一致", "苹果 336.64（-1.11%）、特斯拉 382.70（+2.05%）、阿里 111.37（+5.36%）等 8 只"],
    ["真实日K", "前复权日线", "茅台 426 根、苹果 444 根（2025-01 至今），与交易所数据日期一致"],
    ["实时价买入美股", "按实时价成交", "苹果 10 股 @336.64 成交，费用 5 元，资金精确扣减"],
    ["东财接口断连", "自动重试并切换备源", "K线自动回落腾讯数据源（美股自动匹配 .OQ/.N），实时报价回落腾讯批量接口"],
    ["双均线回测（真实数据）", "指标合理", "贵州茅台区间 基准 -10.32%，海龟策略未触发（未破20日高）符合真实走势"],
    ["动量回测（苹果真实数据）", "指标合理", "17 笔交易、总收益 +17.95%、胜率 58.8%、回撤 11.93%"],
    ["资产曲线对账", "终点=实时总资产", "5 个账户全部一致（误差 ≤0.05 元）"],
    ["越权访问", "403", "选手访问管理接口、管理员访问交易接口均 403"],
    ["排行榜性能", "批量估值", "5 选手全量实时估值 3 秒内返回"],
    ["NPC 竞技场", "八人格自动对战", "8 位 NPC 全部基于真实行情重放：美股动量派 +10.21% 居首，游资快刀在宁德时代动量震荡中 -30.25%，行为与各自人设一致"],
    ["财经快讯", "双源合并与过滤", "昨日收盘以来 99 条（东财+新浪去重合并），A股/美股标签自动分类"],
    ["快讯情绪分析", "利好/利空判定", "99 条中利好 9、利空 6、中性 84，市场情绪判定偏暖，逐条命中词展示"],
    ["比赛多账户", "资金隔离", "比赛账户买入苹果 50 股后比赛总资产 999,994.95 与年度场 966,372.59 互不影响；未报名访问 403"],
    ["打开性能", "缓存生效", "决策树首次 3.3 秒 → 缓存命中 7 毫秒；行情启用 stale-while-revalidate 后页面打开不再阻塞；全接口 gzip 压缩"],
    ["盘中实时性", "当日数据及时可见", "交易日验证：持仓当日盈亏 +5,562 元实时跳动、K线出现当日未完成bar、场内分析指数与涨跌榜 15 秒刷新"],
  ],
  [26, 22, 52]
));

bodyChildren.push(h1("九、系统运行截图"));
bodyChildren.push(...figure(IMG("01-login.png"), "图 1 大赛登录页（暗色金融风）"));
bodyChildren.push(...figure(IMG("02-market.png"), "图 2 行情中心（A股+美股实时涨跌排序）"));
bodyChildren.push(...figure(IMG("03-advisor.png"), "图 3 策略决策树（大盘环境判定 + 信号雷达 + 可执行决策卡）"));
bodyChildren.push(...figure(IMG("04-trade.png"), "图 4 模拟交易（双市场规则 + 实时价下单）"));
bodyChildren.push(...figure(IMG("05-quant.png"), "图 5 量化回测（策略来源标注 + 专业指标报告）"));
bodyChildren.push(...figure(IMG("06-overview.png"), "图 6 资产总览（100万基准资产走势）"));
bodyChildren.push(...figure(IMG("07-ranking.png"), "图 7 大赛排行榜（实时收益率排名与赛程倒计时）"));
bodyChildren.push(...figure(IMG("08-dashboard.png"), "图 8 管理端运营看板"));
bodyChildren.push(...figure(IMG("09-settings.png"), "图 9 赛程设置"));
bodyChildren.push(...figure(IMG("10-npc.png"), "图 10 NPC 竞技场（八位风格交易者真实行情自动对战）"));
bodyChildren.push(...figure(IMG("11-news.png"), "图 11 财经快讯（昨日收盘以来双源合并）"));
bodyChildren.push(...figure(IMG("12-contest.png"), "图 12 比赛窗口与年度场排行"));
bodyChildren.push(...figure(IMG("13-contest-mgmt.png"), "图 13 管理端比赛发布"));
bodyChildren.push(...figure(IMG("14-pulse.png"), "图 14 场内分析（指数卡/市场宽度/实时涨跌榜/强度榜）"));
bodyChildren.push(...figure(IMG("15-holdings.png"), "图 15 持仓分析（分布饼图 + 决策树评级）"));
bodyChildren.push(...figure(IMG("16-pnl.png"), "图 16 收益分析（基准对比/日收益/月度收益）"));

bodyChildren.push(h1("十、部署与运行指南"));
bodyChildren.push(codeLine("# 1. 后端（需可访问东方财富/腾讯行情网络）"));
bodyChildren.push(codeLine("cd quant-system/backend"));
bodyChildren.push(codeLine("pip install -r requirements.txt"));
bodyChildren.push(codeLine("python seed.py                # 拉取真实行情并初始化大赛数据"));
bodyChildren.push(codeLine("python -m uvicorn app.main:app --port 8002"));
bodyChildren.push(codeLine(""));
bodyChildren.push(codeLine("# 2. 前端"));
bodyChildren.push(codeLine("cd quant-system/frontend && npm install && npm run build"));
bodyChildren.push(codeLine("浏览器打开 http://127.0.0.1:8002"));
bodyChildren.push(tableTitle("演示账号"));
bodyChildren.push(makeTable(
  ["角色", "账号", "密码", "说明"],
  [
    ["组委会", "admin", "admin123", "管理端与赛程设置"],
    ["参赛选手", "trader01 ~ trader05", "123456", "模拟资金 100 万，含真实行情下的演示持仓"],
  ],
  [14, 26, 14, 46]
));

bodyChildren.push(h1("十一、总结与展望"));
bodyChildren.push(body("本系统以大学生模拟炒股大赛为场景，完成了真实行情（A股+美股双市场、主备双数据源）、模拟交易、量化回测与大赛运营的完整闭环；核心创新「策略决策树」将多指标信号融合为环境判定与长线/短线/技巧三分支的可执行决策卡，把量化分析的结论直接转化为选手可一键落地的交易计划；NPC 竞技场把六种策略人格化为八个机器人交易者在真实行情上自动对战，为选手提供可观摩、可对比的活教材；财经快讯双源聚合则补齐了消息面这一环。开发中重点解决的工程问题包括：行情主源的间歇性断连与双源降级、日K缓存的增量刷新、双市场交易规则与费用模型、资产曲线与实时总资产的精确对账。"));
bodyChildren.push(body("后续可从四方面演进：一是接入交易所实时推送（WebSocket 行情）实现盘中秒级刷新；二是决策树引入机器学习模型（如 Qlib LightGBM 因子模型）提升信号质量，并支持选手自定义决策规则；三是增加赛前报名、赛中风控（仓位集中度预警）与赛后自动结算证书；四是将网格等技巧方案落地为服务端自动挂单引擎，实现真正的程序化模拟交易。", { after: 200 }));

// ---------- 组装文档 ----------
const doc = new Document({
  creator: "模拟炒股与量化回测系统项目组",
  title: "模拟炒股与量化回测系统开发文档",
  styles: {
    default: {
      document: {
        run: { font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" }, size: 24, color: "000000" },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: {
        run: { font: { ascii: "Calibri", eastAsia: "SimHei" }, size: 32, bold: true, color: P.primary },
        paragraph: { spacing: { before: 360, after: 160, line: 312 }, outlineLevel: 0 },
      },
      heading2: {
        run: { font: { ascii: "Calibri", eastAsia: "SimHei" }, size: 28, bold: true, color: P.primary },
        paragraph: { spacing: { before: 240, after: 120, line: 312 }, outlineLevel: 1 },
      },
    },
  },
  sections: [
    { // 第 1 节：封面（页边距 0，无页码）
      properties: { page: { size: pgSize, margin: { top: 0, bottom: 0, left: 0, right: 0 } } },
      children: buildCoverR1({
        title: "模拟炒股与量化回测系统开发文档",
        subtitle: "Vue 3 + Element Plus + FastAPI + SQLite 的模拟盘与量化回测实践",
        englishLabel: "QUANT PAPER TRADING PLATFORM",
        metaLines: [
          "课程名称：ClaudeCode 应用开发实战（1）管理信息系统",
          "作业名称：第一次作业 —— 模拟炒股与量化回测系统",
          "学号：2024333020403　　姓名：彭宇程",
          "开发方式：AI 辅助编码（ZCode）全程构建",
          "提交日期：2026 年 10 月 12 日",
        ],
        footerLeft: "QUANT PAPER TRADING SYSTEM",
        footerRight: "2026.10",
      }),
    },
    { // 第 2 节：目录（罗马页码）
      properties: {
        type: SectionType.NEXT_PAGE,
        page: { size: pgSize, margin: pgMargin, pageNumbers: { start: 1, formatType: NumberFormat.UPPER_ROMAN } },
      },
      footers: { default: pageNumFooter() },
      children: [
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { before: 480, after: 360 },
          children: [new TextRun({ text: "目  录", bold: true, size: 32, font: { eastAsia: "SimHei", ascii: "Calibri" } })],
        }),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
        new Paragraph({
          spacing: { before: 200 },
          children: [new TextRun({
            text: "注：本目录由域代码生成。如编辑文档后页码变动，请在目录上点击右键并选择「更新域」以刷新页码。",
            italics: true, size: 18, color: "888888", font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" },
          })],
        }),
        // 目录独立成节，下一节的分节符自动换页，无需再插入 PageBreak（避免空白页）
      ],
    },
    { // 第 3 节：正文（阿拉伯页码从 1 起）
      properties: {
        type: SectionType.NEXT_PAGE,
        page: { size: pgSize, margin: pgMargin, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } },
      },
      headers: { default: docHeader() },
      footers: { default: pageNumFooter() },
      children: bodyChildren,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(__dirname, "..", "模拟炒股与量化回测系统开发文档.docx");
  fs.writeFileSync(out, buf);
  console.log("written:", out);
});

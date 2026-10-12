"""文档 v4 补丁（行列表构造，避免引号嵌套问题）。"""
lines = open('body.part.js', encoding='utf-8').read().split('\n')
out = []
i = 0
n = len(lines)


def emit(s):
    out.append(s)


def find(prefix):
    for idx, l in enumerate(lines):
        if l.startswith(prefix):
            return idx
    return -1


while i < n:
    line = lines[i]

    # 1.1 背景补句子
    if line.startswith('bodyChildren.push(body("本系统名为'):
        emit(line.replace(
            '财经快讯自动追踪昨日收盘以来的全部市场消息。',
            '财经快讯自动追踪昨日收盘以来的全部市场消息并进行利好/利空情绪分析；平台采用『年度常驻账户 + 管理员发布限时比赛』的双层账户体系，选手既有一年场长期成绩，也可报名进入特定时期的模拟盘比赛。'))
        i += 1
        continue

    # 1.2 目标补句
    if line.startswith('bodyChildren.push(body("系统目标包括'):
        emit(line.replace(
            '六是提供 NPC 竞技场与财经快讯两大特色模块。',
            '六是提供 NPC 竞技场与财经快讯（含利好利空情绪分析）两大特色模块；七是提供多账户比赛体系，年度场长跑与限时赛并存，比赛资金独立核算；八是全链路性能优化，保证行情页面秒级打开。'))
        i += 1
        continue

    # 数据库设计段
    if line.startswith('bodyChildren.push(body("共 8 张数据表'):
        emit('bodyChildren.push(body("共 10 张数据表：用户表、股票池表、日线行情表、持仓表、成交记录表、策略表、回测记录表、比赛表（contests）、比赛报名表（contest_entries）与赛程设置表。持仓与成交均带 contest_id 字段（0=年度常驻账户，大于 0 为对应比赛账户），实现多账户资金隔离；比赛报名表以（比赛，用户）唯一约束防止重复报名。"));')
        i += 1
        continue

    # 5.1 大赛排行模块行
    if line.startswith('    ["大赛排行",'):
        emit('    ["大赛排行", "比赛窗口（进行中比赛卡片、一键报名、我的比赛收益）+ 年度场/单场比赛排行切换（金银铜牌、收益率条、我的高亮）"],')
        i += 1
        continue

    # 5.1 快讯模块行
    if line.startswith('    ["财经快讯", "自动追踪昨日'):
        emit('    ["财经快讯", "自动追踪昨日收盘以来的全部市场消息：双源合并去重、A股/美股标签筛选、利好利空情绪分析（逐条标注 + 市场情绪温度计）、60 秒自动刷新"],')
        i += 1
        continue

    # 5.2 赛程设置行后加比赛发布
    if line.startswith('    ["赛程设置",'):
        emit(line)
        emit('    ["比赛发布", "创建限时模拟盘比赛（名称/说明/初始资金/起止时间），发布、下架与删除管理，实时统计报名人数"],')
        i += 1
        continue

    # 6.7 快讯正文后追加情绪引擎与 6.8 比赛体系
    if line.startswith('bodyChildren.push(body("快讯模块并行抓取'):
        emit(line)
        emit('bodyChildren.push(body("在此之上内置关键词规则情绪分析引擎：内置利好词表（降准、降息、回购、增持、超预期、创新高等 20 词）与利空词表（减持、退市、制裁、立案、暴跌等 19 词）并分别加权，对每条快讯的标题与摘要打分，得到 利好/利空/中性 三档倾向、情绪分值与命中关键词，页面逐条彩色标注并汇总为『市场情绪温度计』（净情绪值 +3 以上判定偏暖、-3 以下判定偏冷）。规则引擎纯本地运行、毫秒级响应且不依赖大模型服务，适合课堂演示与离线场景。"));')
        emit('bodyChildren.push(h2("6.8 多账户比赛体系"));')
        emit('bodyChildren.push(body("账户分为两层：年度场为选手常驻账户（初始 100 万，长期有效，构成年度排行）；管理员可随时发布限时比赛（名称、说明、初始资金、起止时间），选手在比赛窗口一键报名后获得独立的比赛资金账户。持仓与成交表通过 contest_id 字段（0=年度场）实现账户级隔离，同一选手在年度场与各比赛中的资金、持仓、收益互不影响；交易接口在比赛账户下会校验报名状态与比赛时间窗口（未报名 403、窗口外 400）。排行榜相应分为年度场排行与单场比赛排行，均按总收益率实时排序，比赛结束后成绩封存。"));')
        i += 1
        continue

    # 7 接口表 NPC 行后加比赛接口
    if line.startswith('    ["GET", "/api/npc/arena'):
        emit(line)
        emit('    ["GET", "/api/contests/window", "比赛窗口（进行中比赛 + 我的报名状态）", "登录"],')
        emit('    ["POST", "/api/contests/{id}/join", "报名比赛，获得独立资金账户", "登录"],')
        emit('    ["GET", "/api/contests/{id}/leaderboard", "单场比赛实时排行", "登录"],')
        emit('    ["GET/POST/PUT/DELETE", "/api/admin/contests", "比赛发布与管理", "管理员"],')
        i += 1
        continue

    # 8 测试表快讯行后加三行
    if line.startswith('    ["财经快讯", "双源合并与过滤"'):
        emit(line)
        emit('    ["快讯情绪分析", "利好/利空判定", "99 条中利好 9、利空 6、中性 84，市场情绪判定偏暖，逐条命中词展示"],')
        emit('    ["比赛多账户", "资金隔离", "比赛账户买入苹果 50 股后比赛总资产 999,994.95 与年度场 966,372.59 互不影响；未报名访问 403"],')
        emit('    ["打开性能", "缓存生效", "决策树首次 3.3 秒 → 缓存命中 7 毫秒；行情启用 stale-while-revalidate 后页面打开不再阻塞；全接口 gzip 压缩"],')
        i += 1
        continue

    # 9 截图：11-news 后追加 12/13
    if line.startswith('bodyChildren.push(...figure(IMG("11-news.png"'):
        emit(line)
        emit('bodyChildren.push(...figure(IMG("12-contest.png"), "图 12 比赛窗口与年度场排行"));')
        emit('bodyChildren.push(...figure(IMG("13-contest-mgmt.png"), "图 13 管理端比赛发布"));')
        i += 1
        continue

    emit(line)
    i += 1

open('body.part.js', 'w', encoding='utf-8').write('\n'.join(out))
print('v4 patched, lines:', len(out))

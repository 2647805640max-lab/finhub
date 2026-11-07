# -*- coding: utf-8 -*-
"""投资体系架构图（PIL 手绘，高度按内容测量）。输出 overview.png / gates.png。"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_R = r"C:\Windows\Fonts\msyh.ttc"

BG = (246, 248, 252)
INK = (25, 31, 43)
MUTED = (94, 106, 124)
LANE_FILL = (255, 255, 255)
LANE_EDGE = (212, 220, 232)
CHIP_FILL = (240, 245, 252)
CHIP_EDGE = (174, 192, 218)
ACCENT = (37, 99, 235)
WARN = (185, 28, 28)
OK = (21, 128, 61)
AMBER = (170, 96, 10)
AUDIT = (120, 53, 15)
PURPLE = (147, 51, 234)

F_TITLE = ImageFont.truetype(FONT_B, 42)
F_SUB = ImageFont.truetype(FONT_R, 21)
F_BAND = ImageFont.truetype(FONT_B, 25)
F_CHIP = ImageFont.truetype(FONT_B, 18)
F_DET = ImageFont.truetype(FONT_R, 15)
F_LABEL = ImageFont.truetype(FONT_B, 17)
F_NOTE = ImageFont.truetype(FONT_R, 16)
F_TINY = ImageFont.truetype(FONT_R, 14)
F_TAG = ImageFont.truetype(FONT_B, 13)

CHIP_H = 84


def tsize(d, txt, font):
    b = d.textbbox((0, 0), txt, font=font)
    return b[2] - b[0], b[3] - b[1]


def wrap(d, txt, font, max_w):
    lines, cur = [], ""
    for ch in txt:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if tsize(d, cur + ch, font)[0] <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def draw_chip(d, x, y, w, title, detail, tag=None):
    d.rounded_rectangle([x, y, x + w, y + CHIP_H], radius=10, fill=CHIP_FILL, outline=CHIP_EDGE, width=2)
    d.text((x + 12, y + 8), title, font=F_CHIP, fill=INK)
    if tag:
        tw, _ = tsize(d, tag, F_TAG)
        tx = x + w - 12 - tw - 12
        d.rounded_rectangle([tx, y + 9, x + w - 12, y + 29], radius=7,
                            fill=(255, 244, 230), outline=(226, 170, 96), width=1)
        d.text((tx + 6, y + 11), tag, font=F_TAG, fill=AMBER)
    yy = y + 34
    for ln in wrap(d, detail, F_DET, w - 26)[:2]:
        d.text((x + 12, yy), ln, font=F_DET, fill=MUTED)
        yy += 19


def arrow_down(d, x, y1, y2, label):
    d.line([(x, y1), (x, y2 - 12)], fill=ACCENT, width=3)
    d.polygon([(x - 9, y2 - 14), (x + 9, y2 - 14), (x, y2)], fill=ACCENT)
    if label:
        tw, th = tsize(d, label, F_NOTE)
        cx, cy = x + 18, y1 + (y2 - y1) // 2 - th // 2 - 3
        d.rounded_rectangle([cx - 6, cy - 4, cx + tw + 6, cy + th + 6], radius=6, fill=(232, 240, 252))
        d.text((cx, cy), label, font=F_NOTE, fill=(30, 76, 170))


def side_box(d, x1, y1, x2, title, items, fill, edge, title_color, body_color):
    inner_w = x2 - x1 - 36
    rows = [(it, wrap(d, "· " + it, F_TINY, inner_w)) for it in items]
    h = 52 + sum(len(ls) * 20 + 8 for _, ls in rows) + 8
    d.rounded_rectangle([x1, y1, x2, y1 + h], radius=14, fill=fill, outline=edge, width=2)
    d.text((x1 + 18, y1 + 12), title, font=F_BAND, fill=title_color)
    yy = y1 + 52
    for _, ls in rows:
        for ln in ls:
            d.text((x1 + 18, yy), ln, font=F_TINY, fill=body_color)
            yy += 20
        yy += 8
    return y1 + h


SANITIZE = os.environ.get("ARCH_SANITIZE") == "1"
OUTDIR = os.path.join(OUT, "public") if SANITIZE else OUT
os.makedirs(OUTDIR, exist_ok=True)


def overview() -> str:
    W = 2400
    left, right = 390, 2010
    lane_w = right - left
    top = 150

    bands = [
        ("① 数据源", [
            ("行情", "东财 / 新浪 / 腾讯：指数 + ETF 日线；日频缓存落 data/nav"),
            ("利率与汇率", "中债估值、美债 Treasury 曲线、CFETS 中间价"),
            ("资讯与研报", "财联社 / 华尔街见闻 / RSS / 卖方研报（只作方向参考）"),
            ("持仓快照", "用户上传：支付宝/天天/且慢/银行/券商 → 本机 finwatch/holdings.json"),
            ("国家队", "ETF 申赎与份额变化（F2-补，属推断而非确认）"),
        ]),
        ("② 采集与适配", [
            ("VPS collect_vps.py", "systemd finhub-collect 常驻：A股时段 2 分钟，其余 30 分钟"),
            ("本机 run.py", "8787 常驻：09:15–15:10 每 120 秒，其余 30 分钟"),
            ("ingest-market.ps1", "refresh-pipeline 的 S1：行情落 data/nav，供离线复用"),
            ("factor-ingress.py", "08:30 三因子（布伦特/中债/美债）→ factors-live.json"),
            ("qis-factors.py", "价量因子演算 → factors-qis.json（研究级，不推仓位）"),
        ]),
        ("③ 计算内核", [
            ("timing_core.py", "TimingEngine：六阶段 / 机会与风险评分 / 逐条证据"),
            ("engine_v2.py", "L0 持仓 → L1 信号 → L2 政策 → L3 订单（金额只在政策层算）"),
            ("decision_integrity.py", "完整性门：输入不 PASS 就不出单", "★生产已接"),
            ("engine_core_vps.py", "VPS 侧内核：只把新浪取数换成腾讯，算法不改"),
            ("研究级脚本", "backtest / dyn_sim / policy_stress —— 不进生产路径"),
        ]),
        ("④ 闸门与治理", [
            ("政策硬顶 15%", "HARD_MAX 是权限根：超配被 min() 裁剪并留 policyWarnings"),
            ("引擎完整性门", "持仓≤36h、四指数同日、行情≤4天、字段级 → 否则空单 exit 2", "★已接"),
            ("finhub-data verdict", "Actions 自动算 decisionIntegrity：board 24h / 持仓 36h / 政策未决项"),
            ("check.ps1 27 项", "C0–C26 周检，退出码 0/1/2；FAIL 即数据链有洞"),
            ("refresh-pipeline S1–S6", "每 30 分钟：采集→重算→自检→推送→线上验证，退出码 0/2/1/3"),
        ]),
        ("⑤ 产物与存储", [
            ("contracts/board.json", "本机全量看板，含金额与内部路径，禁止公开"),
            ("board-public.json", "白名单脱敏后的唯一公开件，S3 自检 0 金额"),
            ("metrics / position-history", "权威数字台账与仓位历史序列"),
            ("out/daily_plan.json", "引擎产物；BLOCK 时无 plan、无订单"),
            ("finhub-data 仓", "state.json（公开）+ board.json（含 verdict）"),
            ("VPS 数据目录", "state.json + board.json（隧道消费）"),
            ("memcore", "决策日志 / 每日清单 / 理财守望提醒"),
        ]),
        ("⑥ 分发", [
            ("cloudflared 隧道", "→ VPS serve.py：state 公开、/api/holdings 需 X-FH-Key、personal 401"),
            ("GitHub raw + jsDelivr", "finhub-data@main：board.json / state.json"),
            ("GitHub Pages", "finhub 仓：index.html / board.html / ui-v6.css"),
            ("notify.py", "六通道推送（PushPlus / 企业微信 / Bark…），凭据只读环境变量"),
        ]),
        ("⑦ 呈现与消费", [
            ("首页 index.html", "决策条(BLOCK 灯) / 现在什么情况 / 今日信号卡 / 我的持仓（口令）"),
            ("治理页 + 独立看板", "完整性阻断 / 配置偏离 / 再平衡 / 数据新鲜度"),
            ("手机 PWA", "小米 14：公开层免口令，个人层需口令"),
            ("DSH 会话与定时任务", "08:30 采集 / 08:45 推演 / 每 30min 流水线 / 16:05 汇总 / 周检"),
            ("人工执行", "引擎无实盘权限（auto_live_trading=False），下单由人完成"),
        ]),
    ]

    COL_GAP = 12
    cols = 4
    cw = (lane_w - 32 - (cols - 1) * COL_GAP) // cols
    gap = 44
    heights = []
    for _, items in bands:
        rows = (len(items) + cols - 1) // cols
        heights.append(52 + rows * CHIP_H + (rows - 1) * 10 + 12)

    left_items = [
        "engine-policy.json：从源码导出，sha256 钉死 timing_core / engine_v2",
        "rules.json：个人政策，只能收紧硬顶，不能放宽",
        "conventions / factor-registry：阈值与因子的唯一登记处",
        "sealed/forecast-v1.0.md：预注册演算，哈希封存不得回改",
        "BOUNDARIES.md：边界断言（B-01/B-02），口径漂移即红",
        "ERRATA.md：更正只追加，不改原文",
    ]
    right_items = [
        "out/decision_log.jsonl：每份清单一行，事后可对验收",
        "_audit/refresh-log.jsonl：每轮流水线留痕",
        "check.ps1 27 项：当前 PASS21 / WARN8 / FAIL0",
        "sealed 哈希 + verify 评分：预测先封存再结算",
        "AUDIT_ui-data_20261107.md：本轮审计原件",
        "修前 FAIL / 修后 PASS 日志：TDD 证据",
        "verify_decision_integrity.py：生产自检 9/9 PASS",
        "ERRATA.md：更正只追加，不改原文",
    ]

    footer_h = 178
    H = top + sum(heights) + gap * (len(bands) - 1) + footer_h
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 36), "投资体系总架构 · 2026-11-07 实测版", font=F_TITLE, fill=INK)
    d.text((62, 94),
           "生产链 = VPS 算行情 + 本机 PowerShell 算政策与看板 + GitHub 只做公开数据与页面；"
           "GitHub Actions 不参与生产，唯一例外是 finhub-data 的完整性 verdict。",
           font=F_SUB, fill=MUTED)
    d.text((62, 122), "图例：蓝箭头 = 数据流（标签为交接产物）· 橙线 = 契约权威 · ★ = 本轮新增/已接进生产",
           font=F_TINY, fill=MUTED)

    y = top
    band_ys = []
    labels = [
        "holdings.json · data/nav · 源站原始数据",
        "state.json · factors-live / factors-qis.json",
        "PASS → orders / BLOCK → 空单 + exit 2",
        "decisionIntegrity · 订单清单 · 看板 JSON",
        "board.json（脱敏）· verdict · 隧道文件",
        "HTTP / raw / Pages / 推送",
    ]
    for bi, (title, items) in enumerate(bands):
        h = heights[bi]
        d.rounded_rectangle([left, y, right, y + h], radius=14, fill=LANE_FILL, outline=LANE_EDGE, width=2)
        d.text((left + 16, y + 12), title, font=F_BAND, fill=ACCENT)
        band_ys.append(y)
        for i, item in enumerate(items):
            tag = item[2] if len(item) > 2 else None
            r, c = divmod(i, cols)
            draw_chip(d, left + 16 + c * (cw + COL_GAP), y + 47 + r * (CHIP_H + 10), cw, item[0], item[1], tag)
        if bi < len(bands) - 1:
            arrow_down(d, left + lane_w // 2, y + h + 2, y + h + gap - 2, labels[bi])
        y += h + gap
    total_bottom = y - gap

    l_bottom = side_box(d, 60, top, 340, "契约与策略根", left_items,
                        (252, 248, 238), (226, 208, 176), AUDIT, (118, 88, 48))
    gate_y = band_ys[3]
    mid = min(max(l_bottom - 40, top + 120), gate_y - 60)
    d.line([(340, mid), (362, mid)], fill=AUDIT, width=3)
    d.line([(362, mid), (362, gate_y + 26)], fill=AUDIT, width=3)
    d.line([(362, gate_y + 26), (left - 4, gate_y + 26)], fill=AUDIT, width=3)
    d.polygon([(left - 6, gate_y + 18), (left - 6, gate_y + 34), (left + 4, gate_y + 26)], fill=AUDIT)
    d.text((364, gate_y - 4), "sha256 钉死源码；规则只能收紧", font=F_TINY, fill=AUDIT)

    side_box(d, 2036, top, 2340, "审计与留痕", right_items,
             (243, 245, 249), (206, 214, 226), (70, 80, 96), (80, 90, 104))

    fy = total_bottom + 26
    d.rounded_rectangle([60, fy, 2340, fy + 142], radius=12, fill=(238, 244, 252), outline=(168, 192, 226), width=2)
    d.text((80, fy + 12), "四条铁律（前三条是踩过坑换来的）", font=F_LABEL, fill=ACCENT)
    d.text((80, fy + 46), "① 公开数据仓唯一写者：finhub-data 只允许「内容 API 原地 PUT」，禁用 git push -f（否则旧副本会覆盖新板）。", font=F_NOTE, fill=INK)
    d.text((80, fy + 72), "② 权威靠哈希不靠口头：engine-policy.json 钉死 engine_v2 / timing_core 的 sha256；口径漂移 = 自检红。", font=F_NOTE, fill=INK)
    d.text((80, fy + 98), "③ BLOCK ≠ HOLD：完整性未通过时不出单、不算建议；旧动作不得当作当前建议。", font=F_NOTE, fill=WARN)
    d.text((80, fy + 124), "④ 回路：人工下单 → 平台持仓变化 → 下次上传快照（holdings.json）→ 新一轮；快照不更新，一切判断自然过期。", font=F_NOTE, fill=MUTED)

    path = os.path.join(OUTDIR, "overview.png")
    img.save(path)
    return path


def gates() -> str:
    cols = [
        ("闸门 A · 引擎（生产已接）", ACCENT, [
            ("输入", "holdings 快照 + 四指数行情（asOf）"),
            ("判定", "持仓≤36h / 四指数同日齐全 / 行情≤4天 / 市值·现金字段级 / 未来时钟 5min"),
            ("不通过", "orders = [] · error 置位 · CLI exit 2 · 无 plan/market 键"),
            ("阻断码", "HOLDINGS_STALE · HOLDINGS_ITEM_INVALID · HOLDINGS_CASH_INVALID\nMARKET_PARTIAL · MARKET_STALE · HOLDINGS_READ_ERROR"),
            ("实测", "E06 缺 marketValue → BLOCK；E07 cash=\"NaN\" → BLOCK；E01 正常 → PASS 3 单"),
            ("接线", "engine_v2.py + decision_integrity.py；engine-policy.json 的 sha256 已更新"),
            ("自检", "verify_decision_integrity.py：9/9 PASS"),
            ("当前", "真实快照约 48h → 会 BLOCK；刷新快照后才会 PASS"),
        ]),
        ("闸门 B · 数据仓（已上线）", OK, [
            ("输入", "finhub-data@main 的 board.json"),
            ("判定", "board 24h / 持仓 36h / 四指数 / 行情 4 天 / 政策未决项 / 硬顶≤15%"),
            ("不通过", "写回 decisionIntegrity.status = BLOCK + issues"),
            ("触发", "push 到 board.json（每 30 分钟流水线 S4 之后）"),
            ("当前", "BLOCK · checkedAt 2026-11-07 22:14:23+08 · 持仓 48h>36h"),
            ("失败可见", "run 42380573034 曾 failure（红叉），2bfaafc 用 GITHUB_TOKEN 修好"),
            ("已知风险", "validate 先 --write 再 --check 恒真；烘焙 dataAgeDays 可谎报 PASS"),
        ]),
        ("闸门 C · 页面（已上线）", PURPLE, [
            ("输入", "board.json 的 decisionIntegrity + 个人层快照"),
            ("判定", "无 PASS / 超 24h / 未来>5min / 持仓>1.5 天 / stale=true"),
            ("不通过", "决策条 BLOCK · 金额与执行单遮蔽 · 不给 HOLD/ADD/TRIM/EXIT"),
            ("实测", "注入 totalWealth=1,234,567：BLOCK 下 DOM 0 泄漏；PASS 下全部显示"),
            ("接线", "index.html 的 decisionIntegrityFor；board.html 同款"),
            ("缺口", "个人层三处入口补丁在分支 fix/integrity-personal-layer（未合并）"),
            ("线上", "2026-11-07 22:4x 截图见 BLOCK；首页大字徽章被 .trim 类名吃掉（P1）"),
        ]),
    ]

    cw, cgap, x0, top = 620, 34, 60, 150
    line_h, pad = 20, 14

    img = Image.new("RGB", (10, 10), BG)
    d = ImageDraw.Draw(img)
    content_heights = []
    for _, _, rows in cols:
        h = 62
        for k, v in rows:
            h += 24 + len(wrap(d, v, F_DET, cw - 40)) * line_h + pad
        content_heights.append(h + 18)
    bh = max(content_heights)
    footer_top = top + bh + 40
    H = footer_top + 200
    img = Image.new("RGB", (2100, H), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 34), "三个完整性闸门 · 谁在拦、拦在哪、现在什么状态", font=F_TITLE, fill=INK)
    d.text((62, 94),
           "同一份事实：输入不新 / 不全 / 字段坏了 → 不允许产出可执行建议。三处独立实现，任一处失守都不该让建议漏出去。",
           font=F_SUB, fill=MUTED)

    for i, (title, color, rows) in enumerate(cols):
        x = x0 + i * (cw + cgap)
        d.rounded_rectangle([x, top, x + cw, top + bh], radius=16, fill=LANE_FILL, outline=color, width=3)
        d.text((x + 20, top + 14), title, font=F_BAND, fill=color)
        yy = top + 62
        for k, v in rows:
            d.text((x + 20, yy), k, font=F_LABEL, fill=MUTED)
            yy += 24
            for ln in wrap(d, v, F_DET, cw - 40):
                d.text((x + 20, yy), ln, font=F_DET, fill=INK)
                yy += line_h
            yy += pad
        if i < 2:
            ax = x + cw + 6
            d.line([(ax, top + bh // 2), (ax + cgap - 16, top + bh // 2)], fill=MUTED, width=3)
            d.polygon([(ax + cgap - 18, top + bh // 2 - 8), (ax + cgap - 18, top + bh // 2 + 8),
                       (ax + cgap - 6, top + bh // 2)], fill=MUTED)

    d.rounded_rectangle([60, footer_top, 2040, footer_top + 170], radius=14,
                        fill=(255, 251, 242), outline=(232, 208, 168), width=2)
    d.text((80, footer_top + 14), "写者只有三个；谁晚写谁赢是历史事故源，所以每个产物必须只有一个写通道", font=F_LABEL, fill=AUDIT)
    d.text((80, footer_top + 50), "① 引擎 → out/daily_plan.json（再经 finwatch_publish 校验 PASS，才写决策日志/memcore）", font=F_NOTE, fill=INK)
    d.text((80, footer_top + 78), "② refresh-pipeline S4 → finhub-data 的 board.json / state.json（内容 API 原地 PUT）", font=F_NOTE, fill=INK)
    d.text((80, footer_top + 106), "③ board_sync.py → VPS 数据目录的 board.json（读脱敏件；二扫命中泄漏即中止）", font=F_NOTE, fill=INK)
    d.text((80, footer_top + 134), "三个闸门都 fail-closed：任一处拿不到明确 PASS，就按 BLOCK 处理，不给建议、不出单、不写记忆。", font=F_NOTE, fill=WARN)

    path = os.path.join(OUTDIR, "gates.png")
    img.save(path)
    return path


if __name__ == "__main__":
    print(overview())
    print(gates())

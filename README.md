# FinHub 投资驾驶舱

手机端 PWA：行情 / 三因子 / 持仓 / 告警 / 新闻 / 链式推演。经 GitHub Pages 分发。

> VPS 算行情，本机算政策与看板，GitHub 只存公开数据和页面。
> 引擎只产出建议与订单清单，没有实盘权限；下单永远由人完成。

## 目录结构

- `index.html` / `board.html` / `ui-v6.css` — 前端呈现（首页、治理看板）
- `sw.js` / `manifest.json` — PWA 离线缓存与安装支持
- `contracts/` — 契约的 Python 实现：阈值（`thresholds.py`/`thresholds.json`）、签名（`signing.py`、`ed25519_pure.py`、`signing-key.pub.json`）
- `data/` — 公开脱敏数据：`board.json`（看板公开件，真实金额一律替换为 `[金额已移除]` 占位）、`heartbeat.json`
- `tests/` — 自检测试
- `docs/architecture/` — 架构文档与图（`ARCHITECTURE.md`、`overview.png`、`gates.png`）

## 如何运行 / 自检

```bash
python tests/ui-v6-smoke.py -v            # UI 冒烟 + 完整性行为测试（全量，25 条）
python tests/ui-integrity-behavior.py -v  # 仅行为完整性测试
```

行为测试不是字符串 grep：抽出页面真实内联 JS 渲染函数在 node 下执行，对 blocked / pass / stale / no-board 夹具断言渲染结果，双向都验（blocked 输出不得含任何金额；pass 输出必须保留金额与 trim 工单）。

## 边界 / 安全红线

1. **引擎只产出建议不下单**：`engine_v2.py` 只生成 `daily_plan.json`，完整性门 PASS 才出单、无 PASS 拒写决策日志。
2. **公开/私有严格分离**：本机私有仓 `contracts/board.json` 含金额与内部路径，**不得公开**；本仓库 `data/board.json` 是唯一脱敏公开件，出现真实金额即为泄漏事故。
3. **闸门阻断**：完整性门或数据仓闸门 BLOCK 时，不产生建议、不产生订单。
4. **写者纪律**：本仓库数据只允许内容 API 原地 PUT，禁止 `git push -f`，防止旧副本覆盖新板。

详细架构见 [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)。

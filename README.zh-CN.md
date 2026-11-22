# zeta-audit

[英文](README.md) | **中文**

**把它指向别人给你的零点表，得到一个判定。**

```bash
pip install "zeta-audit[crosscheck]"
zeta-audit zeros.txt
```

```
table       : zeros.txt
sha256      : 3436c916a7878261ac183fd7b9448c9a4736b8bbccf1356874a6ce1788541632
ordinates   : 100,000  (14.134725 .. 74920.827499)
structure   : ok  dupes=0 descents=0 nonpositive=0
residuals   : our max |zeta| = 3.8e-08 over 40 samples, mpmath 1.2e-08
independent : max |diff| vs mpmath = 2.7e-10 over 5 zeros
completeness: count=100,000 vs smooth N(T)=99999.405  S(T) implied = +0.595  (weak sanity check)
              window rows 24901..25100: table 200 vs independent count 200  [ok]
              window rows 49901..50100: table 200 vs independent count 200  [ok]
              window rows 74901..75100: table 200 vs independent count 200  [ok]

RESULT: ALL CHECKS PASSED
```

这是对 Odlyzko `zeros1` 的真实运行结果——10 万个零点，高度到 74,920.8
（sha256 `3436c916…`）。程序输出是英文，字段名见下表：

| 字段 | 含义 |
| --- | --- |
| `structure` | 结构：排序、重复、非正坐标 |
| `residuals` | 残差：采样坐标上的 \|ζ(½+iγ)\|，两套求值器各给一个 |
| `independent` | 独立核对：与 `mpmath.zetazero` 的坐标偏差 |
| `completeness` | 完整性：计数 vs 平滑 N(T)，以及各窗口的独立计数 |
| `[ok]` / `[MISMATCH]` | 该窗口一致 / 不一致 |

## 最要紧的那项检查，以及它是怎么被验证的

多数零点表出错的方式都很平庸：一行顺序错了、重复了一行、编造了一个点。这些好抓。

难的是**漏掉**一个零点——因为它列出的每个坐标都可以是对的，文件只是安静地跳过了一个。

所以这个工具不只核对“写出来的对不对”，它会**数**。取三个各 200 行的窗口，每个窗口内
的零点个数**只从 ζ 本身**重新算一遍（用独立实现：mpmath 的 `nzeros`，Turing 方法），
再与表格在该窗口内列出的行数对比。

证据来自 `out/odlyzko_negative_control.json`——同一张 10 万行的表，**删掉第 50,050 行**：

```
completeness: count=99,999 vs smooth N(T)=99999.405  S(T) implied = -0.405  (weak sanity check)
              window rows 24900..25099: table 200 vs independent count 200  [ok]
              window rows 49900..50099: table 200 vs independent count 201  [MISMATCH]
              window rows 74900..75099: table 200 vs independent count 200  [ok]

RESULT: FAILED
```

它失败了，而且指对了窗口。注意那行弱校验：`|S(T)| = 0.4`，**本来是能通过的**。
「计数 vs 平滑值」这种检查看不见单独一个洞，只有独立计数能。

### 三个试过但不成立的做法

记下来是因为它们都是最直观的想法，而它们全都错——不写下来，别人还会再试一遍。

| 做法 | 为什么不行 |
| --- | --- |
| **局部间隔统计** | 在 GUE（高斯酉系综）间距分布下，约 7% 的**合法**间隔会超过其局部中位数的 2 倍。实测：在一张**完全正确**的 10 万行表上，99,999 个间隔里有 7,155 个被标记。真正的洞和普通涨落分不开。 |
| **辐角原理窗口计数** | 原理正确，但每个窗口需要 O(\|Z\|/step) 次 ζ 求值。T ≈ 4×10⁴ 时约 1.5×10⁴ 个点 × 6 ms，已经不可用。`nzeros` 只要 0.1 秒。 |
| **在零点坐标处调 `nzeros`** | 浮点舍入会让 `nzeros(γ_k)` 不可预测地返回 *k* 或 *k−1*（实测：γ₃ 返回 2 而不是 3）。计数必须在两个零点**之间**取。 |

这三种做法都被 `test_audit_detects_missing_zero` 钉住了，所以日后谁想“简化”回其中任何
一种，CI 都会失败。

## 四项检查

| 检查 | 抓什么 | 怎么抓 |
| --- | --- | --- |
| **structure**（结构） | 换位、重复、降序的坐标 | 排序与重复扫描 |
| **residuals**（残差） | 编造出来的点 | 在采样坐标上算 \|ζ(½+iγ)\|，用**两套**求值器 |
| **independent**（独立） | 系统性错值 | 与 `mpmath.zetazero` 对坐标 |
| **completeness**（完整性） | **漏掉**的零点 | 窗口化的独立计数（见上） |

## 为什么做这个

零点表是承重的“信我”文件。所有对 ζ 的数值使用都依赖它们，而它们以不透明的数据形式
分发，检查这一步却一直没有标准做法。能严格算出零点的工具——[Arb](https://arblib.org)、
[mpmath](https://mpmath.org)——都很好，但它们是在**生产**，不是在审计别人给的文件。

这个仓库就是“检查”那一步，外加让检查本身可信所需的参照材料。

## 其余部分的真实状态（诚实表）

这个栈的多数部分在别处有更强的实现。逐项对照见
**[docs/COMPARISON.md](docs/COMPARISON.md)**。摘要：

| 组件 | 状态 |
| --- | --- |
| 零点表审计（上面那个） | **本仓库的重点**；最接近的已有工作是 [zeta-lab](https://github.com/teal-sea/zeta-lab) 内的一个验证**组件**，不是命令行工具 |
| ζ、θ、Z 求值 | 弱于 Arb（浮点，不是包围区间）——保留自有实现是为了零依赖，且它本身要参与交叉验证 |
| 零点隔离 | 弱于 Arb 的 `acb.zeta_zeros`（没有严格的包围区间） |
| 辐角原理条带计数 | 作为**独立**计数有用；浮点级别，不是严格认证 |
| ψ(x)/R(x) 双实现 | 对别人的代码是一个可用的交叉校验参照 |
| 条件性素数证书 | **仅作演示**——比 MR 慢约 100 倍，且依据是 ERH/GRH，不是 RH |
| 「素数的透明日志」 | 作为产品**已撤回**；通用的日志/Merkle 代码保留 |

## 验证：这些数字凭什么可信

```bash
python tests/run_all.py    # 81 项检查
python verify.py           # 对已提交产物的第三方复核
python pipeline.py         # 重新生成全部产物（约 5 分钟，含 10 万行审计）
python report.py           # 只从产物渲染出 REPORT.md
```

最重要的一项检查是**唯一非循环**的那项：**与 mpmath 吻合**，一个独立实现。

| 检查 | 结果 |
| --- | --- |
| 我们的零点 vs `mpmath.zetazero`（前 50 个） | max \|Δγ\| = 1.4e-11 |
| 我们的 Z(t) vs `mpmath.siegelz` | max \|Δ\| = 1.5e-11（t = 1000） |
| mpmath 的 ζ 在我们给出的坐标处 | max \|ζ\| = 1.9e-11 |
| Odlyzko `zeros1`，10 万行 | 四项检查全部通过 |
| 同一张表，删掉一行 | **FAILED**，且指对了窗口 |

实测结果见 **[REPORT.md](REPORT.md)**，由 `out/*.json` 生成，所以文字不会与证据脱节。

```
零点     649 个零点，0 < γ ≤ 1000；max |ζ(½+iγ)| = 2.6e-11；与已发表表 Δγ = 8.7e-12
条带     T = 100 / 300 / 600：辐角原理计数 == 临界线计数（29/138/341）
显式公式 ψ(10⁵)：50 个零点时误差 −31.79 → 600 个零点时 −0.27
```

## 安装

```bash
pip install zeta-audit                  # 只依赖 numpy
pip install "zeta-audit[crosscheck]"    # 加 mpmath，启用独立检查
```

需要 Python ≥ 3.10。没装 mpmath 时，独立检查与窗口检查会报告 **skipped**，而不是“通过”。

## 用法

```bash
zeta-audit zeros.txt                       # 主入口
zeta-audit zeros.txt --windows 5           # 更多独立窗口
zeta-audit zeros.txt --json r.json         # 完整报告

python -m zeta_audit zeros --t-max 1000      # 找零点并给出残差
python -m zeta_audit strip --t-max 600       # 辐角原理验证
python -m zeta_audit bounds --x-max 10000000 # 误差界审计，每个界的假设都标注
python -m zeta_audit crosscheck              # 与 mpmath 对比
python -m zeta_audit.serve --port 8788       # 标准库 HTTP 包装
```

```python
from zeta_audit import load_table, audit_zero_table

report = audit_zero_table(load_table("zeros.txt"), windows=3)
if not report["all_ok"]:
    for w in report["completeness"]["windows"]:
        if not w["agree"]:
            print("可能在以下行附近有洞：", w["rows"],
                  w["table_zeros_inside"], "vs", w["independent_count"])
```

## 支持的表格式

自动识别；索引列、`key=value`、逗号/制表符分隔、`#` 注释都能处理：

```
14.134725141734693
1 14.134725141734693
gamma=14.134725141734693
```

Odlyzko 和 LMFDB 的下载文件无需转换即可解析——上面那次 10 万行审计直接用的是 Odlyzko
的原始文件。如果你的文件解析不了，那是值得提交的 bug。

## 目录结构

```
zeta_audit/
  audit_table.py   *** 表审计器（命令行：zeta-audit）***
  crosscheck.py    mpmath 交叉验证 + nzeros 窗口（可选依赖）
  zeta.py          ζ(s)、θ(t)、Hardy Z（零依赖浮点实现）
  zeros.py         零点查找 + 残差审计
  explicit.py      ψ(x)、π(x)、li、R(x)，各自带一套冗余的第二实现
  certify.py       辐角原理的条带与窗口计数
  bounds.py        Schoenfeld / Cramér 误差界，逐界标注假设
  primality.py     13 基底无条件测试 + ERH/GRH 基底扫描
  parallel.py      并行扫描 + 实测的顺序耗时估计
  transparency.py  哈希链日志、Merkle 锚、包含证明
  primegen.py      存证演示（不是产品）
  plot.py          零依赖 SVG 图表
  serve.py         标准库 HTTP 服务
data/odlyzko_zeros1.txt   审计所依据的 10 万行参照表
pipeline.py / report.py / verify.py / tests/run_all.py
tests/test_readme_parity.py   保证本文件与英文版 README.md 不失配
docs/COMPARISON.md  与已有工作的逐项对照，包括本仓库输的那些
docs/LAUNCH_COPY.md 介绍用的描述、公告稿、问答
docs/DESCRIPTION.md 仓库 About 字段、PyPI 摘要、长描述、标签
docs/PYPI_README.md PyPI 项目页（由 DESCRIPTION.md 第 3 节生成）
```

## 局限

- **浮点，不是严格认证。** Arb 给的是严格包围区间；这里给的是实测与 mpmath 吻合到约
  1e-12 的估计值。需要证明级算术时请用 Arb，把这里当作第二意见。
- **窗口完整性是采样，不是穷举。** 10 万行里只取 3 个各 200 行的窗口。采样窗口之外的
  洞会被漏掉。`--windows` 是用时间换覆盖率；全量扫描不是这个工具做的事。
- 残差同样是采样：10 万个坐标里取 40 个，原因同上。
- 条带验证在纯 Python 下上限是 T = 600；方法本身可扩展（Platt–Trudgian 做到 3×10¹²），
  解释器不行。
- `2 log²n` 这个基底上界依据的是 **ERH/GRH，不是 RH**。证书会把假设打印出来。
- `CRAMER_C = 1/(4π)` 是一个保守的工程常数，不是文献中的最佳常数；审计会打印比值，
  便于你换成自己的。

MIT。最有用的事情是寄一张能把这个工具判错的表过来。
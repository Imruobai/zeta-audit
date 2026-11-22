# zeta-audit

[英文](README.md) | **中文**

[![ci](https://github.com/Imruobai/zeta-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/Imruobai/zeta-audit/actions/workflows/ci.yml) [![pypi](https://img.shields.io/pypi/v/zeta-audit.svg)](https://pypi.org/project/zeta-audit/)

**把别人给你的零点表丢给它，直接看结论。**

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

这是真跑出来的。表是 Odlyzko 的 `zeros1`，10 万个零点，最高到 74,920.8，sha256
`3436c916…`。输出行是英文（程序就这么打），字段意思如下：

| 字段 | 意思 |
| --- | --- |
| `structure` | 排序对不对、有没有重复、坐标是否非正 |
| `residuals` | 抽样坐标处 \|ζ(½+iγ)\| 有多大，两套求值器各算一遍 |
| `independent` | 和 `mpmath.zetazero` 的坐标差多少 |
| `completeness` | 总数对不对，以及各窗口里零点的真实个数 |
| `[ok]` / `[MISMATCH]` | 这个窗口对上了 / 对不上 |

## 最要紧的一项，以及凭什么信它

零点表常见的毛病都很好抓：某一行顺序颠倒了、重复了一行、凭空多出一个点。这些都简单。

真正难的是**少了一个零点**。表里列出来的每一个坐标都可以是对的，文件只是悄悄漏跳过一行，
你翻不出来。

所以这个工具不只核对“写出来的对不对”，它还要**数**。随便挑三个各 200 行的窗口，每个窗口
里有几个零点，**只拿 ζ 本身重算一遍**（走独立实现，mpmath 的 `nzeros`，Turing 方法），
再和表格在同一个窗口里列出的行数比。

证据在 `out/odlyzko_negative_control.json`：同一张 10 万行的表，把第 50,050 行删掉：

```
completeness: count=99,999 vs smooth N(T)=99999.405  S(T) implied = -0.405  (weak sanity check)
              window rows 24900..25099: table 200 vs independent count 200  [ok]
              window rows 49900..50099: table 200 vs independent count 201  [MISMATCH]
              window rows 74900..75099: table 200 vs independent count 200  [ok]

RESULT: FAILED
```

它报错了，指的就是那个窗口。注意上面那行弱校验：`|S(T)| = 0.4`，这个数是能过的。
拿总数去比平滑值，看不出单独一个洞，只有独立计数才行。

### 三个试过、都不成立的做法

写下来是因为这三个都是第一反应会想到的，而且全错。不记下来，下次还是有人再踩一遍。

| 做法 | 为什么不行 |
| --- | --- |
| **看局部间隔** | GUE 间距分布下，约 7% 的**正常**间隔也会超过局部中位数的两倍。实测在一张**完全正确**的 10 万行表上，99,999 个间隔里标出了 7,155 个。真有个洞，混在噪声里根本分不出来。 |
| **用辐角原理数窗口** | 原理没问题，但一个窗口要 O(\|Z\|/step) 次 ζ 求值。T ≈ 4×10⁴ 时差不多 1.5×10⁴ 个点、每点 6 ms，已经跑不动了。`nzeros` 干同样的活只要 0.1 秒。 |
| **直接在零点坐标上调 `nzeros`** | 浮点舍入会让 `nzeros(γ_k)` 时而返回 *k*、时而返回 *k−1*（实测 γ₃ 返回 2，不是 3）。必须取在两个零点**中间**。 |

这三条都写进了 `test_audit_detects_missing_zero`。以后谁想“顺手简化”回其中任何一种，CI 直接拦下。

## 四项检查

| 检查 | 抓什么 | 怎么抓 |
| --- | --- | --- |
| **structure** 结构 | 换位、重复、降序 | 扫一遍排序和重复 |
| **residuals** 残差 | 编出来的点 | 抽样处算 \|ζ(½+iγ)\|，**两套**求值器 |
| **independent** 独立 | 整体偏了的数 | 和 `mpmath.zetazero` 逐个坐标比 |
| **completeness** 完整性 | **漏掉**的零点 | 窗口独立计数（见上） |

## 为什么写这个

零点表是承重件，全靠一句“信我”。所有对 ζ 的数值计算都压在它上面，可它一直是不透明的数据
文件发出来，检查这一步压根没有标准做法。能严格算零点的工具都很好用，[Arb](https://arblib.org) 和 [mpmath](https://mpmath.org)
都是，但它们在**生产**数据，不是去审计别人手里的文件。

这个仓库补的就是“检查”这一步。另外附带一点参照材料，用来让检查本身也站得住。

## 其他部分的真实水平

坦白说，这里面大部分东西别处都有更强的实现。逐项对比在
**[docs/COMPARISON.md](docs/COMPARISON.md)**，摘要：

| 组件 | 状态 |
| --- | --- |
| 零点表审计（上面那个） | **这才是重点**。最接近的已有东西是 [zeta-lab](https://github.com/teal-sea/zeta-lab) 里的一个验证**组件**，不是命令行工具 |
| ζ、θ、Z 求值 | 不如 Arb，浮点而已，没有包围区间。留着自己这套是为了零依赖，而且它正好要参与交叉验证 |
| 零点隔离 | 不如 Arb 的 `acb.zeta_zeros`，没有严格包围区间 |
| 辐角原理条带计数 | 当**独立**计数有用；浮点级别，谈不上严格认证 |
| ψ(x)/R(x) 双实现 | 别人写代码时能拿它当交叉校验的参照 |
| 条件性素数证书 | **只是演示**。比 MR 慢约 100 倍，而且靠的是 ERH/GRH，不是 RH |
| 「素数的透明日志」 | 当产品**已经撤了**；通用的日志/Merkle 代码还留着 |

## 验证：数字凭什么可信

```bash
python tests/run_all.py    # 84 项检查
python verify.py           # 第三方复核已提交的产物
python pipeline.py         # 全部产物重跑一遍（约 5 分钟，含 10 万行审计）
python report.py           # 只从产物渲染 REPORT.md
```

最要紧的是唯一一个**不循环**的检查：和 mpmath 对不对得上。那是个独立实现。

| 检查 | 结果 |
| --- | --- |
| 我们的零点 vs `mpmath.zetazero`（前 50 个） | max \|Δγ\| = 1.4e-11 |
| 我们的 Z(t) vs `mpmath.siegelz`（t = 1000） | max \|Δ\| = 1.5e-11 |
| mpmath 的 ζ 在我们给出的坐标处 | max \|ζ\| = 1.9e-11 |
| Odlyzko `zeros1`，10 万行 | 四项全过 |
| 同一张表，删掉一行 | **FAILED**，而且指对了窗口 |

其余实测数据在 **[REPORT.md](REPORT.md)**。那份文件是从 `out/*.json` 渲染出来的，所以文字
不会和证据走岔。

```
零点     649 个零点，0 < γ ≤ 1000；max |ζ(½+iγ)| = 2.6e-11；与已发表表 Δγ = 8.7e-12
条带     T = 100 / 300 / 600：辐角原理计数 == 临界线计数（29/138/341）
显式公式 ψ(10⁵)：50 个零点时误差 −31.79 → 600 个零点时 −0.27
```

## 安装

```bash
pip install zeta-audit                  # 只依赖 numpy
pip install "zeta-audit[crosscheck]"    # 加 mpmath，独立检查才可用
```

要 Python ≥ 3.10。没装 mpmath 时，独立检查和窗口检查不会运行，结论是 **PARTIAL**、退出码 **2**，不是 `ALL CHECKS PASSED`。退出码：`0` 全部跑过且全过，`2` 有检查被跳过，`1` 有检查没过。

## 用法

```bash
zeta-audit zeros.txt                       # 主入口
zeta-audit zeros.txt --windows 5           # 多开几个独立窗口
zeta-audit zeros.txt --json r.json         # 出完整报告

python -m zeta_audit zeros --t-max 1000      # 找零点，给出残差
python -m zeta_audit strip --t-max 600       # 辐角原理验证
python -m zeta_audit bounds --x-max 10000000 # 误差界审计，每个界依赖什么都标出来
python -m zeta_audit crosscheck              # 和 mpmath 对一遍
python -m zeta_audit.serve --port 8788       # 标准库写的 HTTP 壳
```

```python
from zeta_audit import load_table, audit_zero_table

report = audit_zero_table(load_table("zeros.txt"), windows=3)
if not report["all_ok"]:
    for w in report["completeness"]["windows"]:
        if not w["agree"]:
            print("possible hole near rows", w["rows"],
                  w["table_zeros_inside"], "vs", w["independent_count"])
```

## 认哪些表格式

自动识别。索引列、`key=value`、逗号或制表符分隔、`#` 注释，都能吃：

```
14.134725141734693
1 14.134725141734693
gamma=14.134725141734693
```

Odlyzko 和 LMFDB 下载下来直接用，不用转换。上面那次 10 万行审计就是拿 Odlyzko 的原始文件
跑的。你要是有文件读不进来，那是个值得提的 bug。

## 目录

```
zeta_audit/
  audit_table.py   *** 表审计器（命令行：zeta-audit）***
  crosscheck.py    和 mpmath 交叉验证 + nzeros 窗口（可选依赖）
  zeta.py          ζ(s)、θ(t)、Hardy Z（零依赖浮点实现）
  zeros.py         找零点 + 残差审计
  explicit.py      ψ(x)、π(x)、li、R(x)，每个都另有一套冗余实现
  certify.py       辐角原理的条带计数和窗口计数
  bounds.py        Schoenfeld / Cramér 误差界，逐条标注依赖
  primality.py     13 基底无条件测试 + ERH/GRH 基底扫描
  parallel.py      并行扫描 + 实测出来的顺序耗时估计
  transparency.py  哈希链日志、Merkle 锚、包含证明
  primegen.py      存证演示（不是产品）
  plot.py          零依赖 SVG 图表
  serve.py         标准库 HTTP 服务
data/odlyzko_zeros1.txt   审计拿来对照的 10 万行表
pipeline.py / report.py / verify.py / tests/run_all.py
tests/test_readme_parity.py   保证这份文件和英文版不会走岔
docs/COMPARISON.md  和已有工作逐项对比，包括我们输的那些
docs/LAUNCH_COPY.md 介绍用的文案、公告稿、问答
docs/DESCRIPTION.md 仓库 About 字段、PyPI 摘要、长描述、标签
docs/PYPI_README.md PyPI 项目页（从 DESCRIPTION.md 第 3 节生成）
docs/DISCOVERABILITY.md 如何让它被找到：PyPI、topics、CI、第一处引用
```

## 局限

- **浮点是浮点，不是认证。** Arb 给的是严格包围区间；这里给的是估计值，实测和 mpmath 吻合
  到大约 1e-12。要证明级算术就用 Arb，这边当第二意见。
- **窗口完整性是抽样，不是穷举。** 10 万行里只挑 3 个各 200 行的窗口。窗口之外的洞会漏掉。
  `--windows` 是拿时间换覆盖率；全表扫一遍不是这个工具干的事。
- 残差也是抽样，10 万个坐标里取 40 个，理由同上。
- 纯 Python 下条带验证最高只能到 T = 600。方法本身能往上扩（Platt–Trudgian 做到了 3×10¹²），
  解释器扩不动。
- `2 log²n` 这个基底上界靠的是 **ERH/GRH，不是 RH**。证书里会把假设打出来。
- `CRAMER_C = 1/(4π)` 是个保守的工程常数，不是文献里的最好常数。审计会把比值打出来，
  你可以换自己的。

MIT。最有用的东西是给我一张能把它判错的表。
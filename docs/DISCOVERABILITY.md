# 提高可发现性：现状诊断与清单

不写空话。先判断这个项目**能被谁找到**、卡在哪一步，再给可执行的动作。

---

## 一、现状：功能已经够，缺的是"被检索到"的三个入口

一个开源工具被找到，只有三条路径。

| 入口 | 现状 | 差距 |
|---|---|---|
| **PyPI** | **未发布** | 最大缺口。`pip install zeta-audit` 现在装不上；PyPI 页面是搜索引擎与 `pip search` 的落地页，也是别人敢用你的前提 |
| **GitHub 站内** | README 已写好，但 **0 stars / 0 引用 / 无 topic** | 无社交证明，搜索排序靠后 |
| **外部引用** | 无 | 没有被任何论文、博客、Awesome 列表引用 |

**结论：功能建设已经饱和，再写代码的边际收益接近零。** 三件事按这个顺序做：发布到 PyPI → 补 GitHub 元数据与 CI → 争取第一处外部引用。

---

## 二、最高优先级：发布到 PyPI

### 为什么这是第一

- `pip install zeta-audit` 是不可逆的信任信号：能装，才有人试。
- PyPI 项目页会被 Google 索引；GitHub 仓库页的权重远低于它。
- PyPI 的分类器和关键词会进入 PyPI 的**分面检索**，这是别人发现你的唯一系统化入口。

### 已经准备好的部分（本仓库已完成）

- `python -m build` 成功产出 sdist + wheel
- `twine check` 双双 **PASSED**
- SPDX `license = "MIT"`，无弃用警告
- `zeta-audit` 控制台脚本在干净 venv 中安装并运行通过
- `.github/workflows/release.yml` 使用 PyPI **Trusted Publishing**（无需存 token）

### 你需要做的（约 10 分钟）

1. 在 PyPI 注册（若未注册）：<https://pypi.org/account/register/>
2. 创建 API token 或配置 Trusted Publishing：
   - PyPI → Your projects → Publishing → Add a new pending publisher
   - owner: `Imruobai`，repo: `zeta-audit`，workflow: `release.yml`，environment: `pypi`
3. 打 tag 触发发布：

```bash
git tag v0.4.1
git push origin v0.4.1
```

或者手动：

```bash
python -m build
python -m twine upload dist/*
```

### 发布后立刻做的事

在 PyPI 项目页填 **全部** 字段：Homepage、Repository、Changelog、Keywords、Classifiers。PyPI 的搜索会吃这些字段，空着等于放弃这部分流量。

---

## 三、第二优先级：GitHub 元数据与 CI

### 3.1 补 topic（5 分钟，影响站内搜索）

仓库首页 → 右侧齿轮 → Topics，填：

```
riemann-zeta  zeta-zeros  number-theory  verification  data-validation
mpmath  odlyzko  lmfdb  mathematics  scientific-computing  cli  python
```

理由：GitHub 站内搜索对 topic 有权重，`riemann-zeta` 和 `zeta-zeros` 是真实存在的浏览入口。

### 3.2 About 字段已定稿（191 字符）

```
Audit a Riemann zeta zero table and catch a missing zero. Four checks: row structure, |zeta(1/2+it)| residuals, an independent mpmath cross-check, and a windowed count taken from zeta itself.
```

### 3.3 CI（本仓库已完成）

`.github/workflows/ci.yml` 覆盖：

- Python 3.10 / 3.11 / 3.12 on Ubuntu，加一个 Windows 3.12
- **只装 numpy 的 job**：断言退出码必须是 **2（PARTIAL）** 而不是 0
- 构建 job：`twine check` + 在干净 venv 装 wheel 并真实运行

**CI 徽章本身就是社交证明。** 一个绿勾说明"有人跑过它"，比十段自述有力。加在 README 顶部：

```markdown
[![ci](https://github.com/Imruobai/zeta-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/Imruobai/zeta-audit/actions/workflows/ci.yml)
```

### 3.4 `CITATION.cff`（本仓库已完成）

有了它，GitHub 仓库页右侧会出现 **"Cite this repository"** 按钮。做研究的人看到这个按钮，引用概率显著提高——这是把"工具"变成"可引用对象"的最低成本动作。

---

## 四、第三优先级：第一处外部引用

这是从"存在"到"被找到"的分水岭，也是最难的一步。三条现实路径，按成功率排序：

### 路径 A：给 zeta-lab 提一个 issue（成功率高，成本低）

我在上一轮核查时读到 `teal-sea/zeta-lab` 的 `zero_layer.py` 注释，他们**自己写出了一个缺口**：

> "It does not check completeness: the count is the layer both routes share, through Arb's Turing count, unless an independent count is added."

我们的窗口化独立计数正好补这个缺口。提一个 issue，只说这件事，不要推销整个仓库：

```
Title: independent zero count as a completeness check for zero_layer.py

Your route-2 comment notes that completeness is shared with route 1 unless an independent
count is added. I have been using mpmath's nzeros at midpoints between ordinates as such a
count, plus an argument-principle fallback; it caught a single deleted row in Odlyzko's
100k table that a plain count-vs-smooth check missed (|S(T)| = 0.4, would have passed).

Numbers and the negative control: <link to out/odlyzko_negative_control.json in the repo>
Happy to send a patch in whatever shape fits the repo.
```

**为什么这个成功率高**：他们的 `CONTRIBUTING.md` 明确接受 agent 协助的贡献，并且把"可复现的缺陷或观察"列为第一类贡献形式。

### 路径 B：OEIS 与 LMFDB 的链接（中等）

- OEIS 有 A series 记录 zero ordinates；在相关条目下留一个"verification tool"链接。
- LMFDB 的 zeros 页面有外部工具链接的传统。

### 路径 C：写一篇技术博客（成本高，回报长尾）

内容不要写"我做了个工具"，写**那个失败的故事**：三个做法都不成立、错在哪里、怎么才成立。这类"负面结果 + 方法"的文章在 r/math、Hacker News 上的存活率远高于工具公告，因为读者能学到东西，而不是被推销。

标题可以考虑：
`How I tried to detect a missing Riemann zeta zero, and the three ways that failed`

---

## 五、不要做的事

| 想法 | 为什么别做 |
|---|---|
| **声称这跟 RH 证明有关** | 会立刻失去懂行的读者，而懂行的才是你的目标用户。README 里已经有 `Not a crypto result` / `Not proof-grade arithmetic`，守住 |
| **把"certified"写进任何描述** | Arb 才是 certified；你的算术是浮点。这个词一旦用错，整个项目的可信度归零 |
| **给 README 堆功能列表** | 现在的一句话定位（"catch a missing zero"）是资产。功能列表会稀释它 |
| **刷 star / 互 star** | 对真实的检索排序无用，且会被识别 |
| **在 RH 相关热门帖下灌水链接** | 短期流量，长期拉黑 |

---

## 六、按投入产出排序的行动清单

| # | 动作 | 耗时 | 预期影响 |
|---|---|---|---|
| 1 | 打 tag 发布 PyPI + `pip install` 可用 | 10 min | **最高**：从"存在"变成"可安装" |
| 2 | 补 GitHub topics + About + CI 徽章 | 5 min | 高：站内搜索入口 |
| 3 | 给 zeta-lab 提 issue（补 completeness 缺口） | 20 min | 高：第一处外部引用 |
| 4 | 写技术博客（三个失败的做法） | 2 h | 中：长尾流量 |
| 5 | 提交到 OEIS / LMFDB 相关页 | 20 min | 中低 |
| 6 | 做 PyPI 页面字段补全 | 10 min | 中：分面检索 |

**如果只做一件：做第 1 件。** 其余所有努力都建立在那上面——一个装不上的工具，写得多好都没人用。

---

## 七、当前仓库已经具备的条件（不需要你再做）

- README 中英双版，一致性由测试守（`test_readme_parity.py`、`test_readme_code_parity.py`）
- 真实验证：Odlyzko 10 万行的正向 + 负向对照
- 打包可构建、元数据合规、`twine check` 通过
- CI 三平台 + 无 mpmath 分支断言
- `CITATION.cff`、`CONTRIBUTING.md`、MIT
- 84 项检查由脚本核对，文档数字不会漂移
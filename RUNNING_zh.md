# 本地运行说明

在项目根目录使用 PowerShell。Python 环境位于 `.venv`，不提交到 GitHub。

当前已安装 Python 3.12 环境所需依赖。若要在另一台 Windows 电脑复现本次安装，在新建的 Python 3.12 虚拟环境内运行 `python -m pip install -r requirements-lock.txt`。锁定文件包含 Windows 专用依赖；其他系统使用老师的 `requirements.txt`，并重新验证运行结果。

## 下载数据

每次新开 PowerShell，需要设置 SEC 请求标识。将示例替换为自己的真实姓名和邮箱；不需要 SEC 账户，不要将联系方式写入提交文件。

```powershell
$env:SEC_USER_AGENT = "Your Name your.netid@nyu.edu"
$env:PYTHONUNBUFFERED = "1"
```

按顺序运行老师的脚本。公司名单使用仓库自带快照，不添加 `--refresh`。

```powershell
& .venv/Scripts/python.exe scripts/00_get_lexicons.py
& .venv/Scripts/python.exe scripts/01_build_universe.py
& .venv/Scripts/python.exe scripts/02_download_filings.py --limit 3
& .venv/Scripts/python.exe scripts/02_download_filings.py
& .venv/Scripts/python.exe scripts/03_get_market_data.py
& .venv/Scripts/python.exe scripts/04_validate_downloads.py
```

`--limit 3` 只用于首次检查。完整下载完成后不要再运行它：虽然已下载的文本仍在，老师的脚本会将报告清单重新写成三家公司的清单。需要恢复时，重新运行不带 `--limit` 的完整下载命令，已有文本会从缓存读取。

脚本 03 的价格和成交量缓存不会充分核验已有数据的时间范围或全部缺失的列。重新定义样本后，需要检查覆盖表并有针对性地更新缓存，不能仅凭脚本正常退出认定数据完整。

## 验证结果

验证脚本不修改原始数据，也不决定最终回归样本。它会核对下载数量、公司及报告类型覆盖、文本词数、披露时间、价格与成交量、按 accession 匹配的历史股数，并输出：

- `outputs/download_validation.json`：总体结果、错误和需要解释的事项。
- `outputs/filing_coverage.csv`：各证券预期与实际下载的报告数量。
- `outputs/repeated_filing_accessions.csv`：多股类证券重复引用的公司报告。
- `outputs/market_coverage.csv`：价格与成交量的可用日期和数量。
- `outputs/filing_share_audit.csv`：每条报告记录的股数匹配、日期和股数代理类型。
- `outputs/negative_dictionary_removed_entries.csv`：starter code 纳入但字典标记已移除的负面词。

`errors` 表示需要解决的输入问题；`warnings` 表示需在分析和报告中处理的限制。没有输入错误不等于研究样本没有偏差，也不等于事件日、收益窗口及回归已经验证。

## 执行分析与生成报告

下载完成后运行以下命令。脚本 05 补充用于恢复历史名义价格与成交量单位的拆股记录。脚本 07 会执行分析脚本 06、运行测试，并保存 Notebook 全部输出，无需重复执行 06。

```powershell
& .venv/Scripts/python.exe scripts/05_get_price_actions.py
& .venv/Scripts/python.exe scripts/07_build_notebook.py
& .venv/Scripts/python.exe scripts/08_build_report.py --author "Your Name" --netid your_netid
```

仅重新计算表格时，可以单独运行 `scripts/06_run_analysis.py`。更改分析代码后重新执行 07 和 08，保持输出一致。

- `assignment1.ipynb`：已执行的 Notebook，包含六张表、一张图、完整稳健性结果和十项测试输出。
- `output/pdf/assignment1_report.pdf`：六页英文报告。
- `METHODOLOGY.md`：样本、变量、TF-IDF、事件日和统计检验定义。
- `AI_USE.md`：实际 AI 使用与作者贡献说明。
- `outputs/analysis/`：本地表格、图、样本审计及全部回归系数，不提交 Git。

本次文本样本为 1,624 份报告，波动率和收益模型分别使用 1,591 和 1,592 份。按用户要求取消了 3 美元股价门槛，保留低价股，并修正普通股措辞与旧式壳公司勾选框的解析。固定 2026 年持仓不能解释为各历史时点的全部 ARK 持仓；完整样本 TF-IDF 也属于回顾性分析。SEC 和 Yahoo 数据可能修订，未来重新下载的数值可能变化。保留本地缓存有助于复核本次结果。

修改解析规则后，需要更新解析缓存版本，或调用 `src.analysis_data.build_text_data(force=True)` 从 HTML 重建，再执行 Notebook。不要只删除一部分文本矩阵文件。

## 提交前

保留老师提供的固定持仓快照。其余下载数据、缓存、运行环境和本地检查输出由 `.gitignore` 排除。最终提交需包含保存运行输出的 Notebook、分析代码及完成的 `AI_USE.md`；PDF 报告另交 Brightspace。

不要把生成的数据文件强制加入 Git。推送前检查 `git status`，确保没有无关文件或个人运行记录。

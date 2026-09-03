# 个人股票研究助手 V1

一个不依赖大模型、在个人电脑本地运行的股票研究工具。功能包括：行情获取与缓存、基本信息、MA/MACD/KDJ/RSI、自选股，以及规则化分析报告。

## 启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

在 VS Code 中，也可以按 `F5`，选择“启动股票研究助手（Streamlit）”。项目已经提供 `.vscode/launch.json`。不要使用“运行 Python 文件”，它不会启动 Streamlit 网页服务。

默认使用 AkShare 的公开数据接口。首次查询某只股票需联网；成功获取后数据会缓存到 SQLite。数据仅供研究，不构成投资建议。

## 代码约定

- 股票代码使用六位数字，例如 `600519`、`000001`。
- 所有分析均基于日线数据；报告明确列出数据截止日。
- 数据获取、指标计算、报告生成与页面展示相互独立，方便后续替换数据源或接入 AI。

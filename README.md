
# 期权风险监控系统

这是一个用于监控加密货币期权市场风险的系统，提供实时数据分析、风险评估、异常检测和可视化功能。

## 功能特点

- **实时期权数据监控**: 从多个交易所获取期权数据，实时跟踪市场动态
- **风险指标计算**: 自动计算波动率指标、偏斜度、看跌/看涨比率等多种风险指标
- **异常监测**: 监测执行价异常偏离、成交量异常变动等异常情况
- **情景分析**: 支持价格变动和波动率变化的情景分析
- **可视化界面**: 丰富的图表和数据可视化功能
- **警报系统**: 当风险指标超过阈值时自动发出警报

## 技术栈

- **后端**: Flask, SQLAlchemy, CCXT
- **前端**: JavaScript, Chart.js, Bootstrap
- **数据库**: SQLite (开发环境), PostgreSQL (生产环境)

## 快速开始

### 环境要求

- Python 3.8+
- 包管理器: pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1. 复制`.env.example`为`.env`并填写必要的配置信息:
   ```
   DATABASE_URL=sqlite:///optionsrisk.db
   SESSION_SECRET=your_secret_key
   ```

2. 配置交易所API (可选但推荐):
   - 在系统设置页面添加交易所API密钥
   - 或直接在`.env`文件中配置:
     ```
     DERIBIT_API_KEY=your_api_key
     DERIBIT_API_SECRET=your_api_secret
     ```

### 运行

```bash
python main.py
```

系统将在 http://localhost:5000 启动。

## 项目结构

- `app.py`: 应用初始化
- `main.py`: 主入口点
- `models.py`: 数据库模型
- `config.py`: 配置选项
- `routes.py`: HTTP路由
- `services/`: 核心服务模块
- `static/`: 静态资源
- `templates/`: HTML模板

## 自定义配置

在`config.py`中可以自定义:

- 监控的加密货币符号
- 警报阈值
- 时间周期设置
- 界面语言

## 贡献指南

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可协议

本项目采用MIT许可协议 - 详见 [LICENSE](LICENSE) 文件。

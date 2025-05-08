# OptionRiskSentry

## 1. 项目概述

OptionRiskSentry 是一个专业的期权风险监控系统，主要用于监控加密货币期权市场的风险指标。该系统提供了实时监控、风险预警、历史数据分析等功能，帮助用户更好地理解和应对市场风险。

## 2. 系统架构

### 2.1 技术栈
- 后端框架：Flask
- 数据库：SQLAlchemy (支持 PostgreSQL)
- 前端：Bootstrap-Flask
- 任务调度：APScheduler
- 加密货币交易所 API：CCXT

### 2.2 核心组件
1. **数据服务层**
   - `DataService`: 负责从交易所获取和存储期权数据
   - `ExchangeAPI`: 封装了与交易所的交互
   - `Scheduler`: 处理定时任务和数据更新

2. **风险分析层**
   - `RiskService`: 计算各种风险指标
   - `RiskCalculator`: 实现具体的风险计算算法
   - `DeviationMonitorService`: 监控期权执行价偏离情况

3. **预警系统**
   - `AlertService`: 处理风险预警的生成和管理
   - 多级预警机制：attention、warning、severe

4. **Web 界面**
   - 仪表盘：实时风险指标展示
   - 历史数据：历史数据分析
   - 预警管理：预警配置和查看
   - 场景分析：模拟不同市场情况下的风险

## 3. 数据模型

### 3.1 核心数据表
1. **OptionData**
   - 存储期权市场数据
   - 包含：期权价格、成交量、隐含波动率、Greeks等

2. **RiskIndicator**
   - 存储计算的风险指标
   - 包含：波动率指数、偏度、看跌看涨比率等

3. **Alert**
   - 存储生成的预警信息
   - 包含：预警类型、消息、触发条件等

4. **StrikeDeviationMonitor**
   - 监控期权执行价偏离情况
   - 包含：偏离百分比、成交量变化等

### 3.2 配置相关表
1. **AlertThreshold**
   - 存储预警阈值设置
   - 支持不同时间周期的阈值配置

2. **SystemSetting**
   - 存储系统配置
   - 支持多种数据类型

3. **ApiCredential**
   - 存储交易所API凭证

## 4. 主要功能

### 4.1 风险监控
- 实时监控多个风险指标
- 支持多个时间周期（15分钟到30天）
- 自定义预警阈值
- 多级预警机制

### 4.2 数据分析
- 历史数据分析
- 期权执行价偏离分析
- 成交量分析
- 场景分析

### 4.3 系统管理
- API凭证管理
- 系统设置管理
- 多语言支持（英文、中文）

## 5. 风险指标

### 5.1 核心指标
1. **Volaxivity**
   - 自定义波动率指数
   - 反映市场波动性

2. **Volatility Skew**
   - 波动率偏度
   - 反映市场情绪

3. **Put-Call Ratio**
   - 看跌看涨比率
   - 反映市场方向性预期

4. **Reflexivity Indicator**
   - 市场反馈循环强度
   - 反映市场自我强化程度

### 5.2 期权 Greeks
- Delta：价格对标的资产价格变化的敏感度
- Gamma：Delta对标的资产价格变化的敏感度
- Theta：时间衰减
- Vega：对波动率变化的敏感度

## 6. 配置说明

### 6.1 系统配置
- 数据保留期：30天
- 期权执行价范围：当前价格±10%
- 支持的时间周期：15分钟、1小时、4小时、1天、7天、30天

### 6.2 预警阈值
每个指标都有三个级别的阈值：
- Attention：需要关注
- Warning：需要警惕
- Severe：严重警告

## 7. API 接口

### 7.1 主要端点
- `/dashboard`: 仪表盘数据
- `/alerts`: 预警管理
- `/historical`: 历史数据
- `/scenario`: 场景分析
- `/settings`: 系统设置
- `/deviation_monitor`: 执行价偏离监控

### 7.2 数据接口
- `/api/dashboard/data`: 获取仪表盘数据
- `/api/historical/data`: 获取历史数据
- `/api/alerts/acknowledge`: 确认预警
- `/api/deviation/data`: 获取偏离数据

## 8. 部署要求

### 8.1 环境要求
- Python >= 3.11
- PostgreSQL 数据库
- 足够的存储空间用于历史数据

### 8.2 依赖包
主要依赖包括：
- Flask >= 3.1.0
- SQLAlchemy >= 2.0.40
- APScheduler >= 3.11.0
- CCXT >= 4.4.78
- 其他依赖见 pyproject.toml

## 9. 安全考虑

1. **API 安全**
   - API 凭证加密存储
   - 定期轮换机制

2. **数据安全**
   - 数据定期清理
   - 敏感信息加密

3. **访问控制**
   - 会话管理
   - 错误处理

## 10. 监控和维护

1. **日志系统**
   - 详细的日志记录
   - 错误追踪

2. **健康检查**
   - `/health` 端点
   - 系统状态监控

3. **数据维护**
   - 自动数据清理
   - 数据完整性检查

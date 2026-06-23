# 🌍 国际热点新闻微信推送系统

> 全自动抓取国际新闻 → 五维热度评分 → 微信推送
>
> 每天 3 次推送，每次 20 条，覆盖 9 大地理区域 + 10 大新闻领域
>
> **完全免费 · 云端运行 · 小白友好**

---

## 📋 目录

1. [功能概述](#功能概述)
2. [你需要准备的（3个免费账号）](#你需要准备的)
3. [第一步：注册 NewsAPI](#第一步注册-newsapi)
4. [第二步：注册 PushPlus 并绑定微信](#第二步注册-pushplus-并绑定微信)
5. [第三步：注册 GitHub 并创建仓库](#第三步注册-github-并创建仓库)
6. [第四步：上传代码到 GitHub](#第四步上传代码到-github)
7. [第五步：配置 Secrets](#第五步配置-secrets)
8. [第六步：启动运行](#第六步启动运行)
9. [常见问题](#常见问题)

---

## 功能概述

| 特性 | 说明 |
|------|------|
| 🔄 自动推送 | 每天 6:00 / 12:00 / 20:00 自动推送 |
| 📰 新闻数量 | 每次 20 条，每天共 60 条精选 |
| 🌍 区域覆盖 | 9 大地理区域全覆盖 |
| 🏷️ 领域分类 | 10 大新闻领域（地缘/军武/经贸/科创/生态/外交/民生/社运/治安/人文）|
| 📊 热度评分 | 五维加权公式 + 降噪修正 + 归一化，0-100 标准分 |
| 📱 推送渠道 | PushPlus → 你的微信 |

### 推送消息格式

每条新闻包含：
1. 序号 + 标题
2. 热度数值（0-100 分）
3. 中文摘要（100-150 字）
4. 3-5 个关键词

### 热度分级

```
🔥🔥 80-100分：顶级全球热点（战争、大国冲突、全球危机）
🔥   60-80分：高热度（区域冲突、大国峰会、跨国政策）
📌  30-60分：中等热度（常规经贸、外事访问）
📎   0-30分：低热度（小国地方民生）
```

---

## 你需要准备的

> ⚠️ 全部免费，大约需要 15 分钟

| 序号 | 事项 | 链接 | 获取什么 |
|------|------|------|---------|
| 1 | 注册 NewsAPI | [newsapi.org](https://newsapi.org/register) | API Key |
| 2 | 注册 PushPlus | [pushplus.plus](https://www.pushplus.plus/) | Token（微信扫码）|
| 3 | 注册 GitHub | [github.com](https://github.com/signup) | 代码托管 & 自动运行 |

---

## 第一步：注册 NewsAPI

> NewsAPI 是全球最大的新闻 API 聚合服务，免费版每天 100 次请求

### 操作步骤：

1. 打开浏览器，访问 **https://newsapi.org/register**
2. 填写注册信息：
   - **Email**: 你的邮箱（QQ邮箱即可）
   - **Password**: 设置密码（8位以上，记下来！）
   - **First Name / Last Name**: 填你的名字（英文或拼音）
   - 勾选 "I'm not a robot"（人机验证）
3. 点击 **「Submit」** 按钮
4. 去你的邮箱 **查看验证邮件**，点击邮件里的验证链接
5. 登录后，你会看到 **API Key** 页面

> 📋 **复制你的 API Key**（一串类似 `a1b2c3d4e5...` 的字符）
>
> 先粘贴到记事本保存，后面要用！

---

## 第二步：注册 PushPlus 并绑定微信

> PushPlus 是一个免费的微信消息推送平台，每天 200 条额度，我们用 3 条

### 操作步骤：

1. 打开浏览器，访问 **https://www.pushplus.plus/**
2. 点击右上角 **「登录/注册」**
3. 用微信扫码登录即可（无需注册账号）
4. 登录后，进入首页
5. 你会看到 **一对多推送** 或 **一对一旁路推送**
   - 建议使用 **「一对一旁路推送」**，直接关注公众号即可接收
6. 点击 **「发送消息」** → 在页面上方会看到你的 **Token**

> 📋 **复制你的 Token**（一串 32 位字符）
>
> 粘贴到记事本保存，后面要用！

### 测试推送：

在 PushPlus 网页上，点击 **「发送消息」**，输入任意内容，点击发送。
你应该能在微信的 **PushPlus 公众号** 里收到消息。
**如果收不到**：确认你已经关注了 PushPlus 公众号。

---

## 第三步：注册 GitHub 并创建仓库

> GitHub 是全球最大的代码托管平台，提供免费自动化运行功能（GitHub Actions）

### 3.1 注册 GitHub 账号

1. 打开 **https://github.com/signup**
2. 填写：
   - **Email**: 你的邮箱
   - **Password**: 设置密码
   - **Username**: 设置用户名（英文 + 数字，如 `zhangsan-news`）
3. 完成人机验证
4. 查收验证邮件，输入验证码
5. 完成注册

### 3.2 创建新仓库

1. 登录后，点击右上角 **「+」** → **「New repository」**
2. 填写：
   - **Repository name**: `international-news-pusher`
   - **Description**: 选填，如 "国际热点新闻推送"
   - **类型**: 选择 **「Public」**（公开仓库免费）
   - ❌ 不要勾选 "Add a README file"
   - ❌ 不要勾选 ".gitignore"
3. 点击底部绿色的 **「Create repository」** 按钮
4. 你会看到一个页面显示 "…or create a new repository on the command line"
   - **把这个页面的 URL 复制下来**，类似 `https://github.com/你的用户名/international-news-pusher.git`

---

## 第四步：上传代码到 GitHub

> ⚠️ 这一步我来帮你做。你需要先告诉我你的 GitHub 用户名，然后：

### 你需要在你的电脑上先下载代码：

**方式一：直接下载（推荐小白）**

我会把全部代码打包给你，你只需要：
1. 下载代码压缩包
2. 登录 GitHub
3. 在你的仓库页面，点击 **「Add file」→「Upload files」**
4. 把所有文件拖进去
5. 点击底部绿色的 **「Commit changes」**

**方式二：使用 Git 命令（稍进阶）**

打开命令行，执行：
```bash
git clone https://github.com/你的用户名/international-news-pusher.git
# 把代码文件复制到该目录
git add .
git commit -m "初始化项目"
git push origin main
```

---

## 第五步：配置 Secrets（最关键的步骤）

> 把 NewsAPI Key 和 PushPlus Token 存到 GitHub，程序自动读取

### 操作步骤：

1. 打开你的 GitHub 仓库页面
2. 点击顶部菜单 **「Settings」**
3. 左侧菜单找到 **「Secrets and variables」→「Actions」**
4. 点击 **「New repository secret」** 按钮

### 5.1 添加 NEWSAPI_KEY

1. **Name** 填写：`NEWSAPI_KEY`（注意大小写！）
2. **Secret** 填写：你第一步获取的 NewsAPI Key
3. 点击 **「Add secret」**

### 5.2 添加 PUSHPLUS_TOKEN

1. 再次点击 **「New repository secret」**
2. **Name** 填写：`PUSHPLUS_TOKEN`（注意大小写！）
3. **Secret** 填写：你第二步获取的 PushPlus Token
4. 点击 **「Add secret」**

完成后，你应该看到 2 个 Secrets：
```
NEWSAPI_KEY      ******
PUSHPLUS_TOKEN   ******
```

---

## 第六步：启动运行

### 6.1 手动测试

1. 在 GitHub 仓库页面，点击顶部菜单 **「Actions」**
2. 左侧找到 **「🌍 国际热点新闻推送」**
3. 点击右侧 **「Run workflow」** 下拉按钮
4. 选择 `auto`，点击绿色的 **「Run workflow」**
5. 等待约 2-3 分钟，你应该能在微信收到第一条推送

### 6.2 定时自动运行

不需要做任何操作！配置好之后，系统会自动在：
- 北京时间 **06:00** 推送晨间速递
- 北京时间 **12:00** 推送午间速递
- 北京时间 **20:00** 推送晚间速递

> ⚠️ GitHub Actions 定时触发可能有 5-30 分钟延迟，这是正常的，不影响使用。

### 6.3 检查运行状态

1. 进入 **「Actions」** 页面
2. 查看最近的运行记录
3. 绿色 ✅ = 成功 / 红色 ❌ = 失败
4. 点击某次运行，可以看到详细日志

---

## 常见问题

### Q1: 没收到推送？
- 确认 PushPlus 公众号已关注（在微信搜索 PushPlus）
- 确认 `PUSHPLUS_TOKEN` 配置正确（注意是 PushPlus 不是 PushPlus）
- 去 GitHub Actions 日志查看报错信息

### Q2: 新闻太少或没新闻？
- 免费 NewsAPI 每天 100 次请求，如果查询太频繁会耗尽
- 检查 `NEWSAPI_KEY` 是否配置正确
- 某些时段国际新闻确实较少，系统会自动扩大搜索范围

### Q3: 推送内容重复？
- 系统会自动维护 `sent_news.json` 去重记录
- 如果 GitHub Actions 提交失败，去重会受影响
- 可以在 Actions 页面手动触发一次，让它重新同步

### Q4: 热度分看起来不对？
- 完整五维热度公式需要商业级数据API支撑
- 当前版本在免费数据范围内做到最优实现
- 核心公式逻辑完整保留（传播体量/互动深度/权威背书/跨国辐射/时效衰减）
- 部分指标使用了合理估算

### Q5: 能不能手动重新推送？
- 进入 GitHub → Actions → 点击 workflow → Run workflow → 选择时段
- 系统会自动去重，不会重复推送已发过的新闻

### Q6: 如何修改推送时间？
- 编辑 `.github/workflows/push.yml`
- 修改 `cron` 表达式（UTC时间 = 北京时间 - 8 小时）

### Q7: 完全免费吗？
- GitHub Actions：免费（每月 2000 分钟，我们用不到 150 分钟）
- NewsAPI：免费（每天 100 次请求）
- PushPlus：免费（每天 200 条消息）
- **总计：$0 / 月 ✅**

---

## 推送消息示例

```
🌍 国际热点新闻速递
━━━━━━━━━━━━━━
📅 2026年6月23日 | ⏰ 午间速递 | 第 2/3 次推送
━━━━━━━━━━━━━━

1. 🔥🔥 [87.5] 以黎边境冲突持续升级，安理会紧急磋商
   📝 据Reuters报道，以色列与黎巴嫩真主党在边境地区发生新一轮交火，
   造成双方数十人伤亡。联合国安理会于当地时间22日召开紧急闭门会议...（共136字）
   🏷️ #地缘 #军武 #中东与北非 #安理会 #油价
   📍 中东与北非 | 地缘·军武

2. 🔥 [76.2] 美联储维持利率不变，全球市场反应分化
   📝 据BBC报道，美联储在6月议息会议后宣布维持联邦基金利率不变，
   但暗示年内可能降息一次。美股三大指数收涨...（共128字）
   🏷️ #经贸 #北美 #货币政策 #美联储
   📍 北美 | 经贸

...（至第 20 条）

━━━━━━━━━━━━━━
📊 本次覆盖统计
━━━━━━━━━━━━━━
📍 地理区域：9/9 全覆盖 ✅
🏷️ 新闻领域：10/10 全覆盖 ✅
📈 热度区间：62.3 - 91.7 | 平均：74.2
⏰ 下次推送：今天 20:00（北京时间）
```

---

## 项目结构

```
international-news-pusher/
├── .github/workflows/
│   └── push.yml                    # 定时触发配置
├── src/
│   ├── main.py                     # 主入口
│   ├── config.py                    # 配置管理
│   ├── news_fetcher.py              # 多源新闻抓取
│   ├── domain_classifier.py         # 10大领域分类
│   ├── region_classifier.py         # 9大区域分类
│   ├── hotness_scorer.py            # 五维热度评分
│   ├── deduplicator.py              # 去重引擎
│   ├── article_generator.py         # 摘要生成 + 关键词
│   └── push_notifier.py             # PushPlus推送
├── data/
│   └── sent_news.json               # 已推送记录
├── requirements.txt
└── README.md
```

---

> 🎉 恭喜！按照以上步骤操作，你就可以每天在微信上收到精选的国际热点新闻了！
>
> 如有问题，请在 GitHub Issues 中提出。

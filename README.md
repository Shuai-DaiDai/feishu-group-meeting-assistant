# 飞书组会助手 Skill 使用说明

> 仓库/目录定位：本 README 同时面向 **人类使用者** 和 **接入该 Skill 的 Agent**。

---

## 一、人类阅读（Owner Guide）

### 你能获得什么（先看收益）
- 输入 `@某人` 或姓名，快速查多人共同空闲时间
- 自动创建组会并写入参与人
- 自动回读校验（避免“创建成功但参与人没写进去”）
- 可清理测试会邀，保持日历干净

#### 示例场景（张三 / 李四）
> 你：帮我看下我、@张三、@李四这周三 16:00 后有没有共同 1 小时空闲？有的话直接给我 2 个候选时间。  
> Agent：查到了，共同空闲有 16:00-17:00、18:00-23:59。要不要我直接发起“组会”并邀请 @张三、@李四？

Agent 会先返回可用时段，再按你的确认创建会议并写入参与人。

### 你需要完成什么（一次性成本）
按顺序完成下面步骤：

### 推荐调用方法（避免走弯路）
1. 一次授权拿齐 scope（含 `offline_access` + calendar + contact）。
2. 先按“ID来源优先级”解析 `@姓名 -> user_id/open_id`：
   - 优先读取消息中的结构化 @mention 实体
   - 其次邮箱换 ID
   - 再次联系人目录检索
   - 最后事件组织者反查
3. 每次结果需附“本次 ID 来源证据”。
4. 不把“订阅日历列表”当主路径（仅作 fallback）。
5. 创建会议时参与人只用 `attendees[{type,user_id}]`。
6. 每次创建后必须回读 `event + attendees list` 校验。

### 1) 在飞书开放平台开通权限
至少需要：
- `calendar:calendar`
- `calendar:calendar.event:read`
- `calendar:calendar.event:create`
- `calendar:calendar.event:update`
- `contact:user.employee_id:readonly`（按姓名/@XXX 映射 user_id 需要）

建议同时开通：
- `contact:user.base:readonly`（按姓名检索组织内用户更稳定）

可选（推荐，减少重复手动授权）：
- `offline_access`

> ⚠️ 关键：联系人相关权限（`contact:*`）请将可用范围配置为**全员可见范围**（或至少覆盖你要发起组会的人），否则 @XXX / 姓名检索会缺人。

### 2) 配置 OAuth 回调地址（默认推荐本机 localhost）
如果你是本机部署 Agent，推荐直接使用：
- `http://127.0.0.1:8787/feishu/oauth/callback`

如果是服务器部署，再使用你自己的公网地址：
- `https://<your-domain>/feishu/oauth/callback`
- 或 `http://<your-server-ip>:8787/feishu/oauth/callback`

> ⚠️ 回调必须指向你自己能接收 `code` 的服务。

### 3) 首次授权（必须）
启动回调服务后，打开授权链接完成一次授权，拿到 `code`。

#### localhost 回调的常见现象（重要）
当你把回调地址配置为 `http://127.0.0.1:3000/callback`，但本机没有对应服务监听时，浏览器可能显示“无法连接服务器”。
这通常不代表授权失败：
- 只要地址栏里出现 `code=...`，授权往往已经成功。
- 请直接复制**完整地址栏 URL**给 Agent（不要只发截图），Agent 可从中提取 code 完成 token 兑换。

### 4) 后续维护
- 如果没开 `offline_access`：token 过期后需重新授权。
- 如果开了 `offline_access`：脚本可用 `refresh_token` 自动续期。

---

## 二、Agent 阅读（Agent Runbook）

### 目标
实现飞书组会场景闭环：
1. 查多人忙闲交集
2. 创建会议并写入参与人
3. 回读校验写入结果
4. 必要时清理重复测试会邀

### 必须遵守

1. **参与人字段格式固定使用**：
```json
"attendees": [
  {"type":"user","user_id":"..."}
]
```
不要使用 `attendee_id/attendee_id_type`。

2. **忙闲查询必须分页**：处理 `has_more/page_token`，否则会漏事件。

3. **写后即验**：
- `GET event?need_attendee=true`
- `GET attendees list`

4. **Token 处理**：
- 优先用 `scripts/feishu-token-manager.py get`
- 无可用 token 时提示用户授权，并执行 `exchange --code`

5. **指导人类时要明确给清单**（不能只丢链接）：
- 要开哪些权限
- 回调地址填什么
- 首次授权怎么做
- 成功后要回传什么（`code=...` 或“已授权”）

---

## 三、快速操作步骤

### A. 启动 OAuth 回调服务
```bash
python3 skills/feishu-calendar-assistant/scripts/feishu-oauth-callback.py
```
默认监听 `0.0.0.0:8787`，请确保：
- 飞书平台配置的回调地址与实际地址一致
- 外网可访问你的回调服务（如需公网授权）

健康检查（本机）：
```bash
curl http://127.0.0.1:8787/health
```

### B. 用授权码初始化 token
```bash
python3 skills/feishu-calendar-assistant/scripts/feishu-token-manager.py exchange --code <CODE>
```

### C. 获取可用 access_token（自动刷新）
```bash
python3 skills/feishu-calendar-assistant/scripts/feishu-token-manager.py get
```

### D. 查询两人交集空闲（推荐：freebusy/batch）
```bash
python3 skills/feishu-calendar-assistant/scripts/feishu-freebusy-batch.py \
  --token "<ACCESS_TOKEN>" \
  --user-id-type user_id \
  --user-id "<USER_ID_A>" \
  --user-id "<USER_ID_B>" \
  --time-min "2026-03-03T19:30:00+08:00" \
  --time-max "2026-03-03T23:59:00+08:00" \
  --min-minutes 30
```

### D-备用. 用事件列表反推（fallback）
```bash
python3 skills/feishu-calendar-assistant/scripts/feishu-freebusy-overlap.py \
  --token "<ACCESS_TOKEN>" \
  --calendar-a "<CALENDAR_ID_A>" \
  --calendar-b "<CALENDAR_ID_B>" \
  --date 2026-03-04 \
  --start 16:00 \
  --end 23:59 \
  --min-minutes 60
```

---

## 四、目录结构

- `skills/feishu-calendar-assistant/`：Skill 源码目录
- `skills/feishu-calendar-assistant.skill`：打包产物


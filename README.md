# S2-IAM-024 会员经理角色越权回归测试

针对角色 `member_manager`（会员经理，site 级）的权限回归用例集。
相关业务代码尚未合并，本包按工单给定的角色矩阵**自建接口桩**（`stubapp/`）：
`@require_permission` 依赖、探针 `/__probe__/{code}` 与 `/__probe__/{code}/records`、
`role_matrix.yml` 种子。真实模块合并后，只需把 `stubapp.main.app` 换成真实 `app`，
用例与期望表一行不用改。

## 一条命令复核

```bash
python verify_3007.py            # 全部 AC，含变异测试
python verify_3007.py --no-mutate   # 只跑用例与结构检查
python -m pytest -q --junitxml=report/junit.xml   # 只跑用例
```

环境：Python 3.11+，`fastapi` `httpx` `pydantic` `pyyaml` `pytest`。
`pip install -r requirements.txt` 即可（Windows / Ubuntu 均验证过）。

## 测试数据（全部虚构）

- 集团 `org-fake-001`；会所 `site-a`、`site-b`
- 被测员工「会员经理测试员（虚构）」`staff-mm-001`，**只在会所 A** 拥有 `member_manager`
- 会员记录 9 条：会所 A 本人负责 3 条、会所 A 同事负责 3 条、会所 B 3 条
- 姓名用「会员OWN01（虚构）」式代号，手机号 `1380000xxxx`，邮箱 `@example.invalid`

## 允许项（期望 200）

| # | 权限点 | 数据范围 |
|---|---|---|
| 1 | crm.member.read | site |
| 2 | event.read | site |
| 3 | space.booking.read | site |
| 4 | crm.member.write | self |
| 5 | crm.followup.write | self |
| 6 | crm.contact.read_sensitive | self |
| 7 | opp.demand.read | self |
| 8 | opp.demand.write | self |
| 9 | kb.article.read | org |
| 10 | ai.assistant.use | self |

## 禁止项（期望 403）

crm.export、opp.match.write、opp.assign、lead.prospect.read、lead.assign、
front.visitor.write、event.manage、content.publish、kb.article.publish、
dash.exec.read、iam.user.read、sys.config.manage。

## 用例清单（40 条）

| 用例 | 条数 | 判什么 |
|---|---|---|
| `test_allow_codes_return_200` | 10 | 每个允许项 200，且 scope 与矩阵一致 |
| `test_deny_codes_return_403` | 12 | 每个禁止项 403，回包 detail.code 对应 |
| `test_member_read_records_site_scope` | 1 | 会所 A 会员 6 条（mem-001..006） |
| `test_member_write_records_self_only` | 1 | 本人负责 3 条（mem-001..003） |
| `test_patch_peer_member_returns_404` | 1 | 改同事记录 404（不泄露存在性） |
| `test_patch_own_member_change_owner_returns_403` | 1 | 本人记录改 owner_id 403 |
| `test_patch_own_member_level_returns_200` | 1 | 正对照：本人记录改 level 200 |
| `test_contact_sensitive_peer_returns_404` | 1 | 读同事敏感字段 404 |
| `test_contact_sensitive_own_returns_200` | 1 | 正对照：读本人敏感字段 200 |
| `test_cross_site_all_allow_denied` | 10 | 切到会所 B，全部允许项 403 |
| `test_matrix_declares_exactly_this_role` | 1 | 矩阵恰好 10 项，禁止项未被授予 |

失败信息统一打印「角色 / 权限点 / 期望 / 实际 / 响应体」，例如：

```
角色=member_manager 权限点=crm.export 期望=403 实际=200 响应={"code":"crm.export",...}
```

## 判定顺序（写死在 `stubapp/matrix.py`）

1. **站点校验**：请求上下文 `site_id` 必须在该员工 `sites` 内，否则一律 403；
2. **权限校验**：`code` 未授予当前角色 -> 403；
3. **数据范围**：`site` 看本站全部、`self` 只看 `owner_id` 本人、`org` 看全组织；
   写接口上体现为「同事记录 404 / 改归属 403 / 改其他字段 200」。

## 变异测试（证明用例抓得住错）

`python tools/mutate_3007.py` 把桩改坏 7 处，每处都必须让 pytest 变红：

1. 矩阵错误授予 `crm.export`
2. `crm.member.read` 范围 site -> self
3. 删掉站点校验（跨会所不再 403）
4. PATCH 不再按范围隐藏同事记录
5. 允许把 `owner_id` 改成别人
6. 敏感字段接口不校验归属
7. 矩阵漏掉 `crm.member.write`

## 集成点

| 桩里的东西 | 真实系统对应 | 接法 |
|---|---|---|
| `stubapp.main.app` | 主应用 FastAPI 实例 | 替换 import，路由前缀保持一致 |
| `stubapp.matrix.MATRIX` | S2-IAM-017 有效权限计算 | 换成 `compute_permissions(staff)` |
| `__probe__` 路由 | 平台权限探针 | 生产环境应关闭或加管理员守卫 |
| `stubapp.store` | PG 夹具 | 换成 `testcontainers` 或事务回滚的 session |

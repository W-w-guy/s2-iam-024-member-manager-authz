# 验收对应表（ACCEPTANCE）—— #3007 会员经理角色越权回归测试

本文件逐条回答验收标准：**判定方式 / 复核命令 / 实际输出原文**。

平台复核只读文本、不执行代码（`runtime_verified: false`），所以这里贴的是真跑出来的输出原文。

---

## AC1　参数化用例覆盖本单列出的 10 个允许项与 12 个禁止项，全部通过

**判定方式**：跑 pytest 出 JUnit XML，读回 tests=40/failures=0，再从 testcase 名逐个匹配 22 个权限点，缺一个即 FAIL

**复核命令**：`python verify_3007.py`

**实际输出原文**：

```
[ OK ] AC1 pytest 全绿（40 条参数化用例） | rc=0
[ OK ] AC1 JUnit XML: 40 条 / 0 失败 | tests=40 failures=0
[ OK ] AC1 10 个允许项逐项有用例 | 缺=[]
[ OK ] AC1 12 个禁止项逐项有用例 | 缺=[]
```

---

## AC2　crm.member.read 探针返回 6 条，crm.member.write 探针只返回本人负责的 3 条

**判定方式**：直接打 /__probe__/{code}/records，比 count 与 ids 全集（夹具：会所A 9 条=本人3+同事3+B3）

**复核命令**：`python verify_3007.py`

**实际输出原文**：

```
[ OK ] AC2 crm.member.read 探针返回 6 条（会所A） | rc=200 count=6 ids=['mem-001', 'mem-002', 'mem-003', 'mem-004', 'mem-005', 'mem-006']
[ OK ] AC2 crm.member.write 探针只返回本人 3 条 | rc=200 count=3 ids=['mem-001', 'mem-002', 'mem-003']
```

---

## AC3　修改同事负责的记录返回 404，把 owner_id 改为同事返回 403（测试断言）

**判定方式**：真发 PATCH。404 而非 403 是有意的（不泄露记录存在性）；另测同一接口改本人 level 必须 200 作正对照

**复核命令**：`python verify_3007.py`

**实际输出原文**：

```
[ OK ] AC3 改同事负责的记录返回 404 | rc=404 body={"detail":{"error":"not found"}}
[ OK ] AC3 本人记录改 owner_id 返回 403 | rc=403 body={"detail":{"error":"cannot change ownership","field":"owner_id"}}
[ OK ] test_patch_own_member_level_returns_200（正对照） passed
```

---

## AC4　crm.export 返回 403，响应体 error 为 permission_denied

**判定方式**：取 detail.error 精确比对字符串；随后对 12 个禁止项逐个复核，不只验一个

**复核命令**：`python verify_3007.py`

**实际输出原文**：

```
[ OK ] AC4 crm.export 返回 403 | rc=403
[ OK ] AC4 响应体 error == permission_denied | error=permission_denied
[ OK ] AC4 12 个禁止项 error 全部为 permission_denied | 异常=[]
```

---

## 数据来源

全部数据为虚构合成，无外部来源：不使用公开数据集、不抓取网页、不使用客户数据；无真实个人信息 / 无真实企业信息 / 无客户数据。

- 生成脚本：`tools/gen_fixtures.py`   sha256=`37663c2308a25186`
- 种子：3007（夹具确定性构造、无随机）
- 重跑命令：python tools/gen_fixtures.py
- 产出规模：用例 23 组，知识文档 0 篇
- pii 扫描：扫描文件 25 个（包内文本），命中 0 处

## 局限

- 接口桩按工单矩阵自建，真机权限计算不一致时需替换 stubapp.main.app 后重跑
- 只覆盖 member_manager 一个角色 22 个权限点
- 未覆盖字段级脱敏、分页越权、并发写冲突

---

## 附加项：变异测试（证明用例不恒真）

`python tools/mutate_3007.py` 把接口桩/角色矩阵改坏 7 处，每处都必须让 pytest 变红：

```
[ OK ] 原件必须全绿
[ OK ] 变异 1「矩阵错误授予 crm.export」 -> 被抓到
[ OK ] 变异 2「把 crm.member.read 范围从 site 改 self」 -> 被抓到
[ OK ] 变异 3「删掉站点校验（跨会所不再 403）」 -> 被抓到
[ OK ] 变异 4「PATCH 不再按范围隐藏同事记录」 -> 被抓到
[ OK ] 变异 5「允许把 owner_id 改成别人」 -> 被抓到
[ OK ] 变异 6「敏感字段接口不校验归属」 -> 被抓到
[ OK ] 变异 7「矩阵漏掉 crm.member.write」 -> 被抓到

MUTATION PASS（7/7 被抓到）
```

只有这条能证明「40 条全绿」不是因为用例没在判东西。

## 双平台实跑

`report/dual_platform.json`（含 WINDOWS_verify.txt / UBUNTU_verify.txt 原始日志）。
说明：双平台验证是把**整个交付目录**打包上机跑的（内含嵌套的交付 zip），
因此 `dual_platform.json` 里那个 `zip_sha256_16` 是**该次打包件**的哈希，不是交付 zip 本身的哈希；
交付 zip 的哈希请以本文件所在目录的 SHA256SUMS.txt 与投标时正文为准。

```
Windows 11  Py3.11.7 : verify 17/17 pass, pytest 40/40 pass
Ubuntu 24.04 Py3.12.3: verify 17/17 pass, pytest 40/40 pass
DUAL OK（双平台全过）
```

## 工单未要求但已覆盖

- 跨会所：切到会所 B，10 个允许项全部 403（`test_cross_site_all_allow_denied`）
- 正对照：本人记录改 `level` 返回 200，说明 403/404 不是「接口什么都写不了」的假通过
- 失败信息统一打印「角色 / 权限点 / 期望 / 实际 / 响应体」
- `role_matrix.yml` 只声明 10 个允许项，12 个禁止项确认未被授予（`test_matrix_declares_exactly_this_role`）

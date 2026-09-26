# TeaWither-01 · 茶萎凋台账

Django 5 + PostgreSQL 服务端渲染应用：Templates + HTMX + 自定义 CSS，无 Vue/React SPA。

## 技术栈

- Django 5、PostgreSQL
- Session 登录
- HTMX（CDN）局部刷新列表
- Docker Compose：`web` + `db`

## 端口与数据库

| 服务 | 端口 |
|------|------|
| Web  | **4100** |
| Postgres | **5440**（容器内 5432） |

数据库账号：`teawither` / `teawither` / 库名 `teawither`

## 快速启动

```bash
cd TeaWither/TeaWither-01
docker compose up --build -d
```

浏览器打开：http://localhost:4100

演示账号：

- `admin` / `123456`（超级用户，角色：**主管**）
- `witherer` / `123456`（角色：**萎凋工**）

容器启动时会自动：`migrate` → `seed_data` → `collectstatic` → `gunicorn`

## 角色矩阵

所有页面均需登录（未登录一律跳转登录页，不允许绕过）。登录后的操作权限：

| 操作 | 萎凋工（witherer） | 主管（admin） |
|------|:---:|:---:|
| 查看首页 / 茶园 / 槽 / 批次列表 | ✅ | ✅ |
| 新建、编辑茶园 | ✅ | ✅ |
| 新建、编辑萎凋槽 | ✅ | ✅ |
| 新建、编辑萎凋批次 | ✅ | ✅ |
| 删除萎凋批次 | ❌ 拒绝并中文提示 | ✅ |
| 删除萎凋槽 | ❌ 拒绝并中文提示 | ✅ 仅当槽下无批次 |
| 删除茶园 | ❌ 拒绝并中文提示 | ✅ 仅当园下无槽 |

角色由 Django 组实现：`主管` 组拥有三个模型的全部权限（含 `delete_*`），
`萎凋工` 组只有 `add/change/view`，没有任何 `delete` 权限。
三个删除入口（茶园 / 萎凋槽 / 批次）在后端共用同一套校验：
先查登录、再查 `delete` 权限、最后查子级数据，规则完全一致。

**删除规则（前后端一致，后端强制）**：

1. 萎凋工访问任一删除入口（确认页或直接 POST）都会被拒绝，并收到中文说明；
   列表页同时不渲染删除按钮（仅隐藏按钮不算后端放行，后端仍会拦截）。
2. 删除茶园时若其下仍有萎凋槽，**必须先拒绝**，提示先删除全部槽位；
   无槽茶园可由主管正常删除。
3. 删除萎凋槽时若其下仍有萎凋批次，**同样拒绝**（不允许级联删除批次），
   提示先删除全部批次；无批次槽位可由主管正常删除。
4. 批次无子级，主管可直接删除。
5. 首页「茶园数 / 槽数 / 批次数」与对应列表行数同源统计，删除成功后误差为 0。

## 本地开发（可选）

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
# 确保本机 Postgres 监听 5440，或先 docker compose up -d db
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5440
python manage.py migrate
python manage.py seed_data
python manage.py runserver 0.0.0.0:4100
```

## 业务模型

1. **Garden（茶园）**：`name`、`altitudeBand`、`notes`
2. **Trough（萎凋槽）**：归属茶园、`troughCode`、`cultivar`、`loadKg`、状态 `loading|withering|ready`；同一茶园内槽位编号唯一
3. **WitherBatch（萎凋批次）**：归属槽位、`startedAt`、`targetMoisture`、`actualMoisture`（可空）、`rollGrade`

**业务规则**：将槽位状态设为 `ready`（可下槽）时，若最新批次的 `actualMoisture` 为空或大于 40，抛出中文 `ValidationError`。

## 种子数据

```bash
python manage.py seed_data
```

幂等：保证账号与角色组存在；已有茶园则跳过样例数据。
样例为两个茶园：**云雾岭一号园**（含 4 个槽位与批次）与
**竹影台二号园**（无任何槽位），用于演示「有槽茶园不可删、无槽茶园可删」。
亦可在环境变量 `TEAWITHER_AUTO_SEED=1` 时于 `post_migrate` 自动播种。

## 目录结构

```
TeaWither-01/
  manage.py
  requirements.txt
  Dockerfile
  entrypoint.sh
  docker-compose.yml
  config/           # 项目配置
  apps/gardens/     # 模型、视图、种子命令
  templates/        # Django 模板
  static/css/       # 自定义样式（茶绿色顶栏）
```

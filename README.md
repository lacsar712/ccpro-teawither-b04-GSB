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

演示账号（密码均为 `123456`）：

- `admin`：超级用户，权限等同主管
- `supervisor`：**主管**，可新建/编辑/删除
- `witherer`：**萎凋工**，可新建/编辑，不可删除

### 角色权限矩阵

| 操作 | 萎凋工 `witherer` | 主管 `supervisor` / `admin` |
|------|:---:|:---:|
| 查看 茶园 / 萎凋槽 / 萎凋批次 | ✔ | ✔ |
| 新建 茶园 / 萎凋槽 / 萎凋批次 | ✔ | ✔ |
| 编辑 茶园 / 萎凋槽 / 萎凋批次 | ✔ | ✔ |
| 删除 茶园 / 萎凋槽 / 萎凋批次 | ✘（后端 403 中文页） | ✔ |

权限由数据库角色组（`主管` / `萎凋工`，见迁移 `0002_role_groups`）+ Django 模型权限承载，
删除类视图统一经 `DeletePermissionRequiredMixin` 校验：**仅隐藏前端按钮不算数，
萎凋工直接访问删除 URL（GET 确认页或 POST 提交）同样被后端拒绝**。未登录访问一律跳转登录页。

### 删除级联约束（后端强制，三个删除入口规则一致）

| 删除对象 | 约束 |
|----------|------|
| 茶园 | 其下**仍有萎凋槽时拒绝删除**，提示先处理全部槽位 |
| 萎凋槽 | 其下**仍有萎凋批次时拒绝删除**，须先删除该槽全部批次（批次删除不连带删槽） |
| 萎凋批次 | 末级记录，主管可直接删除 |

确认页在存在下级记录时不显示提交按钮，且 POST 由同一判定方法再次拦截，前后端一致。
删除成功后首页「茶园/萎凋槽」计数与对应列表行数一致。

容器启动时会自动：`migrate` → `seed_data` → `collectstatic` → `gunicorn`

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

幂等：已有茶园则只保证账号与角色存在。亦可在环境变量 `TEAWITHER_AUTO_SEED=1` 时于 `post_migrate` 自动播种。
样例为**一园有槽、一园无槽**：云雾岭一号园有 1 个可下槽槽位（带批次，用于验证删园被拒）；
竹影台二号园无槽位（用于验证主管删园成功）。

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

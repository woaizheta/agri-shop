# AGENTS.md — 农资店管理系统开发总纲

## 项目身份

**项目名称**：丰收农资店管理系统（AgriShop）

**定位**：面向乡镇农资零售店的进销存 + 合规管理 Web 应用。覆盖种子、农药、化肥、农膜、饲料、农具等品类，核心解决《农药管理条例》要求的农药批次追溯、实名销售、电子台账等合规需求。

**目标用户**：农资店经营者（店主）、店员（收银/仓管）、财务人员。单店单机使用，不需要多店铺/多用户并发架构。

---

## 技术栈决策

| 层 | 技术 | 版本 | 选型理由 |
|---|------|------|---------|
| 后端框架 | FastAPI | 0.115 | 轻量、自动 OpenAPI 文档、支持 async |
| ORM | SQLAlchemy | 2.0 | 声明式模型、成熟稳定 |
| 数据库 | SQLite | 3.x | 单文件零配置，备份=复制文件，足够单机场景 |
| 模板引擎 | Jinja2 | 3.1 | FastAPI 内置支持，服务端渲染 |
| 拼音搜索 | pypinyin | 0.51 | 商品拼音首字母搜索 |
| Excel 导出 | openpyxl | — | 台账、报表导出 |
| 前端 | Bootstrap 5 + Chart.js | CDN | 响应式布局 + 图表，零构建 |
| 打包 | PyInstaller | — | P4 阶段交付 .exe |
| Web 服务器 | uvicorn | 0.30 | ASGI，开发/生产通用 |

**关键架构决策**：
- **不做前后端分离**：服务端渲染（SSR）Jinja2 模板，最小化 JavaScript
- **不做数据库迁移**：SQLAlchemy `Base.metadata.create_all()` 直接建表；改表结构时手动 ALTER TABLE
- **不使用 Alembic**：SQLite + 单机场景不需要迁移工具
- **不使用 Docker**：目标用户是 Windows 桌面，最终 PyInstaller 打包为 .exe

---

## 架构模式

```
浏览器 ──HTTP──► FastAPI (uvicorn) ──SQL──► SQLite (nongzi.db)
                   │
                   ├── Jinja2 渲染 HTML
                   └── 静态文件服务 (css/js)
```

- **路由风格**：RESTful，资源名复数
- **前后端交互**：页面导航 = 完整页面刷新 + URL 参数传递；表单提交 = POST + 302 重定向
- **AJAX**：仅在购物车增删、搜索建议、扫码枪输入等需要无刷新交互处使用（最小量）

---

## 目录规范

```
Project Root/
├── AGENTS.md                  # 本文件
├── .codex/skills/nongzi-dev/
│   └── SKILL.md               # 开发技能手册
├── specs/                     # 阶段需求文档
│   ├── p0-mvp.md
│   ├── p1-compliance.md
│   ├── p2-finance-reports.md
│   ├── p3-advanced.md
│   └── p4-distribution.md
├── nongzi/
│   ├── main.py                # FastAPI 入口 + 路由注册
│   ├── config.py              # 配置中心
│   ├── database.py            # engine / session / Base
│   ├── models/                # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── product.py         # Category, Product
│   │   ├── contact.py         # Supplier, Customer
│   │   ├── purchase.py        # PurchaseOrder, PurchaseItem
│   │   ├── sale.py            # SaleOrder, SaleItem, RestrictedSale
│   │   ├── inventory.py       # Warehouse, Inventory, InventoryBatch
│   │   ├── finance.py         # AR/AP Transaction, Expense
│   │   └── system.py          # User, OperationLog
│   ├── routes/                # 路由处理
│   │   ├── __init__.py
│   │   ├── products.py
│   │   ├── contacts.py
│   │   ├── purchases.py
│   │   ├── sales.py
│   │   ├── inventory.py
│   │   ├── finance.py
│   │   ├── reports.py
│   │   └── system.py
│   ├── templates/             # Jinja2 模板
│   │   ├── base.html
│   │   ├── index.html         # 首页仪表盘
│   │   ├── products/
│   │   ├── contacts/
│   │   ├── purchases/
│   │   ├── sales/
│   │   ├── inventory/
│   │   ├── finance/
│   │   └── system/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       ├── cart.js        # 购物车逻辑
│   │       ├── scanner.js     # 扫码枪输入处理
│   │       └── utils.js       # 通用工具函数
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── pinyin_search.py   # 拼音首字母搜索
│   │   ├── excel_export.py    # Excel 导出
│   │   └── helpers.py         # 通用工具（格式化、计算）
│   └── requirements.txt
```

---

## 编码约定

### Python

- 类名：`PascalCase`（如 `PurchaseOrder`, `InventoryBatch`）
- 函数/变量：`snake_case`（如 `get_product_by_barcode`, `total_amount`）
- 常量：`UPPER_SNAKE_CASE`（如 `RESTRICTED_TOXICITY_LEVELS`）
- 私有方法：前缀 `_`（如 `_calculate_weighted_average_cost`）
- 类型注解：路由函数和工具函数必须写参数类型和返回类型
- Docstring：复杂业务逻辑函数必须写（计量单位换算、移动加权平均等）

### 路由

```python
# 命名模式：资源名复数
router = APIRouter(prefix="/products", tags=["商品管理"])

@router.get("/")                    # 列表
@router.get("/new")                 # 新增表单
@router.post("/")                   # 创建
@router.get("/{id}")                # 详情
@router.get("/{id}/edit")           # 编辑表单
@router.put("/{id}")                # 更新
@router.delete("/{id}")             # 软删除（设 is_active=False）
```

### Jinja2 模板

- 文件名：`kebab-case`（如 `product-form.html`, `purchase-list.html`）
- 继承链：`base.html` → 模块内 `_layout.html` → 具体页面
- 宏（macro）：重复 UI 片段放 `macros.html`
- 不使用 `url_for` 的 static 路径写死为 `/static/...`

### JSON / API

- 字段名：`camelCase`（前端使用场景，如 `productCode`, `isRestricted`）
- 数值金额：统一为浮点数，展示时格式化到 2 位小数
- 日期：ISO 格式 `YYYY-MM-DD`

---

## 数据库约定

### 建表

```python
# main.py 启动时：
from database import engine, Base
Base.metadata.create_all(bind=engine)
```

### 枚举字段

SQLite 不支持 ENUM，统一用 `String` 类型 + Python Enum 约束：

```python
class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    WECHAT = "wechat"
    ALIPAY = "alipay"
    CREDIT = "credit"  # 挂账

class SaleOrder(Base):
    payment_method = Column(String(20), nullable=False)
```

### 软删除

所有业务表默认使用软删除（`is_active` / `is_deleted` 标记），**不做物理删除**。合规表（操作日志、限制农药销售记录）连软删除都不允许。

### 外键与级联

```python
# 核心规则：
# 1. 商品/供应商/客户/仓库 → 被引用时不可删除（RESTRICT）
# 2. 进货单头删除 → 级联删除明细 + 回退库存
# 3. 销售单 → 只允许红冲，不允许删除
```

---

## 开发流程

### 新增功能步骤

1. **读 spec**：在 `specs/` 中找到对应阶段文档，确认本周期的需求及验收标准
2. **建 Model**：在 `nongzi/models/` 中定义 SQLAlchemy 模型
3. **建 Route**：在 `nongzi/routes/` 中实现路由 + 业务逻辑
4. **建 Template**：在 `nongzi/templates/` 中编写 Jinja2 页面
5. **注册路由**：在 `main.py` 中 `app.include_router()`
6. **运行验证**：`uvicorn nongzi.main:app --reload`
7. **验收**：对照 spec 末尾的检查清单逐条通过

### 本地运行

```bash
cd "D:\Users\pc\Documents\New project"
pip install -r nongzi/requirements.txt
uvicorn nongzi.main:app --reload --host 127.0.0.1 --port 8000
# 浏览器打开 http://127.0.0.1:8000
```

### 数据库重置

```bash
del nongzi\nongzi.db
# 重启 uvicorn 自动建表
```

---

## 阶段开发策略

当前阶段：**P0 — 最小可用 MVP**

| 阶段 | 主题 | 周期（估） |
|------|------|-----------|
| P0 | 进-销-存核心闭环 | 2-3 周 |
| P1 | 合规完善（批次、台账、追溯） | 2 周 |
| P2 | 财务报表 + 仪表盘 | 2 周 |
| P3 | 高级特性（扫码、打印、备份） | 1-2 周 |
| P4 | 打包发布 .exe | 1 周 |

**开发顺序为 P0 → P1 → P2 → P3 → P4，不可跳跃。** 完成后一个阶段前，前一个阶段的验收检查清单必须全部通过。

---

## 相关文档

- [开发技能手册](.codex/skills/nongzi-dev/SKILL.md) — 数据模型速查、业务规则、代码模板
- [P0 MVP Spec](specs/p0-mvp.md)
- [P1 合规 Spec](specs/p1-compliance.md)
- [P2 财务报表 Spec](specs/p2-finance-reports.md)
- [P3 高级特性 Spec](specs/p3-advanced.md)
- [P4 发布 Spec](specs/p4-distribution.md)

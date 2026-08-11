# P3 — 高级特性（扫码枪 + 小票 + 备份 + 盘点）

> **目标**：实用场景打磨，让日常操作更顺畅。扫码即卖、一键打印、数据安心。
> **前置条件**：P2 全部验收通过
> **估时**：1-2 周

---

## 交付清单

### C1 升级 — 扫码枪支持

**方案**
- USB 扫码枪键盘模拟模式（HID Keyboard），即插即用，无需安装驱动
- 扫码时就像键盘快速输入一串字符 + 自动回车
- 系统只需正确"接住"这个输入

**实现**
```javascript
// static/js/scanner.js — 开单页面加载
// 在页面放置一个隐藏的 <input id="scanner-input" autofocus>
// 该 input 持续监听，不失去焦点

let scanBuffer = "";
let scanTimer = null;

document.getElementById("scanner-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        if (scanBuffer.length > 0) {
            handleBarcode(scanBuffer.trim());
            scanBuffer = "";
        }
        e.preventDefault();
        return;
    }
    // 扫码枪输入极快（通常 < 10ms 间隔），正常键盘 > 50ms
    scanBuffer += e.key;
    
    clearTimeout(scanTimer);
    scanTimer = setTimeout(() => {
        // 超时未回车 → 清空 buffer（非扫码输入）
        scanBuffer = "";
    }, 100);
});

function handleBarcode(barcode) {
    // AJAX 请求后端搜索条码
    fetch(`/api/products/by-barcode/${barcode}`)
        .then(r => r.json())
        .then(product => {
            if (product) {
                addToCart(product, 1); // 默认加 1 个基本单位
                showToast(`已加入: ${product.name}`);
            } else {
                showToast("未找到该条码商品", "error");
            }
        });
}
```

**后端 API**
```python
@router.get("/api/products/by-barcode/{barcode}")
def get_by_barcode(barcode: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.barcode == barcode,
        Product.is_active == True
    ).first()
    if not product:
        raise HTTPException(404, "未找到商品")
    # 返回商品基本信息 + 实时库存
    ...
```

**防干扰设计**
- 扫描枪输入时，如果用户正在手动搜索框输入，不要触发扫码处理
- 判断逻辑：`document.activeElement.id === "scanner-input"` 才处理

---

### C5 — 小票打印

**方案**
- 使用浏览器 `window.print()` + CSS `@page` 规则
- 生成一个小票预览窗口，自动调起打印对话框
- 支持 58mm 和 80mm 两种宽度（用户设置中选择）

**小票模板（HTML）**

```html
<!-- templates/sales/receipt.html — 独立页面，非 base.html 继承 -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>小票</title>
    <style>
        @page {
            size: {{ receipt_width }} 297mm;  /* 58mm or 80mm */
            margin: 2mm;
        }
        body {
            font-family: 'Courier New', monospace;
            font-size: 10px;
            width: {{ receipt_width }};
        }
        .header { text-align: center; font-weight: bold; font-size: 12px; }
        .divider { border-top: 1px dashed #000; margin: 4px 0; }
        .item { display: flex; justify-content: space-between; }
        .total { font-weight: bold; font-size: 12px; }
        @media print { body { -webkit-print-color-adjust: exact; } }
    </style>
</head>
<body>
    <div class="header">{{ store_name }}</div>
    <div>{{ store_address }}</div>
    <div>{{ store_phone }}</div>
    <div class="divider"></div>
    <div>单号: {{ order.order_no }}</div>
    <div>日期: {{ order.order_date.strftime("%Y-%m-%d %H:%M") }}</div>
    <div class="divider"></div>
    <div class="item"><span>商品</span><span>数量</span><span>金额</span></div>
    {% for item in order.items %}
    <div class="item">
        <span>{{ item.product_name }}</span>
        <span>{{ item.quantity }}</span>
        <span>¥{{ "%.2f"|format(item.amount) }}</span>
    </div>
    {% endfor %}
    <div class="divider"></div>
    <div class="item total">
        <span>合计</span><span>¥{{ "%.2f"|format(order.total_amount) }}</span>
    </div>
    <div>支付: {{ order.payment_method_display }}</div>
    <div class="divider"></div>
    <div style="text-align:center">谢谢惠顾！</div>
    <script>window.onload = () => window.print();</script>
</body>
</html>
```

**触发方式**
- 销售单详情页 → "打印小票"按钮
- 开单成功后自动弹出 → 小票预览窗口 → 用户选择打印或关闭

**宽度配置**
- 系统设置页 → 小票宽度选择: 58mm / 80mm
- 存储在数据库 `system_config` 表或 `config.py`

---

### H3 — 数据管理

**数据库备份**

- 路由：`POST /system/backup`
- 实现：
```python
import shutil
from datetime import datetime

@router.post("/system/backup")
def backup_database():
    db_path = DATABASE_PATH  # nongzi/nongzi.db
    backup_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"nongzi_backup_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    
    return {"message": "备份成功", "path": backup_path}
```

- 前端："一键备份"按钮 → 调用 API → 提示成功 + 显示备份文件路径
- 备份列表：显示历史备份文件（文件名 = 日期时间，文件大小）

**数据库恢复**
- 路由：`POST /system/restore`
- 上传 .db 文件 → 覆盖当前数据库 → 重启应用
- ⚠️ 危险操作 → 双重确认弹窗

**演示数据初始化**
- 路由：`POST /system/init-demo`
- 预置数据：
  - 7 个商品分类
  - 10-15 个商品（涵盖种子、农药、化肥等）
  - 2-3 个供应商
  - 5 个客户（含种植大户、合作社）
  - 3 笔进货单
  - 10 笔销售单
- ⚠️ 会清空现有数据 → 双重确认

---

### C1 升级 — 商品搜索增强

**搜索策略（优先级从高到低）**
1. **条码精确匹配**：输入值 == product.barcode → 直接返回
2. **拼音首字母匹配**：用 pypinyin 将输入转为拼音首字母 → LIKE
   ```python
   from pypinyin import lazy_pinyin
   
   def search_by_pinyin(query: str, db: Session):
       # "BKL" → "吡虫啉"
       products = db.query(Product).filter(Product.is_active == True).all()
       results = []
       for p in products:
           pinyin_initials = "".join([w[0] for w in lazy_pinyin(p.generic_name)])
           if query.upper() in pinyin_initials.upper():
               results.append(p)
       return results
   ```
3. **名称模糊匹配**：general_name LIKE "%query%" OR trade_name LIKE "%query%"

**搜索建议 UI**
- 输入框实时 AJAX（300ms 防抖）
- 下拉列表显示：商品名 + 规格 + 零售价 + 库存
- 上下箭头选择 + 回车确认

---

### D4 — 盘点

**流程**
1. 创建盘点单：选择盘点范围（全部 / 指定分类 / 指定商品）
2. 系统生成盘点明细表（商品 + 系统库存量 + 空白"实盘数"列）
3. 点击"导出盘点表" → 下载 Excel 空白盘点表
4. 实地盘点后，在页面录入实盘数
5. 系统自动计算差异（实盘数 - 系统数）
6. 确认盘点 → 差异处理：
   - 盘盈（实盘 > 系统）→ 生成盘盈入库单，调增库存
   - 盘亏（实盘 < 系统）→ 生成盘亏出库单，调减库存

**盘点单元数据**
- 单号：CH-YYYYMMDD-XXX
- 盘点日期
- 盘点人
- 范围（全部/分类/商品）
- 状态：进行中 / 已完成

---

### D5 — 报损

**流程**
1. 库存详情页 → 某个商品/批次的"报损"按钮
2. 填写报损数量（不可超过可用量）+ 原因（过期/破损/其他）
3. 确认 → 扣减库存 + inventory_batch

- 生成报损单（LS-YYYYMMDD-XXX）
- 库存变化：`inventory.quantity -= 报损数量`，`inventory_batch.available_quantity -= 报损数量`

---

### H4 — 证照提醒

**系统设置页新增字段**

| 字段 | 说明 |
|------|------|
| 农药经营许可证到期日 | Date |
| 营业执照到期日 | Date |
| 提前提醒天数 | Integer，默认 30 |

**首页提醒**
- 到期日前 N 天时，首页顶部显示黄色横幅提醒条
- "⚠ 农药经营许可证将于 2026-07-15 到期（剩余 16 天），请尽快续期"

---

### G2/G3 升级 — 报表导出完善

- 所有报表页面增加"导出 Excel"和"导出 PDF"按钮
- Excel 使用 openpyxl，带表头格式（加粗、边框、居中）
- PDF 使用浏览器 `window.print()` → 用户选择"另存为 PDF"
- 导出文件名包含报表类型 + 日期范围

---

## 验收检查清单

- [ ] 扫码枪扫条码 → 商品自动加入购物车，Toast 提示
- [ ] 扫码时正在搜索框输入 → 不会误触发
- [ ] 条码不存在时提示"未找到"
- [ ] 开单成功后弹出小票预览 → 自动调起打印
- [ ] 58mm/80mm 宽度切换后小票格式正确
- [ ] 一键备份 → backups/ 目录下生成带时间戳的 .db 文件
- [ ] 恢复：上传 .db → 数据恢复正确
- [ ] 演示数据初始化：清空 + 预置数据 → 可正常走通进销流程
- [ ] 搜索"吡虫啉"拼音首字母"BKL" → 正确匹配
- [ ] 搜索建议下拉显示商品名+规格+价格+库存
- [ ] 盘点：创建盘点单 → 导出空表 → 录入实盘数 → 差异计算正确
- [ ] 盘盈/盘亏后库存正确调整
- [ ] 报损：过期商品报损 → 对应批次库存扣减
- [ ] 证照到期前 N 天首页显示黄色横幅提醒
- [ ] 报表 Excel 导出格式正确（表头加粗+边框）

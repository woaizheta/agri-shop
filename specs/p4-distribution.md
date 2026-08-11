# P4 — 包装发布（PyInstaller .exe + 安装引导）

> **目标**：将 Web 应用打包为 Windows 桌面 .exe，双击即用，无需安装 Python。
> **前置条件**：P3 全部验收通过
> **估时**：1 周

---

## 交付清单

### 1. PyInstaller 打包

**目标产物**
- 单个 .exe 文件：`AgriShop.exe`（约 50-80 MB）
- 所有依赖（Python + FastAPI + SQLAlchemy + Jinja2 + pypinyin + openpyxl + uvicorn）打包在内
- 无需用户安装 Python 环境

**打包配置 — `nongzi.spec`**

```python
# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['launcher.py'],  # 启动脚本
    pathex=[],
    binaries=[],
    datas=[
        ('nongzi/templates', 'nongzi/templates'),  # Jinja2 模板
        ('nongzi/static', 'nongzi/static'),         # 静态资源
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'sqlalchemy',
        'jinja2',
        'pypinyin',
        'openpyxl',
        'fastapi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AgriShop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 无控制台窗口
    disable_windowed_traceback=False,
    icon='nongzi/static/icon.ico',  # 应用图标
)
```

**启动脚本 — `launcher.py`**

```python
import os
import sys
import threading
import webbrowser
import uvicorn

def get_app_path():
    """获取应用目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def main():
    app_path = get_app_path()
    os.chdir(app_path)
    
    # 设置 nongzi 模块路径
    sys.path.insert(0, app_path)
    
    # 延迟打开浏览器（等服务器启动后）
    def open_browser():
        webbrowser.open("http://127.0.0.1:8000")
    
    threading.Timer(1.5, open_browser).start()
    
    # 启动 uvicorn
    uvicorn.run(
        "nongzi.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()
```

**打包命令**
```bash
pyinstaller nongzi.spec --clean --noconfirm
# 产物: dist/AgriShop.exe
```

---

### 2. 安装引导（首次运行）

**首次运行检测**
- `AgriShop.exe` 启动时检查 `nongzi.db` 是否存在
- 不存在 → 显示"欢迎使用丰收农资店管理系统"引导页

**引导页内容**
1. 确认店铺信息（店名、地址、电话）：默认读取 `config.py` 的值，可修改
2. 是否导入演示数据？（勾选框，默认勾选）
3. 点击"开始使用"
4. 系统自动：创建 SQLite 数据库 → 建表 → (可选)插入演示数据 → 跳转首页

**实现**
```python
# nongzi/setup.py
def is_first_run():
    return not os.path.exists(DATABASE_PATH)

def initialize_system(store_config: dict, load_demo: bool):
    """首次初始化"""
    # 1. 创建数据库 + 建表
    Base.metadata.create_all(bind=engine)
    
    # 2. 更新店铺配置
    # 3. 创建默认仓库
    # 4. 创建 admin 用户
    # 5. 可选：加载演示数据
    if load_demo:
        from utils.demo_data import load_demo_data
        load_demo_data()
```

**中文乱码处理**
- 所有 Python 文件顶部 `# -*- coding: utf-8 -*-`
- config.py 店铺信息默认用中文
- 打包时确保中文正常显示

---

### 3. 版本管理

**版本号**
```python
# nongzi/config.py
VERSION = "1.0.0"
BUILD_DATE = "2026-07-15"
```

**启动时展示**
- 首页底部显示版本号：`v1.0.0`
- 关于页面：版本号 + 构建日期 + 技术栈信息

---

### 4. 自动更新检测（可选）

**方案**
- 连接 GitHub Release API 检查最新版本号
- 如果线上版本 > 本地版本 → 首页顶部蓝色提示条"有新版本 v1.1.0 可用，点击下载"
- 点击 → 打开浏览器跳转 GitHub Release 下载页
- ⚠️ 不做自动下载/自动替换（避免杀毒软件误报）

**实现（可选，不强制）**
```python
import requests

def check_update():
    try:
        resp = requests.get(
            "https://api.github.com/repos/yourname/agrishop/releases/latest",
            timeout=5
        )
        if resp.status_code == 200:
            latest = resp.json()["tag_name"].lstrip("v")
            return latest if latest > VERSION else None
    except Exception:
        pass  # 网络不可用时静默跳过
    return None
```

---

### 5. 应用图标

- 生成或准备一个 256×256 的 `.ico` 文件，放在 `nongzi/static/icon.ico`
- 应用名 + 图标 = 专业感

---

### 6. 分发清单

最终交付给用户的文件：
```
AgriShop_v1.0.0/
├── AgriShop.exe         # 主程序（双击运行）
├── 使用说明.txt          # 简要操作指南
└── (首次运行后自动生成):
    ├── nongzi.db        # 数据库
    └── backups/         # 备份目录
```

---

## 验收检查清单

- [ ] `pyinstaller nongzi.spec` 成功无报错
- [ ] `dist/AgriShop.exe` 可双击运行，弹出浏览器打开 http://127.0.0.1:8000
- [ ] 首次运行显示引导页：填写店铺信息 → 选演示数据 → 开始使用
- [ ] 引导页后数据库自动创建，表结构正确
- [ ] 演示数据完整可操作（进-销-存全链路跑通）
- [ ] 中文显示正常（页面、报错信息、小票）
- [ ] 关闭浏览器后，后台 uvicorn 可正常通过托盘退出（或直接关闭 cmd 窗口）
- [ ] .exe 可拷贝到其他 Windows 电脑上运行（复制即用）
- [ ] 版本号在首页底部正确显示
- [ ] (可选) 有新版本时首页显示更新提示

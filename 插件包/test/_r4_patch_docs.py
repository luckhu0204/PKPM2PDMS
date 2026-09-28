# -*- coding: utf-8 -*-
"""R3 修复脚本（本会话自建）：给 docs/交付清单.md 与 docs/使用说明.md 写入 §p.10-5 未部署声明。

只改本包 docs 下的两份文档（本工作流自己的交付物），UTF-8 无 BOM 原样写回。
"""
import os

DOCS = r"D:\AI_Work\PKPM数据解析\PKPM2PDMS导入导出\docs"
DECL = ("**本包未部署，需要用户自己在 PDMS 停机时按 docs/使用说明.md 安装。**")


def patch(path, old, new):
    t = open(path, "rb").read().decode("utf-8")
    if new.strip() in t:
        print("已存在，跳过：", os.path.basename(path))
        return
    assert old in t, "锚点缺失：%s" % path
    t = t.replace(old, new, 1)
    open(path, "wb").write(t.encode("utf-8"))
    print("已更新：", os.path.basename(path), len(t.encode("utf-8")), "bytes")


# ---- 交付清单.md：头部声明 + 交付位置行更新
p = os.path.join(DOCS, "交付清单.md")
patch(
    p,
    "> R2 增量（PDT 完整导入导出、数据库四向转化、转化表、荷载不做）用 **〔R2〕** 标注。",
    "> R2 增量（PDT 完整导入导出、数据库四向转化、转化表、荷载不做）用 **〔R2〕** 标注；\n"
    "> R3 增量（.NET 插件、部署脚本、引擎 exe、唯一化函数）见 §1a 与 `pdms-net/`。\n"
    ">\n"
    "> **未部署声明（契约 §p.10-5）**：" + DECL + "\n"
    "> 截至本文更新（2026-09-25，R3）：本工作区与交付副本都**没有**执行过任何部署脚本；\n"
    "> `D:\\AVEVA` 注册三件套与 G 盘插件目录在验收前后零变化（acceptance_r3.py 检查 19 的\n"
    "> C14 基线核对）。R3 起安装路线以 `pdms-net/deploy/deploy_pkpm2pdms.py` 为准（缺省\n"
    "> dry-run、`--execute` 真做、`undeploy_pkpm2pdms.py` 回滚）；`install/install.ps1` 为\n"
    "> v1 遗留方案（§p.8，文件保留不删）。",
)
t = open(p, "rb").read().decode("utf-8")
old_row = ("| **交付副本**：`G:\\工作\\PDMS相关\\00 PDMS插件\\02 实用插件\\PKPM导入导出插件\\"
           "PKPM2PDMS导入导出\\` | ⚠️ **尚未落盘**（核验见 §5.3：插件目录下只有 `P-TRANS\\` "
           "与样本原件） |")
new_row = ("| **交付副本（R3 起为准）**：`D:\\AI_Work\\PKPM数据解析\\交付_PKPM2PDMS插件\\`"
           "（含整包副本 `插件包\\`、`交付清单.txt`、`SHA256哈希清单.txt`、`从这里开始.txt`、"
           "v1 遗留 `安装程序\\`） | ✅ 存在（由 `deliver/collect_to_workspace.py --refresh` "
           "归集；逐文件 SHA256 见 `SHA256哈希清单.txt`） |\n"
           "| 历史说明 | `G:\\工作\\…\\PKPM导入导出插件\\` 按 §p.10-3 **不写**（G 盘清单在"
           "验收前后零变化） |")
if old_row in t:
    t = t.replace(old_row, new_row, 1)
    open(p, "wb").write(t.encode("utf-8"))
    print("交付位置行已更新")
else:
    print("交付位置行锚点未找到（人工核对）")

# ---- 使用说明.md：§2 安装开头加声明
p = os.path.join(DOCS, "使用说明.md")
patch(
    p,
    "## 2. 安装（PDMS 侧界面）\n\n安装脚本 `install\\install.ps1`",
    "## 2. 安装（PDMS 侧界面）\n\n"
    "> **未部署声明（契约 §p.10-5）**：" + DECL + "\n"
    "> 本工作流只交付脚本与产物，**没有**在真实 `D:\\AVEVA` 上执行过任何安装；\n"
    "> R3 起安装路线以 `pdms-net/deploy/deploy_pkpm2pdms.py`（缺省 dry-run、`--execute` 真做、\n"
    "> `undeploy_pkpm2pdms.py` 回滚）为准；下文的 `install\\install.ps1` 是 v1 遗留方案（§p.8，\n"
    "> 文件保留不删，仍可用）。\n\n"
    "安装脚本 `install\\install.ps1`",
)
print("done")

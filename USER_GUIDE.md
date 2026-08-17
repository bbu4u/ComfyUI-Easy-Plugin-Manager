# ComfyUI Universal Plugin Manager 操作说明

## 1. 打开管理器

将插件放入 `ComfyUI/custom_nodes/ComfyUI-Universal-Plugin-Manager` 后重启 ComfyUI。打开左侧边栏的“插件管理”。

页面会扫描 ComfyUI 配置的全部 `custom_nodes` 目录，并显示四个栏目：

- 可更新：远程仓库存在新提交的 Git 插件。
- Git安装：目录本身是完整 Git 仓库并且配置了 `origin`。
- 非Git安装项目：压缩包复制、单文件或没有可管理远程仓库的项目。
- 全部：显示所有已扫描项目。

顶部搜索框可以按项目名称筛选。点击项目名称会打开 GitHub 页面；非 Git 项目会搜索“项目名称 + github”。名称右侧的复制图标用于复制完整项目名称。

## 2. 检查和更新插件

进入页面时会自动检查 Git 远程更新，也可以点击“刷新”重新扫描。

### 单个更新

点击 Git 项目右侧的“升级”。升级只执行 Git fast-forward，不会自动安装依赖。

如果项目存在本地修改，页面会要求二次确认。确认后，本地修改和未跟踪文件会先保存到该仓库的 Git stash，再执行升级。如果远程没有新版本，则不会创建 stash，也不会改变本地文件。

### 批量更新

在“可更新”栏目勾选多个项目，或者点击“全选”，然后点击“更新所选”。单个项目失败不会中断其他项目。

注意：可更新栏目只更新项目代码。代码更新后如需处理依赖，请转到“Git安装”或“全部”栏目点击对应项目的“更新依赖”。

## 3. 安装新插件

点击页面顶部“安装插件”，输入完整 GitHub 仓库地址，例如：

```text
https://github.com/owner/repository.git
```

“同时安装依赖包”默认勾选：

- 勾选：克隆插件后，自动安装项目的 requirements 依赖。
- 取消：只克隆 Git 项目，不安装依赖。

插件默认安装到 ComfyUI 配置中的首个 `custom_nodes` 目录。如果同名目录已存在，管理器会拒绝覆盖。

## 4. 安装或更新依赖

“Git安装”“非Git安装项目”和“全部”栏目中的普通目录项目提供“更新依赖”按钮。

管理器自动查找：

```text
requirements.txt
requirements-*.txt
requirements_*.txt
requirements/*.txt
```

依赖安装等价于使用当前 ComfyUI Python 执行：

```text
python.exe -m pip --isolated install --disable-pip-version-check -r requirements.txt
```

依赖只允许安装到当前 ComfyUI 的虚拟环境或便携版 `python_embeded`。如果检测到系统全局 Python，操作会被拒绝。管理器不会执行插件的 `install.py`。

## 5. 切换版本

点击 Git 项目的“版本”，可以切换到：

- 本地或远程分支。
- Git 标签。
- 最近提交。

切换前会创建 `refs/upm/backups/*` 引用。存在本地修改时，确认后会先保存到 Git stash。切换到标签或提交后，仓库会处于 detached HEAD 状态；需要继续普通升级时，应先切回分支。

## 6. 将非 Git 项目转换为 Git

### 手动转换

点击“切换为 Git 管理”，输入确认后的 GitHub 仓库地址。管理器会：

1. 克隆目标仓库。
2. 将当前原目录完整移动到备份目录。
3. 用新克隆的 Git 仓库替换原目录。

### 自动检测和批量转换

在“非Git安装项目”栏目点击“检测 GitHub 链接”。检测结果分为“已找到”和“未找到”。

管理器只接受名称明确匹配的结果。模糊匹配或多个候选不会自动转换。请打开候选链接确认仓库正确，再勾选一个、多个或全选，点击“转换所选并更新到最新”。

原项目备份位于：

```text
ComfyUI/user/universal_plugin_manager/backups
```

## 7. 删除和恢复插件

点击“删除”后，项目不会被永久删除，而是移动到：

```text
ComfyUI/user/universal_plugin_manager/trash
```

需要恢复时，先关闭 ComfyUI，再将对应目录手动移回 `custom_nodes`。

## 8. 重新启动 ComfyUI

执行需要重启的操作后，页面顶部会出现“重新启动”。点击并确认后，管理器会使用当前 Python 和原启动参数重新启动 ComfyUI。

在 Windows 便携版中，当前命令行窗口会保持打开。重启会中断正在运行的生成任务，请先等待任务完成。

## 9. 常见情况

### 项目没有出现在 Git安装栏目

只有项目目录本身包含 `.git`，并且配置了 `origin`，才会被识别为可管理 Git 项目。仅位于 ComfyUI 父仓库中不算独立 Git 插件。

### 更新后插件仍然异常

项目升级不会自动更新依赖。请到其他栏目执行“更新依赖”，然后重新启动 ComfyUI。

### 依赖安装失败

查看 ComfyUI 命令行中的 pip 错误。常见原因包括网络或代理不可用、Python 版本不兼容、依赖没有适配当前操作系统。

### 本地修改保存在哪里

升级或切换版本前保存的修改位于对应插件仓库的 Git stash 中，可以在该插件目录执行：

```text
git stash list
```

恢复前建议先确认当前代码版本，避免产生冲突。

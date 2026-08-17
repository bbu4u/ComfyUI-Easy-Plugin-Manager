# ComfyUI Universal Plugin Manager

一个不依赖 ComfyUI Registry 登记信息的本地插件管理器。它直接扫描 ComfyUI 配置的全部 `custom_nodes` 路径，并根据插件目录本身是否为完整 Git 仓库进行分类。

## 一期功能

- 搜索全部插件，并按“可更新、Git 安装、非 Git 安装项目、全部”四个栏目展示数量。
- 可管理插件：安全升级、切换分支/标签/最近提交、打开仓库网页、移入回收站。
- 不可管理插件：按“插件名 + github”打开浏览器搜索、绑定 GitHub 仓库并迁移为 Git 管理、移入回收站。
- 插件名称也可点击：Git 项目打开仓库网页，非 Git 项目直接搜索对应的 GitHub 项目。
- 项目名称右侧提供复制图标，可直接复制完整目录名称。
- “可更新”栏目支持逐项勾选、全选和批量更新，单个失败不会中断其他插件。
- “非 Git”栏目支持批量检测名称明确匹配的 GitHub 仓库，并将用户勾选的项目一次性备份、转换为 Git 管理并克隆最新版本。
- 支持输入 GitHub 仓库地址安装新插件，并使用 ComfyUI 当前 Python 环境自动安装根目录 `requirements.txt` 中的依赖。
- 安装新插件时可取消“同时安装依赖包”；默认启用。
- Git 安装、非 Git 安装项目和全部栏目提供独立的“更新依赖”操作；可更新栏目只更新项目代码，并明确提示依赖需单独处理。
- 执行需要重启的操作后显示“重新启动”按钮，使用当前 Python 和启动参数在原命令行窗口中重启 ComfyUI。
- 迁移前自动完整备份原目录。
- 升级仅允许 fast-forward；列表不因本地修改改变颜色或阻止操作。
- 存在本地修改时，升级会二次确认；确认后先把修改（含未跟踪文件）保存到 Git stash，再执行更新。
- 存在本地修改时，切换版本会二次确认并把修改（含未跟踪文件）保存到 Git stash。
- 未跟踪的 `__pycache__`、`.pyc`、`.pyo` 和常见系统缓存文件不会被误判为本地修改。
- 每次升级或切换版本前创建 `refs/upm/backups/*` Git 引用。
- 不直接永久删除文件。

## 安装

将整个 `ComfyUI-Universal-Plugin-Manager` 文件夹复制到：

```text
ComfyUI/custom_nodes/ComfyUI-Universal-Plugin-Manager
```

重启 ComfyUI。左侧边栏将出现“🧩 插件管理”。

项目本身不需要额外 Python 依赖，但系统必须能执行 `git`。

## 数据安全

- 删除的插件保存在 `ComfyUI/user/universal_plugin_manager/trash`。
- 迁移前的原插件保存在 `ComfyUI/user/universal_plugin_manager/backups`。
- GitHub 自动检测优先读取插件自身元数据，并使用 ComfyUI-Manager 公共插件目录补充匹配；模糊或多候选结果不会自动转换。
- 管理器自身禁止从界面删除或迁移。
- 符号链接和 Windows 目录联接一期只展示，不允许修改。
- 操作参数通过固定参数数组传递给 Git，不使用 shell 拼接。
- 依赖只允许安装到 ComfyUI 当前虚拟环境或便携版 `python_embeded`，检测到系统全局 Python 时会拒绝执行。
- 修改类接口默认只接受来自 `127.0.0.1` / `::1` 的请求；通过局域网访问时只能查看列表。

## 一期限制

- 不自动安装、卸载或回退 Python 依赖。
- 不执行插件自己的 `install.py` 或 `uninstall.py`。
- 自动依赖安装只处理根目录 `requirements*.txt` 和 `requirements/*.txt`，使用当前 ComfyUI Python 执行隔离模式 pip，不会自动执行插件提供的脚本。
- 只支持把普通目录迁移到 GitHub 仓库；单文件插件暂不能迁移。
- 切换代码版本后，若依赖也发生变化，需要手动重新安装该插件的 `requirements.txt`。
- 操作完成后需要重启 ComfyUI 才能完全生效。

## 开发测试

```powershell
python -m unittest discover -s tests -v
```

## 操作说明

完整使用方法请参阅 [USER_GUIDE.md](USER_GUIDE.md)，包含插件安装、批量更新、依赖安装、版本切换、非 Git 转换、删除恢复和页面重启操作。

## License

MIT

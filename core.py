from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


class PluginManagerError(RuntimeError):
    def __init__(self, message: str, *, code: str = "operation_failed", status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


class PluginService:
    """Safe, registry-independent management for custom node Git repositories."""

    SKIPPED_NAMES = {"__pycache__", ".git", ".upm_backups", ".upm_trash"}
    GITHUB_HTTPS_RE = re.compile(
        r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?$",
        re.IGNORECASE,
    )
    GITHUB_SSH_RE = re.compile(
        r"^(?:ssh://)?git@github\.com[:/][A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?$",
        re.IGNORECASE,
    )
    COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
    GENERATED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    GENERATED_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
    GENERATED_SUFFIXES = {".pyc", ".pyo"}
    CATALOG_REPOSITORY = "https://github.com/ltdrdata/ComfyUI-Manager.git"

    def __init__(
        self,
        custom_node_roots: Iterable[str | os.PathLike[str]],
        storage_root: str | os.PathLike[str],
        *,
        git_executable: str = "git",
        protected_paths: Iterable[str | os.PathLike[str]] = (),
    ) -> None:
        self.roots = tuple(self._normal_path(Path(x)) for x in custom_node_roots)
        self.storage_root = self._normal_path(Path(storage_root))
        self.git_executable = git_executable
        self.protected_paths = {self._normal_path(Path(x)) for x in protected_paths}
        self._mutation_lock = threading.RLock()

    @staticmethod
    def _normal_path(path: Path) -> Path:
        return Path(os.path.abspath(os.path.normpath(str(path))))

    @staticmethod
    def _is_link(path: Path) -> bool:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        return bool(is_junction and is_junction())

    @staticmethod
    def _plugin_id(path: Path) -> str:
        normalized = os.path.normcase(str(path)).encode("utf-8", errors="surrogatepass")
        return hashlib.sha256(normalized).hexdigest()[:24]

    def _run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 120,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        try:
            result = subprocess.run(
                args,
                cwd=str(cwd) if cwd else None,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise PluginManagerError("未找到 Git，请先安装 Git 并确保 git.exe 位于 PATH。", code="git_missing") from exc
        except subprocess.TimeoutExpired as exc:
            raise PluginManagerError("Git 操作超时，请检查网络或代理设置。", code="git_timeout") from exc

        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout or "Git command failed").strip()
            raise PluginManagerError(detail, code="git_failed")
        return result

    def _git(
        self,
        repo: Path,
        *args: str,
        timeout: int = 120,
        check: bool = True,
    ) -> str:
        result = self._run(
            [self.git_executable, "-C", str(repo), *args],
            timeout=timeout,
            check=check,
        )
        return result.stdout.strip()

    def _is_git_repo(self, path: Path) -> bool:
        if not path.is_dir() or self._is_link(path):
            return False
        # Git searches parent directories. Requiring a local .git marker and an
        # exact work-tree root prevents a copied plugin from being mistaken for
        # the parent ComfyUI repository.
        if not (path / ".git").exists():
            return False
        top_level = self._git(path, "rev-parse", "--show-toplevel", check=False)
        if not top_level:
            return False
        return os.path.normcase(str(self._normal_path(Path(top_level)))) == os.path.normcase(str(path))

    @classmethod
    def _is_generated_untracked(cls, relative_path: str) -> bool:
        normalized = relative_path.replace("\\", "/").strip("/")
        parts = [part for part in normalized.split("/") if part]
        if not parts:
            return False
        if any(part in cls.GENERATED_DIR_NAMES for part in parts[:-1]):
            return True
        filename = parts[-1]
        return filename in cls.GENERATED_FILE_NAMES or Path(filename).suffix.lower() in cls.GENERATED_SUFFIXES

    def _working_tree_state(self, path: Path) -> tuple[bool, int]:
        tracked_changes = self._git(path, "status", "--porcelain", "--untracked-files=no", check=False)
        if tracked_changes:
            return True, 0
        untracked_raw = self._git(path, "ls-files", "--others", "--exclude-standard", "-z", check=False)
        untracked = [item for item in untracked_raw.split("\0") if item]
        meaningful = [item for item in untracked if not self._is_generated_untracked(item)]
        ignored_generated = len(untracked) - len(meaningful)
        return bool(meaningful), ignored_generated

    @staticmethod
    def remote_to_web_url(remote: str | None) -> str | None:
        if not remote:
            return None
        remote = remote.strip()
        match = re.match(r"^(?:ssh://)?git@github\.com[:/](.+?)(?:\.git)?/?$", remote, re.IGNORECASE)
        if match:
            return f"https://github.com/{match.group(1).removesuffix('.git')}"
        match = re.match(r"^https?://github\.com/(.+?)(?:\.git)?/?$", remote, re.IGNORECASE)
        if match:
            return f"https://github.com/{match.group(1).removesuffix('.git')}"
        if remote.startswith("http://") or remote.startswith("https://"):
            return remote.removesuffix(".git").rstrip("/")
        return None

    def _inspect(self, path: Path, root: Path) -> dict[str, Any]:
        is_file = path.is_file()
        is_link = self._is_link(path)
        is_git = self._is_git_repo(path) if not is_file and not is_link else False
        remote = None
        branch = None
        commit = None
        short_commit = None
        tag = None
        dirty = False
        ignored_generated_count = 0
        update_available = False
        behind_count = 0

        if is_git:
            remote = self._git(path, "remote", "get-url", "origin", check=False) or None
            branch = self._git(path, "symbolic-ref", "--short", "HEAD", check=False) or None
            commit = self._git(path, "rev-parse", "HEAD", check=False) or None
            short_commit = commit[:8] if commit else None
            tag = self._git(path, "describe", "--tags", "--exact-match", "HEAD", check=False) or None
            dirty, ignored_generated_count = self._working_tree_state(path)
            if branch and remote:
                upstream = self._git(
                    path,
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{upstream}",
                    check=False,
                ) or f"origin/{branch}"
                counts = self._git(path, "rev-list", "--left-right", "--count", f"HEAD...{upstream}", check=False)
                if counts:
                    parts = counts.replace("\t", " ").split()
                    if len(parts) == 2 and all(part.isdigit() for part in parts):
                        behind_count = int(parts[1])
                        update_available = behind_count > 0

        manageable = bool(is_git and remote and not is_link)
        if path in self.protected_paths:
            reason = "管理器自身受保护"
        elif is_link:
            reason = "符号链接或目录联接暂不允许修改"
        elif is_file:
            reason = "单文件插件没有独立 Git 仓库"
        elif not is_git:
            reason = "目录不是 Git 仓库"
        elif not remote:
            reason = "Git 仓库没有 origin 远程地址"
        else:
            reason = None

        return {
            "id": self._plugin_id(path),
            "name": path.name,
            "path": str(path),
            "root": str(root),
            "kind": "file" if is_file else "directory",
            "manageable": manageable,
            "protected": path in self.protected_paths,
            "reason": reason,
            "remote": remote,
            "web_url": self.remote_to_web_url(remote),
            "branch": branch,
            "tag": tag,
            "commit": commit,
            "short_commit": short_commit,
            "dirty": dirty,
            "ignored_generated_count": ignored_generated_count,
            "update_available": update_available,
            "behind_count": behind_count,
        }

    def scan(self) -> list[dict[str, Any]]:
        plugins: list[dict[str, Any]] = []
        seen: set[Path] = set()
        for root in self.roots:
            if not root.is_dir():
                continue
            for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
                if path.name in self.SKIPPED_NAMES or path.name.startswith(".upm_"):
                    continue
                if path.name.startswith("."):
                    continue
                if not path.is_dir() and not (path.is_file() and path.suffix.lower() == ".py"):
                    continue
                normalized = self._normal_path(path)
                if normalized in seen:
                    continue
                seen.add(normalized)
                plugins.append(self._inspect(normalized, root))
        return plugins

    def _find(self, plugin_id: str) -> tuple[dict[str, Any], Path]:
        for plugin in self.scan():
            if plugin["id"] == plugin_id:
                return plugin, self._normal_path(Path(plugin["path"]))
        raise PluginManagerError("插件不存在或列表已经变化，请刷新后重试。", code="plugin_not_found", status=404)

    def _require_manageable(self, plugin_id: str) -> tuple[dict[str, Any], Path]:
        plugin, path = self._find(plugin_id)
        if not plugin["manageable"]:
            raise PluginManagerError(plugin["reason"] or "此插件不可进行 Git 管理。", code="not_manageable")
        if plugin["protected"]:
            raise PluginManagerError("不能操作管理器自身。", code="protected_plugin")
        return plugin, path

    def _create_backup_ref(self, path: Path) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        ref = f"refs/upm/backups/{stamp}"
        self._git(path, "update-ref", ref, "HEAD")
        return ref

    @staticmethod
    def summarize(plugins: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "total": len(plugins),
            "updatable": sum(1 for item in plugins if item["manageable"] and item["update_available"]),
            "git": sum(1 for item in plugins if item["manageable"]),
            "non_git": sum(1 for item in plugins if not item["manageable"]),
        }

    def check_updates(self, *, max_workers: int = 4) -> dict[str, Any]:
        """Fetch remotes concurrently, then return a fresh classified snapshot."""
        with self._mutation_lock:
            manageable = [item for item in self.scan() if item["manageable"] and not item["protected"]]
            failures: list[dict[str, str]] = []

            def fetch(item: dict[str, Any]) -> None:
                self._git(Path(item["path"]), "fetch", "--quiet", "--prune", "origin", timeout=180)

            with ThreadPoolExecutor(max_workers=max(1, min(max_workers, 8))) as executor:
                futures = {executor.submit(fetch, item): item for item in manageable}
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        future.result()
                    except Exception as exc:
                        failures.append({"name": item["name"], "message": str(exc)})

            plugins = self.scan()
            return {"plugins": plugins, "summary": self.summarize(plugins), "failures": failures}

    def update(self, plugin_id: str, *, allow_dirty: bool = False) -> dict[str, Any]:
        with self._mutation_lock:
            plugin, path = self._require_manageable(plugin_id)
            if plugin["dirty"] and not allow_dirty:
                raise PluginManagerError(
                    "插件存在本地修改，需要确认保存修改后才能升级。",
                    code="dirty_confirmation_required",
                )
            if not plugin["branch"]:
                raise PluginManagerError("当前处于版本/提交游离状态，请先切换到分支后再升级。", code="detached_head")

            before = plugin["commit"]
            self._git(path, "fetch", "--tags", "--prune", "origin", timeout=300)
            upstream = self._git(
                path,
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{upstream}",
                check=False,
            )
            if not upstream:
                candidate = f"origin/{plugin['branch']}"
                exists = self._git(path, "rev-parse", "--verify", candidate, check=False)
                if not exists:
                    raise PluginManagerError(
                        f"分支 {plugin['branch']} 没有上游分支，无法自动升级。",
                        code="missing_upstream",
                    )
                upstream = candidate
                self._git(path, "branch", "--set-upstream-to", upstream, plugin["branch"])

            behind_raw = self._git(path, "rev-list", "--count", f"HEAD..{upstream}")
            behind_count = int(behind_raw or "0")
            if behind_count == 0:
                return {
                    "message": "已经是最新版本",
                    "changed": False,
                    "before": before,
                    "after": before,
                    "backup_ref": None,
                    "stash_created": False,
                    "plugin": self._inspect(path, Path(plugin["root"])),
                    "restart_required": False,
                }

            merge_base = self._git(path, "merge-base", "HEAD", upstream, check=False)
            if not merge_base or merge_base != before:
                raise PluginManagerError(
                    "本地分支与远程分支已经分叉，无法自动 fast-forward 升级。",
                    code="diverged_branch",
                )

            backup_ref = self._create_backup_ref(path)
            stash_created = False
            if plugin["dirty"]:
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._git(path, "stash", "push", "--include-untracked", "-m", f"UPM update {stamp}")
                stash_created = True
            self._git(path, "merge", "--ff-only", upstream, timeout=300)
            after = self._git(path, "rev-parse", "HEAD")
            return {
                "message": "升级完成" if before != after else "已经是最新版本",
                "changed": before != after,
                "before": before,
                "after": after,
                "backup_ref": backup_ref,
                "stash_created": stash_created,
                "plugin": self._inspect(path, Path(plugin["root"])),
                "restart_required": before != after,
            }

    def batch_update(self, plugin_ids: Iterable[str], *, allow_dirty: bool = False) -> dict[str, Any]:
        unique_ids = list(dict.fromkeys(str(value) for value in plugin_ids if value))
        if not unique_ids or len(unique_ids) > 250:
            raise PluginManagerError("请选择 1 至 250 个插件。", code="invalid_batch")
        successes: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        for plugin_id in unique_ids:
            name = plugin_id
            try:
                plugin, _path = self._find(plugin_id)
                name = plugin["name"]
                result = self.update(plugin_id, allow_dirty=allow_dirty)
                successes.append({"id": plugin_id, "name": name, **result})
            except Exception as exc:
                failures.append({"id": plugin_id, "name": name, "message": str(exc)})
        return {
            "message": f"批量更新完成：成功 {len(successes)} 个，失败 {len(failures)} 个",
            "successes": successes,
            "failures": failures,
            "restart_required": any(item["restart_required"] for item in successes),
        }

    def versions(self, plugin_id: str, *, fetch: bool = True) -> dict[str, Any]:
        plugin, path = self._require_manageable(plugin_id)
        if fetch:
            self._git(path, "fetch", "--tags", "--prune", "origin", timeout=300)

        local_raw = self._git(path, "for-each-ref", "--format=%(refname:short)", "refs/heads", check=False)
        remote_raw = self._git(path, "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin", check=False)
        local_branches = [x for x in local_raw.splitlines() if x]
        remote_branches = []
        for value in remote_raw.splitlines():
            if not value or value.endswith("/HEAD"):
                continue
            remote_branches.append(value.removeprefix("origin/"))
        branches = sorted(set(local_branches + remote_branches), key=str.casefold)

        tags_raw = self._git(
            path,
            "for-each-ref",
            "--sort=-version:refname",
            "--format=%(refname:short)",
            "refs/tags",
            check=False,
        )
        tags = [x for x in tags_raw.splitlines() if x][:100]

        log_raw = self._git(
            path,
            "log",
            "-30",
            "--date=short",
            "--pretty=format:%H%x1f%h%x1f%cs%x1f%s",
            check=False,
        )
        commits = []
        for line in log_raw.splitlines():
            parts = line.split("\x1f", 3)
            if len(parts) == 4:
                commits.append({"sha": parts[0], "short": parts[1], "date": parts[2], "subject": parts[3]})
        return {
            "current": {"branch": plugin["branch"], "tag": plugin["tag"], "commit": plugin["commit"]},
            "branches": branches,
            "tags": tags,
            "commits": commits,
        }

    def switch_version(
        self,
        plugin_id: str,
        target_type: str,
        target: str,
        *,
        allow_dirty: bool = False,
    ) -> dict[str, Any]:
        with self._mutation_lock:
            plugin, path = self._require_manageable(plugin_id)
            if plugin["dirty"] and not allow_dirty:
                raise PluginManagerError(
                    "插件存在本地修改，需要确认备份修改后才能切换版本。",
                    code="dirty_confirmation_required",
                )
            target = (target or "").strip()
            if target_type not in {"branch", "tag", "commit"} or not target:
                raise PluginManagerError("无效的版本目标。", code="invalid_target")

            available = self.versions(plugin_id, fetch=True)
            before = plugin["commit"]
            backup_ref = self._create_backup_ref(path)
            stash_created = False
            if plugin["dirty"]:
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._git(path, "stash", "push", "--include-untracked", "-m", f"UPM version switch {stamp}")
                stash_created = True

            if target_type == "tag":
                if target not in available["tags"]:
                    raise PluginManagerError("指定标签不存在。", code="target_not_found")
                self._git(path, "switch", "--detach", f"refs/tags/{target}")
            elif target_type == "branch":
                if target not in available["branches"]:
                    raise PluginManagerError("指定分支不存在。", code="target_not_found")
                local_exists = self._git(path, "rev-parse", "--verify", f"refs/heads/{target}", check=False)
                if local_exists:
                    self._git(path, "switch", target)
                else:
                    self._git(path, "switch", "--track", "-c", target, f"origin/{target}")
            else:
                if not self.COMMIT_RE.fullmatch(target):
                    raise PluginManagerError("提交 ID 格式无效。", code="invalid_commit")
                exists = self._git(path, "rev-parse", "--verify", f"{target}^{{commit}}", check=False)
                if not exists:
                    raise PluginManagerError("指定提交不存在。", code="target_not_found")
                self._git(path, "switch", "--detach", target)

            after = self._git(path, "rev-parse", "HEAD")
            return {
                "message": "版本切换完成",
                "before": before,
                "after": after,
                "backup_ref": backup_ref,
                "stash_created": stash_created,
                "plugin": self._inspect(path, Path(plugin["root"])),
                "restart_required": before != after,
            }

    def _validate_github_url(self, remote_url: str) -> str:
        remote_url = (remote_url or "").strip()
        if not (self.GITHUB_HTTPS_RE.fullmatch(remote_url) or self.GITHUB_SSH_RE.fullmatch(remote_url)):
            raise PluginManagerError(
                "请输入完整的 GitHub 仓库地址，例如 https://github.com/owner/repo.git",
                code="invalid_repository_url",
            )
        return remote_url

    def _repository_name(self, remote_url: str) -> str:
        match = re.search(r"github\.com[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", remote_url, re.IGNORECASE)
        if not match:
            raise PluginManagerError("无法从地址确定仓库名称。", code="invalid_repository_url")
        name = match.group(2)
        if not name or name in {".", ".."}:
            raise PluginManagerError("仓库名称无效。", code="invalid_repository_url")
        return name

    @staticmethod
    def _isolated_python_environment() -> dict[str, Any]:
        executable = Path(sys.executable).resolve()
        is_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
        lowered = str(executable).casefold()
        is_portable = (
            "python_embeded" in lowered
            or "python_embedded" in lowered
            or any(executable.parent.glob("python*._pth"))
        )
        if not (is_venv or is_portable):
            raise PluginManagerError(
                "当前 ComfyUI 没有运行在独立 Python 环境中，为避免修改系统全局 Python，已拒绝安装依赖。",
                code="python_environment_not_isolated",
            )
        return {
            "python_executable": str(executable),
            "environment_type": "virtualenv" if is_venv else "portable",
        }

    @staticmethod
    def _requirement_files(plugin_path: Path) -> list[Path]:
        candidates: set[Path] = set()
        for pattern in ("requirements.txt", "requirements-*.txt", "requirements_*.txt"):
            candidates.update(path for path in plugin_path.glob(pattern) if path.is_file())
        requirements_dir = plugin_path / "requirements"
        if requirements_dir.is_dir():
            candidates.update(path for path in requirements_dir.glob("*.txt") if path.is_file())
        return sorted(candidates, key=lambda path: str(path).casefold())

    def _install_dependencies(self, plugin_path: Path) -> dict[str, Any]:
        requirements = self._requirement_files(plugin_path)
        if not requirements:
            return {
                "requirements_found": False,
                "dependencies_installed": False,
                "dependency_files": [],
                "python_environment": None,
            }
        environment = self._isolated_python_environment()
        for requirement in requirements:
            result = self._run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "--isolated",
                    "install",
                    "--disable-pip-version-check",
                    "-r",
                    str(requirement),
                ],
                cwd=plugin_path,
                timeout=1800,
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "pip install failed").strip()
                if len(detail) > 4000:
                    detail = detail[-4000:]
                raise PluginManagerError(
                    f"依赖文件 {requirement.name} 安装失败：{detail}",
                    code="dependency_install_failed",
                )
        return {
            "requirements_found": True,
            "dependencies_installed": True,
            "dependency_files": [str(path.relative_to(plugin_path)).replace("\\", "/") for path in requirements],
            "python_environment": environment,
        }

    def update_dependencies(self, plugin_id: str) -> dict[str, Any]:
        with self._mutation_lock:
            plugin, path = self._find(plugin_id)
            if plugin["protected"]:
                raise PluginManagerError("不能从界面修改管理器自身的依赖。", code="protected_plugin")
            if plugin["kind"] != "directory" or self._is_link(path):
                raise PluginManagerError("此项目不是可安装依赖的普通目录。", code="unsupported_plugin_kind")
            result = self._install_dependencies(path)
            message = (
                f"依赖安装完成，共处理 {len(result['dependency_files'])} 个依赖文件"
                if result["requirements_found"]
                else "未找到 requirements 依赖文件"
            )
            return {
                "message": message,
                "plugin": plugin,
                **result,
                "restart_required": result["dependencies_installed"],
            }

    def install(self, remote_url: str, *, install_dependencies: bool = True) -> dict[str, Any]:
        with self._mutation_lock:
            remote_url = self._validate_github_url(remote_url)
            repository_name = self._repository_name(remote_url)
            root = next((path for path in self.roots if path.is_dir()), None)
            if root is None:
                raise PluginManagerError("没有可用的 custom_nodes 目录。", code="custom_nodes_missing")
            target = self._normal_path(root / repository_name)
            if target.parent != root:
                raise PluginManagerError("仓库安装路径无效。", code="invalid_install_path")
            if target.exists():
                raise PluginManagerError(f"插件目录已存在：{target.name}", code="plugin_already_exists")

            temp_path = root / f".upm_install_{uuid.uuid4().hex}"
            dependency_result: dict[str, Any] = {}
            try:
                self._run(
                    [self.git_executable, "clone", "--recurse-submodules", remote_url, str(temp_path)],
                    timeout=600,
                )
                if not (temp_path / ".git").exists():
                    raise PluginManagerError("克隆结果不是完整 Git 仓库。", code="invalid_clone")
                if install_dependencies:
                    dependency_result = self._install_dependencies(temp_path)
                else:
                    dependency_result = {
                        "requirements_found": bool(self._requirement_files(temp_path)),
                        "dependencies_installed": False,
                        "dependency_files": [
                            str(path.relative_to(temp_path)).replace("\\", "/")
                            for path in self._requirement_files(temp_path)
                        ],
                        "python_environment": None,
                    }
                shutil.move(str(temp_path), str(target))
            finally:
                if temp_path.exists():
                    shutil.rmtree(temp_path, ignore_errors=True)

            plugin = self._inspect(target, root)
            return {
                "message": (
                    "插件及依赖安装完成"
                    if dependency_result["dependencies_installed"]
                    else "插件安装完成，依赖未安装"
                    if dependency_result["requirements_found"]
                    else "插件安装完成，未发现 requirements 依赖文件"
                ),
                "path": str(target),
                "plugin": plugin,
                **dependency_result,
                "restart_required": True,
            }

    @staticmethod
    def _normalized_plugin_name(value: str) -> str:
        value = re.sub(r"(?:[-_.](?:main|master))$", "", value.strip(), flags=re.IGNORECASE)
        return re.sub(r"[^a-z0-9]+", "", value.casefold())

    @classmethod
    def _github_url_from_text(cls, value: str) -> str | None:
        match = re.search(
            r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)",
            value,
            re.IGNORECASE,
        )
        if not match:
            return None
        owner = match.group(1)
        repo = match.group(2).rstrip(".,").removesuffix(".git")
        return f"https://github.com/{owner}/{repo}"

    def _local_github_candidates(self, path: Path) -> set[str]:
        candidates: set[str] = set()
        filenames = ("README.md", "README.MD", "pyproject.toml", "package.json", "setup.py")
        for filename in filenames:
            candidate = path / filename
            try:
                if not candidate.is_file() or candidate.stat().st_size > 1_000_000:
                    continue
                text = candidate.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in re.finditer(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text, re.IGNORECASE):
                url = self._github_url_from_text(match.group(0))
                if url:
                    candidates.add(url)
        return candidates

    def _load_github_catalog(self) -> Any:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        cache_path = self.storage_root / "github-catalog.json"
        if cache_path.is_file() and time.time() - cache_path.stat().st_mtime < 6 * 60 * 60:
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        clone_error: Exception | None = None
        try:
            with tempfile.TemporaryDirectory(prefix="upm_catalog_") as temp_dir:
                checkout = Path(temp_dir) / "manager"
                self._run(
                    [
                        self.git_executable,
                        "clone",
                        "--quiet",
                        "--depth",
                        "1",
                        "--filter=blob:none",
                        "--no-checkout",
                        self.CATALOG_REPOSITORY,
                        str(checkout),
                    ],
                    timeout=300,
                )
                raw = self._git(checkout, "show", "HEAD:custom-node-list.json", timeout=180)
                payload = json.loads(raw)
                cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                return payload
        except Exception as exc:
            clone_error = exc
        if cache_path.is_file():
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        raise PluginManagerError(
            f"无法获取 GitHub 插件目录：{clone_error}",
            code="catalog_unavailable",
        )

    def detect_github(self, plugin_ids: Iterable[str]) -> dict[str, Any]:
        unique_ids = list(dict.fromkeys(str(value) for value in plugin_ids if value))
        if not unique_ids or len(unique_ids) > 250:
            raise PluginManagerError("请选择 1 至 250 个非 Git 插件。", code="invalid_batch")

        snapshot = {plugin["id"]: plugin for plugin in self.scan()}
        targets: list[tuple[dict[str, Any], Path]] = []
        not_found: list[dict[str, Any]] = []
        for plugin_id in unique_ids:
            plugin = snapshot.get(plugin_id)
            if not plugin:
                not_found.append({"id": plugin_id, "name": plugin_id, "reason": "插件不存在或列表已经变化"})
                continue
            path = self._normal_path(Path(plugin["path"]))
            if plugin["manageable"]:
                continue
            if plugin["kind"] != "directory" or plugin["protected"] or self._is_link(path):
                targets.append((plugin, path))
                continue
            targets.append((plugin, path))

        if not targets:
            return {"found": [], "not_found": not_found}

        catalog = self._load_github_catalog()
        entries = catalog.get("custom_nodes", []) if isinstance(catalog, dict) else catalog
        catalog_by_repo: dict[str, set[str]] = {}
        catalog_by_title: dict[str, set[str]] = {}
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                files = entry.get("files", [])
                if isinstance(files, str):
                    files = [files]
                urls = {url for value in files if isinstance(value, str) if (url := self._github_url_from_text(value))}
                title_key = self._normalized_plugin_name(str(entry.get("title", "")))
                for url in urls:
                    repo_key = self._normalized_plugin_name(url.rstrip("/").rsplit("/", 1)[-1])
                    if repo_key:
                        catalog_by_repo.setdefault(repo_key, set()).add(url)
                    if title_key:
                        catalog_by_title.setdefault(title_key, set()).add(url)

        found: list[dict[str, Any]] = []
        for plugin, path in targets:
            if plugin["kind"] != "directory" or plugin["protected"] or self._is_link(path):
                not_found.append({"id": plugin["id"], "name": plugin["name"], "reason": plugin["reason"] or "不支持转换"})
                continue
            name_key = self._normalized_plugin_name(plugin["name"])
            local_urls = {
                url
                for url in self._local_github_candidates(path)
                if self._normalized_plugin_name(url.rstrip("/").rsplit("/", 1)[-1]) == name_key
            }
            candidates = local_urls or catalog_by_repo.get(name_key, set()) or catalog_by_title.get(name_key, set())
            if len(candidates) == 1:
                found.append(
                    {
                        "id": plugin["id"],
                        "name": plugin["name"],
                        "url": next(iter(candidates)),
                        "source": "插件文件" if local_urls else "ComfyUI-Manager 插件目录",
                    }
                )
            elif len(candidates) > 1:
                not_found.append({"id": plugin["id"], "name": plugin["name"], "reason": "找到多个候选仓库，无法安全确定"})
            else:
                not_found.append({"id": plugin["id"], "name": plugin["name"], "reason": "未找到名称明确匹配的仓库"})
        return {"found": found, "not_found": not_found}

    def migrate(self, plugin_id: str, remote_url: str) -> dict[str, Any]:
        with self._mutation_lock:
            plugin, path = self._find(plugin_id)
            if plugin["manageable"]:
                raise PluginManagerError("该插件已经是可管理的 Git 仓库。", code="already_manageable")
            if plugin["protected"]:
                raise PluginManagerError("不能迁移管理器自身。", code="protected_plugin")
            if plugin["kind"] != "directory" or self._is_link(path):
                raise PluginManagerError("一期仅支持将普通插件目录迁移为 Git 管理。", code="unsupported_plugin_kind")
            remote_url = self._validate_github_url(remote_url)

            temp_path = path.parent / f".upm_migrate_{uuid.uuid4().hex}"
            backup_root = self.storage_root / "backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = backup_root / f"{stamp}_{path.name}"
            counter = 1
            while backup_path.exists():
                backup_path = backup_root / f"{stamp}_{counter}_{path.name}"
                counter += 1

            try:
                self._run(
                    [self.git_executable, "clone", "--recurse-submodules", remote_url, str(temp_path)],
                    timeout=600,
                )
                if not (temp_path / ".git").exists():
                    raise PluginManagerError("克隆结果不是完整 Git 仓库。", code="invalid_clone")
                shutil.move(str(path), str(backup_path))
                try:
                    shutil.move(str(temp_path), str(path))
                except Exception:
                    shutil.move(str(backup_path), str(path))
                    raise
            finally:
                if temp_path.exists():
                    shutil.rmtree(temp_path, ignore_errors=True)

            migrated = self._inspect(path, Path(plugin["root"]))
            return {
                "message": "已切换为 Git 管理，原目录已备份",
                "backup_path": str(backup_path),
                "plugin": migrated,
                "restart_required": True,
            }

    def batch_migrate(self, items: Iterable[dict[str, Any]]) -> dict[str, Any]:
        normalized = [item for item in items if isinstance(item, dict)]
        if not normalized or len(normalized) > 250:
            raise PluginManagerError("请选择 1 至 250 个插件。", code="invalid_batch")
        successes: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in normalized:
            plugin_id = str(item.get("id", ""))
            if not plugin_id or plugin_id in seen:
                continue
            seen.add(plugin_id)
            name = plugin_id
            try:
                plugin, _path = self._find(plugin_id)
                name = plugin["name"]
                result = self.migrate(plugin_id, str(item.get("url", "")))
                successes.append({"id": plugin_id, "name": name, **result})
            except Exception as exc:
                failures.append({"id": plugin_id, "name": name, "message": str(exc)})
        return {
            "message": f"批量转换完成：成功 {len(successes)} 个，失败 {len(failures)} 个",
            "successes": successes,
            "failures": failures,
            "restart_required": bool(successes),
        }

    def delete(self, plugin_id: str) -> dict[str, Any]:
        with self._mutation_lock:
            plugin, path = self._find(plugin_id)
            if plugin["protected"]:
                raise PluginManagerError("不能删除管理器自身。", code="protected_plugin")
            trash_root = self.storage_root / "trash"
            trash_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            trash_path = trash_root / f"{stamp}_{path.name}"
            counter = 1
            while trash_path.exists():
                trash_path = trash_root / f"{stamp}_{counter}_{path.name}"
                counter += 1
            shutil.move(str(path), str(trash_path))
            return {
                "message": "插件已移入回收站",
                "trash_path": str(trash_path),
                "restart_required": True,
            }

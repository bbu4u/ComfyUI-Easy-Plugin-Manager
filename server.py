from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import sys

from aiohttp import web
import folder_paths
from server import PromptServer

from .core import PluginManagerError, PluginService


LOGGER = logging.getLogger("ComfyUI-Universal-Plugin-Manager")
PLUGIN_ROOT = Path(__file__).resolve().parent


def _custom_node_roots() -> list[str]:
    roots = folder_paths.get_folder_paths("custom_nodes")
    if not roots:
        roots = [str(PLUGIN_ROOT.parent)]
    return roots


def _storage_root() -> Path:
    get_user_directory = getattr(folder_paths, "get_user_directory", None)
    if get_user_directory:
        return Path(get_user_directory()) / "universal_plugin_manager"
    return PLUGIN_ROOT / "data"


SERVICE = PluginService(
    _custom_node_roots(),
    _storage_root(),
    protected_paths=[PLUGIN_ROOT],
)
ROUTES = PromptServer.instance.routes


def _restart_current_process() -> None:
    try:
        LOGGER.warning("Restarting ComfyUI with the current Python executable and arguments")
        os.execv(sys.executable, [sys.executable, *sys.argv])
    except Exception:
        LOGGER.exception("Unable to restart ComfyUI")


def _ok(payload=None, **extra):
    body = {"ok": True}
    if payload is not None:
        body["data"] = payload
    body.update(extra)
    return web.json_response(body)


def _error(exc: Exception):
    if isinstance(exc, PluginManagerError):
        return web.json_response(
            {"ok": False, "error": {"code": exc.code, "message": str(exc)}},
            status=exc.status,
        )
    LOGGER.exception("Unexpected plugin manager error")
    return web.json_response(
        {"ok": False, "error": {"code": "internal_error", "message": "内部错误，请查看 ComfyUI 控制台日志。"}},
        status=500,
    )


async def _json(request: web.Request) -> dict:
    try:
        data = await request.json()
    except Exception as exc:
        raise PluginManagerError("请求内容不是有效 JSON。", code="invalid_json") from exc
    if not isinstance(data, dict):
        raise PluginManagerError("请求内容格式无效。", code="invalid_json")
    return data


def _require_local_mutation(request: web.Request) -> None:
    remote = request.remote
    if remote and remote not in {"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"}:
        raise PluginManagerError(
            "为安全起见，一期只允许从运行 ComfyUI 的本机执行修改操作。",
            code="local_access_required",
            status=403,
        )


@ROUTES.get("/universal-plugin-manager/v1/plugins")
async def list_plugins(_request):
    try:
        plugins = await asyncio.to_thread(SERVICE.scan)
        return _ok(
            plugins,
            summary=SERVICE.summarize(plugins),
            process_id=os.getpid(),
        )
    except Exception as exc:
        return _error(exc)


@ROUTES.get("/universal-plugin-manager/v1/versions")
async def list_versions(request):
    try:
        plugin_id = request.query.get("id", "")
        result = await asyncio.to_thread(SERVICE.versions, plugin_id)
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/check-updates")
async def check_updates(request):
    try:
        _require_local_mutation(request)
        result = await asyncio.to_thread(SERVICE.check_updates)
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/update")
async def update_plugin(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        result = await asyncio.to_thread(
            SERVICE.update,
            str(data.get("id", "")),
            allow_dirty=bool(data.get("allow_dirty", False)),
        )
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/batch-update")
async def batch_update_plugins(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        plugin_ids = data.get("ids", [])
        if not isinstance(plugin_ids, list):
            raise PluginManagerError("插件列表格式无效。", code="invalid_batch")
        result = await asyncio.to_thread(
            SERVICE.batch_update,
            plugin_ids,
            allow_dirty=bool(data.get("allow_dirty", False)),
        )
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/switch")
async def switch_plugin(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        result = await asyncio.to_thread(
            SERVICE.switch_version,
            str(data.get("id", "")),
            str(data.get("target_type", "")),
            str(data.get("target", "")),
            allow_dirty=bool(data.get("allow_dirty", False)),
        )
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/migrate")
async def migrate_plugin(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        result = await asyncio.to_thread(
            SERVICE.migrate,
            str(data.get("id", "")),
            str(data.get("remote_url", "")),
        )
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/detect-github")
async def detect_github_plugins(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        plugin_ids = data.get("ids", [])
        if not isinstance(plugin_ids, list):
            raise PluginManagerError("插件列表格式无效。", code="invalid_batch")
        result = await asyncio.to_thread(SERVICE.detect_github, plugin_ids)
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/batch-migrate")
async def batch_migrate_plugins(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        items = data.get("items", [])
        if not isinstance(items, list):
            raise PluginManagerError("插件列表格式无效。", code="invalid_batch")
        result = await asyncio.to_thread(SERVICE.batch_migrate, items)
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/install")
async def install_plugin(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        result = await asyncio.to_thread(
            SERVICE.install,
            str(data.get("remote_url", "")),
            install_dependencies=bool(data.get("install_dependencies", True)),
        )
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/update-dependencies")
async def update_plugin_dependencies(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        result = await asyncio.to_thread(SERVICE.update_dependencies, str(data.get("id", "")))
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/restart")
async def restart_comfyui(request):
    try:
        _require_local_mutation(request)
        asyncio.get_running_loop().call_later(1.0, _restart_current_process)
        result = {"message": "ComfyUI 正在重新启动", "restart_scheduled": True}
        return _ok(result)
    except Exception as exc:
        return _error(exc)


@ROUTES.post("/universal-plugin-manager/v1/delete")
async def delete_plugin(request):
    try:
        _require_local_mutation(request)
        data = await _json(request)
        result = await asyncio.to_thread(SERVICE.delete, str(data.get("id", "")))
        return _ok(result)
    except Exception as exc:
        return _error(exc)

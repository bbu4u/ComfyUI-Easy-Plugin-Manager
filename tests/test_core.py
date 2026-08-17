from __future__ import annotations

import os
import subprocess
import shutil
import unittest
import uuid
from pathlib import Path

from core import PluginManagerError, PluginService


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {args}\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return result.stdout.strip()


class LocalMigrationService(PluginService):
    def _validate_github_url(self, remote_url: str) -> str:
        return remote_url


class CatalogService(PluginService):
    def _load_github_catalog(self):
        return {
            "custom_nodes": [
                {
                    "title": "Copied Plugin",
                    "files": ["https://github.com/example/CopiedPlugin"],
                }
            ]
        }


class LocalInstallService(LocalMigrationService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependencies_checked = False

    def _repository_name(self, remote_url: str) -> str:
        return "InstalledPlugin"

    def _install_dependencies(self, plugin_path: Path):
        self.dependencies_checked = True
        return {
            "requirements_found": False,
            "dependencies_installed": False,
            "dependency_files": [],
            "python_environment": None,
        }


class DependencyRecordingService(PluginService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pip_commands = []

    @staticmethod
    def _isolated_python_environment():
        return {"python_executable": "test-python", "environment_type": "test"}

    def _run(self, args, **kwargs):
        if "pip" in args and "install" in args:
            self.pip_commands.append(args)
            return subprocess.CompletedProcess(args, 0, "ok", "")
        return super()._run(args, **kwargs)


class PluginServiceTests(unittest.TestCase):
    def setUp(self):
        test_tmp = Path(os.environ.get("UPM_TEST_ROOT", Path(__file__).resolve().parent / "_runtime"))
        self.base = test_tmp / uuid.uuid4().hex
        self.base.mkdir(parents=True)
        self.custom_nodes = self.base / "custom_nodes"
        self.custom_nodes.mkdir()
        self.storage = self.base / "user" / "universal_plugin_manager"
        self.origin = self.base / "origin.git"
        self.source = self.base / "source"

        run("git", "init", "--bare", str(self.origin))
        run("git", "init", "-b", "main", str(self.source))
        run("git", "config", "user.name", "Test User", cwd=self.source)
        run("git", "config", "user.email", "test@example.com", cwd=self.source)
        (self.source / "node.py").write_text("VERSION = 1\n", encoding="utf-8")
        run("git", "add", "node.py", cwd=self.source)
        run("git", "commit", "-m", "initial", cwd=self.source)
        run("git", "tag", "v1.0.0", cwd=self.source)
        run("git", "remote", "add", "origin", str(self.origin), cwd=self.source)
        run("git", "push", "-u", "origin", "main", "--tags", cwd=self.source)
        run("git", "--git-dir", str(self.origin), "symbolic-ref", "HEAD", "refs/heads/main")

        self.plugin = self.custom_nodes / "ExamplePlugin"
        run("git", "clone", str(self.origin), str(self.plugin))
        (self.custom_nodes / "CopiedPlugin").mkdir()
        (self.custom_nodes / "single_node.py").write_text("pass\n", encoding="utf-8")
        self.service = PluginService([self.custom_nodes], self.storage)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def by_name(self, name: str):
        return next(item for item in self.service.scan() if item["name"] == name)

    def test_scan_classifies_git_directory_copy_and_single_file(self):
        managed = self.by_name("ExamplePlugin")
        copied = self.by_name("CopiedPlugin")
        single = self.by_name("single_node.py")
        self.assertTrue(managed["manageable"])
        self.assertEqual(managed["branch"], "main")
        self.assertFalse(copied["manageable"])
        self.assertIn("不是 Git", copied["reason"])
        self.assertFalse(single["manageable"])
        self.assertEqual(single["kind"], "file")

    def test_untracked_python_cache_does_not_mark_repository_dirty(self):
        cache = self.plugin / "__pycache__"
        cache.mkdir()
        (cache / "node.cpython-313.pyc").write_bytes(b"generated")
        plugin = self.by_name("ExamplePlugin")
        self.assertFalse(plugin["dirty"])
        self.assertEqual(plugin["ignored_generated_count"], 1)

    def test_parent_git_repository_does_not_make_child_plugin_manageable(self):
        comfy_root = self.base / "nested-case" / "ComfyUI"
        nodes_root = comfy_root / "custom_nodes"
        copied = nodes_root / "CopiedInsideComfy"
        copied.mkdir(parents=True)
        run("git", "init", "-b", "main", str(comfy_root))
        run("git", "remote", "add", "origin", "https://github.com/Comfy-Org/ComfyUI.git", cwd=comfy_root)
        service = PluginService([nodes_root], self.storage)
        plugin = service.scan()[0]
        self.assertFalse(plugin["manageable"])
        self.assertIn("不是 Git", plugin["reason"])

    def test_update_fast_forwards_and_creates_backup_ref(self):
        plugin = self.by_name("ExamplePlugin")
        before = plugin["commit"]
        (self.source / "node.py").write_text("VERSION = 2\n", encoding="utf-8")
        run("git", "add", "node.py", cwd=self.source)
        run("git", "commit", "-m", "version two", cwd=self.source)
        run("git", "push", cwd=self.source)

        result = self.service.update(plugin["id"])
        self.assertTrue(result["changed"])
        self.assertNotEqual(before, result["after"])
        backup = run("git", "rev-parse", result["backup_ref"], cwd=self.plugin)
        self.assertEqual(backup, before)

    def test_batch_update_continues_and_reports_results(self):
        plugin = self.by_name("ExamplePlugin")
        (self.source / "node.py").write_text("VERSION = 4\n", encoding="utf-8")
        run("git", "add", "node.py", cwd=self.source)
        run("git", "commit", "-m", "batch update", cwd=self.source)
        run("git", "push", cwd=self.source)

        result = self.service.batch_update([plugin["id"], "missing-id"])

        self.assertEqual(len(result["successes"]), 1)
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["successes"][0]["name"], "ExamplePlugin")

    def test_dirty_repository_can_be_stashed_then_updated_or_switched(self):
        plugin = self.by_name("ExamplePlugin")
        (self.plugin / "local.txt").write_text("local\n", encoding="utf-8")
        with self.assertRaises(PluginManagerError) as context:
            self.service.update(plugin["id"])
        self.assertEqual(context.exception.code, "dirty_confirmation_required")

        (self.source / "node.py").write_text("VERSION = 2\n", encoding="utf-8")
        run("git", "add", "node.py", cwd=self.source)
        run("git", "commit", "-m", "version two", cwd=self.source)
        run("git", "push", cwd=self.source)
        result = self.service.update(plugin["id"], allow_dirty=True)
        self.assertTrue(result["changed"])
        self.assertTrue(result["stash_created"])
        self.assertIn("UPM update", run("git", "stash", "list", cwd=self.plugin))
        self.assertFalse(result["plugin"]["dirty"])

        (self.plugin / "another-local.txt").write_text("local again\n", encoding="utf-8")
        with self.assertRaises(PluginManagerError) as context:
            self.service.switch_version(plugin["id"], "tag", "v1.0.0")
        self.assertEqual(context.exception.code, "dirty_confirmation_required")

        result = self.service.switch_version(plugin["id"], "tag", "v1.0.0", allow_dirty=True)
        self.assertTrue(result["stash_created"])
        self.assertIn("UPM version switch", run("git", "stash", "list", cwd=self.plugin))
        self.assertFalse(result["plugin"]["dirty"])

    def test_confirmed_dirty_update_does_not_stash_when_already_current(self):
        plugin = self.by_name("ExamplePlugin")
        local_file = self.plugin / "local.txt"
        local_file.write_text("keep this\n", encoding="utf-8")

        result = self.service.update(plugin["id"], allow_dirty=True)

        self.assertFalse(result["changed"])
        self.assertFalse(result["stash_created"])
        self.assertIsNone(result["backup_ref"])
        self.assertEqual(local_file.read_text(encoding="utf-8"), "keep this\n")
        self.assertEqual(run("git", "stash", "list", cwd=self.plugin), "")

    def test_versions_and_switch_to_tag(self):
        plugin = self.by_name("ExamplePlugin")
        versions = self.service.versions(plugin["id"])
        self.assertIn("main", versions["branches"])
        self.assertIn("v1.0.0", versions["tags"])
        result = self.service.switch_version(plugin["id"], "tag", "v1.0.0")
        self.assertEqual(result["plugin"]["tag"], "v1.0.0")

    def test_check_updates_fetches_remote_and_marks_behind_repository(self):
        plugin = self.by_name("ExamplePlugin")
        self.assertFalse(plugin["update_available"])
        (self.source / "node.py").write_text("VERSION = 3\n", encoding="utf-8")
        run("git", "add", "node.py", cwd=self.source)
        run("git", "commit", "-m", "a deliberately long update explanation for checking", cwd=self.source)
        run("git", "push", cwd=self.source)

        result = self.service.check_updates(max_workers=2)
        refreshed = next(item for item in result["plugins"] if item["name"] == "ExamplePlugin")
        self.assertTrue(refreshed["update_available"])
        self.assertEqual(refreshed["behind_count"], 1)
        self.assertEqual(result["summary"]["updatable"], 1)

    def test_migrate_backs_up_copy_and_replaces_it_with_clone(self):
        service = LocalMigrationService([self.custom_nodes], self.storage)
        plugin = next(item for item in service.scan() if item["name"] == "CopiedPlugin")
        marker = self.custom_nodes / "CopiedPlugin" / "local-only.txt"
        marker.write_text("keep me\n", encoding="utf-8")
        result = service.migrate(plugin["id"], str(self.origin))
        self.assertTrue((self.custom_nodes / "CopiedPlugin" / ".git").exists())
        self.assertTrue(Path(result["backup_path"], "local-only.txt").exists())
        self.assertTrue(result["plugin"]["manageable"])

    def test_detect_github_reports_found_and_not_found(self):
        unknown = self.custom_nodes / "UnknownPlugin"
        unknown.mkdir()
        service = CatalogService([self.custom_nodes], self.storage)
        copied = next(item for item in service.scan() if item["name"] == "CopiedPlugin")
        unknown_plugin = next(item for item in service.scan() if item["name"] == "UnknownPlugin")

        result = service.detect_github([copied["id"], unknown_plugin["id"]])

        self.assertEqual(result["found"][0]["url"], "https://github.com/example/CopiedPlugin")
        self.assertEqual(result["not_found"][0]["name"], "UnknownPlugin")

    def test_batch_migrate_continues_and_reports_results(self):
        service = LocalMigrationService([self.custom_nodes], self.storage)
        plugin = next(item for item in service.scan() if item["name"] == "CopiedPlugin")

        result = service.batch_migrate(
            [
                {"id": plugin["id"], "url": str(self.origin)},
                {"id": "missing-id", "url": str(self.origin)},
            ]
        )

        self.assertEqual(len(result["successes"]), 1)
        self.assertEqual(len(result["failures"]), 1)
        self.assertTrue((self.custom_nodes / "CopiedPlugin" / ".git").exists())

    def test_install_clones_plugin_and_checks_dependencies(self):
        service = LocalInstallService([self.custom_nodes], self.storage)

        result = service.install(str(self.origin))

        installed = self.custom_nodes / "InstalledPlugin"
        self.assertTrue((installed / ".git").exists())
        self.assertTrue(service.dependencies_checked)
        self.assertTrue(result["plugin"]["manageable"])
        self.assertFalse(result["requirements_found"])

    def test_install_refuses_existing_plugin_directory(self):
        service = LocalInstallService([self.custom_nodes], self.storage)
        (self.custom_nodes / "InstalledPlugin").mkdir()

        with self.assertRaises(PluginManagerError) as context:
            service.install(str(self.origin))

        self.assertEqual(context.exception.code, "plugin_already_exists")

    def test_install_can_skip_dependency_installation(self):
        service = LocalInstallService([self.custom_nodes], self.storage)

        result = service.install(str(self.origin), install_dependencies=False)

        self.assertFalse(service.dependencies_checked)
        self.assertFalse(result["dependencies_installed"])

    def test_update_dependencies_finds_supported_requirement_files(self):
        plugin_path = self.custom_nodes / "CopiedPlugin"
        (plugin_path / "requirements.txt").write_text("\n", encoding="utf-8")
        requirement_dir = plugin_path / "requirements"
        requirement_dir.mkdir()
        (requirement_dir / "windows.txt").write_text("\n", encoding="utf-8")
        service = DependencyRecordingService([self.custom_nodes], self.storage)
        plugin = next(item for item in service.scan() if item["name"] == "CopiedPlugin")

        result = service.update_dependencies(plugin["id"])

        self.assertTrue(result["dependencies_installed"])
        self.assertEqual(len(result["dependency_files"]), 2)
        self.assertEqual(len(service.pip_commands), 2)
        self.assertTrue(all("--isolated" in command for command in service.pip_commands))

    def test_delete_moves_plugin_to_trash(self):
        plugin = self.by_name("CopiedPlugin")
        result = self.service.delete(plugin["id"])
        self.assertFalse((self.custom_nodes / "CopiedPlugin").exists())
        self.assertTrue(Path(result["trash_path"]).exists())

    def test_protected_plugin_cannot_be_deleted(self):
        protected = self.custom_nodes / "ProtectedManager"
        protected.mkdir()
        service = PluginService([self.custom_nodes], self.storage, protected_paths=[protected])
        plugin = next(item for item in service.scan() if item["name"] == "ProtectedManager")
        with self.assertRaises(PluginManagerError) as context:
            service.delete(plugin["id"])
        self.assertEqual(context.exception.code, "protected_plugin")


if __name__ == "__main__":
    unittest.main()

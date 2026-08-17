import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const BASE = "/universal-plugin-manager/v1";

const style = document.createElement("style");
style.textContent = `
.upm-sidebar-icon:before { content: "🧩"; }
.upm-root { height:100%; display:flex; flex-direction:column; color:var(--fg-color,#ddd); background:var(--bg-color,#202020); font:13px/1.45 Inter,system-ui,sans-serif; }
.upm-head { padding:14px 12px 10px; border-bottom:1px solid var(--border-color,#3a3a3a); background:linear-gradient(150deg,rgba(99,102,241,.18),transparent 62%); }
.upm-title-row { display:flex; align-items:center; gap:8px; }
.upm-title { margin:0; font-size:16px; font-weight:700; flex:1; }
.upm-refresh { border:1px solid var(--border-color,#555); background:var(--comfy-input-bg,#2d2d2d); color:inherit; border-radius:7px; cursor:pointer; padding:5px 9px; }
.upm-refresh:hover { border-color:#818cf8; }
.upm-refresh.restart { border-color:#f59e0b; background:#92400e; color:#fff; }
.upm-search-wrap { position:relative; margin-top:10px; }
.upm-search { box-sizing:border-box; width:100%; padding:8px 10px 8px 30px; border:1px solid var(--border-color,#52525b); border-radius:8px; background:var(--comfy-input-bg,#252525); color:inherit; outline:none; }
.upm-search:focus { border-color:#818cf8; box-shadow:0 0 0 2px rgba(99,102,241,.16); }
.upm-search-icon { position:absolute; left:10px; top:50%; transform:translateY(-50%); opacity:.6; pointer-events:none; }
.upm-tabs { display:flex; gap:4px; padding:8px 8px; overflow-x:auto; border-bottom:1px solid var(--border-color,#333); }
.upm-tab { flex:0 0 auto; padding:6px 8px; border:0; border-radius:7px; color:inherit; background:transparent; cursor:pointer; white-space:nowrap; font-size:11px; }
.upm-tab.active { color:#fff; background:#4f46e5; }
.upm-toolbar { min-height:0; display:flex; align-items:center; gap:8px; padding:7px 8px; border-bottom:1px solid var(--border-color,#333); }
.upm-toolbar:empty { display:none; }
.upm-toolbar-label { display:flex; align-items:center; gap:5px; white-space:nowrap; }
.upm-toolbar-spacer { flex:1; }
.upm-selection-count { color:#a1a1aa; font-size:11px; }
.upm-list { flex:1; overflow:auto; padding:6px 8px; }
.upm-empty,.upm-loading { padding:28px 12px; text-align:center; opacity:.7; }
.upm-card { min-width:0; display:flex; align-items:center; gap:8px; margin-bottom:5px; padding:7px 8px; border:1px solid var(--border-color,#3f3f46); border-radius:8px; background:var(--comfy-input-bg,#292929); }
.upm-card.update { border-color:rgba(99,102,241,.7); }
.upm-card-name { min-width:36px; flex:1; padding:0; border:0; background:transparent; color:inherit; font:inherit; font-weight:600; text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer; }
.upm-card-name:hover { color:#a5b4fc; text-decoration:underline; }
.upm-card-name:focus-visible { outline:2px solid #818cf8; outline-offset:2px; border-radius:3px; }
.upm-copy-name { flex:0 0 auto; width:24px; height:24px; display:grid; place-items:center; padding:0; border:0; border-radius:5px; background:transparent; color:#a1a1aa; cursor:pointer; font-size:14px; }
.upm-copy-name:hover { color:#fff; background:rgba(99,102,241,.2); }
.upm-copy-name:focus-visible { outline:2px solid #818cf8; outline-offset:1px; }
.upm-check { flex:0 0 auto; margin:0; accent-color:#6366f1; cursor:pointer; }
.upm-actions { flex:0 0 auto; display:flex; gap:3px; flex-wrap:nowrap; }
.upm-btn { border:1px solid var(--border-color,#555); border-radius:6px; padding:3px 6px; background:rgba(255,255,255,.04); color:inherit; cursor:pointer; font-size:11px; white-space:nowrap; }
.upm-btn:hover:not(:disabled) { border-color:#818cf8; background:rgba(99,102,241,.14); }
.upm-btn.primary { background:#4338ca; border-color:#6366f1; color:white; }
.upm-btn.danger { color:#fca5a5; }
.upm-btn:disabled { opacity:.42; cursor:not-allowed; }
.upm-notice { margin:8px 10px 0; padding:8px 9px; border-radius:7px; background:rgba(245,158,11,.11); color:#fcd34d; font-size:11px; }
.upm-notice-link { margin-left:6px; padding:0; border:0; background:transparent; color:#fde68a; text-decoration:underline; cursor:pointer; font:inherit; }
.upm-overlay { position:fixed; inset:0; z-index:100000; display:grid; place-items:center; padding:20px; background:rgba(0,0,0,.68); }
.upm-dialog { width:min(620px,96vw); max-height:82vh; overflow-y:auto; overflow-x:hidden; border:1px solid #4b5563; border-radius:13px; background:#202124; color:#eee; box-shadow:0 24px 80px rgba(0,0,0,.55); }
.upm-dialog-head { display:flex; align-items:center; gap:8px; padding:14px 16px; border-bottom:1px solid #3f3f46; }
.upm-dialog-head h3 { flex:1; margin:0; font-size:16px; }
.upm-dialog-body { padding:16px; }
.upm-dialog-foot { display:flex; justify-content:flex-end; gap:8px; padding:12px 16px; border-top:1px solid #3f3f46; }
.upm-field { display:block; margin-bottom:12px; }
.upm-field span { display:block; margin-bottom:5px; color:#c7c7cc; }
.upm-input,.upm-select { box-sizing:border-box; display:block; min-width:0; max-width:100%; width:100%; padding:8px 9px; border:1px solid #52525b; border-radius:7px; background:#18181b; color:#eee; text-overflow:ellipsis; }
.upm-help { color:#a1a1aa; font-size:12px; }
.upm-result-section + .upm-result-section { margin-top:16px; }
.upm-result-title { margin:0 0 7px; font-size:13px; }
.upm-result-list { display:flex; flex-direction:column; gap:5px; max-height:42vh; overflow:auto; }
.upm-result-row { display:flex; align-items:center; gap:8px; min-width:0; padding:7px 8px; border:1px solid #3f3f46; border-radius:7px; background:#18181b; }
.upm-result-main { min-width:0; flex:1; }
.upm-result-name { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.upm-result-meta { display:block; color:#a1a1aa; font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.upm-result-link { color:#a5b4fc; text-decoration:none; }
.upm-result-link:hover { text-decoration:underline; }
.upm-spinner { display:inline-block; width:12px; height:12px; border:2px solid currentColor; border-right-color:transparent; border-radius:50%; animation:upm-spin .7s linear infinite; vertical-align:-2px; }
@keyframes upm-spin { to { transform:rotate(360deg); } }
`;
document.head.appendChild(style);

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

async function request(path, options = {}) {
    const response = await api.fetchApi(`${BASE}${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    let payload;
    try { payload = await response.json(); }
    catch { throw new Error(`服务器返回了无效响应 (${response.status})`); }
    if (!response.ok || !payload.ok) {
        throw new Error(payload?.error?.message || `操作失败 (${response.status})`);
    }
    return payload;
}

function notify(message, type = "info") {
    const toast = app.extensionManager?.toast;
    if (toast?.add) {
        toast.add({ severity: type === "error" ? "error" : "success", summary: type === "error" ? "操作失败" : "插件管理器", detail: message, life: 5000 });
    } else {
        console[type === "error" ? "error" : "log"](`[Universal Plugin Manager] ${message}`);
    }
}

function modal(title) {
    const overlay = el("div", "upm-overlay");
    const dialog = el("div", "upm-dialog");
    const head = el("div", "upm-dialog-head");
    head.append(el("h3", "", title));
    const close = el("button", "upm-btn", "关闭");
    const body = el("div", "upm-dialog-body");
    const foot = el("div", "upm-dialog-foot");
    head.append(close);
    dialog.append(head, body, foot);
    overlay.append(dialog);
    document.body.append(overlay);
    const destroy = () => overlay.remove();
    close.onclick = destroy;
    overlay.addEventListener("click", (event) => { if (event.target === overlay) destroy(); });
    return { overlay, body, foot, destroy };
}

function button(text, action, className = "") {
    const node = el("button", `upm-btn ${className}`.trim(), text);
    node.onclick = action;
    return node;
}

function truncate(value, maxLength = 58) {
    const text = String(value || "");
    return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

class PluginPanel {
    constructor(root) {
        this.root = root;
        this.plugins = [];
        this.summary = { total: 0, updatable: 0, git: 0, non_git: 0 };
        this.filter = "updatable";
        this.query = "";
        this.checkingUpdates = false;
        this.busy = new Set();
        this.selectedUpdates = new Set();
        this.updateFailures = [];
        this.backgroundError = "";
        this.restartNeeded = localStorage.getItem("upm-restart-needed") === "1";
        this.processId = null;
        this.build();
        this.load();
    }

    build() {
        this.root.className = "upm-root";
        this.root.replaceChildren();
        const head = el("div", "upm-head");
        const titleRow = el("div", "upm-title-row");
        titleRow.append(el("h2", "upm-title", "通用插件管理器"));
        const install = el("button", "upm-refresh", "安装插件");
        install.onclick = () => this.installPlugin();
        this.restartButton = el("button", "upm-refresh restart", "重新启动");
        this.restartButton.onclick = () => this.restartComfyUI();
        this.restartButton.hidden = !this.restartNeeded;
        const refresh = el("button", "upm-refresh", "刷新");
        refresh.onclick = () => this.load();
        titleRow.append(install, this.restartButton, refresh);
        const searchWrap = el("div", "upm-search-wrap");
        searchWrap.append(el("span", "upm-search-icon", "⌕"));
        this.search = el("input", "upm-search");
        this.search.type = "search";
        this.search.placeholder = "搜索插件名称";
        this.search.oninput = () => { this.query = this.search.value.trim().toLocaleLowerCase(); this.render(); };
        searchWrap.append(this.search);
        head.append(titleRow, searchWrap);
        this.tabs = el("div", "upm-tabs");
        this.toolbar = el("div", "upm-toolbar");
        this.notice = el("div", "upm-notice", "升级、切换版本或删除后，需要重启 ComfyUI 才会完全生效。删除操作会移入回收站。 ");
        this.list = el("div", "upm-list");
        this.root.append(head, this.tabs, this.toolbar, this.notice, this.list);
        this.renderTabs();
    }

    renderTabs() {
        this.tabs.replaceChildren();
        const definitions = [
            ["updatable", `可更新（${this.summary.updatable}）${this.checkingUpdates ? "…" : ""}`],
            ["git", `Git安装（${this.summary.git}）`],
            ["non_git", `非Git安装项目（${this.summary.non_git}）`],
            ["all", `全部（${this.summary.total}）`],
        ];
        for (const [key, label] of definitions) {
            const tab = el("button", `upm-tab${this.filter === key ? " active" : ""}`, label);
            tab.dataset.filter = key;
            tab.onclick = () => { this.filter = key; this.renderTabs(); this.render(); };
            this.tabs.append(tab);
        }
    }

    async load(checkRemote = true) {
        this.list.replaceChildren(el("div", "upm-loading", "正在扫描插件…"));
        try {
            const payload = await request("/plugins");
            this.plugins = payload.data;
            this.summary = payload.summary;
            const storedProcessId = localStorage.getItem("upm-restart-process-id");
            if (this.restartNeeded && storedProcessId && storedProcessId !== String(payload.process_id)) {
                this.clearRestartNeeded();
            }
            this.processId = String(payload.process_id || "");
            const validIds = new Set(this.plugins.filter((item) => item.manageable && item.update_available).map((item) => item.id));
            this.selectedUpdates = new Set([...this.selectedUpdates].filter((id) => validIds.has(id)));
            this.renderTabs();
            this.render();
            if (checkRemote) await this.checkUpdates();
        } catch (error) {
            this.list.replaceChildren(el("div", "upm-empty", error.message));
        }
    }

    async checkUpdates() {
        this.checkingUpdates = true;
        this.updateFailures = [];
        this.backgroundError = "";
        this.renderTabs();
        try {
            const payload = await request("/check-updates", { method: "POST", body: "{}" });
            this.plugins = payload.data.plugins;
            this.summary = payload.data.summary;
            const validIds = new Set(this.plugins.filter((item) => item.manageable && item.update_available).map((item) => item.id));
            this.selectedUpdates = new Set([...this.selectedUpdates].filter((id) => validIds.has(id)));
            this.updateFailures = payload.data.failures;
        } catch (error) {
            this.backgroundError = `自动检查更新未完成：${error.message}`;
        } finally {
            this.checkingUpdates = false;
            this.renderTabs();
            this.render();
        }
    }

    visiblePlugins() {
        let plugins = this.plugins;
        if (this.filter === "updatable") plugins = plugins.filter((x) => x.manageable && x.update_available);
        else if (this.filter === "git") plugins = plugins.filter((x) => x.manageable);
        else if (this.filter === "non_git") plugins = plugins.filter((x) => !x.manageable);
        if (this.query) plugins = plugins.filter((x) => x.name.toLocaleLowerCase().includes(this.query));
        return plugins;
    }

    render() {
        this.list.replaceChildren();
        const plugins = this.visiblePlugins();
        const noticeText = this.filter === "updatable"
            ? "此处升级只更新插件项目代码，不会安装依赖。需要处理依赖时，请到 Git安装、非Git安装项目或全部栏目点击“更新依赖”。"
            : "升级、切换版本、安装依赖或删除后，可使用顶部“重新启动”让 ComfyUI 在当前命令行窗口内重启。";
        this.notice.replaceChildren(document.createTextNode(noticeText));
        if (this.updateFailures.length) {
            const details = el("button", "upm-notice-link", `${this.updateFailures.length} 个仓库未能检查更新，查看详情`);
            details.onclick = () => this.showUpdateCheckFailures();
            this.notice.append(document.createElement("br"), details);
        } else if (this.backgroundError) {
            this.notice.append(document.createElement("br"), document.createTextNode(this.backgroundError));
        }
        this.renderToolbar(plugins);
        if (!plugins.length) {
            this.list.append(el("div", "upm-empty", "没有符合条件的插件"));
            return;
        }
        for (const plugin of plugins) this.list.append(this.renderCard(plugin));
    }

    renderToolbar(plugins) {
        this.toolbar.replaceChildren();
        if (this.filter === "updatable" && plugins.length) {
            const selectAll = el("input", "upm-check");
            selectAll.type = "checkbox";
            const selectedCount = plugins.filter((plugin) => this.selectedUpdates.has(plugin.id)).length;
            selectAll.checked = selectedCount === plugins.length;
            selectAll.indeterminate = selectedCount > 0 && selectedCount < plugins.length;
            selectAll.onchange = () => {
                for (const plugin of plugins) {
                    if (selectAll.checked) this.selectedUpdates.add(plugin.id);
                    else this.selectedUpdates.delete(plugin.id);
                }
                this.render();
            };
            const label = el("label", "upm-toolbar-label");
            label.append(selectAll, el("span", "", "全选"));
            const count = el("span", "upm-selection-count", `已选 ${this.selectedUpdates.size} 个`);
            const update = button("更新所选", () => this.batchUpdateSelected(), "primary");
            update.disabled = this.selectedUpdates.size === 0;
            this.toolbar.append(label, count, el("span", "upm-toolbar-spacer"), update);
        } else if (this.filter === "non_git" && plugins.length) {
            const eligible = plugins.filter((plugin) => plugin.kind === "directory" && !plugin.protected);
            this.toolbar.append(
                el("span", "upm-selection-count", "自动匹配名称明确对应的 GitHub 仓库"),
                el("span", "upm-toolbar-spacer"),
            );
            const detect = button("检测 GitHub 链接", () => this.detectGithub(eligible), "primary");
            detect.disabled = eligible.length === 0;
            this.toolbar.append(detect);
        }
    }

    renderCard(plugin) {
        const card = el("section", `upm-card${plugin.update_available ? " update" : ""}`);
        if (this.filter === "updatable") {
            const checkbox = el("input", "upm-check");
            checkbox.type = "checkbox";
            checkbox.checked = this.selectedUpdates.has(plugin.id);
            checkbox.setAttribute("aria-label", `选择 ${plugin.name}`);
            checkbox.onchange = () => {
                if (checkbox.checked) this.selectedUpdates.add(plugin.id);
                else this.selectedUpdates.delete(plugin.id);
                this.render();
            };
            card.append(checkbox);
        }
        const name = el("button", "upm-card-name", plugin.name);
        name.type = "button";
        name.onclick = () => this.openPluginPage(plugin);
        name.setAttribute("aria-label", plugin.manageable && plugin.web_url ? `打开 ${plugin.name} 项目页面` : `搜索 ${plugin.name} 的 GitHub 项目`);
        if (plugin.manageable) {
            const version = plugin.tag || plugin.branch || "detached";
            name.title = `${plugin.name}\n${version} · ${plugin.short_commit || "未知提交"}${plugin.dirty ? " · 有本地修改" : ""}\n${plugin.remote || ""}\n点击打开项目页面`;
        } else {
            name.title = `${plugin.name}\n${plugin.reason || "无法进行 Git 管理"}\n点击搜索 GitHub 项目`;
        }
        const copyName = el("button", "upm-copy-name", "⧉");
        copyName.type = "button";
        copyName.title = "复制项目名称";
        copyName.setAttribute("aria-label", `复制项目名称 ${plugin.name}`);
        copyName.onclick = () => this.copyPluginName(plugin.name, copyName);
        const actions = el("div", "upm-actions");
        const isBusy = this.busy.has(plugin.id);
        if (plugin.manageable) {
            actions.append(
                button("升级", () => this.updatePlugin(plugin), "primary"),
                button("版本", () => this.chooseVersion(plugin)),
                button("GitHub", () => window.open(plugin.web_url, "_blank", "noopener,noreferrer")),
                button("删除", () => this.deletePlugin(plugin), "danger"),
            );
            actions.children[2].disabled = !plugin.web_url;
        } else {
            actions.append(
                button("搜索", () => this.searchPlugin(plugin)),
                button("切换为 Git 管理", () => this.migratePlugin(plugin), "primary"),
                button("删除", () => this.deletePlugin(plugin), "danger"),
            );
            actions.children[1].disabled = plugin.kind !== "directory" || plugin.protected;
        }
        if (this.filter !== "updatable" && plugin.kind === "directory" && !plugin.protected) {
            actions.insertBefore(button("更新依赖", () => this.updateDependencies(plugin)), actions.lastElementChild);
        }
        for (const action of actions.children) action.disabled ||= isBusy || plugin.protected;
        card.append(name, copyName, actions);
        return card;
    }

    async copyPluginName(name, trigger) {
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(name);
            } else {
                const textarea = document.createElement("textarea");
                try {
                    textarea.value = name;
                    textarea.style.position = "fixed";
                    textarea.style.opacity = "0";
                    document.body.append(textarea);
                    textarea.select();
                    if (!document.execCommand("copy")) throw new Error("浏览器拒绝复制操作");
                } finally {
                    textarea.remove();
                }
            }
            trigger.textContent = "✓";
            trigger.title = "已复制";
            setTimeout(() => {
                trigger.textContent = "⧉";
                trigger.title = "复制项目名称";
            }, 1200);
        } catch (error) {
            notify(`复制失败：${error.message}`, "error");
        }
    }

    showUpdateCheckFailures() {
        const dialog = modal("未能检查更新的仓库");
        dialog.body.append(el("p", "upm-help", "这些项目本次未能连接远程仓库，其他项目的检查结果不受影响。"));
        const list = el("div", "upm-result-list");
        for (const item of this.updateFailures) {
            const row = el("div", "upm-result-row");
            const main = el("span", "upm-result-main");
            main.append(el("span", "upm-result-name", item.name), el("span", "upm-result-meta", item.message));
            row.append(main);
            list.append(row);
        }
        dialog.body.append(list);
    }

    async batchUpdateSelected() {
        const selected = this.plugins.filter((plugin) => this.selectedUpdates.has(plugin.id));
        if (!selected.length) return;
        const dirtyCount = selected.filter((plugin) => plugin.dirty).length;
        let allowDirty = false;
        if (dirtyCount) {
            allowDirty = window.confirm(`所选 ${selected.length} 个插件中有 ${dirtyCount} 个存在本地修改。\n\n继续后，这些修改会分别保存到各自的 Git stash，再执行批量更新。确认继续吗？`);
            if (!allowDirty) return;
        }
        for (const plugin of selected) this.busy.add(plugin.id);
        this.render();
        try {
            const payload = await request("/batch-update", {
                method: "POST",
                body: JSON.stringify({ ids: selected.map((plugin) => plugin.id), allow_dirty: allowDirty }),
            });
            this.markRestartNeeded(payload.data);
            for (const item of payload.data.successes) this.selectedUpdates.delete(item.id);
            notify(payload.data.message, payload.data.failures.length ? "error" : "info");
            if (payload.data.failures.length) this.showBatchResults("批量更新结果", payload.data);
            await this.load(false);
        } catch (error) {
            notify(error.message, "error");
        } finally {
            for (const plugin of selected) this.busy.delete(plugin.id);
            this.render();
        }
    }

    async runBusy(plugin, operation) {
        this.busy.add(plugin.id);
        this.render();
        try { return await operation(); }
        finally { this.busy.delete(plugin.id); this.render(); }
    }

    async updatePlugin(plugin) {
        let allowDirty = false;
        if (plugin.dirty) {
            allowDirty = window.confirm("检测到本地修改。继续升级会先把全部修改（含未跟踪文件）保存到 Git stash，再更新插件。\n\n确认继续升级吗？");
            if (!allowDirty) return;
        }
        await this.runBusy(plugin, async () => {
            try {
                const payload = await request("/update", { method: "POST", body: JSON.stringify({ id: plugin.id, allow_dirty: allowDirty }) });
                this.markRestartNeeded(payload.data);
                notify(payload.data.stash_created ? `${payload.data.message}，本地修改已保存到 Git stash` : payload.data.message);
                await this.load(false);
            } catch (error) { notify(error.message, "error"); }
        });
    }

    async chooseVersion(plugin) {
        const dialog = modal(`切换版本 · ${plugin.name}`);
        dialog.body.append(el("div", "upm-loading", "正在获取远程分支和标签…"));
        try {
            const payload = await request(`/versions?id=${encodeURIComponent(plugin.id)}`);
            const versions = payload.data;
            dialog.body.replaceChildren();
            const field = el("label", "upm-field");
            field.append(el("span", "", "目标版本"));
            const select = el("select", "upm-select");
            const addGroup = (label, type, items, formatter) => {
                if (!items.length) return;
                const group = document.createElement("optgroup");
                group.label = label;
                for (const item of items) {
                    const option = document.createElement("option");
                    option.value = `${type}:${typeof item === "string" ? item : item.sha}`;
                    option.textContent = formatter(item);
                    group.append(option);
                }
                select.append(group);
            };
            addGroup("分支", "branch", versions.branches, (x) => truncate(x));
            addGroup("标签", "tag", versions.tags, (x) => truncate(x));
            addGroup("最近提交", "commit", versions.commits, (x) => `${x.short} · ${x.date} · ${truncate(x.subject, 52)}`);
            field.append(select);
            dialog.body.append(field);
            const confirm = button("切换并重启后生效", async () => {
                const separator = select.value.indexOf(":");
                const targetType = select.value.slice(0, separator);
                const target = select.value.slice(separator + 1);
                let allowDirty = false;
                if (plugin.dirty) {
                    allowDirty = window.confirm("检测到本地修改。继续切换会先把全部修改（含未跟踪文件）保存到 Git stash。\n\n确认继续切换版本吗？");
                    if (!allowDirty) return;
                }
                confirm.disabled = true;
                confirm.innerHTML = '<span class="upm-spinner"></span> 切换中';
                try {
                    const result = await request("/switch", { method: "POST", body: JSON.stringify({ id: plugin.id, target_type: targetType, target, allow_dirty: allowDirty }) });
                    this.markRestartNeeded(result.data);
                    notify(result.data.stash_created ? `${result.data.message}，本地修改已保存到 Git stash` : result.data.message);
                    dialog.destroy();
                    await this.load(false);
                } catch (error) {
                    notify(error.message, "error");
                    confirm.disabled = false;
                    confirm.textContent = "切换并重启后生效";
                }
            }, "primary");
            confirm.disabled = !select.options.length;
            dialog.foot.append(confirm);
        } catch (error) {
            dialog.body.replaceChildren(el("div", "upm-empty", error.message));
        }
    }

    searchPlugin(plugin) {
        const query = encodeURIComponent(`${plugin.name} github`);
        window.open(`https://www.google.com/search?q=${query}`, "_blank", "noopener,noreferrer");
    }

    openPluginPage(plugin) {
        if (plugin.manageable && plugin.web_url) {
            window.open(plugin.web_url, "_blank", "noopener,noreferrer");
        } else {
            this.searchPlugin(plugin);
        }
    }

    async detectGithub(plugins) {
        if (!plugins.length) return;
        const dialog = modal("检测非 Git 插件的 GitHub 项目");
        dialog.body.append(el("div", "upm-loading", `正在检测 ${plugins.length} 个插件，请稍候…`));
        try {
            const payload = await request("/detect-github", {
                method: "POST",
                body: JSON.stringify({ ids: plugins.map((plugin) => plugin.id) }),
            });
            const { found, not_found: notFound } = payload.data;
            dialog.body.replaceChildren();
            const selected = new Set();
            const foundSection = el("section", "upm-result-section");
            const foundTitle = el("h4", "upm-result-title", `已找到（${found.length}）`);
            const foundList = el("div", "upm-result-list");
            const convert = button("转换所选并更新到最新", async () => {
                const items = found.filter((item) => selected.has(item.id)).map((item) => ({ id: item.id, url: item.url }));
                if (!items.length) return;
                if (!window.confirm(`确定转换所选 ${items.length} 个插件吗？\n\n原目录会先完整备份，再替换为检测到的 GitHub 仓库最新版本。`)) return;
                convert.disabled = true;
                convert.innerHTML = '<span class="upm-spinner"></span> 转换中';
                try {
                    const result = await request("/batch-migrate", { method: "POST", body: JSON.stringify({ items }) });
                    this.markRestartNeeded(result.data);
                    dialog.destroy();
                    notify(result.data.message, result.data.failures.length ? "error" : "info");
                    if (result.data.failures.length) this.showBatchResults("批量转换结果", result.data);
                    await this.load(false);
                } catch (error) {
                    notify(error.message, "error");
                    convert.disabled = false;
                    convert.textContent = "转换所选并更新到最新";
                }
            }, "primary");
            const updateConvertState = () => {
                convert.disabled = selected.size === 0;
                convert.textContent = `转换所选并更新到最新（${selected.size}）`;
            };

            if (found.length) {
                const selectAll = el("input", "upm-check");
                selectAll.type = "checkbox";
                selectAll.onchange = () => {
                    for (const item of found) {
                        if (selectAll.checked) selected.add(item.id);
                        else selected.delete(item.id);
                    }
                    for (const checkbox of foundList.querySelectorAll("input[type=checkbox]")) checkbox.checked = selectAll.checked;
                    updateConvertState();
                };
                const allLabel = el("label", "upm-toolbar-label");
                allLabel.append(selectAll, el("span", "", "全选已找到项目"));
                foundSection.append(foundTitle, allLabel);
                for (const item of found) {
                    const row = el("label", "upm-result-row");
                    const checkbox = el("input", "upm-check");
                    checkbox.type = "checkbox";
                    checkbox.onchange = () => {
                        if (checkbox.checked) selected.add(item.id);
                        else selected.delete(item.id);
                        selectAll.checked = selected.size === found.length;
                        selectAll.indeterminate = selected.size > 0 && selected.size < found.length;
                        updateConvertState();
                    };
                    const main = el("span", "upm-result-main");
                    main.append(el("span", "upm-result-name", item.name));
                    const link = el("a", "upm-result-meta upm-result-link", `${item.url} · ${item.source}`);
                    link.href = item.url;
                    link.target = "_blank";
                    link.rel = "noopener noreferrer";
                    link.onclick = (event) => event.stopPropagation();
                    main.append(link);
                    row.append(checkbox, main);
                    foundList.append(row);
                }
                foundSection.append(foundList);
            } else {
                foundSection.append(foundTitle, el("div", "upm-empty", "没有找到名称明确匹配的仓库"));
            }
            dialog.body.append(foundSection);

            const missingSection = el("section", "upm-result-section");
            missingSection.append(el("h4", "upm-result-title", `未找到（${notFound.length}）`));
            const missingList = el("div", "upm-result-list");
            for (const item of notFound) {
                const row = el("div", "upm-result-row");
                const main = el("span", "upm-result-main");
                main.append(el("span", "upm-result-name", item.name), el("span", "upm-result-meta", item.reason));
                row.append(main, button("手动搜索", () => this.searchPlugin(item)));
                missingList.append(row);
            }
            if (notFound.length) missingSection.append(missingList);
            dialog.body.append(missingSection);
            updateConvertState();
            dialog.foot.append(convert);
        } catch (error) {
            dialog.body.replaceChildren(el("div", "upm-empty", error.message));
        }
    }

    showBatchResults(title, data) {
        const dialog = modal(title);
        const successSection = el("section", "upm-result-section");
        successSection.append(el("h4", "upm-result-title", `成功（${data.successes.length}）`));
        if (data.successes.length) {
            const list = el("div", "upm-result-list");
            for (const item of data.successes) list.append(el("div", "upm-result-row", item.name));
            successSection.append(list);
        }
        const failureSection = el("section", "upm-result-section");
        failureSection.append(el("h4", "upm-result-title", `失败（${data.failures.length}）`));
        if (data.failures.length) {
            const list = el("div", "upm-result-list");
            for (const item of data.failures) {
                const row = el("div", "upm-result-row");
                const main = el("span", "upm-result-main");
                main.append(el("span", "upm-result-name", item.name), el("span", "upm-result-meta", item.message));
                row.append(main);
                list.append(row);
            }
            failureSection.append(list);
        }
        dialog.body.append(successSection, failureSection);
    }

    markRestartNeeded(result) {
        if (!result?.restart_required) return;
        this.restartNeeded = true;
        localStorage.setItem("upm-restart-needed", "1");
        if (this.processId) localStorage.setItem("upm-restart-process-id", this.processId);
        if (this.restartButton) this.restartButton.hidden = false;
    }

    clearRestartNeeded() {
        this.restartNeeded = false;
        localStorage.removeItem("upm-restart-needed");
        localStorage.removeItem("upm-restart-process-id");
        if (this.restartButton) this.restartButton.hidden = true;
    }

    async restartComfyUI() {
        if (!window.confirm("确定现在重新启动 ComfyUI 吗？\n\n当前命令行窗口会保持打开，正在运行的任务可能会被中断。")) return;
        this.restartButton.disabled = true;
        this.restartButton.innerHTML = '<span class="upm-spinner"></span> 重启中';
        try {
            const payload = await request("/restart", { method: "POST", body: "{}" });
            this.clearRestartNeeded();
            notify(payload.data.message);
        } catch (error) {
            notify(error.message, "error");
            this.restartButton.disabled = false;
            this.restartButton.textContent = "重新启动";
        }
    }

    async updateDependencies(plugin) {
        if (!window.confirm(`确定为“${plugin.name}”安装或更新 requirements 依赖吗？\n\n只会使用 ComfyUI 当前的独立 Python 环境，不会安装到系统全局 Python。`)) return;
        await this.runBusy(plugin, async () => {
            try {
                const payload = await request("/update-dependencies", { method: "POST", body: JSON.stringify({ id: plugin.id }) });
                this.markRestartNeeded(payload.data);
                notify(payload.data.message);
            } catch (error) {
                notify(error.message, "error");
            }
        });
    }

    installPlugin() {
        const dialog = modal("安装 GitHub 插件");
        const field = el("label", "upm-field");
        field.append(el("span", "", "GitHub 仓库地址"));
        const input = el("input", "upm-input");
        input.placeholder = "https://github.com/owner/repository.git";
        input.autocomplete = "off";
        field.append(input);
        const dependencyOption = el("label", "upm-toolbar-label");
        const installDependencies = el("input", "upm-check");
        installDependencies.type = "checkbox";
        installDependencies.checked = true;
        dependencyOption.append(installDependencies, el("span", "", "同时安装依赖包"));
        dialog.body.append(
            field,
            dependencyOption,
            el("p", "upm-help", "插件会克隆到首个 custom_nodes 目录。勾选后，将使用 ComfyUI 当前的独立 Python 环境安装 requirements 依赖；不会使用系统全局 Python，也不会执行 install.py。"),
            el("p", "upm-help", "请只安装你信任的仓库；Python 依赖包的安装过程可能执行其构建代码，并可能改变当前环境中的包版本。"),
        );
        const confirm = button("安装插件及依赖", async () => {
            const remoteUrl = input.value.trim();
            if (!remoteUrl) { input.focus(); return; }
            const dependencyText = installDependencies.checked ? "并安装项目 requirements 依赖" : "但不安装项目依赖";
            if (!window.confirm(`确认安装此 GitHub 插件，${dependencyText}吗？\n\n安装完成后需要重启 ComfyUI。`)) return;
            confirm.disabled = true;
            confirm.innerHTML = '<span class="upm-spinner"></span> 克隆并安装依赖中';
            try {
                const payload = await request("/install", {
                    method: "POST",
                    body: JSON.stringify({ remote_url: remoteUrl, install_dependencies: installDependencies.checked }),
                });
                this.markRestartNeeded(payload.data);
                notify(`${payload.data.message}：${payload.data.path}`);
                dialog.destroy();
                await this.load(false);
            } catch (error) {
                notify(error.message, "error");
                confirm.disabled = false;
                confirm.textContent = "安装插件及依赖";
            }
        }, "primary");
        dialog.foot.append(confirm);
        input.onkeydown = (event) => { if (event.key === "Enter") confirm.click(); };
        setTimeout(() => input.focus(), 0);
    }

    migratePlugin(plugin) {
        const dialog = modal(`切换为 Git 管理 · ${plugin.name}`);
        const field = el("label", "upm-field");
        field.append(el("span", "", "GitHub 仓库地址"));
        const input = el("input", "upm-input");
        input.placeholder = "https://github.com/owner/repository.git";
        input.autocomplete = "off";
        field.append(input);
        dialog.body.append(
            field,
            el("p", "upm-help", "系统会先克隆仓库，成功后把当前目录完整移动到 user/universal_plugin_manager/backups，再用 Git 仓库替换。请确认搜索结果与插件确实对应。"),
        );
        dialog.foot.append(button("先搜索 GitHub", () => this.searchPlugin(plugin)));
        const confirm = button("确认迁移", async () => {
            if (!input.value.trim()) { input.focus(); return; }
            confirm.disabled = true;
            confirm.innerHTML = '<span class="upm-spinner"></span> 克隆并备份中';
            try {
                const payload = await request("/migrate", { method: "POST", body: JSON.stringify({ id: plugin.id, remote_url: input.value.trim() }) });
                this.markRestartNeeded(payload.data);
                notify(`${payload.data.message}：${payload.data.backup_path}`);
                dialog.destroy();
                await this.load(false);
            } catch (error) {
                notify(error.message, "error");
                confirm.disabled = false;
                confirm.textContent = "确认迁移";
            }
        }, "primary");
        dialog.foot.append(confirm);
        setTimeout(() => input.focus(), 0);
    }

    async deletePlugin(plugin) {
        if (!window.confirm(`确定移除插件“${plugin.name}”吗？\n\n文件会移入 user/universal_plugin_manager/trash，可手动恢复。`)) return;
        await this.runBusy(plugin, async () => {
            try {
                const payload = await request("/delete", { method: "POST", body: JSON.stringify({ id: plugin.id }) });
                this.markRestartNeeded(payload.data);
                notify(`${payload.data.message}：${payload.data.trash_path}`);
                await this.load(false);
            } catch (error) { notify(error.message, "error"); }
        });
    }
}

app.registerExtension({
    name: "UniversalPluginManager.UI",
    async setup() {
        const sidebar = {
            id: "universal-plugin-manager",
            title: "插件管理",
            tooltip: "通用插件管理器",
            icon: "upm-sidebar-icon",
            type: "custom",
            render: (root) => new PluginPanel(root),
        };
        if (app.extensionManager?.registerSidebarTab) {
            app.extensionManager.registerSidebarTab(sidebar);
        } else {
            console.warn("[Universal Plugin Manager] 当前前端不支持自定义侧边栏，请升级 ComfyUI 前端。");
        }
    },
});

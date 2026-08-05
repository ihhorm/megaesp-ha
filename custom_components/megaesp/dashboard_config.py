from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from aiohttp.web import Response
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DASHBOARD_CONFIG_FILENAME, DASHBOARD_FILENAME, DEFAULT_DASHBOARD_CONFIG, DOMAIN
from .dashboard_builder import build_dashboard, dump_yaml


def dashboard_config_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DASHBOARD_CONFIG_FILENAME))


def dashboard_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DASHBOARD_FILENAME))


def load_dashboard_config(hass: HomeAssistant) -> dict:
    path = dashboard_config_path(hass)
    if not path.exists():
        return deepcopy(DEFAULT_DASHBOARD_CONFIG)
    try:
        data = json.loads(path.read_text())
    except ValueError:
        return deepcopy(DEFAULT_DASHBOARD_CONFIG)
    return merge_dashboard_config(data)


def merge_dashboard_config(data: dict) -> dict:
    merged = deepcopy(DEFAULT_DASHBOARD_CONFIG)
    merged.update(data)
    merged["section_titles"] = {
        **DEFAULT_DASHBOARD_CONFIG["section_titles"],
        **data.get("section_titles", {}),
    }
    return merged


def save_dashboard_config(hass: HomeAssistant, data: dict) -> dict:
    merged = merge_dashboard_config(data)
    dashboard_config_path(hass).write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
    return merged


def build_dashboard_entities(hass: HomeAssistant) -> list[dict]:
    registry = er.async_get(hass)
    entities: list[dict] = []
    for entry in registry.entities.values():
        if entry.platform != DOMAIN or entry.disabled_by:
            continue
        entities.append(
            {
                "entity_id": entry.entity_id,
                "platform": entry.platform,
                "disabled_by": entry.disabled_by,
                "original_name": entry.original_name,
                "device_id": entry.device_id,
            }
        )
    return entities


def build_dashboard_states(hass: HomeAssistant) -> dict[str, str]:
    return {state.entity_id: str(state.state) for state in hass.states.async_all()}


def regenerate_dashboard(hass: HomeAssistant, config: dict) -> None:
    dashboard = build_dashboard(build_dashboard_entities(hass), build_dashboard_states(hass), config)
    dashboard_path(hass).write_text("\n".join(dump_yaml(dashboard)) + "\n")


def html_shell(title: str, body: str, script: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e5e7eb; margin: 0; }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 20px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    p {{ color: #cbd5e1; margin: 0 0 16px; }}
    textarea, pre {{ width: 100%; min-height: 65vh; border-radius: 12px; border: 1px solid #94a3b8; background: #f8fafc; color: #0f172a; padding: 16px; font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; box-sizing: border-box; overflow: auto; white-space: pre-wrap; margin: 0; caret-color: #0f172a; }}
    textarea {{ resize: vertical; }}
    .actions {{ display: flex; gap: 12px; align-items: center; margin: 16px 0; flex-wrap: wrap; }}
    .split {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 16px; }}
    .panel-title {{ margin: 0 0 8px; color: #94a3b8; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .editor-shell {{ display: grid; grid-template-columns: 56px minmax(0, 1fr); gap: 0; border-radius: 12px; overflow: hidden; border: 1px solid #94a3b8; background: #f8fafc; }}
    .gutter {{ min-height: 65vh; padding: 16px 8px; background: #e2e8f0; color: #64748b; text-align: right; font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: pre; user-select: none; overflow: hidden; }}
    .editor-shell textarea {{ border: 0; border-left: 1px solid #cbd5e1; border-radius: 0; min-height: 65vh; }}
    .error {{ margin-top: 8px; color: #b91c1c; font: 13px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: pre-wrap; }}
    button {{ border: 0; border-radius: 10px; background: #ea580c; color: white; padding: 10px 18px; font-weight: 600; cursor: pointer; }}
    button.secondary {{ background: #334155; }}
    .status {{ color: #fbbf24; min-height: 24px; }}
    .hint {{ font-size: 13px; color: #94a3b8; }}
    code {{ background: #1e293b; padding: 2px 6px; border-radius: 6px; color: #e5e7eb; }}
    @media (max-width: 900px) {{ .split {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">{body}</div>
  <script>
    function getHaToken() {{
      const raw = localStorage.getItem('hassTokens');
      if (!raw) throw new Error('Home Assistant token not found in browser storage');
      const data = JSON.parse(raw);
      if (!data.access_token) throw new Error('Home Assistant access token not found');
      return data.access_token;
    }}

    async function haFetch(url, options = {{}}) {{
      const token = getHaToken();
      const headers = new Headers(options.headers || {{}});
      headers.set('Authorization', 'Bearer ' + token);
      return fetch(url, {{ ...options, headers }});
    }}

    {script}
  </script>
</body>
</html>"""


class MegaEspDashboardConfigApiView(HomeAssistantView):
    url = "/api/megaesp/dashboard-config"
    name = "api:megaesp:dashboard-config"
    requires_auth = True

    async def get(self, request):
        return self.json(load_dashboard_config(request.app["hass"]))

    async def post(self, request):
        data = await request.json()
        if not isinstance(data, dict):
            return self.json_message("JSON root must be an object", status_code=400)

        hass = request.app["hass"]
        config = save_dashboard_config(hass, data)
        regenerate_dashboard(hass, config)
        return self.json({"ok": True, "regenerated": True})


class MegaEspDashboardYamlApiView(HomeAssistantView):
    url = "/api/megaesp/dashboard-yaml"
    name = "api:megaesp:dashboard-yaml"
    requires_auth = True

    async def get(self, request):
        path = dashboard_path(request.app["hass"])
        if not path.exists():
            return Response(text="# megaesp-dashboard.yaml not found\n", content_type="text/plain")
        return Response(text=path.read_text(), content_type="text/plain")


class MegaEspDashboardConfigEditorView(HomeAssistantView):
    url = "/megaesp/dashboard-config-editor"
    name = "megaesp:dashboard-config-editor"
    requires_auth = False

    async def get(self, request):
        body = """
    <h1>MegaESP Dashboard Config</h1>
    <p>Edit <code>megaesp-dashboard-config.json</code> directly from Home Assistant.</p>
    <div class="actions">
      <button id="save">Save + Rebuild</button>
      <button class="secondary" id="reload">Reload File</button>
      <button class="secondary" id="pretty">Pretty JSON</button>
      <div class="status" id="status"></div>
    </div>
    <div class="split">
      <div>
        <div class="panel-title">Editor</div>
        <div class="editor-shell">
          <pre id="gutter" class="gutter"></pre>
          <textarea id="editor" spellcheck="false"></textarea>
        </div>
        <div id="error" class="error"></div>
      </div>
      <div>
        <div class="panel-title">Preview</div>
        <pre id="preview"></pre>
      </div>
    </div>
    <p class="hint">Readable mode without syntax highlighting. Save updates <code>megaesp-dashboard-config.json</code> and rebuilds <code>megaesp-dashboard.yaml</code>.</p>
"""
        script = """
    const editor = document.getElementById('editor');
    const preview = document.getElementById('preview');
    const gutter = document.getElementById('gutter');
    const errorEl = document.getElementById('error');
    const statusEl = document.getElementById('status');

    function renderGutter() {
      const lines = Math.max(1, editor.value.split('\n').length);
      gutter.textContent = Array.from({ length: lines }, (_, i) => String(i + 1)).join('\n');
      gutter.scrollTop = editor.scrollTop;
    }

    function renderPreview() {
      preview.textContent = editor.value || '{}';
      renderGutter();
    }

    function showJsonError(err) {
      errorEl.textContent = err ? ('JSON error: ' + err.message) : '';
    }

    async function loadConfig() {
      statusEl.textContent = 'Loading...';
      const response = await haFetch('/api/megaesp/dashboard-config');
      if (!response.ok) throw new Error('Load failed: ' + response.status);
      const data = await response.json();
      editor.value = JSON.stringify(data, null, 2);
      showJsonError(null);
      renderPreview();
      statusEl.textContent = '';
    }

    async function saveConfig() {
      try {
        statusEl.textContent = 'Validating...';
        const payload = JSON.parse(editor.value);
        showJsonError(null);
        statusEl.textContent = 'Saving...';
        const response = await haFetch('/api/megaesp/dashboard-config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.message || ('Save failed: ' + response.status));
        editor.value = JSON.stringify(payload, null, 2);
        renderPreview();
        statusEl.textContent = 'Saved and rebuilt.';
      } catch (err) {
        showJsonError(err);
        statusEl.textContent = 'Error: ' + err.message;
      }
    }

    function prettyJson() {
      try {
        editor.value = JSON.stringify(JSON.parse(editor.value), null, 2);
        showJsonError(null);
        renderPreview();
        statusEl.textContent = 'Formatted.';
      } catch (err) {
        showJsonError(err);
        statusEl.textContent = 'Error: ' + err.message;
      }
    }

    editor.addEventListener('input', () => {
      renderPreview();
      try {
        JSON.parse(editor.value);
        showJsonError(null);
      } catch (err) {
        showJsonError(err);
      }
    });
    editor.addEventListener('scroll', () => {
      gutter.scrollTop = editor.scrollTop;
    });
    document.getElementById('save').addEventListener('click', saveConfig);
    document.getElementById('reload').addEventListener('click', () => loadConfig().catch((err) => { statusEl.textContent = 'Error: ' + err.message; }));
    document.getElementById('pretty').addEventListener('click', prettyJson);
    loadConfig().catch((err) => { statusEl.textContent = 'Error: ' + err.message; });
"""
        return Response(text=html_shell("MegaESP Dashboard Config", body, script), content_type="text/html")


class MegaEspDashboardYamlView(HomeAssistantView):
    url = "/megaesp/dashboard-yaml"
    name = "megaesp:dashboard-yaml"
    requires_auth = False

    async def get(self, request):
        body = """
    <h1>MegaESP Generated YAML</h1>
    <p>Current generated file: <code>megaesp-dashboard.yaml</code></p>
    <div class="actions">
      <button id="reload">Reload YAML</button>
      <div class="status" id="status"></div>
    </div>
    <pre id="viewer"></pre>
"""
        script = """
    const viewer = document.getElementById('viewer');
    const statusEl = document.getElementById('status');

    async function loadYaml() {
      statusEl.textContent = 'Loading...';
      const response = await haFetch('/api/megaesp/dashboard-yaml');
      if (!response.ok) throw new Error('Load failed: ' + response.status);
      viewer.textContent = await response.text();
      statusEl.textContent = '';
    }

    document.getElementById('reload').addEventListener('click', () => loadYaml().catch((err) => { statusEl.textContent = 'Error: ' + err.message; }));
    loadYaml().catch((err) => { statusEl.textContent = 'Error: ' + err.message; });
"""
        return Response(text=html_shell("MegaESP Generated YAML", body, script), content_type="text/html")

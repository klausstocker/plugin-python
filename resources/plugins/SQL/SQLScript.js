/* Shared SQL editor support. Uses the existing local Ace runtime. */
var SQLPluginUI = window.SQLPluginUI || (window.SQLPluginUI = (() => {
    function decode(dto) {
        if (!dto.jsonData) return {};
        try { return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(dto.jsonData), c => c.charCodeAt(0)))); }
        catch (_) { try { return JSON.parse(dto.jsonData); } catch (_) { return {}; } }
    }
    function base(dto) {
        return (dto.serviceBase || dto.params?.serviceBase || dto.pluginDto?.params?.serviceBase || '/pluginsql').replace(/\/$/, '');
    }
    function client(service) {
        let token;
        async function request(path, body) {
            if (!token) {
                const response = await fetch(service + '/exectoken', {credentials: 'include'});
                if (!response.ok) throw new Error('Could not load execution token');
                token = (await response.json()).token;
            }
            const response = await fetch(service + path, {method: 'POST', credentials: 'include',
                headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token}, body: JSON.stringify(body)});
            const data = await response.json();
            if (!response.ok) throw new Error(data.output || data.detail || 'SQL request failed');
            return data;
        }
        return request;
    }
    function styles() {
        if (document.getElementById('sql-plugin-style')) return;
        const style = document.createElement('style');
        style.id = 'sql-plugin-style';
        style.textContent = `.sql-plugin {font-family: sans-serif; max-width: 100%;}
            .sql-plugin .sql-panels {display:flex; gap:12px; flex-wrap:wrap;}
            .sql-plugin .sql-panel {flex:1 1 320px; min-width:0;}
            .sql-plugin .sql-editor-tabs {display:flex; gap:8px; flex-wrap:wrap; border-bottom:1px solid #aaa;}
            .sql-plugin .sql-editor-tabs button {margin:0 0 8px; padding:6px 14px; border:1px solid #b8b8b8; border-radius:4px; background:#f0f0f0; color:black;}
            .sql-plugin .sql-editor-tabs button[aria-selected="true"] {background:#dce9ff;}
            .sql-plugin .sql-editor-panels {border:1px solid #aaa; border-top:0; padding:12px;}
            .sql-plugin .sql-editor {height:300px; resize:vertical; overflow:auto; border:1px solid #aaa;}
            .sql-plugin textarea {width:100%; height:100%; box-sizing:border-box; font-family:monospace;}
            .sql-plugin pre {white-space:pre-wrap; overflow-wrap:anywhere; padding:12px; min-height:60px;}
            .sql-plugin button {padding:8px 14px; margin:8px 8px 8px 0; cursor:pointer;}
            .sql-plugin label {display:block; margin:10px 0;}
            .sql-plugin .sql-output {background:var(--sql-bg); color:var(--sql-fg);}
            .sql-config {display:flex; gap:8px; align-items:flex-start; width:100%;}
            .sql-config .sql-config-main {flex:2; min-width:0;}
            .sql-config .sql-tab-title-row {display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;}
            .sql-config .sql-tab-title-row h3 {margin:0;}
            .sql-config .sql-example-toolbar {margin-left:auto; display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
            .sql-config .sql-example-toolbar label {display:flex; align-items:center; gap:8px; margin:0;}
            .sql-config .sql-example-toolbar select {width:auto; min-width:120px; max-width:100%; padding:6px; margin:0;}
            .sql-config .sql-example-toolbar button {margin:0; padding:6px 14px;}
            .sql-config .sql-example-confirm {max-width:420px; border:1px solid #aaa; border-radius:6px; padding:20px;}
            .sql-config .sql-example-confirm::backdrop {background:rgba(0,0,0,0.35);}
            .sql-config .sql-config-help {flex:1; min-width:0; padding:8px; border:1px solid #ccc; max-height:75vh; overflow:auto; box-sizing:border-box;}
            .sql-config .sql-help-heading {display:flex; align-items:center; justify-content:space-between; gap:8px;}
            .sql-config .sql-help-heading h3 {margin:0;}
            .sql-config .sql-help-heading button {padding:4px 8px; margin:0;}
            .sql-config .sql-help-collapsed {flex:0 0 auto; padding:4px;}
            .sql-config .sql-help-collapsed .sql-help-content, .sql-config .sql-help-collapsed h3 {display:none;}
            .sql-config .sql-help-content h1 {font-size:1.1em; margin:12px 0 8px;}
            .sql-config .sql-help-content h2 {font-size:1em; margin:14px 0 4px;}
            .sql-config .sql-help-content p {margin:4px 0 8px;}
            .sql-config .sql-help-content .help-logo {width:72px; height:72px; object-fit:contain; float:right; margin:0 0 8px 10px;}
            .sql-config .sql-help-content section {display:flow-root;}
            .sql-config .sql-help-content code {overflow-wrap:anywhere;}
            @media (max-width:700px) {.sql-config {flex-direction:column;} .sql-config .sql-config-main, .sql-config .sql-config-help {width:100%;} .sql-config .sql-help-collapsed {width:auto;}}
            .sql-plugin h3 {margin:10px 0;}`;
        document.head.appendChild(style);
    }
    function theme(root) {
        styles();
        root.style.setProperty('--sql-bg', window.dark_design === true ? 'black' : 'white');
        root.style.setProperty('--sql-fg', window.dark_design === true ? 'rgb(70, 242, 70)' : 'black');
    }
    async function loadAce(service) {
        const path = service + '/static/ace/1.44.0';
        if (!window.ace) {
            if (!window.pluginAceLoadPromise) window.pluginAceLoadPromise = new Promise(resolve => {
                const script = document.createElement('script');
                script.src = path + '/ace.js';
                script.onload = () => resolve(true);
                script.onerror = () => { window.pluginAceLoadPromise = null; resolve(false); };
                document.head.appendChild(script);
            });
            await window.pluginAceLoadPromise;
        }
        if (!window.ace) return false;
        for (const key of ['basePath', 'modePath', 'themePath', 'workerPath']) ace.config.set(key, path);
        // Small project-owned mode, so SQL needs no additional bundled library.
        if (!ace.require('ace/mode/letto_sql')) {
            ace.define('ace/mode/letto_sql', ['require', 'exports', 'module', 'ace/lib/oop', 'ace/mode/text', 'ace/mode/text_highlight_rules'], function(require, exports) {
                const oop = require('ace/lib/oop');
                const TextMode = require('ace/mode/text').Mode;
                const TextRules = require('ace/mode/text_highlight_rules').TextHighlightRules;
                function Rules() {
                    this.$rules = {start: [
                        {token:'comment', regex:'--.*$'},
                        {token:'comment', regex:'/\\*', next:'comment'},
                        {token:'string', regex:"'", next:'string'},
                        {token:'variable', regex:'"', next:'identifier'},
                        {token:'constant.numeric', regex:'\\b[0-9]+(?:\\.[0-9]+)?\\b'},
                        {token:'keyword', regex:'\\b(?:select|from|where|join|left|right|inner|outer|on|as|and|or|not|null|is|in|exists|like|between|group|by|having|order|asc|desc|limit|offset|union|all|distinct|insert|into|values|update|set|delete|create|table|drop|alter|primary|foreign|key|references|constraint|unique|default|check|with|recursive|returning|case|when|then|else|end|begin|commit|rollback|trigger|view|index)\\b', caseInsensitive:true}
                    ], comment:[{token:'comment', regex:'.*?\\*/', next:'start'}, {defaultToken:'comment'}],
                    string:[{token:'string', regex:"''"}, {token:'string', regex:"'", next:'start'}, {defaultToken:'string'}],
                    identifier:[{token:'variable', regex:'""'}, {token:'variable', regex:'"', next:'start'}, {defaultToken:'variable'}]};
                    this.normalizeRules();
                }
                oop.inherits(Rules, TextRules);
                function Mode() { this.HighlightRules = Rules; this.$id = 'ace/mode/letto_sql'; }
                oop.inherits(Mode, TextMode);
                exports.Mode = Mode;
            });
        }
        return true;
    }
    function editor(element, value, language, readonly, service, onChange = () => {}) {
        const textarea = document.createElement('textarea');
        textarea.value = value;
        textarea.readOnly = readonly;
        textarea.setAttribute('aria-label', element.getAttribute('aria-label') || language + ' code');
        element.appendChild(textarea);
        const control = {get: () => textarea.value, set: text => { textarea.value = text; onChange(text); },
            mode: mode => { language = mode; }, resize: () => {}};
        textarea.addEventListener('input', () => onChange(textarea.value));
        for (const type of ['keydown', 'keypress', 'keyup']) element.addEventListener(type, event => {
            if (event.key === 'Enter') event.stopPropagation();
        });
        loadAce(service).then(available => {
            if (!available || !element.isConnected) return;
            const current = textarea.value;
            element.replaceChildren();
            const editor = ace.edit(element);
            editor.setTheme(window.dark_design === true ? 'ace/theme/monokai' : 'ace/theme/chrome');
            const mode = language => editor.session.setMode(language === 'python' ? 'ace/mode/python' : 'ace/mode/letto_sql');
            mode(language);
            editor.session.setUseWorker(false);
            editor.setValue(current, -1);
            editor.setReadOnly(readonly);
            editor.session.on('change', () => onChange(editor.getValue()));
            control.get = () => editor.getValue();
            control.set = text => editor.setValue(text, -1);
            control.mode = mode;
            control.resize = () => editor.resize(true);
        }).catch(() => {}); // The textarea remains available if Ace cannot load.
        return control;
    }
    return {decode, base, client, theme, editor};
})());

function initPluginSQL(dtoString, active) {
    const dto = JSON.parse(dtoString || '{}');
    const container = document.getElementById(dto.tagName + '_div');
    if (!container) return;
    const config = SQLPluginUI.decode(dto);
    const service = SQLPluginUI.base(dto);
    const request = SQLPluginUI.client(service);
    const field = document.getElementsByClassName(dto.tagName + '_inp')[0];
    const initial = field?.value || config.indication || '-- Write your SQL here\n';
    if (active && field && !field.value) field.value = initial;
    container.querySelector('.sql-plugin')?.remove();
    const root = document.createElement('div');
    root.className = 'sql-plugin';
    root.innerHTML = `<div class="sql-panels"><section class="sql-panel"><h3>answer.sql</h3><div class="sql-editor" aria-label="Student SQL"></div></section>
        <section class="sql-panel"><h3>Output</h3><pre class="sql-output" role="status"></pre></section></div>`;
    container.appendChild(root);
    SQLPluginUI.theme(root);
    const editor = SQLPluginUI.editor(root.querySelector('.sql-editor'), initial, 'sql', !active, service,
        value => { if (active && field) field.value = value; });
    if (active && config.evalConfig?.runAtTest !== false) {
        const button = document.createElement('button');
        button.type = 'button'; button.textContent = 'Run SQL';
        root.appendChild(button);
        button.addEventListener('click', async () => {
            button.disabled = true;
            const output = root.querySelector('pre');
            output.textContent = 'Running SQL…';
            try { output.textContent = (await request('/run', {code:editor.get(), questionConfigDto:config})).output; }
            catch (error) { output.textContent = error.message; }
            finally { button.disabled = false; }
        });
    }
}

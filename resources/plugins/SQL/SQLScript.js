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
    function datasetVariables(...sources) {
        const parse = value => {
            if (typeof value !== 'string') return value;
            try { return JSON.parse(value); } catch (_) { return null; }
        };
        const cleanUnit = value => String(value ?? '').split(',')[0].replace(/^['"]+|['"]+$/g, '').trim();
        const number = value => typeof value === 'string' && value.trim() && !Number.isNaN(Number(value)) ? Number(value) : value;
        function extract(source) {
            source = parse(source);
            if (!source || typeof source !== 'object') return [];
            if (Array.isArray(source)) return source.filter(item => item && typeof item.name === 'string' && item.name)
                .map(item => ({name:item.name, value:item.value, unit:item.unit || ''}));
            if (source.datasetVariables != null) return extract(source.datasetVariables);
            if (source.params) {
                const nested = extract(source.params);
                if (nested.length) return nested;
            }
            const hash = parse(source.vars);
            if (!hash || typeof hash !== 'object' || Array.isArray(hash)) return [];
            const variables = hash.vars && typeof hash.vars === 'object' ? hash.vars : hash;
            return Object.entries(variables).map(([name, variable]) => {
                const result = variable?.calcErgebnisDto || {};
                const json = parse(result.json) || {};
                const text = typeof result.string === 'string' ? result.string : '';
                const numeric = text.match(/^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)/);
                const quotedUnit = text.match(/'([^']+)'/);
                const suffixUnit = text.match(/^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*([^\s]+)\s*$/);
                const fallbackUnit = cleanUnit(variable?.ze);
                return {name,
                    value:Object.prototype.hasOwnProperty.call(json, 'd') ? number(json.d) : numeric ? number(numeric[1]) : text,
                    unit:cleanUnit(json.originalEinheitString || json.grundEinheitString || quotedUnit?.[1] || suffixUnit?.[1]
                        || (/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(fallbackUnit) ? '' : fallbackUnit))};
            });
        }
        for (const source of sources) {
            const variables = extract(source);
            if (variables.length) return variables;
        }
        return [];
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
            .sql-student .sql-panels {gap:0; flex-wrap:nowrap; height:340px; margin-bottom:10px;}
            .sql-student .sql-panels.vertical {flex-direction:column;}
            .sql-student .sql-panel {display:flex; flex-direction:column; min-width:120px; min-height:80px; overflow:hidden; border:1px solid #d0d0d0; box-sizing:border-box;}
            .sql-student .sql-file-info {padding:10px; background:#f0f0f0; color:black; font: bold 16px monospace; border-bottom:1px solid #ccc; flex-shrink:0;}
            .sql-student .sql-main-header {display:flex; align-items:center; justify-content:space-between; gap:8px;}
            .sql-student .sql-header-actions {display:inline-flex; align-items:center; gap:6px;}
            .sql-student .sql-layout-toggle {margin:0; padding:0 8px; min-width:36px; height:32px; border:1px solid #b8b8b8; border-radius:4px; background:#f0f0f0; color:black; font-size:16px; line-height:1;}
            .sql-student .sql-help-link {display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; border:1px solid #888; border-radius:50%; background:#f7f7f7; color:#444; font: bold 12px sans-serif; text-decoration:none; line-height:1;}
            .sql-student .sql-editor {flex:1; height:auto; min-height:0; border:0; resize:none; font:16px monospace;}
            .sql-student textarea {border:0; resize:none; font:16px monospace;}
            .sql-student .sql-output {flex:1; width:100%; min-height:0; margin:0; padding:8px; overflow:auto; font:16px monospace; box-sizing:border-box;}
            .sql-student .sql-splitter {background:#d0d0d0; flex:0 0 8px; touch-action:none; user-select:none;}
            .sql-student .horizontal .sql-splitter {cursor:col-resize;}
            .sql-student .vertical .sql-splitter {cursor:row-resize;}
            .sql-student .sql-actions {margin-top:8px; display:flex; align-items:center; flex-wrap:wrap;}
            .sql-student .sql-actions button {color:black; background:#f0f0f0; padding:10px 20px; display:inline-flex; align-items:center; font-size:14px; font-weight:bold; margin:4px 8px 4px 0; border:1px solid #b8b8b8; border-radius:5px; transition:background-color 0.3s ease, color 0.3s ease;}
            .sql-student .sql-actions button:active {background:#333; color:white; transform:scale(0.98);}
            .sql-student .sql-actions button:disabled {opacity:0.5; cursor:not-allowed;}
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
            .sql-config .dataset-variable-section {display:flex; flex-direction:column; flex:1 1 0; min-width:0; margin-top:16px; border:1px solid #d0d0d0; border-radius:4px; padding:8px; background:#fafafa;}
            .sql-config .dataset-variable-head-row {display:flex; align-items:center; gap:6px; margin-bottom:6px;}
            .sql-config .dataset-variable-head-row h4 {margin:0;}
            .sql-config .dataset-variable-help {display:inline-flex; align-items:center; justify-content:center; width:16px; height:16px; border:1px solid #888; border-radius:50%; color:#444; font-size:11px; font-weight:700; cursor:help;}
            .sql-config .dataset-variable-list {max-height:160px; overflow:auto;}
            .sql-config .dataset-variable-table {width:100%; border-collapse:collapse; font-family:monospace; font-size:12px;}
            .sql-config .dataset-variable-table th, .sql-config .dataset-variable-table td {border:1px solid #ddd; padding:4px 6px; text-align:left; vertical-align:top;}
            .sql-config .dataset-variable-table th {background:#f0f0f0;}
            .sql-config .dataset-variable-empty {margin:0; color:#666; font-size:12px;}
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
            mode: mode => { language = mode; }, resize: () => {}, target: filename => ({textarea, filename})};
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
            control.target = filename => ({editor, filename});
        }).catch(() => {}); // The textarea remains available if Ace cannot load.
        return control;
    }
    async function bindFormatting(button, output, service, getTarget, request, onChange) {
        button.disabled = true;
        try {
            const {bindFormatButton} = await import(service + '/static/formatting/client.js');
            if (!button.isConnected) return;
            return bindFormatButton({button, output, getTarget, onChange,
                requestFormat: async (code, filename) => {
                    const data = await request('/format', {code, filename});
                    if (typeof data.code !== 'string') throw new Error('Formatter returned no code');
                    return data.code;
                }});
        } catch (error) { button.title = 'Formatter unavailable: ' + error.message; }
    }
    return {decode, base, client, theme, editor, bindFormatting, datasetVariables};
})());

function initPluginSQL(dtoString, active) {
    const dto = JSON.parse(dtoString || '{}');
    const container = document.getElementById(dto.tagName + '_div');
    if (!container) return;
    const config = SQLPluginUI.decode(dto);
    const service = SQLPluginUI.base(dto);
    const request = SQLPluginUI.client(service);
    const field = document.getElementsByClassName(dto.tagName + '_inp')[0];
    const defaultMain = config.indication ?? '-- Write your SQL here\n';
    const initial = field?.value || defaultMain;
    if (active && field && !field.value) field.value = initial;
    container.querySelector('.sql-plugin')?.remove();
    const root = document.createElement('div');
    root.className = 'sql-plugin sql-student';
    root.innerHTML = `<div class="sql-panels horizontal">
        <section class="sql-panel sql-main-panel"><div class="sql-file-info sql-main-header"><span>main.sql</span>
        <span class="sql-header-actions"><button type="button" class="sql-layout-toggle" aria-label="Switch to vertical layout" title="Switch to vertical layout">⇅</button>
        ${active ? '<button type="button" class="sql-layout-toggle" data-reset-code title="Aufgabe neu starten" aria-label="Aufgabe neu starten">&#8634;</button>' : ''}
        <a class="sql-help-link" target="_blank" rel="noopener" aria-label="SQL help" title="SQL help">?</a></span></div>
        <div class="sql-editor" aria-label="Student SQL"></div></section>
        <div class="sql-splitter" role="separator" tabindex="0" aria-label="Resize panels" aria-orientation="vertical" aria-valuemin="15" aria-valuemax="85"></div>
        <section class="sql-panel sql-output-panel"><div class="sql-file-info">output</div><pre class="sql-output" role="status"></pre></section></div>
        <div class="sql-actions"></div>`;
    container.appendChild(root);
    SQLPluginUI.theme(root);
    const editor = SQLPluginUI.editor(root.querySelector('.sql-editor'), initial, 'sql', !active, service,
        value => { if (active && field) field.value = value; });
    root.querySelector('.sql-help-link').href = service + '/help';
    const panels = root.querySelector('.sql-panels');
    const mainPanel = root.querySelector('.sql-main-panel');
    const outputPanel = root.querySelector('.sql-output-panel');
    const splitter = root.querySelector('.sql-splitter');
    const layoutToggle = root.querySelector('.sql-layout-toggle');
    const actions = root.querySelector('.sql-actions');
    let horizontal = true;
    let ratio = 2 / 3;
    function applyLayout() {
        panels.classList.toggle('horizontal', horizontal);
        panels.classList.toggle('vertical', !horizontal);
        mainPanel.style.flex = `${ratio} 1 0`;
        outputPanel.style.flex = `${1 - ratio} 1 0`;
        splitter.setAttribute('aria-orientation', horizontal ? 'vertical' : 'horizontal');
        splitter.setAttribute('aria-valuenow', String(Math.round(ratio * 100)));
        layoutToggle.textContent = horizontal ? '⇅' : '⇄';
        layoutToggle.title = horizontal ? 'Switch to vertical layout' : 'Switch to horizontal layout';
        layoutToggle.setAttribute('aria-label', layoutToggle.title);
        editor.resize();
    }
    function resize(value) {
        ratio = Math.min(0.85, Math.max(0.15, value));
        applyLayout();
    }
    layoutToggle.addEventListener('click', () => { horizontal = !horizontal; applyLayout(); });
    splitter.addEventListener('pointerdown', event => {
        event.preventDefault();
        const move = moveEvent => {
            if (moveEvent.pointerId !== event.pointerId) return;
            const rect = panels.getBoundingClientRect();
            const size = horizontal ? rect.width : rect.height;
            if (size > 0) resize((horizontal ? moveEvent.clientX - rect.left : moveEvent.clientY - rect.top) / size);
        };
        const finish = () => {
            document.removeEventListener('pointermove', move);
            document.removeEventListener('pointerup', finish);
            document.removeEventListener('pointercancel', finish);
        };
        document.addEventListener('pointermove', move);
        document.addEventListener('pointerup', finish);
        document.addEventListener('pointercancel', finish);
    });
    splitter.addEventListener('keydown', event => {
        const decrease = horizontal ? 'ArrowLeft' : 'ArrowUp';
        const increase = horizontal ? 'ArrowRight' : 'ArrowDown';
        if (![decrease, increase, 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        resize(event.key === 'Home' ? 0.15 : event.key === 'End' ? 0.85 : ratio + (event.key === decrease ? -0.05 : 0.05));
    });
    if (window.ResizeObserver) {
        const observer = new ResizeObserver(() => {
            if (root.isConnected) editor.resize();
            else observer.disconnect();
        });
        observer.observe(mainPanel);
    }
    applyLayout();
    if (active) {
        const resetButton = root.querySelector('[data-reset-code]');
        const dialog = document.createElement('dialog');
        dialog.setAttribute('aria-label', 'Aufgabe neu starten');
        dialog.innerHTML = `<p>Code auf den ursprünglichen Angabetext zurücksetzen? Deine Änderungen gehen dabei verloren.</p>
            <button type="button" data-reset-no autofocus>Nein</button>
            <button type="button" data-reset-yes>Ja</button>`;
        root.appendChild(dialog);
        resetButton.addEventListener('click', () => dialog.showModal());
        dialog.querySelector('[data-reset-no]').addEventListener('click', () => dialog.close());
        dialog.querySelector('[data-reset-yes]').addEventListener('click', () => {
            editor.set(defaultMain);
            if (field) field.value = defaultMain;
            dialog.close();
            const target = editor.target('main.sql');
            (target.editor || target.textarea).focus();
        });
        const format = document.createElement('button');
        format.type = 'button'; format.textContent = 'Format Code'; format.dataset.studentFormat = '';
        actions.appendChild(format);
        SQLPluginUI.bindFormatting(format, root.querySelector('pre'), service,
            () => editor.target('main.sql'), request, () => { if (field) field.value = editor.get(); });
    }
    if (active && config.evalConfig?.runAtTest !== false) {
        const button = document.createElement('button');
        button.type = 'button'; button.textContent = 'Run SQL';
        button.dataset.studentRun = '';
        actions.appendChild(button);
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

async function configPluginSQL(dtoString) {
    const dto = JSON.parse(dtoString || '{}');
    const container = document.getElementById('configform_div');
    if (!container) return;
    // LeTTo can invoke the configuration script without loading the student script.
    if (!window.SQLPluginUI) {
        const service = (dto.serviceBase || dto.params?.serviceBase || dto.pluginDto?.params?.serviceBase || '/pluginsql').replace(/\/$/, '');
        try {
            if (!window.sqlPluginSupportPromise) {
                window.sqlPluginSupportPromise = new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = service + '/static/SQLScript.js';
                    script.onload = () => {
                        if (window.SQLPluginUI) resolve();
                        else { window.sqlPluginSupportPromise = null; reject(new Error('SQL editor support is missing.')); }
                    };
                    script.onerror = () => {
                        window.sqlPluginSupportPromise = null;
                        script.remove();
                        reject(new Error('Could not load SQL editor support. Check the /pluginsql/ proxy route and deployed plugin resources.'));
                    };
                    document.head.appendChild(script);
                });
            }
            await window.sqlPluginSupportPromise;
        } catch (error) {
            if (container.isConnected) container.textContent = error.message;
            return;
        }
        if (!container.isConnected) return;
    }
    const field = document.querySelector('.configform_config');
    let config = SQLPluginUI.decode(dto);
    try { config = {...config, ...JSON.parse(field?.value || '{}')}; } catch (_) {}
    const service = SQLPluginUI.base(dto);
    const request = SQLPluginUI.client(service);
    const root = document.createElement('div');
    root.className = 'sql-plugin sql-config';
    root.innerHTML = `<div class="sql-config-main"><div class="sql-editor-tabs" role="tablist" aria-label="Question code">
        <button type="button" role="tab" data-tab="validation" aria-selected="true">UnitTest</button>
        <button type="button" role="tab" data-tab="indication" aria-selected="false" tabindex="-1">Template</button>
        <button type="button" role="tab" data-tab="preparation" aria-selected="false" tabindex="-1">Preparation</button>
        </div><div class="sql-editor-panels">
        <section data-panel="preparation" role="tabpanel" hidden><h3>Database preparation</h3>
        <p>SQL statements to create tables and insert the initial data.</p>
        <div class="sql-editor" data-editor="preparation" aria-label="Database preparation code"></div></section>
        <section data-panel="indication" role="tabpanel" hidden><h3>Student starter SQL / preview</h3><p>The current preview SQL is saved as the student starter code.</p>
        <div class="sql-editor" data-editor="indication" aria-label="Student starter SQL"></div></section>
        <section data-panel="validation" role="tabpanel"><div class="sql-tab-title-row"><h3>Python unit tests</h3>
        <div class="sql-example-toolbar"><label>Example: <select data-example-select disabled aria-label="SQL example"><option>Loading examples…</option></select></label>
        <button type="button" data-example-apply disabled>Apply</button></div></div>
        <div class="sql-editor" data-editor="validation" aria-label="Python grading tests"></div></section></div>
        <label>CPU time (seconds) <input data-setting="cpu" type="number" min="1" step="1"></label>
        <label><input data-setting="run" type="checkbox"> Allow students to run SQL</label>
        <button type="button" data-format disabled>Format</button>
        <button type="button" data-action="run">Run SQL</button>
        <button type="button" data-action="check">Check tests</button>
        <button type="button" data-action="scorePlugin">Calculate score</button>
        <pre class="sql-output" role="status"></pre>
        </div><aside class="sql-config-help" aria-label="SQL help">
        <div class="sql-help-heading"><h3>Help</h3><button type="button" data-help-toggle aria-expanded="true" aria-label="Hide help" title="Hide help">◂</button></div>
        <div class="sql-help-content"></div></aside>
        <dialog class="sql-example-confirm" aria-label="Replace current code?">
        <h3>Replace current code?</h3><p>Applying this example replaces preparation SQL, template, tests, and options.</p>
        <button type="button" data-example-cancel>Cancel</button><button type="button" data-example-confirm>Apply</button></dialog>`;
    container.replaceChildren(root);
    SQLPluginUI.theme(root);
    const helpPanel = root.querySelector('.sql-config-help');
    const helpContent = root.querySelector('.sql-help-content');
    const helpToggle = root.querySelector('[data-help-toggle]');
    helpToggle.addEventListener('click', () => {
        const collapsed = helpPanel.classList.toggle('sql-help-collapsed');
        helpToggle.setAttribute('aria-expanded', String(!collapsed));
        helpToggle.setAttribute('aria-label', collapsed ? 'Show help' : 'Hide help');
        helpToggle.title = collapsed ? 'Show help' : 'Hide help';
        helpToggle.textContent = collapsed ? '▸' : '◂';
        for (const editor of Object.values(editors)) editor.resize();
    });
    async function renderHelp() {
        try {
            let help = dto.params?.help || dto.pluginDto?.params?.help;
            if (!help) {
                const response = await fetch(service + '/help', {credentials:'include'});
                if (!response.ok) throw new Error('Help request failed');
                help = await response.text();
            }
            if (!root.isConnected) return;
            const document = new DOMParser().parseFromString(help, 'text/html');
            document.querySelectorAll('style, script, link[rel="stylesheet"]').forEach(element => element.remove());
            document.querySelectorAll('img[data-plugin-static-file]').forEach(image => {
                image.src = service + '/static/' + encodeURIComponent(image.dataset.pluginStaticFile);
            });
            document.querySelectorAll('a[data-plugin-help-file]').forEach(link => {
                link.href = service + '/static/' + encodeURIComponent(link.dataset.pluginHelpFile);
            });
            helpContent.replaceChildren(...document.body.childNodes);
        } catch (_) {
            helpContent.textContent = 'Prepare tables and data in SQL, provide starter SQL, and grade with Python Checker unit tests.';
        }
    }
    renderHelp();
    const cpu = root.querySelector('[data-setting="cpu"]');
    const run = root.querySelector('[data-setting="run"]');
    cpu.value = config.cpuTime || 5;
    run.checked = config.evalConfig?.runAtTest !== false;
    const editors = {};
    let applyingExample = false;
    function save() {
        if (!editors.validation || applyingExample) return;
        config = {preparation:editors.preparation.get(),
            indication:editors.indication.get(), validation:editors.validation.get(),
            cpuTime:Math.max(1, Math.trunc(Number(cpu.value) || 5)), evalConfig:{runAtTest:run.checked},
            datasetVariables:config.datasetVariables || []};
        const variables = dto.params?.datasetVariables;
        if (variables) { try { config.datasetVariables = typeof variables === 'string' ? JSON.parse(variables) : variables; } catch (_) {} }
        if (field) { field.value = JSON.stringify(config); field.dispatchEvent(new Event('change', {bubbles:true})); }
    }
    const defaults = {preparation:"CREATE TABLE products (name TEXT, price INTEGER);\nINSERT INTO products VALUES ('Pen', 2), ('Book', 8);\n",
        indication:'SELECT name, price FROM products ORDER BY price;\n',
        validation:"import unittest\nimport answer\n\nclass Checker(unittest.TestCase):\n    def test_result(self):\n        self.assertEqual(answer.rows, [('Pen', 2), ('Book', 8)])\n\n    def test_database(self):\n        self.assertEqual(answer.connection.execute('SELECT COUNT(*) FROM products').fetchone(), (2,))\n"};
    for (const name of ['preparation', 'indication', 'validation']) {
        editors[name] = SQLPluginUI.editor(root.querySelector(`[data-editor="${name}"]`), config[name] ?? defaults[name],
            name === 'validation' ? 'python' : 'sql', false, service, save);
    }
    const tabs = [...root.querySelectorAll('[role="tab"]')];
    const panels = [...root.querySelectorAll('[role="tabpanel"]')];
    const tabPrefix = 'sql-config-' + (dto.tagName || 'dev');
    function selectTab(tab) {
        for (const candidate of tabs) {
            const selected = candidate === tab;
            candidate.setAttribute('aria-selected', String(selected));
            candidate.tabIndex = selected ? 0 : -1;
        }
        for (const panel of panels) panel.hidden = panel.dataset.panel !== tab.dataset.tab;
        editors[tab.dataset.tab].resize();
    }
    tabs.forEach((tab, index) => {
        const panel = panels.find(panel => panel.dataset.panel === tab.dataset.tab);
        tab.id = tabPrefix + '-tab-' + tab.dataset.tab;
        panel.id = tabPrefix + '-panel-' + tab.dataset.tab;
        tab.setAttribute('aria-controls', panel.id);
        panel.setAttribute('aria-labelledby', tab.id);
        tab.addEventListener('click', () => selectTab(tab));
        tab.addEventListener('keydown', event => {
            let next;
            if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
            else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
            else if (event.key === 'Home') next = 0;
            else if (event.key === 'End') next = tabs.length - 1;
            else return;
            event.preventDefault();
            selectTab(tabs[next]);
            tabs[next].focus();
        });
    });
    cpu.addEventListener('input', save);
    run.addEventListener('change', save);
    const buttons = [...root.querySelectorAll('[data-action]')];
    const exampleSelect = root.querySelector('[data-example-select]');
    const exampleApply = root.querySelector('[data-example-apply]');
    const output = root.querySelector('.sql-output');
    SQLPluginUI.bindFormatting(root.querySelector('[data-format]'), output, service, () => {
        const active = tabs.find(tab => tab.getAttribute('aria-selected') === 'true').dataset.tab;
        return editors[active].target(active === 'validation' ? 'main.py' : active === 'preparation' ? 'preparation.sql' : 'main.sql');
    }, request, save);
    let exampleCount = 0;
    function confirmExampleOverwrite() {
        const dialog = root.querySelector('.sql-example-confirm');
        const cancel = root.querySelector('[data-example-cancel]');
        const confirm = root.querySelector('[data-example-confirm]');
        return new Promise(resolve => {
            const finish = overwrite => {
                cancel.removeEventListener('click', onCancel);
                confirm.removeEventListener('click', onConfirm);
                dialog.removeEventListener('cancel', onEscape);
                resolve(overwrite);
            };
            const onCancel = () => { dialog.close('cancel'); finish(false); };
            const onConfirm = () => { dialog.close('apply'); finish(true); };
            const onEscape = event => { event.preventDefault(); onCancel(); };
            cancel.addEventListener('click', onCancel);
            confirm.addEventListener('click', onConfirm);
            dialog.addEventListener('cancel', onEscape);
            dialog.returnValue = '';
            dialog.showModal();
            cancel.focus();
        });
    }
    async function setupExamples() {
        try {
            const data = await request('/example', {index:0});
            if (!root.isConnected) return;
            exampleSelect.replaceChildren();
            exampleCount = data.count;
            for (let index = 0; index < data.count; index++) {
                const option = document.createElement('option');
                option.value = String(index);
                option.textContent = `${String(index + 1).padStart(2, '0')} ${data.names[index]}`;
                exampleSelect.appendChild(option);
            }
            exampleSelect.disabled = exampleApply.disabled = !exampleCount;
        } catch (error) {
            exampleSelect.options[0].textContent = 'Examples unavailable';
            output.textContent = error.message;
        }
    }
    exampleApply.addEventListener('click', async () => {
        exampleApply.disabled = exampleSelect.disabled = true;
        buttons.forEach(button => { button.disabled = true; });
        try {
            const {output:example} = await request('/example', {index:Number(exampleSelect.value)});
            const changed = ['preparation', 'indication', 'validation'].some(name =>
                editors[name].get().trim() && editors[name].get().trim() !== example[name].trim());
            if (changed && !await confirmExampleOverwrite()) return;
            applyingExample = true;
            try {
                for (const name of ['preparation', 'indication', 'validation']) editors[name].set(example[name]);
                cpu.value = example.cpuTime;
                run.checked = example.evalConfig.runAtTest;
            } finally { applyingExample = false; }
            save();
            for (const editor of Object.values(editors)) editor.resize();
            output.textContent = 'Example applied.';
        } catch (error) { output.textContent = error.message; }
        finally {
            exampleSelect.disabled = exampleApply.disabled = !exampleCount;
            buttons.forEach(button => { button.disabled = false; });
        }
    });
    for (const button of buttons) button.addEventListener('click', async () => {
        save();
        buttons.forEach(button => { button.disabled = true; });
        exampleSelect.disabled = exampleApply.disabled = true;
        const startedAt = performance.now();
        output.setAttribute('aria-busy', 'true');
        output.textContent = 'Running…';
        try {
            const data = await request('/' + button.dataset.action, {code:editors.indication.get(), testcode:editors.validation.get(), questionConfigDto:config});
            output.textContent = data.output;
        } catch (error) { output.textContent = error.message; }
        finally {
            if (button.dataset.action !== 'run') {
                output.textContent += `\n\n${button.textContent} timing: ${((performance.now() - startedAt) / 1000).toFixed(2)}s elapsed.`;
            }
            output.setAttribute('aria-busy', 'false');
            buttons.forEach(button => { button.disabled = false; });
            exampleSelect.disabled = exampleApply.disabled = !exampleCount;
        }
    });
    save();
    setupExamples();
}

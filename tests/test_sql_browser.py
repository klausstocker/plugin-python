"""Opt-in smoke test using an installed Chrome (no additional dependencies)."""
import functools
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unittest
from shared.sql_examples import EXAMPLE_NAMES, sql_example


ROOT = Path(__file__).resolve().parents[1]
CHROME = Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Google/Chrome/Application/chrome.exe'

HTML = '''<!doctype html><meta charset="utf-8">
<input class="configform_config" type="hidden" value="{}"><div id="configform_div"></div>
<div id="student_div"></div><input class="student_inp"><pre id="result">WAIT</pre>
<script>window.onerror = message => document.getElementById('result').textContent = 'FAIL: ' + message;</script>
<script src="/resources/plugins/SQL/SQLScript.js"></script>
<script src="/resources/plugins/SQL/SQLConfigScript.js"></script>
<script>
const realFetch = window.fetch.bind(window);
const examples = SQL_EXAMPLES_JSON;
let failNextCheck = false;
window.fetch = async (url, options) => {
    if (url.endsWith('/help')) return realFetch('/resources/help/SQL.html');
    if (url.endsWith('/example')) return {ok:true, json:async () => ({count:examples.length,
        names:['select_products', 'insert_products', 'update_prices', 'delete_products', 'join_products'],
        output:examples[JSON.parse(options.body).index]})};
    if (failNextCheck && url.endsWith('/check')) { failNextCheck = false; throw Error('Test connection failure'); }
    return {ok:true, json:async () => url.endsWith('/exectoken') ? {token:'test'} : {output:'Query output'}};
};
const serviceBase = '/resources';
configPluginSQL(JSON.stringify({serviceBase, params:{datasetVariables:[{name:'n', value:3}]}}));
initPluginSQL(JSON.stringify({tagName:'student', serviceBase}), true);
function assert(value, message) { if (!value) throw Error(message); }
setTimeout(async () => {
    try {
        assert(document.querySelectorAll('.ace_editor').length === 4, 'Ace editors not initialized');
        const config = JSON.parse(document.querySelector('.configform_config').value);
        assert(config.preparation.includes('CREATE TABLE'), 'Preparation not persisted');
        assert(config.validation.includes('Checker'), 'Tests not persisted');
        assert(config.datasetVariables[0].value === 3, 'Dataset not persisted');
        const main = document.querySelector('.sql-config-main');
        const help = document.querySelector('.sql-config-help');
        assert(help.getBoundingClientRect().left >= main.getBoundingClientRect().right, 'Help should be to the right');
        assert(help.textContent.includes('Kurz erklärt'), 'Shared help document not loaded');
        const logos = [...help.querySelectorAll('img')];
        assert(logos.length === 2 && logos.every(image => image.complete && image.naturalWidth > 0), 'Help logos did not load');
        const toggle = help.querySelector('[data-help-toggle]');
        toggle.click();
        assert(toggle.getAttribute('aria-expanded') === 'false', 'Help did not collapse');
        toggle.click();
        assert(toggle.getAttribute('aria-expanded') === 'true', 'Help did not expand');
        const tabs = [...document.querySelectorAll('[role="tab"]')];
        const panels = [...document.querySelectorAll('[role="tabpanel"]')];
        assert(tabs.length === 3, 'Expected three editor tabs');
        assert(panels.filter(panel => !panel.hidden).length === 1, 'Only one editor should be visible');
        assert(!document.querySelector('[data-panel="validation"]').hidden, 'UnitTest should be selected initially');
        for (const tab of tabs) {
            tab.click();
            const panel = document.getElementById(tab.getAttribute('aria-controls'));
            assert(!panel.hidden && panel.offsetWidth > 0, 'Selected editor panel is not visible');
            assert(tab.getAttribute('aria-selected') === 'true', 'Selected tab state missing');
            assert(panels.filter(panel => !panel.hidden).length === 1, 'Multiple editors visible');
        }
        const preparationEditor = ace.edit(document.querySelector('[data-editor="preparation"]'));
        preparationEditor.setValue('CREATE TABLE saved (value INTEGER);', -1);
        tabs[0].click();
        tabs[2].click();
        assert(preparationEditor.getValue().includes('saved'), 'Switching tabs lost editor contents');
        assert(JSON.parse(document.querySelector('.configform_config').value).preparation.includes('saved'), 'Hidden editor contents not saved');
        tabs[2].dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowRight', bubbles:true}));
        assert(tabs[0].getAttribute('aria-selected') === 'true', 'Keyboard tab navigation failed');
        const editor = ace.edit(document.querySelector('#student_div .sql-editor'));
        assert(editor.session.getMode().$id === 'ace/mode/letto_sql', 'SQL mode not loaded');
        editor.setValue('SELECT 42;', -1);
        assert(document.querySelector('.student_inp').value === 'SELECT 42;', 'Student answer not persisted');
        assert(ace.edit(document.querySelector('[data-editor="preparation"]')).session.getMode().$id === 'ace/mode/letto_sql', 'SQL preparation mode not loaded');
        assert(ace.edit(document.querySelector('[data-editor="validation"]')).session.getMode().$id === 'ace/mode/python', 'Python test mode not loaded');
        assert(!document.querySelector('[data-setting="language"]'), 'Preparation language selector should not exist');
        const exampleSelect = document.querySelector('[data-example-select]');
        const exampleApply = document.querySelector('[data-example-apply]');
        const titleRow = document.querySelector('.sql-tab-title-row');
        const titleRect = titleRow.querySelector('h3').getBoundingClientRect();
        const controlsRect = exampleSelect.closest('.sql-example-toolbar').getBoundingClientRect();
        assert(Math.abs((titleRect.top + titleRect.bottom) / 2 - (controlsRect.top + controlsRect.bottom) / 2) < 2, 'Examples should share the unit-test title row');
        assert(Math.abs(controlsRect.right - titleRow.getBoundingClientRect().right) < 2, 'Examples should align to the right of the title row');
        const configField = document.querySelector('.configform_config');
        const delay = () => new Promise(resolve => setTimeout(resolve, 100));
        async function waitFor(condition, message) {
            for (let attempt = 0; attempt < 40; attempt++) {
                if (condition()) return;
                await delay();
            }
            throw Error(typeof message === 'function' ? message() : message);
        }
        assert(exampleSelect.options.length === 5, 'Five examples should be available');
        assert(exampleSelect.options[0].textContent === '01 select_products', 'Example numbering missing');
        const savedBeforeCancel = configField.value;
        exampleSelect.value = '1'; exampleApply.click();
        await waitFor(() => document.querySelector('dialog').open, 'Overwrite confirmation missing');
        assert(document.querySelector('dialog').open, 'Overwrite confirmation missing');
        document.querySelector('[data-example-cancel]').click();
        await waitFor(() => !exampleApply.disabled, 'Cancel did not finish');
        assert(configField.value === savedBeforeCancel, 'Cancel overwrote existing code');
        for (let index = 0; index < 5; index++) {
            exampleSelect.value = String(index); exampleApply.click();
            await waitFor(() => document.querySelector('dialog').open || !exampleApply.disabled, 'Example request did not finish');
            if (document.querySelector('dialog').open) {
                document.querySelector('[data-example-confirm]').click();
            }
            await waitFor(() => !exampleApply.disabled, () => 'Applying example ' + index + ' did not finish; dialog open=' + document.querySelector('dialog').open + '; return=' + document.querySelector('dialog').returnValue + '; output=' + document.querySelector('.sql-output').textContent);
            assert(!exampleApply.disabled, 'Apply stayed disabled');
            const saved = JSON.parse(configField.value);
            assert(saved.preparation.includes('CREATE TABLE'), 'Applying example lost preparation');
            assert(saved.validation.includes('Checker'), 'Applying example lost tests');
            assert(saved.datasetVariables[0].value === 3, 'Applying example lost question datasets');
        }
        assert(JSON.parse(configField.value).indication.includes('Join products'), 'JOIN template was not applied');
        for (const action of ['check', 'scorePlugin']) {
            document.querySelector(`[data-action="${action}"]`).click(); await delay();
            assert(/\\d+\\.\\d{2}s elapsed/.test(document.querySelector('.sql-output').textContent), 'Elapsed time missing');
        }
        failNextCheck = true;
        document.querySelector('[data-action="check"]').click(); await delay();
        assert(document.querySelector('.sql-output').textContent.includes('Test connection failure'), 'Check error not displayed');
        assert(document.querySelector('.sql-output').textContent.includes('s elapsed'), 'Failed check timing missing');
        document.querySelector('#student_div button').click();
        await new Promise(resolve => setTimeout(resolve, 100));
        assert(document.querySelector('#student_div pre').textContent === 'Query output', 'Run SQL output missing');
        document.getElementById('result').textContent = 'PASS';
    } catch (error) { document.getElementById('result').textContent = 'FAIL: ' + error.message; }
}, 1500);
</script>'''
HTML = HTML.replace('SQL_EXAMPLES_JSON', json.dumps([sql_example(index).model_dump() for index in range(len(EXAMPLE_NAMES))]))


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/smoke':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path.startswith('/resources/static/ace/'):
            self.path = self.path.replace('/resources/static/ace/', '/resources/vendor/ace/', 1)
            super().do_GET()
        elif self.path.startswith('/resources/static/'):
            self.path = self.path.replace('/resources/static/', '/resources/plugins/SQL/', 1)
            super().do_GET()
        else:
            super().do_GET()

    def log_message(self, *args):
        pass


@unittest.skipUnless(os.getenv('SQL_BROWSER_TEST') == 'true' and CHROME.exists(), 'Set SQL_BROWSER_TEST=true with Chrome installed')
class TestSqlBrowser(unittest.TestCase):
    def test_ace_configuration_persistence_and_student_run(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as profile:
                process = subprocess.run([str(CHROME), '--headless', '--disable-gpu', '--no-first-run',
                                          '--no-default-browser-check', '--disable-extensions',
                                          '--window-size=1280,900',
                                          '--user-data-dir=' + profile, '--dump-dom', '--virtual-time-budget=8000',
                                          f'http://127.0.0.1:{server.server_port}/smoke'],
                                         capture_output=True, text=True, encoding='utf-8', timeout=30)
                result = re.search(r'<pre id="result">([^<]*)</pre>', process.stdout)
                self.assertIsNotNone(result, process.stderr[-1000:])
                self.assertEqual(result.group(1), 'PASS')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

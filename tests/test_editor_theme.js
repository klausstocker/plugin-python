// Unit tests using the real LeTTo helpers and Node's built-in runner.
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const plugins = path.join(__dirname, '..', 'resources', 'plugins');
const source = name => readFileSync(path.join(plugins, name), 'utf8');

function fixture({environment, tools = true} = {}) {
    const listeners = new Set();
    let observer;
    const window = {
        LeTTo: environment,
        addEventListener(type, listener) {
            assert.equal(type, 'letto-umgebung');
            listeners.add(listener);
        },
        removeEventListener(type, listener) { listeners.delete(listener); }
    };
    const context = vm.createContext({
        window, document: {documentElement: {}},
        MutationObserver: class {
            constructor(callback) { this.callback = callback; observer = this; }
            observe() { this.active = true; }
            disconnect() { this.active = false; }
        }
    });
    if (tools) vm.runInContext(source('plugintools.js'), context);
    vm.runInContext(source('editor-theme.js'), context);
    const root = () => {
        const colors = new Map();
        return {isConnected: true, colors, style: {setProperty: (key, value) => colors.set(key, value)}};
    };
    const editor = () => ({theme: null, code: 'saved answer', undo: ['previous edit'],
        setTheme(theme) { this.theme = theme; }});
    function change(environment) {
        window.LeTTo = environment;
        for (const listener of listeners) listener({detail: environment});
    }
    return {context, window, root, editor, change, listeners,
        collect: () => observer.callback(), observing: () => observer.active};
}

for (const [theme, dark] of [
    ['default', false], ['theme-soft-light', false], ['theme-soft-dark', true],
    ['theme-dark', true], ['theme-high-contrast', false]
]) {
    test(theme + ': applies the agreed Ace theme and output colors', () => {
        const f = fixture({environment: {theme, dunkel: dark}});
        const root = f.root(), editor = f.editor();
        f.context.PluginEditorTheme.bind(root, () => [editor]);
        assert.equal(editor.theme, dark ? 'ace/theme/monokai' : 'ace/theme/chrome');
        for (const key of ['--plugin-output-background', '--sql-bg']) {
            assert.equal(root.colors.get(key), dark ? 'black' : 'white');
        }
        for (const key of ['--plugin-output-color', '--sql-fg']) {
            assert.equal(root.colors.get(key), dark ? 'rgb(70, 242, 70)' : 'black');
        }
    });
}

test('design changes update multiple editors without changing answers or Undo', () => {
    const f = fixture();
    const first = f.editor(), second = f.editor(), root = f.root();
    f.context.PluginEditorTheme.bind(root, () => [first, second]);
    for (const dunkel of [true, false, true]) {
        f.change({dunkel});
        for (const editor of [first, second]) {
            assert.equal(editor.theme, dunkel ? 'ace/theme/monokai' : 'ace/theme/chrome');
            assert.equal(editor.code, 'saved answer');
            assert.deepEqual(editor.undo, ['previous edit']);
        }
    }
});

test('an editor loaded after a design change uses the latest environment', () => {
    const f = fixture();
    let editor = null;
    const update = f.context.PluginEditorTheme.bind(f.root(), () => [editor]);
    f.change({dunkel: true});
    editor = f.editor();
    update();
    assert.equal(editor.theme, 'ace/theme/monokai');
});

for (const failure of ['no environment', 'missing tools', 'broken tools']) {
    test(failure + ': uses light instead of the old dark flag', () => {
        const f = fixture({tools: failure !== 'missing tools'});
        f.window.dark_design = true; // Must never influence the default.
        if (failure === 'broken tools') {
            vm.runInContext('lettoDunkel = () => { throw Error("broken"); };' +
                'lettoOnUmgebung = () => { throw Error("broken"); };', f.context);
        }
        const root = f.root(), editor = f.editor();
        f.context.PluginEditorTheme.bind(root, () => [editor]);
        assert.equal(editor.theme, 'ace/theme/chrome');
        assert.equal(root.colors.get('--plugin-output-background'), 'white');
        root.isConnected = false;
        assert.doesNotThrow(f.collect);
    });
}

test('removed roots unsubscribe while other open editors keep updating', () => {
    const f = fixture();
    const first = f.root(), second = f.root();
    const firstEditor = f.editor(), secondEditor = f.editor();
    f.context.PluginEditorTheme.bind(first, () => [firstEditor]);
    f.context.PluginEditorTheme.bind(second, () => [secondEditor]);
    assert.equal(f.listeners.size, 2);
    first.isConnected = false;
    f.collect();
    assert.equal(f.listeners.size, 1);
    assert.equal(f.observing(), true);
    f.change({dunkel: true});
    assert.equal(firstEditor.theme, 'ace/theme/chrome');
    assert.equal(secondEditor.theme, 'ace/theme/monokai');
    second.isConnected = false;
    f.collect();
    assert.equal(f.listeners.size, 0);
    assert.equal(f.observing(), false);
});

test('rebinding a reused root replaces its previous listener and editors', () => {
    const f = fixture();
    const root = f.root(), oldEditor = f.editor(), newEditor = f.editor();
    f.context.PluginEditorTheme.bind(root, () => [oldEditor]);
    f.context.PluginEditorTheme.bind(root, () => [newEditor]);
    assert.equal(f.listeners.size, 1);
    f.change({dunkel: true});
    assert.equal(oldEditor.theme, 'ace/theme/chrome');
    assert.equal(newEditor.theme, 'ace/theme/monokai');
});

test('reloading the shared integration preserves existing bindings', () => {
    const f = fixture();
    const editor = f.editor();
    f.context.PluginEditorTheme.bind(f.root(), () => [editor]);
    vm.runInContext(source('editor-theme.js'), f.context);
    f.change({dunkel: true});
    assert.equal(f.listeners.size, 1);
    assert.equal(editor.theme, 'ace/theme/monokai');
});

test('late initialization of an absent or removed root does not register listeners', () => {
    const f = fixture();
    const root = f.root();
    root.isConnected = false;
    for (const element of [null, root]) {
        const update = f.context.PluginEditorTheme.bind(element);
        assert.doesNotThrow(update);
    }
    assert.equal(f.listeners.size, 0);
});

for (const support of ['available', 'missing theme script', 'missing plugintools']) {
    test('SQL integration: ' + support + ' keeps the editor usable', async () => {
        const f = fixture({environment: {dunkel: true}, tools: support !== 'missing plugintools'});
        if (support === 'missing theme script') delete f.window.PluginEditorTheme;
        const editor = f.editor();
        editor.session = {setMode() {}, setUseWorker() {}, on() {}};
        editor.setValue = value => { editor.code = value; };
        editor.getValue = () => editor.code;
        editor.setReadOnly = () => {};
        f.context.ace = f.window.ace = {
            config: {set() {}}, require: () => ({}), edit: () => editor
        };
        f.context.document.getElementById = () => ({}); // Shared SQL styles already installed.
        f.context.document.createElement = () => ({setAttribute() {}, addEventListener() {}});
        const element = Object.assign(f.root(), {
            getAttribute: () => 'SQL code', appendChild() {}, replaceChildren() {}, addEventListener() {}
        });
        vm.runInContext(source('SQL/SQLScript.js'), f.context);
        f.context.SQLPluginUI.theme(element);
        const control = f.context.SQLPluginUI.editor(element, 'select 1;', 'sql', false, '/pluginsql');
        await new Promise(resolve => setImmediate(resolve));
        assert.equal(control.get(), 'select 1;');
        assert.equal(editor.theme, support === 'available' ? 'ace/theme/monokai' : 'ace/theme/chrome');
        f.change({dunkel: false});
        assert.equal(editor.theme, 'ace/theme/chrome');
        assert.equal(control.get(), 'select 1;');
    });
}

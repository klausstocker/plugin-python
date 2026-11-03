// Unit tests with Node's built-in runner; no browser or third-party packages.
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const resources = path.join(__dirname, '..', 'resources', 'plugins');
const source = (plugin, suffix = 'Script') =>
    readFileSync(path.join(resources, plugin, plugin + suffix + '.js'), 'utf8');

for (const plugin of ['Python', 'Cpp', 'SQL']) {
    new vm.Script(source(plugin, 'ConfigScript'));
    const context = vm.createContext({window: {}});
    vm.runInContext(source(plugin), context);
    assert.equal(typeof context['initPlugin' + plugin], 'function');
    const bind = context['bind' + plugin + 'Answer'];
    const fixture = (value = '') => {
        const field = {value, isConnected: true};
        const parent = {getElementsByClassName: () => [field], parentElement: null};
        const container = {getElementsByClassName: () => [], parentElement: parent, isConnected: true};
        return {field, container};
    };

    test(plugin + ': switching starter code on a reused field discards the previous starter', () => {
        const {field, container} = fixture();
        const first = bind(container, 'question', 'starter A', true);
        assert.equal(first.initial, 'starter A');
        assert.equal(field.value, 'starter A');
        const second = bind(container, 'question', 'starter B', true);
        assert.equal(second.initial, 'starter B');
        assert.equal(field.value, 'starter B');
        first.set('late result from A');
        assert.equal(field.value, 'starter B');
    });

    test(plugin + ': saved answers survive initial rendering and repeated initialization', () => {
        const {field, container} = fixture('saved solution');
        const first = bind(container, 'question', 'starter', true);
        assert.equal(first.initial, 'saved solution');
        first.set('student edits');
        assert.equal(bind(container, 'question', 'starter', true).initial, 'student edits');
        assert.equal(field.value, 'student edits');
    });

    test(plugin + ': intentionally cleared code stays empty on repeated initialization', () => {
        const {container} = fixture();
        bind(container, 'question', 'starter', true).set('');
        assert.equal(bind(container, 'question', 'starter', true).initial, '');
    });

    test(plugin + ': a newly supplied server answer takes precedence on a reused field', () => {
        const {field, container} = fixture();
        bind(container, 'question', 'starter A', true);
        field.value = 'saved solution B';
        assert.equal(bind(container, 'question', 'starter B', true).initial, 'saved solution B');
    });

    test(plugin + ': answer lookup stays within the nearest question fragment', () => {
        const {field, container} = fixture('own solution');
        const other = {value: 'other solution'};
        container.parentElement.parentElement = {getElementsByClassName: () => [other, field]};
        assert.equal(bind(container, 'question', 'starter', true).initial, 'own solution');
        assert.equal(other.value, 'other solution');
    });

    test(plugin + ': ambiguous fields never select the first answer', () => {
        const {field, container} = fixture('other solution');
        container.parentElement.getElementsByClassName = () => [field, {value: 'another solution'}];
        const answer = bind(container, 'question', 'starter', true);
        assert.equal(answer.initial, 'starter');
        answer.set('edit');
        assert.equal(field.value, 'other solution');
    });

    test(plugin + ': removed editors cannot write into retained answer fields', () => {
        const {field, container} = fixture();
        const answer = bind(container, 'question', 'starter', true);
        container.isConnected = false;
        answer.set('late edit');
        assert.equal(field.value, 'starter');
    });

    test(plugin + ': read-only views do not modify submitted answers', () => {
        const {field, container} = fixture('saved solution');
        const answer = bind(container, 'question', 'starter', false);
        assert.equal(answer.initial, 'saved solution');
        answer.set('edit');
        assert.equal(field.value, 'saved solution');
        assert.equal(field._pluginCodeAnswer, undefined);
    });
}

test('SQL: only the latest dialog initializes after shared support finishes loading', async () => {
    let finish;
    const pending = new Promise(resolve => { finish = resolve; });
    const container = {isConnected: true};
    const reachedCurrentDialog = new Error('current dialog reached');
    let fieldReads = 0;
    const context = vm.createContext({
        window: {sqlPluginSupportPromise: pending},
        document: {
            getElementById: () => container,
            querySelector() { fieldReads++; throw reachedCurrentDialog; }
        }
    });
    vm.runInContext(source('SQL', 'ConfigScript'), context);
    const first = context.configPluginSQL('{}');
    const second = context.configPluginSQL('{}');
    context.window.SQLPluginUI = {};
    finish();
    await first;
    await assert.rejects(second, error => error === reachedCurrentDialog);
    assert.equal(fieldReads, 1);
});

for (const plugin of ['Python', 'Cpp']) {
    // Exercise the production async initializer in isolation from layout/network code.
    const script = source(plugin, 'ConfigScript');
    const start = script.indexOf('async function setupEditors(');
    const end = script.indexOf('\n    function fallbackTextArea(', start);
    const initializer = script.slice(start, end);
    test(plugin + ': a delayed example list ignores a closed dialog', async () => {
        let finish;
        const pending = new Promise(resolve => { finish = resolve; });
        const select = {isConnected: true, innerHTML: 'old options'};
        const button = {isConnected: true};
        const context = vm.createContext({
            ids: {exampleSelectId: 'select', exampleApplyId: 'button'},
            document: {getElementById: id => id === 'select' ? select : button},
            requestExample: () => pending
        });
        const examplesStart = script.indexOf('async function setupExamples(');
        const examplesEnd = script.indexOf('\n    function ', examplesStart);
        vm.runInContext(script.slice(examplesStart, examplesEnd), context);
        const loading = context.setupExamples();
        select.isConnected = button.isConnected = false;
        finish({count: 0});
        await loading;
        assert.equal(select.innerHTML, 'old options');
    });
    const fixture = (available = true) => {
        let finish;
        const pending = new Promise(resolve => { finish = () => resolve(available); });
        const elements = {unit: {isConnected: true}, preview: {isConnected: true}};
        const writes = [];
        const context = vm.createContext({
            ids: {unitEditorId: 'unit', previewEditorId: 'preview'},
            document: {getElementById: id => elements[id]},
            ensureAceLoaded: () => pending,
            window: {ace: true}, aceTheme: 'theme',
            state: {validation: 'test A', indication: 'starter A'},
            unitEditor: null, previewEditor: null, editorAccess: {},
            refreshFormat() {}, saveConfig() {},
            fallbackTextArea: (id, value) => writes.push([elements[id], value]),
            fallbackTextAreaSetter() {},
            ace: {edit: element => ({setTheme() {}, session: {
                setMode() {}, setValue: value => writes.push([element, value]), on() {}
            }})}
        });
        vm.runInContext(initializer, context);
        return {context, elements, writes, finish};
    };

    for (const available of [true, false]) {
        test(plugin + ': a delayed initializer ignores replaced dialog elements (Ace=' + available + ')', async () => {
            const {context, elements, writes, finish} = fixture(available);
            const pending = context.setupEditors('test A', 'starter A');
            elements.unit.isConnected = elements.preview.isConnected = false;
            elements.unit = {isConnected: true};
            elements.preview = {isConnected: true};
            finish();
            await pending;
            assert.deepEqual(writes, []);
        });

        test(plugin + ': loading an example before Ace finishes uses the latest code (Ace=' + available + ')', async () => {
            const {context, elements, writes, finish} = fixture(available);
            const pending = context.setupEditors('test A', 'starter A');
            context.state.validation = 'test B';
            context.state.indication = 'starter B';
            finish();
            await pending;
            assert.deepEqual(writes, [[elements.unit, 'test B'], [elements.preview, 'starter B']]);
        });
    }
}

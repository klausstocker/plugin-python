/* Load after plugintools.js; shared by student and configuration editors. */
var PluginEditorTheme = window.PluginEditorTheme || (window.PluginEditorTheme = (() => {
    const bindings = new Map();
    let observer;

    function bind(root, getEditors = () => []) {
        if (!root?.isConnected) return () => {};
        bindings.get(root)?.();
        function update(environment) {
            if (!root.isConnected) return;
            let dark = false;
            try {
                dark = environment ? environment.dunkel === true : lettoDunkel() === true;
            } catch (_) { /* Missing/broken plugintools: keep the light default. */ }
            const background = dark ? 'black' : 'white';
            const foreground = dark ? 'rgb(70, 242, 70)' : 'black';
            root.style.setProperty('--plugin-output-background', background);
            root.style.setProperty('--plugin-output-color', foreground);
            root.style.setProperty('--sql-bg', background);
            root.style.setProperty('--sql-fg', foreground);
            for (const editor of getEditors()) {
                editor?.setTheme(dark ? 'ace/theme/monokai' : 'ace/theme/chrome');
            }
        }
        let unsubscribe = () => {};
        try { unsubscribe = lettoOnUmgebung(update); } catch (_) {}
        function dispose() {
            unsubscribe();
            bindings.delete(root);
            if (!bindings.size) observer.disconnect();
        }
        if (!observer) observer = new MutationObserver(() => {
            for (const [element, cleanup] of bindings) {
                if (!element.isConnected) cleanup();
            }
        });
        bindings.set(root, dispose);
        observer.observe(document.documentElement, {childList: true, subtree: true});
        update();
        // Async Ace initialization calls this again once its editors exist.
        return update;
    }
    return {bind};
})());

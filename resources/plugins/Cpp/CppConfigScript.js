const CPP_CONFIG_SCRIPT_COMMIT_HASH = "unknown";

async function configPluginCpp(dtoString) {
    const dto = JSON.parse(dtoString || "{}");
    const params = dto.params || (dto.pluginDto && dto.pluginDto.params) || {};
    const base = (dto.serviceBase || params.serviceBase || "/plugincpp").replace(/\/$/, "");
    const field = document.querySelector(".configform_config");
    const root = document.getElementById("configform_div");
    if (!field || !root) return;
    let config = {};
    function decode(value) {
        if (!value) return {};
        try { return JSON.parse(value); }
        catch (_) { return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(value), c => c.charCodeAt(0)))); }
    }
    try { config = decode(field.value && field.value !== "{}" ? field.value : (dto.jsonData || params.config)); }
    catch (_) { config = {}; }
    config = Object.assign({language: "cpp", indication: "", validation: "", files: {}, cpuTime: 5, evalConfig: {runAtTest: true, lintAtTest: false}}, config);
    root.innerHTML = `<div class="cpp-config">
      <h2>C/C++ configuration</h2>
      <label>Answer language <select data-cpp="language"><option value="cpp">C++17</option><option value="c">C17</option></select></label>
      <p data-cpp="language-warning" role="status" hidden style="color:#8a4b00"></p>
      <label>CPU time (seconds) <input data-cpp="cpu" type="number" min="1" step="1"></label>
      <label><input data-cpp="run" type="checkbox"> Allow students to run their program</label>
      <p>Template</p><textarea data-cpp="indication" rows="12" spellcheck="false" style="width:100%;font-family:monospace"></textarea>
      <p>Catch2 tests (C++17, also for C answers)</p><textarea data-cpp="validation" rows="16" spellcheck="false" style="width:100%;font-family:monospace"></textarea>
      <p><button data-cpp="check" type="button">Test template</button></p>
      <p>Files available to the submitted program</p><input data-cpp="upload" type="file" multiple><ul data-cpp="files"></ul>
      <p><select data-cpp="example"><option value="0">Function test</option><option value="1">stdout</option><option value="2">Read a file</option></select> <button data-cpp="load" type="button">Load example</button></p>
      <p data-cpp="build"></p><pre data-cpp="output" style="white-space:pre-wrap"></pre>
      <details><summary>C/C++ help</summary><div data-cpp="help"></div></details>
    </div>`;
    const element = name => root.querySelector(`[data-cpp="${name}"]`);
    const token = fetch(base + "/exectoken").then(response => {
        if (!response.ok) throw new Error("Unable to obtain execution token");
        return response.json();
    }).then(data => data.token);
    async function request(path, body, multipart = false) {
        const headers = {Authorization: "Bearer " + await token};
        if (!multipart) headers["Content-Type"] = "application/json";
        const response = await fetch(base + path, {method: "POST", headers, body: multipart ? body : JSON.stringify(body)});
        const data = await response.json();
        if (!response.ok) throw new Error(data.output || data.error || data.detail || response.statusText);
        return data;
    }
    function save() {
        if (config.language !== element("language").value) {
            const warning = element("language-warning");
            warning.textContent = "Answer language changed. Check the template and test forward declarations: C answers need extern \"C\"; C++ answers use C++ linkage. The bundled examples select linkage automatically with __has_include(\"answer.c\"). Your code has not been rewritten; see the help for the pattern.";
            warning.hidden = false;
        }
        config.language = element("language").value;
        config.indication = element("indication").value;
        config.validation = element("validation").value;
        config.cpuTime = Math.max(1, Math.floor(Number(element("cpu").value) || 5));
        config.evalConfig = {runAtTest: element("run").checked, lintAtTest: false};
        config.linterWeight = 0;
        field.value = JSON.stringify(config);
        field.dispatchEvent(new Event("input", {bubbles: true}));
        field.dispatchEvent(new Event("change", {bubbles: true}));
    }
    function showFiles() {
        element("files").replaceChildren();
        Object.entries(config.files || {}).forEach(([name]) => {
            const item = document.createElement("li");
            item.append(document.createTextNode(name + " "));
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = "Remove from question";
            button.onclick = () => { delete config.files[name]; showFiles(); save(); };
            item.append(button);
            element("files").append(item);
        });
    }
    function render() {
        element("language-warning").hidden = true;
        element("language").value = config.language;
        element("cpu").value = config.cpuTime;
        element("run").checked = config.evalConfig.runAtTest !== false;
        element("indication").value = config.indication;
        element("validation").value = config.validation;
        showFiles();
        save();
    }
    ["language", "cpu", "run", "indication", "validation"].forEach(name => element(name).addEventListener("input", save));
    async function action(callback) {
        try { await callback(); }
        catch (error) { element("output").textContent = error.message; }
    }
    element("check").onclick = () => action(async () => {
        save();
        const data = await request("/check", {code: config.indication, testcode: config.validation, questionConfigDto: config});
        element("output").textContent = data.output;
    });
    element("upload").onchange = () => action(async () => {
        for (const file of element("upload").files) {
            const body = new FormData(); body.append("file", file);
            const data = await request("/files/upload", body, true);
            config.files[data.displayName] = data;
        }
        element("upload").value = "";
        showFiles(); save();
    });
    element("load").onclick = () => action(async () => {
        if (!window.confirm("Replace the template, tests and file list with this example?")) return;
        const data = await request("/example", {index: Number(element("example").value), questionConfigDto: config});
        config = data.output;
        render();
    });
    render();
    action(async () => {
        const response = await fetch(base + "/help");
        if (!response.ok) throw new Error("Unable to load C/C++ help");
        element("help").innerHTML = await response.text();
    });
    action(async () => {
        const response = await fetch(base + "/buildhash", {headers: {Authorization: "Bearer " + await token}});
        const data = await response.json();
        element("build").textContent = "Script build: " + CPP_CONFIG_SCRIPT_COMMIT_HASH + "; server build: " + (data.commitHash || "unknown");
    });
}

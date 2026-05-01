try {
    $ = jQuery;
} catch (e) {}

function configPluginPython(dtoString) {
    const config_form_div = "#configform_div";
    const config_form_config = ".configform_config";

    const dto = JSON.parse(dtoString || "{}");
    let jsonData = {};
    try {
        jsonData = dto.jsonData ? JSON.parse(dto.jsonData) : {};
    } catch (e) {
        jsonData = {};
    }

    const configField = $(config_form_config)[0];
    const pluginTag = dto.tagName || "pluginpython";
    const serviceBase = ((dto.pluginDto && dto.pluginDto.serviceBase) || "/pluginpython").replace(/\/$/, "");
    const pluginToken = (dto.params && dto.params.pluginToken) || "";

    const ids = {
        rootClass: "pluginConfigForm",
        tabsWrapId: `tabsWrap_${pluginTag}`,
        unitEditorId: `unitEditor_${pluginTag}`,
        previewEditorId: `previewEditor_${pluginTag}`,
        outputId: `sharedOutput_${pluginTag}`,
        btnRunId: `sharedRun_${pluginTag}`,
        btnLintId: `sharedLint_${pluginTag}`,
        btnCheckId: `sharedCheck_${pluginTag}`,
        exampleSelectId: `exampleSelect_${pluginTag}`,
        exampleApplyId: `exampleApply_${pluginTag}`,
        fileNameId: `fileName_${pluginTag}`,
        fileListId: `fileList_${pluginTag}`,
        fileUploadId: `fileUpload_${pluginTag}`,
        optRunAtTestId: `optRunAtTest_${pluginTag}`,
        optUnitTestAtTestId: `optUnitTestAtTest_${pluginTag}`,
        optLintAtTestId: `optLintAtTest_${pluginTag}`
    };

    const state = parseConfig(configField && configField.value ? configField.value : "", jsonData);
    const questionConfigDto = parseQuestionConfigDto(configField && configField.value ? configField.value : "", dto);

    drawForm();
    ensureStyles();
    setupTabs();
    setupEditors(state.validation, state.indication);
    setupFileTab();
    setupOptionsTab();
    bindSharedButtons();
    setupExamples();
    renderHelp();
    saveConfig();

    function parseConfig(rawValue, fallbackData) {
        const configRawValue = extractRawConfig(rawValue);
        const defaults = {
            indication: (fallbackData && fallbackData.indication) || "# Preview code\n",
            validation: (fallbackData && fallbackData.validation) || "# Unit test code\n",
            files: (fallbackData && fallbackData.files) || {},
            evalConfig: {
                runAtTest: fallbackData && fallbackData.evalConfig ? !!fallbackData.evalConfig.runAtTest : true,
                unitTestAtTest: fallbackData && fallbackData.evalConfig ? !!fallbackData.evalConfig.unitTestAtTest : false,
                lintAtTest: fallbackData && fallbackData.evalConfig ? !!fallbackData.evalConfig.lintAtTest : true
            }
        };

        if (!configRawValue) return defaults;

        try {
            const parsed = JSON.parse(configRawValue);
            return {
                indication: parsed.indication || defaults.indication,
                validation: parsed.validation || defaults.validation,
                files: parsed.files || defaults.files,
                evalConfig: {
                    runAtTest: parsed.evalConfig && typeof parsed.evalConfig.runAtTest === "boolean" ? parsed.evalConfig.runAtTest : defaults.evalConfig.runAtTest,
                    unitTestAtTest: parsed.evalConfig && typeof parsed.evalConfig.unitTestAtTest === "boolean" ? parsed.evalConfig.unitTestAtTest : defaults.evalConfig.unitTestAtTest,
                    lintAtTest: parsed.evalConfig && typeof parsed.evalConfig.lintAtTest === "boolean" ? parsed.evalConfig.lintAtTest : defaults.evalConfig.lintAtTest
                }
            };
        } catch (e) {
            return {
                indication: configRawValue,
                validation: defaults.validation,
                files: defaults.files,
                evalConfig: defaults.evalConfig
            };
        }
    }


    function parseQuestionConfigDto(rawValue, sourceDto) {
        const fallback = sourceDto && sourceDto.questionConfigDto && typeof sourceDto.questionConfigDto === "object"
            ? { ...sourceDto.questionConfigDto }
            : {};

        if (!rawValue) return fallback;

        try {
            const parsed = JSON.parse(rawValue);
            if (parsed && typeof parsed === "object" && Object.prototype.hasOwnProperty.call(parsed, "config")) {
                return { ...fallback, ...parsed };
            }
        } catch (e) {}

        return fallback;
    }

    function extractRawConfig(rawValue) {
        if (!rawValue) return "";

        try {
            const parsed = JSON.parse(rawValue);
            if (parsed && typeof parsed === "object" && typeof parsed.config === "string") {
                return parsed.config;
            }
        } catch (e) {}

        return rawValue;
    }

    function drawForm() {
        const selector = "." + ids.rootClass;
        if ($(selector).length > 0) {
            $(selector).remove();
        }

        $(config_form_div).append(`
            <div class="${ids.rootClass}">
                <div class="config-main">
                    <div class="tab-buttons">
                        <button type="button" class="tab-btn active" data-tab="tab-unittest">UnitTest</button>
                        <button type="button" class="tab-btn" data-tab="tab-preview">Preview</button>
                        <button type="button" class="tab-btn" data-tab="tab-files">Files</button>
                        <button type="button" class="tab-btn" data-tab="tab-options">Configuration</button>
                    </div>

                    <div id="${ids.tabsWrapId}" class="tab-panels">
                        <div class="tab-panel active" id="tab-unittest">
                            <div class="tab-title-row">
                                <h3>Unit test</h3>
                                <div class="unit-example-controls">
                                    <label for="${ids.exampleSelectId}">Example:</label>
                                    <select id="${ids.exampleSelectId}" class="text-input unit-example-select"></select>
                                    <button type="button" id="${ids.exampleApplyId}" class="cfg-btn">Apply</button>
                                </div>
                            </div>
                            <div id="${ids.unitEditorId}" class="editor-box"></div>
                        </div>

                        <div class="tab-panel" id="tab-preview">
                            <h3>Preview editor</h3>
                            <div id="${ids.previewEditorId}" class="editor-box"></div>
                        </div>

                        <div class="tab-panel" id="tab-files">
                            <h3>File management</h3>
                            <div class="files-grid">
                                <div>
                                    <label>File name</label>
                                    <input id="${ids.fileNameId}" type="text" class="text-input" placeholder="example.py" />
                                    <div class="btn-row small-gap">
                                        <button type="button" class="cfg-btn" data-file-action="delete">delete</button>
                                        <button type="button" class="cfg-btn" data-file-action="download">download</button>
                                    </div>
                                    <div class="btn-row small-gap">
                                        <input id="${ids.fileUploadId}" type="file" />
                                        <button type="button" class="cfg-btn" data-file-action="upload">import</button>
                                    </div>
                                </div>
                                <div>
                                    <label>Stored files</label>
                                    <div id="${ids.fileListId}" class="file-list"></div>
                                </div>
                            </div>
                        </div>

                        <div class="tab-panel" id="tab-options">
                            <h3>Configuration flags</h3>
                            <label class="checkbox-row"><input id="${ids.optRunAtTestId}" type="checkbox" /> runAtTest</label>
                            <label class="checkbox-row"><input id="${ids.optUnitTestAtTestId}" type="checkbox" /> unitTestAtTest</label>
                            <label class="checkbox-row"><input id="${ids.optLintAtTestId}" type="checkbox" /> lintAtTest</label>
                        </div>
                    </div>

                    <div class="shared-actions">
                        <div class="btn-row">
                            <button type="button" id="${ids.btnRunId}" class="cfg-btn">run</button>
                            <button type="button" id="${ids.btnLintId}" class="cfg-btn">lint</button>
                            <button type="button" id="${ids.btnCheckId}" class="cfg-btn">check</button>
                        </div>
                        <pre id="${ids.outputId}" class="output-box"></pre>
                    </div>
                </div>

                <div class="config-help">
                    <h3>Help</h3>
                    <a href="https://doc.letto.at/wiki/Plugins" target="_blank">Wiki-Plugins</a>
                    <div id="configPluginHelp"></div>
                    <div id="configPluginWiki"></div>
                </div>
            </div>
        `);
    }

    function ensureStyles() {
        const styleId = "pluginpython-config-style";
        if (document.getElementById(styleId)) return;

        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = `
            .pluginConfigForm {
                display: flex;
                width: 100%;
                height: 75vh;
                box-sizing: border-box;
                gap: 10px;
            }
            .pluginConfigForm .config-main {
                flex: 2;
                display: flex;
                flex-direction: column;
                gap: 10px;
                min-width: 0;
            }
            .pluginConfigForm .config-help {
                flex: 1;
                border: 1px solid #ccc;
                padding: 10px;
                overflow: auto;
                min-width: 0;
            }
            .pluginConfigForm .tab-buttons {
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
            }
            .pluginConfigForm .tab-btn,
            .pluginConfigForm .cfg-btn {
                border: 1px solid #b8b8b8;
                background: #f0f0f0;
                padding: 6px 14px;
                border-radius: 4px;
                cursor: pointer;
            }
            .pluginConfigForm .tab-btn.active {
                background: #dce9ff;
            }
            .pluginConfigForm .tab-panels {
                flex: 1;
                min-height: 0;
                border: 1px solid #ccc;
                padding: 8px;
            }
            .pluginConfigForm .tab-panel {
                display: none;
                height: 100%;
                min-height: 0;
                flex-direction: column;
                gap: 8px;
            }
            .pluginConfigForm .tab-panel.active {
                display: flex;
            }
            .pluginConfigForm .tab-title-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
            }
            .pluginConfigForm .tab-title-row h3 {
                margin: 0;
            }
            .pluginConfigForm .unit-example-controls {
                margin-left: auto;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .pluginConfigForm .unit-example-select {
                width: auto;
                min-width: 120px;
                margin: 0;
            }
            .pluginConfigForm .editor-box {
                flex: 1;
                min-height: 0;
                border: 1px solid #d0d0d0;
            }
            .pluginConfigForm .shared-actions {
                border: 1px solid #ccc;
                padding: 8px;
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-height: 180px;
            }
            .pluginConfigForm .output-box {
                margin: 0;
                flex: 1;
                min-height: 120px;
                border: 1px solid #d0d0d0;
                background: #101010;
                color: #8df58d;
                padding: 8px;
                overflow: auto;
                white-space: pre-wrap;
                font-family: monospace;
                font-size: 13px;
            }
            .pluginConfigForm .files-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                min-height: 0;
                height: 100%;
            }
            .pluginConfigForm .text-input {
                width: 100%;
                box-sizing: border-box;
                margin: 4px 0 8px;
                font-family: monospace;
            }
            .pluginConfigForm .file-list {
                border: 1px solid #d0d0d0;
                min-height: 220px;
                max-height: 100%;
                overflow: auto;
                padding: 6px;
                font-family: monospace;
            }
            .pluginConfigForm .file-item {
                padding: 4px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
            }
            .pluginConfigForm .file-item:hover {
                background: #f5f5f5;
            }
            .pluginConfigForm .checkbox-row {
                display: block;
                margin: 8px 0;
            }
            .pluginConfigForm .small-gap {
                gap: 6px;
            }
            .pluginConfigForm iframe {
                width: 100%;
                height: 60vh;
                border: none;
            }
        `;
        document.head.appendChild(style);
    }

    function setupTabs() {
        const root = document.getElementById(ids.tabsWrapId).closest(".config-main");
        const tabButtons = root.querySelectorAll(".tab-btn");
        const panels = root.querySelectorAll(".tab-panel");

        tabButtons.forEach((btn) => {
            btn.addEventListener("click", () => {
                const target = btn.getAttribute("data-tab");
                tabButtons.forEach((b) => b.classList.remove("active"));
                panels.forEach((p) => p.classList.remove("active"));
                btn.classList.add("active");
                const panel = document.getElementById(target);
                if (panel) panel.classList.add("active");
            });
        });
    }

    function ensureAceLoaded() {
        return new Promise((resolve) => {
            if (window.ace) {
                resolve(true);
                return;
            }
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.js";
            script.onload = () => resolve(true);
            script.onerror = () => resolve(false);
            document.head.appendChild(script);
        });
    }

    async function setupEditors(initialUnit, initialPreview) {
        const aceAvailable = await ensureAceLoaded();

        if (aceAvailable && window.ace) {
            const unitEditor = ace.edit(ids.unitEditorId);
            unitEditor.setTheme("ace/theme/monokai");
            unitEditor.session.setMode("ace/mode/python");
            unitEditor.session.setValue(initialUnit || "");

            const previewEditor = ace.edit(ids.previewEditorId);
            previewEditor.setTheme("ace/theme/monokai");
            previewEditor.session.setMode("ace/mode/python");
            previewEditor.session.setValue(initialPreview || "");

            unitEditor.session.on("change", saveConfig);
            previewEditor.session.on("change", saveConfig);

            configPluginPython._getUnitCode = () => unitEditor.getValue();
            configPluginPython._getPreviewCode = () => previewEditor.getValue();
            configPluginPython._setUnitCode = (value) => unitEditor.session.setValue(value || "");
            configPluginPython._setPreviewCode = (value) => previewEditor.session.setValue(value || "");
        } else {
            fallbackTextArea(ids.unitEditorId, initialUnit, "_getUnitCode");
            fallbackTextArea(ids.previewEditorId, initialPreview, "_getPreviewCode");
            fallbackTextAreaSetter(ids.unitEditorId, "_setUnitCode");
            fallbackTextAreaSetter(ids.previewEditorId, "_setPreviewCode");
        }
    }

    function fallbackTextArea(targetId, value, key) {
        const target = document.getElementById(targetId);
        target.innerHTML = `<textarea style="width:100%;height:100%;box-sizing:border-box;font-family:monospace;">${escapeHtml(value || "")}</textarea>`;
        const ta = target.querySelector("textarea");
        ta.addEventListener("input", saveConfig);
        configPluginPython[key] = () => ta.value;
    }

    function fallbackTextAreaSetter(targetId, key) {
        configPluginPython[key] = (value) => {
            const target = document.getElementById(targetId);
            const ta = target ? target.querySelector("textarea") : null;
            if (ta) ta.value = value || "";
        };
    }

    function getUnitCode() {
        return configPluginPython._getUnitCode ? configPluginPython._getUnitCode() : "";
    }

    function getPreviewCode() {
        return configPluginPython._getPreviewCode ? configPluginPython._getPreviewCode() : "";
    }

    function setupFileTab() {
        const fileNameInput = document.getElementById(ids.fileNameId);
        const fileList = document.getElementById(ids.fileListId);
        const fileUpload = document.getElementById(ids.fileUploadId);

        function renderFileList() {
            const names = Object.keys(state.files || {}).sort();
            if (!names.length) {
                fileList.innerHTML = "<em>No files stored.</em>";
                return;
            }
            fileList.innerHTML = names.map((name) => `<div class="file-item" data-file="${escapeHtmlAttr(name)}">${escapeHtml(name)}</div>`).join("");
            fileList.querySelectorAll(".file-item").forEach((row) => {
                row.addEventListener("click", () => {
                    const name = row.getAttribute("data-file");
                    fileNameInput.value = name;
                });
            });
        }

        document.querySelectorAll("[data-file-action]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const action = btn.getAttribute("data-file-action");
                const name = (fileNameInput.value || "").trim();

                if (action === "delete") {
                    if (!name || !state.files[name]) return;
                    delete state.files[name];
                    renderFileList();
                    saveConfig();
                    return;
                }

                if (action === "download") {
                    if (!name || state.files[name] == null) return;
                    const blob = new Blob([state.files[name]], { type: "text/plain" });
                    const a = document.createElement("a");
                    a.href = URL.createObjectURL(blob);
                    a.download = name;
                    a.click();
                    URL.revokeObjectURL(a.href);
                    return;
                }

                if (action === "upload") {
                    const file = fileUpload.files && fileUpload.files[0];
                    if (!file) return;
                    const text = await file.text();
                    state.files[file.name] = text;
                    fileNameInput.value = file.name;
                    fileUpload.value = "";
                    renderFileList();
                    saveConfig();
                }
            });
        });

        renderFileList();
    }

    function setupOptionsTab() {
        const runAtTest = document.getElementById(ids.optRunAtTestId);
        const unitTestAtTest = document.getElementById(ids.optUnitTestAtTestId);
        const lintAtTest = document.getElementById(ids.optLintAtTestId);

        runAtTest.checked = !!state.evalConfig.runAtTest;
        unitTestAtTest.checked = !!state.evalConfig.unitTestAtTest;
        lintAtTest.checked = !!state.evalConfig.lintAtTest;

        [runAtTest, unitTestAtTest, lintAtTest].forEach((el) => {
            el.addEventListener("change", () => {
                state.evalConfig.runAtTest = !!runAtTest.checked;
                state.evalConfig.unitTestAtTest = !!unitTestAtTest.checked;
                state.evalConfig.lintAtTest = !!lintAtTest.checked;
                saveConfig();
            });
        });
    }

    function bindSharedButtons() {
        const outputEl = document.getElementById(ids.outputId);

        bindRequest(ids.btnRunId, "/run", () => ({ code: getActiveEditorCode() }), outputEl);
        bindRequest(ids.btnLintId, "/lint", () => ({ code: getActiveEditorCode() }), outputEl);
        bindRequest(ids.btnCheckId, "/check", () => ({ code: getPreviewCode(), testcode: getUnitCode() }), outputEl);
    }

    async function setupExamples() {
        const select = document.getElementById(ids.exampleSelectId);
        const applyBtn = document.getElementById(ids.exampleApplyId);
        if (!select || !applyBtn) return;

        const initial = await requestExample(0);
        if (!initial || typeof initial.count !== "number") {
            applyBtn.disabled = true;
            return;
        }

        select.innerHTML = "";
        for (let i = 0; i < initial.count; i += 1) {
            const option = document.createElement("option");
            option.value = String(i);
            option.textContent = `Example ${i + 1}`;
            select.appendChild(option);
        }
        select.disabled = initial.count === 0;
        applyBtn.disabled = initial.count === 0;
        select.value = "0";

        applyBtn.addEventListener("click", async () => {
            const index = Number(select.value);
            const exampleData = await requestExample(index);
            if (exampleData && exampleData.output) {
                applyExample(exampleData.output);
            }
        });
    }

    async function requestExample(index) {
        try {
            const response = await fetch(serviceBase + "/example", {
                method: "POST",
                headers: buildHeaders(),
                body: JSON.stringify({ index: index })
            });
            return await response.json();
        } catch (error) {
            return null;
        }
    }

    function applyExample(example) {
        if (!example) return;
        state.files = example.files || {};
        state.evalConfig = example.evalConfig || { runAtTest: true, unitTestAtTest: false, lintAtTest: true };

        if (configPluginPython._setUnitCode) configPluginPython._setUnitCode(example.validation || "");
        if (configPluginPython._setPreviewCode) configPluginPython._setPreviewCode(example.indication || "");

        setupFileTab();
        setupOptionsTab();
        saveConfig();
    }

    function getActiveEditorCode() {
        const activeTab = document.querySelector(".pluginConfigForm .tab-panel.active");
        if (!activeTab) return getPreviewCode();
        if (activeTab.id === "tab-unittest") return getUnitCode();
        return getPreviewCode();
    }

    function bindRequest(buttonId, endpoint, bodyBuilder, outputEl) {
        const btn = document.getElementById(buttonId);
        if (!btn) return;

        btn.addEventListener("click", async (event) => {
            event.preventDefault();
            saveConfig();
            const oldText = btn.textContent;
            btn.disabled = true;
            btn.textContent = "working...";
            outputEl.textContent = "";

            try {
                const response = await fetch(serviceBase + endpoint, {
                    method: "POST",
                    headers: buildHeaders(),
                    body: JSON.stringify(bodyBuilder())
                });
                const data = await response.json();
                outputEl.textContent = data && data.output ? data.output : JSON.stringify(data);
            } catch (error) {
                outputEl.textContent = "Error: " + (error && error.message ? error.message : "request failed");
            } finally {
                btn.disabled = false;
                btn.textContent = oldText;
            }
        });
    }

    function saveConfig() {
        if (!configField) return;

        const pluginConfig = {
            indication: getPreviewCode(),
            validation: getUnitCode(),
            files: state.files || {},
            evalConfig: state.evalConfig || {}
        };

        questionConfigDto.validation = pluginConfig.validation;
        questionConfigDto.config = JSON.stringify(pluginConfig);

        configField.value = JSON.stringify(questionConfigDto);
    }

    function renderHelp() {
        if (dto.params && dto.params.help != null) {
            const helpElement = document.getElementById("configPluginHelp");
            helpElement.innerHTML = dto.params.help;
        }

        if (dto.params && dto.params.wikiurl != null) {
            const wikiElement = document.getElementById("configPluginWiki");
            wikiElement.innerHTML = '<iframe src="' + dto.params.wikiurl + '"></iframe>';
        }
    }

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function escapeHtmlAttr(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function buildHeaders() {
        const headers = { "Content-Type": "application/json" };
        if (pluginToken) {
            headers["Authorization"] = "Bearer " + pluginToken;
        }
        return headers;
    }
}

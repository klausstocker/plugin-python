try {
    $ = jQuery;
} catch (e) {}

const PYTHON_CONFIG_SCRIPT_COMMIT_HASH = "c70dad38cc61";

function configPluginPython(dtoString) {
    // -------------------------- Verbindungskonstante zu LeTTo ---------------------------------------
    // Div Element welches im Konfigurations-Formular liegt - MUSS für LETTO SO HEISSEN!!
    const config_form_div = "#configform_div";
    // verstecktes Input-Element für die Eingabe - MUSS für LETTO SO HEISSEN !!
    const config_form_config = ".configform_config";
    // ------------------------------------------------------------------------------------------------

    const dto = JSON.parse(dtoString || "{}");
    const jsonData = parseDtoJsonData(dto);
    logDatasetTransfer("config init dto", dto);
    logDatasetTransfer("config init jsonData", jsonData);

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
        btnScoreId: `sharedScore_${pluginTag}`,
        exampleSelectId: `exampleSelect_${pluginTag}`,
        exampleApplyId: `exampleApply_${pluginTag}`,
        fileListId: `fileList_${pluginTag}`,
        fileUploadId: `fileUpload_${pluginTag}`,
        optRunAtTestId: `optRunAtTest_${pluginTag}`,
        optLintAtTestId: `optLintAtTest_${pluginTag}`,
        linterConfigId: `linterConfig_${pluginTag}`,
        linterWeightId: `linterWeight_${pluginTag}`,
        buildInfoId: `buildInfo_${pluginTag}`,
        helpToggleId: `helpToggle_${pluginTag}`,
        outputToggleId: `outputToggle_${pluginTag}`,
        mainSplitId: `mainSplit_${pluginTag}`,
        splitHandleId: `splitHandle_${pluginTag}`
    };

    const state = parseConfig(configField && configField.value ? configField.value : "", jsonData);
    const questionConfigDto = parseQuestionConfigDto(configField && configField.value ? configField.value : "", dto);
    logDatasetTransfer("config parsed questionConfigDto", questionConfigDto);

    drawForm();
    ensureStyles();
    setupTabs();
    setupResizableSections();
    setupEditors(state.validation, state.indication);
    setupFileTab();
    setupOptionsTab();
    setupBuildInfo();
    bindSharedButtons();
    setupExamples();
    renderHelp();
    saveConfig();


    function logDatasetTransfer(label, value) {
        if (!window.console || typeof window.console.log !== "function") return;

        const summary = summarizeDatasetVariables(value);
        window.console.log(`[pluginpython dataset] ${label}`, summary, value);
    }

    function summarizeDatasetVariables(value) {
        const result = {
            hasValue: !!value,
            topLevelKeys: value && typeof value === "object" ? Object.keys(value) : [],
            datasetFields: {}
        };
        if (!value || typeof value !== "object") return result;

        ["vars", "cvars", "varsMaxima", "mvars", "varsQuestion"].forEach((field) => {
            if (value[field] != null) {
                result.datasetFields[field] = summarizeDatasetField(value[field]);
            }
        });

        if (value.q && typeof value.q === "object") {
            result.q = summarizeDatasetVariables(value.q).datasetFields;
        }
        if (value.params && typeof value.params === "object") {
            result.params = summarizeDatasetVariables(value.params).datasetFields;
        }
        if (value.pluginDto && typeof value.pluginDto === "object") {
            result.pluginDto = summarizeDatasetVariables(value.pluginDto);
        }
        if (value.questionConfigDto && typeof value.questionConfigDto === "object") {
            result.questionConfigDto = summarizeDatasetVariables(value.questionConfigDto);
        }

        return result;
    }

    function summarizeDatasetField(fieldValue) {
        if (typeof fieldValue === "string") {
            return { type: "string", length: fieldValue.length, preview: fieldValue.slice(0, 200) };
        }
        if (!fieldValue || typeof fieldValue !== "object") {
            return { type: typeof fieldValue, value: fieldValue };
        }
        const vars = fieldValue.vars && typeof fieldValue.vars === "object" ? fieldValue.vars : fieldValue;
        const variableValues = {};
        if (vars && typeof vars === "object") {
            Object.keys(vars).forEach((name) => {
                variableValues[name] = summarizeDatasetVariable(vars[name]);
            });
        }
        return {
            type: Array.isArray(fieldValue) ? "array" : "object",
            keys: Object.keys(fieldValue),
            variableNames: vars && typeof vars === "object" ? Object.keys(vars) : [],
            variableValues: variableValues
        };
    }

    function summarizeDatasetVariable(variableValue) {
        if (!variableValue || typeof variableValue !== "object") {
            return { type: typeof variableValue, value: variableValue };
        }
        const calcResult = variableValue.calcErgebnisDto || {};
        return {
            type: "object",
            keys: Object.keys(variableValue),
            calcErgebnisDto: variableValue.calcErgebnisDto && typeof variableValue.calcErgebnisDto === "object" ? {
                type: calcResult.type,
                string: calcResult.string,
                json: calcResult.json
            } : null,
            ze: variableValue.ze,
            hasCalcParams: variableValue.cp != null
        };
    }

    function parseDtoJsonData(sourceDto) {
        if (!sourceDto || !sourceDto.jsonData) return {};
        try {
            try {
                return JSON.parse(atob(sourceDto.jsonData));
            } catch (decodeError) {
                return JSON.parse(sourceDto.jsonData);
            }
        } catch (e) {
            return {};
        }
    }

    function parseJsonObject(rawValue) {
        if (!rawValue || typeof rawValue !== "string") return null;
        try {
            const parsed = JSON.parse(rawValue);
            return parsed && typeof parsed === "object" ? parsed : null;
        } catch (e) {
            return null;
        }
    }

    function extractFilesFromConfigValue(rawValue) {
        const parsed = parseJsonObject(rawValue);
        if (!parsed) return {};
        if (parsed.files && typeof parsed.files === "object") return parsed.files;
        return {};
    }

    function currentStoredFiles() {
        if (state.files && Object.keys(state.files).length) return state.files;
        const savedFiles = configField ? extractFilesFromConfigValue(configField.value) : {};
        if (Object.keys(savedFiles).length) {
            state.files = savedFiles;
            return state.files;
        }
        return state.files || {};
    }

    function parseConfig(rawValue, fallbackData) {
        const defaults = {
            indication: (fallbackData && fallbackData.indication) || "# Preview code\n",
            validation: (fallbackData && fallbackData.validation) || "# Unit test code\n",
            files: (fallbackData && fallbackData.files) || extractFilesFromConfigValue(rawValue) || {},
            evalConfig: {
                runAtTest: fallbackData && fallbackData.evalConfig ? !!fallbackData.evalConfig.runAtTest : true,
                lintAtTest: fallbackData && fallbackData.evalConfig ? !!fallbackData.evalConfig.lintAtTest : true
            },
            linterConfig: (fallbackData && fallbackData.linterConfig) || "",
            linterWeight: parseWeightValue(fallbackData && fallbackData.linterWeight)
        };

        if (!rawValue) return defaults;

        try {
            const parsed = JSON.parse(rawValue);
            return {
                indication: parsed.indication || defaults.indication,
                validation: parsed.validation || defaults.validation,
                files: parsed.files || defaults.files,
                evalConfig: {
                    runAtTest: parsed.evalConfig && typeof parsed.evalConfig.runAtTest === "boolean" ? parsed.evalConfig.runAtTest : defaults.evalConfig.runAtTest,
                    lintAtTest: parsed.evalConfig && typeof parsed.evalConfig.lintAtTest === "boolean" ? parsed.evalConfig.lintAtTest : defaults.evalConfig.lintAtTest
                },
                linterConfig: typeof parsed.linterConfig === "string" ? parsed.linterConfig : defaults.linterConfig,
                linterWeight: parseWeightValue(parsed.linterWeight != null ? parsed.linterWeight : defaults.linterWeight)
            };
        } catch (e) {
            return {
                indication: rawValue,
                validation: defaults.validation,
                files: defaults.files,
                evalConfig: defaults.evalConfig,
                linterConfig: defaults.linterConfig,
                linterWeight: defaults.linterWeight
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
            if (parsed && typeof parsed === "object") {
                return { ...fallback, ...parsed };
            }
        } catch (e) {}

        return fallback;
    }

    function drawForm() {
        const selector = "." + ids.rootClass;
        if ($(selector).length > 0) {
            $(selector).remove();
        }

        $(config_form_div).append(`
            <div class="${ids.rootClass}">
                <div class="config-main">
                    <div class="tab-head-row">
                        <div class="tab-buttons">
                            <button type="button" class="tab-btn active" data-tab="tab-unittest">UnitTest</button>
                            <button type="button" class="tab-btn" data-tab="tab-preview">Preview</button>
                            <button type="button" class="tab-btn" data-tab="tab-files">Files</button>
                            <button type="button" class="tab-btn" data-tab="tab-options">Configuration</button>
                        </div>
                    </div>

                    <div id="${ids.mainSplitId}" class="main-split" data-output-hidden="false">
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
                                        <label>Upload file</label>
                                        <div class="btn-row small-gap">
                                            <input id="${ids.fileUploadId}" type="file" />
                                            <button type="button" class="cfg-btn" data-file-action="upload">import</button>
                                        </div>
                                        <div class="btn-row small-gap">
                                            <button type="button" class="cfg-btn" data-file-action="download">download selected</button>
                                            <button type="button" class="cfg-btn" data-file-action="delete">delete selected</button>
                                        </div>
                                        <p class="file-help">Select a stored file to download or delete it.</p>
                                    </div>
                                    <div>
                                        <label>Stored files</label>
                                        <div id="${ids.fileListId}" class="file-list"></div>
                                    </div>
                                </div>
                            </div>

                            <div class="tab-panel" id="tab-options">
                                <h3>Configuration flags</h3>
                                <div id="${ids.buildInfoId}" class="build-info" title="Source commit or build revision for this configuration script">
                                    <span>Script build: <span data-build-role="script">${escapeHtml(PYTHON_CONFIG_SCRIPT_COMMIT_HASH)}</span></span>
                                    <span class="build-separator"> | </span>
                                    <span>Server build: <span data-build-role="server">loading...</span></span>
                                </div>
                                <div class="flags-row">
                                    <label class="checkbox-row"><input id="${ids.optRunAtTestId}" type="checkbox" /> run at test</label>
                                    <label class="checkbox-row"><input id="${ids.optLintAtTestId}" type="checkbox" /> lint at test</label>
                                </div>
                                <div class="linter-head-row">
                                    <label for="${ids.linterConfigId}">Linter configuration</label>
                                    <label for="${ids.linterWeightId}" title="unit test scores is weighted with 1.0, choose linter weight">Weight</label>
                                    <input id="${ids.linterWeightId}" type="text" inputmode="decimal" class="text-input linter-weight-input" placeholder="0.0" />
                                </div>
                                <textarea id="${ids.linterConfigId}" class="text-input" rows="4" placeholder="e.g. --disable=C0114,C0116"></textarea>
                            </div>
                        </div>

                        <div id="${ids.splitHandleId}" class="split-handle" title="Drag to resize editor/output sections"></div>

                        <div class="shared-actions">
                            <div class="shared-head-row">
                                <div class="btn-row">
                                    <button type="button" id="${ids.btnRunId}" class="cfg-btn">run</button>
                                    <button type="button" id="${ids.btnLintId}" class="cfg-btn">lint</button>
                                    <button type="button" id="${ids.btnCheckId}" class="cfg-btn">check</button>
                                    <button type="button" id="${ids.btnScoreId}" class="cfg-btn">score</button>
                                </div>
                                <button type="button" id="${ids.outputToggleId}" class="icon-btn" title="Hide output">▾</button>
                            </div>
                            <pre id="${ids.outputId}" class="output-box"></pre>
                        </div>
                    </div>
                </div>

                <div class="config-help">
                    <div class="help-head-row">
                        <h3>Help</h3>
                        <button type="button" id="${ids.helpToggleId}" class="icon-btn" title="Hide help">◂</button>
                    </div>
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
                gap: 8px;
            }
            .pluginConfigForm .config-main {
                flex: 2;
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-width: 0;
            }
            .pluginConfigForm .config-help {
                flex: 1;
                border: 1px solid #ccc;
                padding: 8px;
                overflow: auto;
                min-width: 0;
            }
            .pluginConfigForm .tab-buttons {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            .pluginConfigForm .tab-head-row,
            .pluginConfigForm .shared-head-row,
            .pluginConfigForm .help-head-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }
            .pluginConfigForm .help-head-row h3 {
                margin: 0;
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
            .pluginConfigForm .main-split {
                flex: 1;
                min-height: 0;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .pluginConfigForm .tab-panels {
                min-height: 0;
                border: 1px solid #ccc;
                padding: 8px;
            }
            .pluginConfigForm .main-split[data-output-hidden="false"] .tab-panels {
                flex: 0 0 65%;
            }
            .pluginConfigForm .main-split[data-output-hidden="false"] .shared-actions {
                flex: 1 1 auto;
            }
            .pluginConfigForm .main-split[data-output-hidden="true"] .split-handle {
                display: none;
            }
            .pluginConfigForm .main-split[data-output-hidden="true"] .tab-panels {
                flex: 1 1 auto;
            }
            .pluginConfigForm .main-split[data-output-hidden="true"] .shared-actions {
                flex: 0 0 auto;
                min-height: auto;
            }
            .pluginConfigForm .main-split[data-output-hidden="true"] .output-box {
                display: none;
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
                gap: 8px;
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
            .pluginConfigForm .split-handle {
                height: 8px;
                border: 1px solid #ccc;
                background: #f3f3f3;
                cursor: row-resize;
                border-radius: 4px;
            }
            .pluginConfigForm .icon-btn {
                border: 1px solid #b8b8b8;
                background: #fafafa;
                width: 24px;
                height: 24px;
                line-height: 20px;
                text-align: center;
                border-radius: 4px;
                cursor: pointer;
                padding: 0;
                font-size: 14px;
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
                gap: 8px;
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
                display: flex;
                justify-content: space-between;
                gap: 8px;
            }
            .pluginConfigForm .file-size {
                color: #666;
                font-size: 12px;
            }
            .pluginConfigForm .file-item:hover {
                background: #f5f5f5;
            }
            .pluginConfigForm .file-item.selected {
                background: #e8f1ff;
                outline: 1px solid #7aa7e9;
            }
            .pluginConfigForm .file-help {
                margin: 8px 0 0;
                color: #666;
                font-size: 12px;
            }
            .pluginConfigForm .checkbox-row {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                margin: 0;
            }
            .pluginConfigForm .flags-row {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            .pluginConfigForm .build-info {
                display: inline-block;
                margin: 0 0 8px;
                padding: 4px 6px;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background: #f7f7f7;
                color: #444;
                font-family: monospace;
                font-size: 12px;
            }
            .pluginConfigForm .build-info.build-mismatch {
                border-color: #d00;
                background: #fff0f0;
            }
            .pluginConfigForm .build-info .build-mismatch-text {
                color: #d00;
                font-weight: 700;
            }
            .pluginConfigForm .linter-head-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }
            .pluginConfigForm .linter-weight-input {
                width: 90px;
                margin: 0;
            }
            .pluginConfigForm .small-gap {
                gap: 8px;
            }
            .pluginConfigForm iframe {
                width: 100%;
                height: 60vh;
                border: none;
            }
        `;
        document.head.appendChild(style);
    }

    function setupResizableSections() {
        const root = document.querySelector("." + ids.rootClass);
        if (!root) return;

        const helpCol = root.querySelector(".config-help");
        const helpToggle = document.getElementById(ids.helpToggleId);
        const mainSplit = document.getElementById(ids.mainSplitId);
        const splitHandle = document.getElementById(ids.splitHandleId);
        const tabsWrap = document.getElementById(ids.tabsWrapId);
        const outputToggle = document.getElementById(ids.outputToggleId);

        if (helpToggle && helpCol) {
            helpToggle.addEventListener("click", () => {
                const hidden = helpCol.style.display === "none";
                helpCol.style.display = hidden ? "" : "none";
                helpToggle.textContent = hidden ? "◂" : "▸";
                helpToggle.title = hidden ? "Hide help" : "Show help";
            });
        }

        if (outputToggle && mainSplit) {
            outputToggle.addEventListener("click", () => {
                const hidden = mainSplit.getAttribute("data-output-hidden") === "true";
                mainSplit.setAttribute("data-output-hidden", hidden ? "false" : "true");
                outputToggle.textContent = hidden ? "▾" : "▸";
                outputToggle.title = hidden ? "Hide output" : "Show output";
            });
        }

        if (splitHandle && mainSplit && tabsWrap) {
            splitHandle.addEventListener("mousedown", (event) => {
                event.preventDefault();
                const rect = mainSplit.getBoundingClientRect();
                const splitHeight = splitHandle.offsetHeight + 8;
                const minTop = 140;
                const minBottom = 80;

                function onMove(moveEvent) {
                    const pos = moveEvent.clientY - rect.top;
                    const maxTop = rect.height - minBottom - splitHeight;
                    const nextTop = Math.max(minTop, Math.min(maxTop, pos));
                    tabsWrap.style.flex = `0 0 ${nextTop}px`;
                }

                function onUp() {
                    document.removeEventListener("mousemove", onMove);
                    document.removeEventListener("mouseup", onUp);
                }

                document.addEventListener("mousemove", onMove);
                document.addEventListener("mouseup", onUp);
            });
        }
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
        const fileList = document.getElementById(ids.fileListId);
        const fileUpload = document.getElementById(ids.fileUploadId);
        let selectedFileName = "";

        function getFileInfo(name) {
            const value = state.files && state.files[name];
            if (value && typeof value === "object") return value;
            if (typeof value === "string") return { content: value, size: value.length };
            return {};
        }

        function createUniqueDisplayName(preferredName) {
            const cleanName = (preferredName || "uploaded-file").trim() || "uploaded-file";
            if (!state.files || state.files[cleanName] == null) return cleanName;

            const dotIndex = cleanName.lastIndexOf(".");
            const hasExtension = dotIndex > 0;
            const base = hasExtension ? cleanName.substring(0, dotIndex) : cleanName;
            const extension = hasExtension ? cleanName.substring(dotIndex) : "";
            let counter = 2;
            let candidate = `${base}-${counter}${extension}`;
            while (state.files[candidate] != null) {
                counter += 1;
                candidate = `${base}-${counter}${extension}`;
            }
            return candidate;
        }

        function renderFileList() {
            const names = Object.keys(state.files || {}).sort();
            if (!names.length) {
                selectedFileName = "";
                fileList.innerHTML = "<em>No files stored.</em>";
                return;
            }
            if (selectedFileName && !state.files[selectedFileName]) {
                selectedFileName = "";
            }
            fileList.innerHTML = names.map((name) => {
                const info = getFileInfo(name);
                const details = info.size != null ? ` <span class="file-size">(${escapeHtml(formatBytes(info.size))})</span>` : "";
                const selectedClass = name === selectedFileName ? " selected" : "";
                return `<div class="file-item${selectedClass}" data-file="${escapeHtmlAttr(name)}"><span>${escapeHtml(name)}</span>${details}</div>`;
            }).join("");
            fileList.querySelectorAll(".file-item").forEach((row) => {
                row.addEventListener("click", () => {
                    selectedFileName = row.getAttribute("data-file") || "";
                    renderFileList();
                });
            });
        }

        document.querySelectorAll("[data-file-action]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const action = btn.getAttribute("data-file-action");
                const name = selectedFileName;

                if (action === "delete") {
                    if (!name || !state.files[name]) return;
                    const info = getFileInfo(name);
                    if (info.storedName) {
                        await requestFileDelete(info.storedName);
                    }
                    delete state.files[name];
                    selectedFileName = "";
                    renderFileList();
                    saveConfig();
                    return;
                }

                if (action === "download") {
                    if (!name || state.files[name] == null) return;
                    const info = getFileInfo(name);
                    if (info.storedName) {
                        const a = document.createElement("a");
                        a.href = `${serviceBase}/files/download/${encodeURIComponent(info.storedName)}?name=${encodeURIComponent(name)}${pluginToken ? `&token=${encodeURIComponent(pluginToken)}` : ""}`;
                        a.download = name;
                        a.click();
                    } else {
                        const blob = new Blob([info.content || ""], { type: "text/plain" });
                        const a = document.createElement("a");
                        a.href = URL.createObjectURL(blob);
                        a.download = name;
                        a.click();
                        URL.revokeObjectURL(a.href);
                    }
                    return;
                }

                if (action === "upload") {
                    const file = fileUpload.files && fileUpload.files[0];
                    if (!file) return;
                    const uploaded = await requestFileUpload(file);
                    const displayName = createUniqueDisplayName(uploaded.displayName || file.name);
                    state.files[displayName] = { storedName: uploaded.storedName, size: uploaded.size };
                    selectedFileName = displayName;
                    fileUpload.value = "";
                    renderFileList();
                    saveConfig();
                }
            });
        });

        renderFileList();
    }

    async function requestFileUpload(file) {
        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(serviceBase + "/files/upload", {
            method: "POST",
            headers: buildAuthHeaders(),
            body: formData
        });
        if (!response.ok) throw new Error("File upload failed");
        return await response.json();
    }

    async function requestFileDelete(storedName) {
        const response = await fetch(serviceBase + "/files/delete", {
            method: "POST",
            headers: buildHeaders(),
            body: JSON.stringify({ storedName: storedName })
        });
        if (!response.ok) throw new Error("File delete failed");
        return await response.json();
    }

    function formatBytes(value) {
        const bytes = Number(value || 0);
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
    }

    async function setupBuildInfo() {
        const buildInfo = document.getElementById(ids.buildInfoId);
        if (!buildInfo) return;

        const scriptHash = PYTHON_CONFIG_SCRIPT_COMMIT_HASH || "unknown";
        const scriptElement = buildInfo.querySelector('[data-build-role="script"]');
        const serverElement = buildInfo.querySelector('[data-build-role="server"]');
        if (scriptElement) scriptElement.textContent = scriptHash;

        try {
            const response = await fetch(serviceBase + "/buildhash", {
                method: "GET",
                headers: buildAuthHeaders()
            });
            if (!response.ok) throw new Error("Build hash request failed");

            const body = await response.json();
            const serverHash = body && body.commitHash ? String(body.commitHash) : "unknown";
            if (serverElement) serverElement.textContent = serverHash;

            const mismatch = serverHash !== scriptHash;
            buildInfo.classList.toggle("build-mismatch", mismatch);
            if (scriptElement) scriptElement.classList.toggle("build-mismatch-text", mismatch);
            if (serverElement) serverElement.classList.toggle("build-mismatch-text", mismatch);
        } catch (e) {
            if (serverElement) serverElement.textContent = "unavailable";
            buildInfo.classList.add("build-mismatch");
            if (scriptElement) scriptElement.classList.add("build-mismatch-text");
            if (serverElement) serverElement.classList.add("build-mismatch-text");
        }
    }

    function setupOptionsTab() {
        const runAtTest = document.getElementById(ids.optRunAtTestId);
        const lintAtTest = document.getElementById(ids.optLintAtTestId);
        const linterConfig = document.getElementById(ids.linterConfigId);
        const linterWeight = document.getElementById(ids.linterWeightId);

        if (runAtTest) runAtTest.checked = !!state.evalConfig.runAtTest;
        if (lintAtTest) lintAtTest.checked = !!state.evalConfig.lintAtTest;
        if (linterConfig) linterConfig.value = state.linterConfig || "";
        if (linterWeight) linterWeight.value = formatWeightValue(state.linterWeight);

        [runAtTest, lintAtTest, linterConfig, linterWeight].forEach((el) => {
            if (!el) return;
            const onOptionChanged = (event) => {
                syncOptionsStateFromInputs();
                saveConfig();
                if (el === linterWeight && event && event.type === "change") {
                    linterWeight.value = formatWeightValue(state.linterWeight);
                }
            };
            el.addEventListener("change", onOptionChanged);
            el.addEventListener("input", onOptionChanged);
        });
    }

    function syncOptionsStateFromInputs() {
        const runAtTest = document.getElementById(ids.optRunAtTestId);
        const lintAtTest = document.getElementById(ids.optLintAtTestId);
        const linterConfig = document.getElementById(ids.linterConfigId);
        const linterWeight = document.getElementById(ids.linterWeightId);

        state.evalConfig.runAtTest = !!(runAtTest && runAtTest.checked);
        state.evalConfig.lintAtTest = !!(lintAtTest && lintAtTest.checked);
        state.linterConfig = linterConfig ? linterConfig.value : "";

        const parsedWeight = linterWeight ? parseWeightValue(linterWeight.value) : 0.0;
        state.linterWeight = Number.isFinite(parsedWeight) ? parsedWeight : 0.0;
    }

    function parseWeightValue(rawValue) {
        const normalized = String(rawValue == null ? "" : rawValue).trim().replace(",", ".");
        if (normalized === "" || normalized === "." || normalized === "-" || normalized === "+") return 0.0;
        const parsed = Number(normalized);
        return Number.isFinite(parsed) ? parsed : 0.0;
    }

    function formatWeightValue(value) {
        const parsed = Number(value);
        if (!Number.isFinite(parsed)) return "0.0";
        return String(parsed);
    }

    function bindSharedButtons() {
        const outputEl = document.getElementById(ids.outputId);

        bindRequest(ids.btnRunId, "/run", () => ({ code: getActiveEditorCode(), questionConfigDto: buildQuestionConfigDtoPayload() }), outputEl);
        bindRequest(ids.btnLintId, "/lint", () => ({ code: getActiveEditorCode(), questionConfigDto: buildQuestionConfigDtoPayload() }), outputEl);
        bindRequest(ids.btnCheckId, "/check", () => ({ code: getPreviewCode(), testcode: getUnitCode(), questionConfigDto: buildQuestionConfigDtoPayload() }), outputEl);
        bindRequest(ids.btnScoreId, "/scorePlugin", () => ({ code: getPreviewCode(), testcode: getUnitCode(), questionConfigDto: buildQuestionConfigDtoPayload() }), outputEl);
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
        state.evalConfig = example.evalConfig || { runAtTest: true, lintAtTest: true };

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
                const payload = bodyBuilder();
                logDatasetTransfer(`config request ${endpoint} payload`, payload);
                const response = await fetch(serviceBase + endpoint, {
                    method: "POST",
                    headers: buildHeaders(),
                    body: JSON.stringify(payload)
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

    function buildQuestionConfigDtoPayload() {
        syncOptionsStateFromInputs();
        const payload = {
            linterConfig: state.linterConfig || "",
            linterWeight: Number(state.linterWeight || 0.0),
            files: currentStoredFiles()
        };
        logDatasetTransfer("config buildQuestionConfigDtoPayload", payload);
        return payload;
    }

    function saveConfig() {
        if (!configField) return;
        syncOptionsStateFromInputs();

        const pluginConfig = {
            indication: getPreviewCode(),
            validation: getUnitCode(),
            files: currentStoredFiles(),
            evalConfig: state.evalConfig || {},
            linterConfig: state.linterConfig || "",
            linterWeight: Number(state.linterWeight || 0.0)
        };

        questionConfigDto.validation = pluginConfig.validation;
        questionConfigDto.indication = pluginConfig.indication;
        questionConfigDto.files = pluginConfig.files;
        questionConfigDto.evalConfig = pluginConfig.evalConfig;
        questionConfigDto.linterConfig = pluginConfig.linterConfig;
        questionConfigDto.linterWeight = pluginConfig.linterWeight;

        logDatasetTransfer("config saveConfig questionConfigDto", questionConfigDto);
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

    function buildAuthHeaders() {
        const headers = {};
        if (pluginToken) {
            headers["Authorization"] = "Bearer " + pluginToken;
        }
        return headers;
    }

    function buildHeaders() {
        return { "Content-Type": "application/json", ...buildAuthHeaders() };
    }
}

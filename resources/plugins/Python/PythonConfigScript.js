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
    const dtoParams = (dto.params && typeof dto.params === "object")
        ? dto.params
        : (dto.pluginDto && dto.pluginDto.params && typeof dto.pluginDto.params === "object" ? dto.pluginDto.params : {});
    const jsonData = parseDtoJsonData(dto);

    const configField = $(config_form_config)[0];
    const pluginTag = dto.tagName || "pluginpython";
    const serviceBase = ((dto.pluginDto && dto.pluginDto.serviceBase) || dto.serviceBase || dtoParams.serviceBase || "/pluginpython").replace(/\/$/, "");
    const pluginTokenPromise = requestExecutionToken();

    const ids = {
        rootClass: "pluginPythonConfigForm",
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
        linterPresetName: `linterPreset_${pluginTag}`,
        linterWeightId: `linterWeight_${pluginTag}`,
        cpuTimeId: `cpuTime_${pluginTag}`,
        buildInfoId: `buildInfo_${pluginTag}`,
        datasetVariablesId: `datasetVariables_${pluginTag}`,
        helpToggleId: `helpToggle_${pluginTag}`,
        exampleConfirmId: `exampleConfirm_${pluginTag}`,
        exampleConfirmYesId: `exampleConfirmYes_${pluginTag}`,
        exampleConfirmNoId: `exampleConfirmNo_${pluginTag}`,
        outputToggleId: `outputToggle_${pluginTag}`,
        mainSplitId: `mainSplit_${pluginTag}`,
        splitHandleId: `splitHandle_${pluginTag}`
    };

    const linterPresets = [
        { id: "errors", label: "Only errors", config: "--disable=all --enable=F,E" },
        { id: "warnings", label: "Errors + warnings", config: "--disable=all --enable=F,E,W" },
        { id: "conventions", label: "Conventions", config: "--disable=all --enable=F,E,W,C --disable=C0114,C0115,C0116" },
        { id: "docstrings", label: "Conventions + docstrings", config: "--disable=all --enable=F,E,W,C" },
        { id: "all", label: "Default", config: "" },
        { id: "custom", label: "Custom", config: null }
    ];

    const state = parseConfig(configField && configField.value ? configField.value : "", jsonData);
    const questionConfigDto = parseQuestionConfigDto(configField && configField.value ? configField.value : "", dto);
    const datasetVariables = extractDatasetVariablesForQuestionConfig(dto, jsonData, questionConfigDto);
    questionConfigDto.datasetVariables = datasetVariables;
    // Keep editor callbacks local so reopening the dialog cannot read stale editors.
    const editorAccess = {};
    let unitEditor = null;
    let previewEditor = null;

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


    function extractDatasetVariablesForQuestionConfig(sourceDto, sourceJsonData, sourceQuestionConfigDto) {
        const candidates = [
            dtoParams,
            sourceDto && sourceDto.params,
            sourceDto && sourceDto.q,
            sourceDto,
            sourceJsonData && sourceJsonData.q,
            sourceJsonData,
            sourceQuestionConfigDto
        ];
        for (const candidate of candidates) {
            const variables = extractDatasetVariables(candidate);
            if (variables.length) return variables;
        }
        return [];
    }

    function extractDatasetVariables(value) {
        if (!value || typeof value !== "object") return [];
        if (Array.isArray(value)) return normalizeDatasetVariableList(value);
        if (value.datasetVariables != null) return extractDatasetVariables(parseMaybeJson(value.datasetVariables));
        if (value.params && typeof value.params === "object") {
            const fromParams = extractDatasetVariables(value.params);
            if (fromParams.length) return fromParams;
        }
        if (value.vars != null) return extractDatasetVariablesFromVarHash(value.vars);
        return [];
    }

    function normalizeDatasetVariableList(value) {
        return value
            .filter((item) => item && typeof item === "object" && typeof item.name === "string" && item.name)
            .map((item) => ({ name: item.name, value: item.value, unit: item.unit }));
    }

    function extractDatasetVariablesFromVarHash(varHash) {
        const vars = varHash && typeof varHash === "object" && varHash.vars && typeof varHash.vars === "object"
            ? varHash.vars
            : varHash;
        if (!vars || typeof vars !== "object" || Array.isArray(vars)) return [];
        return Object.keys(vars).map((name) => {
            const variable = extractDatasetVariableValue(vars[name]);
            return { name: name, value: variable.value, unit: variable.unit };
        });
    }

    function extractDatasetVariableValue(variableDto) {
        const calcResult = variableDto && typeof variableDto === "object" ? variableDto.calcErgebnisDto : null;
        const parsedJson = parseMaybeJson(calcResult && calcResult.json) || {};
        const calcString = calcResult && typeof calcResult.string === "string" ? calcResult.string : "";
        const explicitUnit = parsedJson.originalEinheitString || parsedJson.grundEinheitString || extractDatasetUnitFromString(calcString);
        return {
            value: extractDatasetValue(parsedJson, calcString),
            unit: explicitUnit ? cleanDatasetUnit(explicitUnit) : unitFromZe(variableDto && variableDto.ze)
        };
    }

    function extractDatasetValue(parsedJson, calcString) {
        if (Object.prototype.hasOwnProperty.call(parsedJson, "d")) {
            return normalizeDatasetNumber(parsedJson.d);
        }
        const match = typeof calcString === "string" ? calcString.match(/^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)/) : null;
        return match ? normalizeDatasetNumber(match[1]) : calcString;
    }

    function extractDatasetUnitFromString(calcString) {
        if (typeof calcString !== "string") return null;
        const quoted = calcString.match(/'([^']+)'/);
        if (quoted) return quoted[1];
        const unquoted = calcString.match(/^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*([^\s]+)\s*$/);
        return unquoted ? unquoted[1] : null;
    }

    function normalizeDatasetNumber(value) {
        if (typeof value !== "string") return value;
        const parsed = Number(value);
        return Number.isNaN(parsed) ? value : parsed;
    }

    function cleanDatasetUnit(unit) {
        if (unit == null) return "";
        let unitText = String(unit).trim();
        if (unitText.indexOf(",") >= 0) unitText = unitText.split(",", 1)[0];
        unitText = unitText.replace(/^['"]+|['"]+$/g, "").trim();
        return unitText;
    }

    function unitFromZe(ze) {
        const unit = cleanDatasetUnit(ze);
        // Numeric-only metadata is not a physical unit.
        return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(unit) ? "" : unit;
    }

    function parseMaybeJson(value) {
        if (typeof value !== "string") return value;
        if (!value) return null;
        try {
            return JSON.parse(value);
        } catch (e) {
            return null;
        }
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
            indication: fallbackData && typeof fallbackData.indication === "string" ? fallbackData.indication : "# Template code\n",
            validation: fallbackData && typeof fallbackData.validation === "string" ? fallbackData.validation : "# Unit test code\n",
            files: (fallbackData && fallbackData.files) || extractFilesFromConfigValue(rawValue) || {},
            evalConfig: {
                runAtTest: fallbackData && fallbackData.evalConfig ? !!fallbackData.evalConfig.runAtTest : true,
                lintAtTest: fallbackData && fallbackData.evalConfig ? !!fallbackData.evalConfig.lintAtTest : true
            },
            linterConfig: (fallbackData && fallbackData.linterConfig) || "",
            linterWeight: parseWeightValue(fallbackData && fallbackData.linterWeight),
            cpuTime: parseCpuTimeValue(fallbackData && fallbackData.cpuTime)
        };

        if (!rawValue) return defaults;

        try {
            const parsed = JSON.parse(rawValue);
            return {
                indication: typeof parsed.indication === "string" ? parsed.indication : defaults.indication,
                validation: typeof parsed.validation === "string" ? parsed.validation : defaults.validation,
                files: parsed.files || defaults.files,
                evalConfig: {
                    runAtTest: parsed.evalConfig && typeof parsed.evalConfig.runAtTest === "boolean" ? parsed.evalConfig.runAtTest : defaults.evalConfig.runAtTest,
                    lintAtTest: parsed.evalConfig && typeof parsed.evalConfig.lintAtTest === "boolean" ? parsed.evalConfig.lintAtTest : defaults.evalConfig.lintAtTest
                },
                linterConfig: typeof parsed.linterConfig === "string" ? parsed.linterConfig : defaults.linterConfig,
                linterWeight: parseWeightValue(parsed.linterWeight != null ? parsed.linterWeight : defaults.linterWeight),
                cpuTime: parseCpuTimeValue(parsed.cpuTime != null ? parsed.cpuTime : defaults.cpuTime)
            };
        } catch (e) {
            return {
                indication: rawValue,
                validation: defaults.validation,
                files: defaults.files,
                evalConfig: defaults.evalConfig,
                linterConfig: defaults.linterConfig,
                linterWeight: defaults.linterWeight,
                cpuTime: defaults.cpuTime
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
        $(config_form_div).find(selector).remove();

        $(config_form_div).append(`
            <div class="${ids.rootClass}">
                <div class="config-main">
                    <div class="tab-head-row">
                        <div class="tab-buttons">
                            <button type="button" class="tab-btn active" data-tab="tab-unittest">UnitTest</button>
                            <button type="button" class="tab-btn" data-tab="tab-preview">Template</button>
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
                                <h3>Template editor</h3>
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
                                <div id="${ids.buildInfoId}" class="build-info" title="Source commit or build revision for this configuration script">
                                    <span>Script build: <span data-build-role="script">${escapeHtml(PYTHON_CONFIG_SCRIPT_COMMIT_HASH)}</span></span>
                                    <span class="build-separator"> | </span>
                                    <span>Server build: <span data-build-role="server">loading...</span></span>
                                </div>
                                <div class="flags-row">
                                    <label for="${ids.cpuTimeId}" title="Maximum processor time in seconds (default: 5). Waiting and sleep do not consume CPU time. Elapsed request time can be longer; Jobe also enforces a wall-clock watchdog at twice the CPU limit.">CPU time limit (seconds)</label>
                                    <input id="${ids.cpuTimeId}" title="CPU seconds, not elapsed seconds. A 5-second CPU limit can take about 10 seconds plus request overhead." type="number" min="1" step="1" class="text-input cpu-time-input" placeholder="5" />
                                    <label class="checkbox-row"><input id="${ids.optRunAtTestId}" type="checkbox" /> enable run</label>
                                    <label class="checkbox-row"><input id="${ids.optLintAtTestId}" type="checkbox" /> enable lint</label>
                                </div>
                                <div class="config-horizontal-row">
                                    <div class="linter-config-section">
                                        <div class="linter-head-row">
                                            <label for="${ids.linterConfigId}">Linter configuration</label>
                                            <label for="${ids.linterWeightId}" title="unit test scores is weighted with 1.0, choose linter weight">Weight</label>
                                            <input id="${ids.linterWeightId}" type="text" inputmode="decimal" class="text-input linter-weight-input" placeholder="0.0" />
                                        </div>
                                        <div class="linter-config-body">
                                            <div class="linter-presets" role="radiogroup" aria-label="Linter presets">
                                                ${linterPresets.map((preset) => `<label class="checkbox-row"><input type="radio" name="${ids.linterPresetName}" value="${preset.id}" /> ${preset.label}</label>`).join("")}
                                            </div>
                                            <textarea id="${ids.linterConfigId}" class="text-input" rows="4" placeholder="e.g. --disable=C0114,C0116"></textarea>
                                        </div>
                                    </div>
                                    <div class="dataset-variable-section" title="Dataset variables are provided to UnitTest as a generated dataset.py file. Use from dataset import DATASET_VARIABLES and then DATASET_VARIABLES[&quot;name&quot;].value or .unit. Valid Python identifiers can also be imported directly, e.g. from dataset import myVar.">
                                        <div class="dataset-variable-head-row">
                                            <h4>Available dataset variables</h4>
                                            <span class="dataset-variable-help" aria-label="Dataset variable usage help">?</span>
                                        </div>
                                        <div id="${ids.datasetVariablesId}" class="dataset-variable-list">${renderDatasetVariableList(datasetVariables)}</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div id="${ids.splitHandleId}" class="split-handle" title="Drag to resize editor/output sections"></div>

                        <div class="shared-actions">
                            <div class="shared-head-row">
                                <div class="btn-row">
                                    <button type="button" id="${ids.btnRunId}" class="cfg-btn" title="Führt den Template-Code aus. Nur im Template-Tab verfügbar; UnitTests mit check ausführen." disabled>run</button>
                                    <button type="button" id="${ids.btnLintId}" class="cfg-btn" title="Prüft den Stil des UnitTest-Codes im UnitTest-Tab, sonst den Template-Code.">lint</button>
                                    <button type="button" id="${ids.btnCheckId}" class="cfg-btn" title="Führt die UnitTests mit dem Template-Code aus.">check</button>
                                    <button type="button" id="${ids.btnScoreId}" class="cfg-btn" title="Berechnet die Punkte aus UnitTests und Linter-Ergebnis.">score</button>
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
                        <button type="button" id="${ids.helpToggleId}" class="icon-btn" title="Hide help" aria-label="Hide help" aria-expanded="true">◂</button>
                    </div>
                    <a href="https://doc.letto.at/wiki/Plugins" target="_blank">Wiki-Plugins</a>
                    <div id="configPluginHelp"></div>
                    <div id="configPluginWiki"></div>
                </div>

                <div id="${ids.exampleConfirmId}" class="confirm-overlay" role="dialog" aria-modal="true" aria-labelledby="${ids.exampleConfirmId}_title" hidden>
                    <div class="confirm-dialog">
                        <h3 id="${ids.exampleConfirmId}_title">Eigenen Code überschreiben?</h3>
                        <p>Das ausgewählte Beispiel ersetzt Ihren vorhandenen Code. Möchten Sie ihn wirklich überschreiben?</p>
                        <div class="btn-row confirm-actions">
                            <button type="button" id="${ids.exampleConfirmNoId}" class="cfg-btn">Nein</button>
                            <button type="button" id="${ids.exampleConfirmYesId}" class="cfg-btn confirm-overwrite">Ja, überschreiben</button>
                        </div>
                    </div>
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
            .pluginPythonConfigForm {
                display: flex;
                width: 100%;
                height: 75vh;
                box-sizing: border-box;
                gap: 8px;
            }
            .pluginPythonConfigForm .config-main {
                flex: 2;
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-width: 0;
            }
            .pluginPythonConfigForm .config-help {
                flex: 1;
                border: 1px solid #ccc;
                padding: 8px;
                overflow: auto;
                min-width: 0;
            }
            .pluginPythonConfigForm .config-help.help-collapsed {
                flex: 0 0 auto;
                align-self: flex-start;
                padding: 4px;
                overflow: visible;
            }
            .pluginPythonConfigForm .config-help.help-collapsed > :not(.help-head-row),
            .pluginPythonConfigForm .config-help.help-collapsed .help-head-row h3 {
                display: none;
            }
            .pluginPythonConfigForm .config-help h4 {
                margin: 14px 0 4px;
            }
            .pluginPythonConfigForm .config-help p,
            .pluginPythonConfigForm .config-help ul {
                margin: 4px 0 8px;
            }
            .pluginPythonConfigForm .config-help ul {
                padding-left: 20px;
            }
            .pluginPythonConfigForm .confirm-overlay {
                position: fixed;
                inset: 0;
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 16px;
                background: rgba(0, 0, 0, 0.45);
            }
            .pluginPythonConfigForm .confirm-overlay[hidden] {
                display: none;
            }
            .pluginPythonConfigForm .confirm-dialog {
                width: min(440px, 100%);
                padding: 20px;
                border-radius: 6px;
                background: #fff;
                box-shadow: 0 8px 28px rgba(0, 0, 0, 0.3);
            }
            .pluginPythonConfigForm .confirm-dialog h3 {
                margin: 0 0 8px;
            }
            .pluginPythonConfigForm .confirm-actions {
                justify-content: flex-end;
                margin-top: 16px;
            }
            .pluginPythonConfigForm .confirm-overwrite {
                border-color: #a12622;
                background: #a12622;
            }
            .pluginPythonConfigForm .tab-buttons {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            .pluginPythonConfigForm .tab-head-row,
            .pluginPythonConfigForm .shared-head-row,
            .pluginPythonConfigForm .help-head-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }
            .pluginPythonConfigForm .help-head-row h3 {
                margin: 0;
            }
            .pluginPythonConfigForm .tab-btn,
            .pluginPythonConfigForm .cfg-btn {
                border: 1px solid #b8b8b8;
                background: #f0f0f0;
                padding: 6px 14px;
                border-radius: 4px;
                cursor: pointer;
            }
            .pluginPythonConfigForm .tab-btn.active {
                background: #dce9ff;
            }
            .pluginPythonConfigForm .main-split {
                flex: 1;
                min-height: 0;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .pluginPythonConfigForm .tab-panels {
                min-height: 0;
                border: 1px solid #ccc;
                padding: 8px;
            }
            .pluginPythonConfigForm .main-split[data-output-hidden="false"] .tab-panels {
                flex: 0 0 65%;
            }
            .pluginPythonConfigForm .main-split[data-output-hidden="false"] .shared-actions {
                flex: 1 1 auto;
            }
            .pluginPythonConfigForm .main-split[data-output-hidden="true"] .split-handle {
                display: none;
            }
            .pluginPythonConfigForm .main-split[data-output-hidden="true"] .tab-panels {
                flex: 1 1 auto;
            }
            .pluginPythonConfigForm .main-split[data-output-hidden="true"] .shared-actions {
                flex: 0 0 auto;
                min-height: auto;
            }
            .pluginPythonConfigForm .main-split[data-output-hidden="true"] .output-box {
                display: none;
            }
            .pluginPythonConfigForm .tab-panel {
                display: none;
                height: 100%;
                min-height: 0;
                flex-direction: column;
                gap: 8px;
            }
            .pluginPythonConfigForm .tab-panel.active {
                display: flex;
            }
            .pluginPythonConfigForm .tab-title-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
            }
            .pluginPythonConfigForm .tab-title-row h3 {
                margin: 0;
            }
            .pluginPythonConfigForm .unit-example-controls {
                margin-left: auto;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .pluginPythonConfigForm .unit-example-select {
                width: auto;
                min-width: 120px;
                margin: 0;
            }
            .pluginPythonConfigForm .editor-box {
                flex: 1;
                min-height: 0;
                border: 1px solid #d0d0d0;
            }
            .pluginPythonConfigForm .split-handle {
                height: 8px;
                border: 1px solid #ccc;
                background: #f3f3f3;
                cursor: row-resize;
                border-radius: 4px;
            }
            .pluginPythonConfigForm .icon-btn {
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
            .pluginPythonConfigForm .shared-actions {
                border: 1px solid #ccc;
                padding: 8px;
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-height: 180px;
            }
            .pluginPythonConfigForm .output-box {
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
            .pluginPythonConfigForm .request-progress {
                display: block;
                width: 120px;
                height: 4px;
                margin-top: 10px;
                overflow: hidden;
                background: #303830;
                border-radius: 2px;
            }
            .pluginPythonConfigForm .request-progress::after {
                content: "";
                display: block;
                width: 40%;
                height: 100%;
                background: #8df58d;
                animation: python-request-progress 1.2s linear infinite;
            }
            @keyframes python-request-progress {
                from { transform: translateX(-100%); }
                to { transform: translateX(250%); }
            }
            @media (prefers-reduced-motion: reduce) {
                .pluginPythonConfigForm .request-progress::after { animation: none; }
            }
            .pluginPythonConfigForm .files-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
                min-height: 0;
                height: 100%;
            }
            .pluginPythonConfigForm .text-input {
                width: 100%;
                box-sizing: border-box;
                margin: 4px 0 8px;
                font-family: monospace;
            }
            .pluginPythonConfigForm .file-list {
                border: 1px solid #d0d0d0;
                min-height: 220px;
                max-height: 100%;
                overflow: auto;
                padding: 6px;
                font-family: monospace;
            }
            .pluginPythonConfigForm .file-item {
                padding: 4px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                gap: 8px;
            }
            .pluginPythonConfigForm .file-size {
                color: #666;
                font-size: 12px;
            }
            .pluginPythonConfigForm .file-item:hover {
                background: #f5f5f5;
            }
            .pluginPythonConfigForm .file-item.selected {
                background: #e8f1ff;
                outline: 1px solid #7aa7e9;
            }
            .pluginPythonConfigForm .file-help {
                margin: 8px 0 0;
                color: #666;
                font-size: 12px;
            }
            .pluginPythonConfigForm .checkbox-row {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                margin: 0;
            }
            .pluginPythonConfigForm .flags-row {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            .pluginPythonConfigForm .build-info {
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
            .pluginPythonConfigForm .build-info.build-mismatch {
                border-color: #d00;
                background: #fff0f0;
            }
            .pluginPythonConfigForm .build-info .build-mismatch-text {
                color: #d00;
                font-weight: 700;
            }
            .pluginPythonConfigForm .config-horizontal-row {
                display: flex;
                gap: 8px;
                align-items: stretch;
                min-height: 0;
            }
            .pluginPythonConfigForm .linter-config-section,
            .pluginPythonConfigForm .dataset-variable-section {
                flex: 1 1 0;
                min-width: 0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px;
                background: #fafafa;
            }
            .pluginPythonConfigForm .linter-config-section {
                display: flex;
                flex-direction: column;
            }
            .pluginPythonConfigForm .linter-head-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }
            .pluginPythonConfigForm .linter-weight-input,
            .pluginPythonConfigForm .cpu-time-input {
                width: 90px;
                margin: 0;
            }
            .pluginPythonConfigForm .linter-config-body {
                display: flex;
                align-items: stretch;
                gap: 12px;
                flex: 1;
                min-width: 0;
            }
            .pluginPythonConfigForm .linter-presets {
                display: flex;
                flex-direction: column;
                gap: 4px;
                flex: 0 0 auto;
                padding-top: 4px;
            }
            .pluginPythonConfigForm .linter-config-section textarea {
                width: 0;
                min-width: 80px;
                flex: 1;
                min-height: 120px;
                margin-bottom: 0;
            }
            .pluginPythonConfigForm .dataset-variable-section {
                display: flex;
                flex-direction: column;
            }
            .pluginPythonConfigForm .dataset-variable-head-row {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 6px;
            }
            .pluginPythonConfigForm .dataset-variable-head-row h4 {
                margin: 0;
            }
            .pluginPythonConfigForm .dataset-variable-help {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 16px;
                height: 16px;
                border: 1px solid #888;
                border-radius: 50%;
                color: #444;
                font-size: 11px;
                font-weight: 700;
                cursor: help;
            }
            .pluginPythonConfigForm .dataset-variable-list {
                max-height: 160px;
                overflow: auto;
            }
            .pluginPythonConfigForm .dataset-variable-table {
                width: 100%;
                border-collapse: collapse;
                font-family: monospace;
                font-size: 12px;
            }
            .pluginPythonConfigForm .dataset-variable-table th,
            .pluginPythonConfigForm .dataset-variable-table td {
                border: 1px solid #ddd;
                padding: 4px 6px;
                text-align: left;
                vertical-align: top;
            }
            .pluginPythonConfigForm .dataset-variable-table th {
                background: #f0f0f0;
            }
            .pluginPythonConfigForm .dataset-variable-empty {
                margin: 0;
                color: #666;
                font-size: 12px;
            }
            .pluginPythonConfigForm .small-gap {
                gap: 8px;
            }
            .pluginPythonConfigForm iframe {
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
                const collapsed = helpCol.classList.toggle("help-collapsed");
                helpToggle.textContent = collapsed ? "▸" : "◂";
                helpToggle.title = collapsed ? "Show help" : "Hide help";
                helpToggle.setAttribute("aria-expanded", String(!collapsed));
                helpToggle.setAttribute("aria-label", helpToggle.title);
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
                // Ace must recalculate and redraw after its hidden tab becomes visible.
                if (target === "tab-unittest" && unitEditor) unitEditor.resize(true);
                if (target === "tab-preview" && previewEditor) previewEditor.resize(true);
                updateRunButtonState();
            });
        });
        updateRunButtonState();
    }

    function updateRunButtonState() {
        const button = document.getElementById(ids.btnRunId);
        const previewPanel = document.getElementById("tab-preview");
        if (button) {
            button.disabled = button.dataset.requestPending === "true"
                || !previewPanel || !previewPanel.classList.contains("active");
        }
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
            unitEditor = ace.edit(ids.unitEditorId);
            unitEditor.setTheme("ace/theme/monokai");
            unitEditor.session.setMode("ace/mode/python");
            unitEditor.session.setValue(initialUnit || "");

            previewEditor = ace.edit(ids.previewEditorId);
            previewEditor.setTheme("ace/theme/monokai");
            previewEditor.session.setMode("ace/mode/python");
            previewEditor.session.setValue(initialPreview || "");

            unitEditor.session.on("change", saveConfig);
            previewEditor.session.on("change", saveConfig);

            editorAccess._getUnitCode = () => unitEditor.getValue();
            editorAccess._getPreviewCode = () => previewEditor.getValue();
            editorAccess._setUnitCode = (value) => unitEditor.session.setValue(value || "");
            editorAccess._setPreviewCode = (value) => previewEditor.session.setValue(value || "");
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
        editorAccess[key] = () => ta.value;
    }

    function fallbackTextAreaSetter(targetId, key) {
        editorAccess[key] = (value) => {
            const target = document.getElementById(targetId);
            const ta = target ? target.querySelector("textarea") : null;
            if (ta) ta.value = value || "";
        };
    }

    function getUnitCode() {
        return editorAccess._getUnitCode ? editorAccess._getUnitCode() : state.validation;
    }

    function getPreviewCode() {
        return editorAccess._getPreviewCode ? editorAccess._getPreviewCode() : state.indication;
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
                        const token = await pluginTokenPromise;
                        const tokenQuery = token ? `&token=${encodeURIComponent(token)}` : "";
                        a.href = `${serviceBase}/files/download/${encodeURIComponent(info.storedName)}?name=${encodeURIComponent(name)}${tokenQuery}`;
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
            headers: await buildAuthHeaders(),
            credentials: "include",
            body: formData
        });
        if (!response.ok) throw new Error("File upload failed");
        return await response.json();
    }

    async function requestFileDelete(storedName) {
        const response = await fetch(serviceBase + "/files/delete", {
            method: "POST",
            headers: await buildHeaders(),
            credentials: "include",
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
                headers: await buildAuthHeaders(),
                credentials: "include"
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
        const cpuTime = document.getElementById(ids.cpuTimeId);

        if (runAtTest) runAtTest.checked = !!state.evalConfig.runAtTest;
        if (lintAtTest) lintAtTest.checked = !!state.evalConfig.lintAtTest;
        if (linterConfig) linterConfig.value = state.linterConfig || "";
        if (linterWeight) linterWeight.value = formatWeightValue(state.linterWeight);
        if (cpuTime) cpuTime.value = formatCpuTimeValue(state.cpuTime);

        const presetRadios = Array.from(document.getElementsByName(ids.linterPresetName));
        const selectPreset = (presetId) => {
            presetRadios.forEach((radio) => { radio.checked = radio.value === presetId; });
        };
        const matchingPreset = linterPresets.find((preset) => preset.config === (state.linterConfig || ""));
        selectPreset(matchingPreset ? matchingPreset.id : "custom");
        presetRadios.forEach((radio) => {
            radio.onchange = () => {
                if (!radio.checked) return;
                const preset = linterPresets.find((entry) => entry.id === radio.value);
                if (!preset || preset.config === null || !linterConfig) return;
                linterConfig.value = preset.config;
                syncOptionsStateFromInputs();
                saveConfig();
            };
        });

        [runAtTest, lintAtTest, linterConfig, linterWeight, cpuTime].forEach((el) => {
            if (!el) return;
            const onOptionChanged = (event) => {
                if (el === linterConfig) selectPreset("custom");
                syncOptionsStateFromInputs();
                saveConfig();
                if (el === linterWeight && event && event.type === "change") {
                    linterWeight.value = formatWeightValue(state.linterWeight);
                }
                if (el === cpuTime && event && event.type === "change") {
                    cpuTime.value = formatCpuTimeValue(state.cpuTime);
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
        const cpuTime = document.getElementById(ids.cpuTimeId);

        state.evalConfig.runAtTest = !!(runAtTest && runAtTest.checked);
        state.evalConfig.lintAtTest = !!(lintAtTest && lintAtTest.checked);
        state.linterConfig = linterConfig ? linterConfig.value : "";

        const parsedWeight = linterWeight ? parseWeightValue(linterWeight.value) : 0.0;
        state.linterWeight = Number.isFinite(parsedWeight) ? parsedWeight : 0.0;
        state.cpuTime = parseCpuTimeValue(cpuTime ? cpuTime.value : state.cpuTime);
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

    function parseCpuTimeValue(rawValue) {
        const parsed = Number.parseInt(String(rawValue == null ? "" : rawValue).trim(), 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 5;
    }

    function formatCpuTimeValue(value) {
        return String(parseCpuTimeValue(value));
    }

    function bindSharedButtons() {
        const outputEl = document.getElementById(ids.outputId);

        bindRequest(ids.btnRunId, "/run", () => ({ code: getPreviewCode(), questionConfigDto: buildQuestionConfigDtoPayload({ includeDataset: false }) }), outputEl, { showTiming: true, label: "Run" });
        bindRequest(ids.btnLintId, "/lint", () => ({ code: getActiveEditorCode(), questionConfigDto: buildQuestionConfigDtoPayload({ includeDataset: false }) }), outputEl);
        bindRequest(ids.btnCheckId, "/check", () => ({ code: getPreviewCode(), testcode: getUnitCode(), questionConfigDto: buildQuestionConfigDtoPayload() }), outputEl, { showTiming: true, label: "Check" });
        bindRequest(ids.btnScoreId, "/scorePlugin", () => ({ code: getPreviewCode(), testcode: getUnitCode(), questionConfigDto: buildQuestionConfigDtoPayload() }), outputEl, { showTiming: true, label: "Score" });
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
                if (hasUserCodeToOverwrite(exampleData.output) && !(await confirmExampleOverwrite())) return;
                applyExample(exampleData.output);
            }
        });
    }

    function hasUserCodeToOverwrite(example) {
        const placeholderUnitCode = "# Unit test code";
        const placeholderPreviewCode = "# Template code";
        const currentUnitCode = getUnitCode().trim();
        const currentPreviewCode = getPreviewCode().trim();
        const exampleUnitCode = String((example && example.validation) || "").trim();
        const examplePreviewCode = String((example && example.indication) || "").trim();

        const unitWouldBeOverwritten = currentUnitCode
            && currentUnitCode !== placeholderUnitCode
            && currentUnitCode !== exampleUnitCode;
        const previewWouldBeOverwritten = currentPreviewCode
            && currentPreviewCode !== placeholderPreviewCode
            && currentPreviewCode !== "# Preview code"
            && currentPreviewCode !== examplePreviewCode;
        return !!(unitWouldBeOverwritten || previewWouldBeOverwritten);
    }

    function confirmExampleOverwrite() {
        const dialog = document.getElementById(ids.exampleConfirmId);
        const yesButton = document.getElementById(ids.exampleConfirmYesId);
        const noButton = document.getElementById(ids.exampleConfirmNoId);
        if (!dialog || !yesButton || !noButton) return Promise.resolve(false);

        return new Promise((resolve) => {
            const close = (overwrite) => {
                dialog.hidden = true;
                yesButton.removeEventListener("click", onYes);
                noButton.removeEventListener("click", onNo);
                dialog.removeEventListener("click", onBackdropClick);
                document.removeEventListener("keydown", onKeyDown);
                resolve(overwrite);
            };
            const onYes = () => close(true);
            const onNo = () => close(false);
            const onBackdropClick = (event) => {
                if (event.target === dialog) close(false);
            };
            const onKeyDown = (event) => {
                if (event.key === "Escape") close(false);
            };

            yesButton.addEventListener("click", onYes);
            noButton.addEventListener("click", onNo);
            dialog.addEventListener("click", onBackdropClick);
            document.addEventListener("keydown", onKeyDown);
            dialog.hidden = false;
            noButton.focus();
        });
    }

    async function requestExample(index) {
        try {
            const response = await fetch(serviceBase + "/example", {
                method: "POST",
                headers: await buildHeaders(),
                credentials: "include",
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

        if (editorAccess._setUnitCode) editorAccess._setUnitCode(example.validation || "");
        if (editorAccess._setPreviewCode) editorAccess._setPreviewCode(example.indication || "");

        setupFileTab();
        // Editor changes save the current form options, so load these afterwards.
        state.linterConfig = example.linterConfig || "";
        state.linterWeight = parseWeightValue(example.linterWeight);
        setupOptionsTab();
        saveConfig();
    }

    function getActiveEditorCode() {
        const activeTab = document.querySelector(".pluginPythonConfigForm .tab-panel.active");
        if (!activeTab) return getPreviewCode();
        if (activeTab.id === "tab-unittest") return getUnitCode();
        return getPreviewCode();
    }

    function bindRequest(buttonId, endpoint, bodyBuilder, outputEl, options) {
        const btn = document.getElementById(buttonId);
        if (!btn) return;

        btn.addEventListener("click", async (event) => {
            event.preventDefault();
            if (btn.disabled) return;
            saveConfig();
            const oldText = btn.textContent;
            btn.dataset.requestPending = "true";
            const showTiming = !!(options && options.showTiming);
            const actionLabel = (options && options.label) || oldText;
            const now = () => (typeof performance !== "undefined" && performance.now ? performance.now() : Date.now());
            const startedAt = now();
            let progressDelay = null;
            let elapsedTimer = null;
            let progressText = null;
            let cpuTime = parseCpuTimeValue(state.cpuTime);

            const elapsedSeconds = () => (now() - startedAt) / 1000;
            const timingText = (limitExceeded = false) => `${actionLabel} timing: ${elapsedSeconds().toFixed(2)}s elapsed${limitExceeded ? ` (CPU time limit: ${cpuTime}s)` : ""}.`;
            const updateElapsed = () => {
                btn.textContent = `working... ${Math.floor(elapsedSeconds())}s elapsed`;
                progressText.textContent = `${actionLabel} running...\nElapsed time: ${elapsedSeconds().toFixed(1)}s`;
            };

            btn.disabled = true;
            btn.textContent = "working...";
            outputEl.textContent = "";
            outputEl.setAttribute("aria-busy", "true");
            progressDelay = window.setTimeout(() => {
                progressText = document.createElement("span");
                const progressBar = document.createElement("span");
                progressBar.className = "request-progress";
                progressBar.setAttribute("role", "progressbar");
                progressBar.setAttribute("aria-label", `${actionLabel} running`);
                outputEl.replaceChildren(progressText, progressBar);
                updateElapsed();
                elapsedTimer = window.setInterval(updateElapsed, 100);
            }, 1000);

            try {
                const payload = bodyBuilder();
                cpuTime = parseCpuTimeValue(payload && payload.questionConfigDto && payload.questionConfigDto.cpuTime);
                const response = await fetch(serviceBase + endpoint, {
                    method: "POST",
                    headers: await buildHeaders(),
                    credentials: "include",
                    body: JSON.stringify(payload)
                });
                const data = await readExecutionResponse(response);
                const responseText = data && data.output ? data.output : JSON.stringify(data);
                const limitExceeded = /Error while running code: Time limit exceeded/.test(responseText);
                outputEl.textContent = showTiming ? `${responseText}\n\n${timingText(limitExceeded)}` : responseText;
            } catch (error) {
                const errorText = "Error: " + (error && error.message ? error.message : "request failed");
                outputEl.textContent = showTiming ? `${errorText}\n\n${timingText()}` : errorText;
            } finally {
                delete btn.dataset.requestPending;
                if (progressDelay !== null) window.clearTimeout(progressDelay);
                if (elapsedTimer !== null) window.clearInterval(elapsedTimer);
                outputEl.setAttribute("aria-busy", "false");
                btn.disabled = false;
                if (buttonId === ids.btnRunId) updateRunButtonState();
                btn.textContent = oldText;
            }
        });
    }

    function buildQuestionConfigDtoPayload(options) {
        syncOptionsStateFromInputs();
        const includeDataset = !options || options.includeDataset !== false;
        const payload = {
            linterConfig: state.linterConfig || "",
            linterWeight: Number(state.linterWeight || 0.0),
            cpuTime: parseCpuTimeValue(state.cpuTime),
            files: currentStoredFiles()
        };
        if (includeDataset) {
            payload.datasetVariables = datasetVariables;
        }
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
            linterWeight: Number(state.linterWeight || 0.0),
            cpuTime: parseCpuTimeValue(state.cpuTime),
            datasetVariables: datasetVariables
        };

        questionConfigDto.validation = pluginConfig.validation;
        questionConfigDto.indication = pluginConfig.indication;
        questionConfigDto.files = pluginConfig.files;
        questionConfigDto.evalConfig = pluginConfig.evalConfig;
        questionConfigDto.linterConfig = pluginConfig.linterConfig;
        questionConfigDto.linterWeight = pluginConfig.linterWeight;
        questionConfigDto.cpuTime = pluginConfig.cpuTime;
        questionConfigDto.datasetVariables = pluginConfig.datasetVariables;

        configField.value = JSON.stringify(questionConfigDto);
    }

    async function renderHelp() {
        const helpElement = document.getElementById("configPluginHelp");
        if (helpElement) {
            const suppliedHelp = (typeof dtoParams.help === "string" ? dtoParams.help.trim() : "") || await defaultHelpHtml();
            if (suppliedHelp) {
                const helpDocument = new DOMParser().parseFromString(suppliedHelp, "text/html");
                // Help is a complete HTML document; its body styles must not affect LeTTo.
                helpDocument.querySelectorAll("style, link[rel='stylesheet'], script").forEach((element) => element.remove());
                helpDocument.querySelectorAll("a[data-plugin-help-file]").forEach((link) => {
                    link.setAttribute("href", `${serviceBase}/static/${encodeURIComponent(link.dataset.pluginHelpFile)}`);
                });
                helpDocument.querySelectorAll("img[data-plugin-static-file]").forEach((image) => {
                    image.setAttribute("src", `${serviceBase}/static/${encodeURIComponent(image.dataset.pluginStaticFile)}`);
                });
                helpElement.replaceChildren(...Array.from(helpDocument.body.childNodes));
            } else {
                helpElement.innerHTML = "<p>Help is not available. Please contact the plugin author.</p>";
            }
        }

        if (dtoParams.wikiurl != null) {
            const wikiElement = document.getElementById("configPluginWiki");
            wikiElement.innerHTML = '<iframe src="' + dtoParams.wikiurl + '"></iframe>';
        }
    }

    async function defaultHelpHtml() {
        try {
            const response = await fetch(serviceBase + "/help", {
                method: "GET",
                credentials: "include"
            });
            if (!response.ok) throw new Error("Help request failed");
            return await response.text();
        } catch (e) {
            return "";
        }
    }

    function renderDatasetVariableList(variables) {
        if (!variables || !variables.length) {
            return '<p class="dataset-variable-empty">No dataset variables available for this question.</p>';
        }

        const rows = variables.map((variable) => {
            const name = variable && variable.name != null ? variable.name : "";
            const unit = variable && variable.unit != null ? variable.unit : "";
            return `
                <tr>
                    <td>${escapeHtml(name)}</td>
                    <td>${escapeHtml(formatDatasetVariableValue(variable && variable.value))}</td>
                    <td>${escapeHtml(unit)}</td>
                </tr>
            `;
        }).join("");

        return `
            <table class="dataset-variable-table" aria-label="Available dataset variables">
                <thead>
                    <tr><th>Name</th><th>Value</th><th>Unit</th></tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    function formatDatasetVariableValue(value) {
        if (value == null) return "";
        if (typeof value === "object") {
            try {
                return JSON.stringify(value);
            } catch (e) {
                return String(value);
            }
        }
        return String(value);
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

    async function readExecutionResponse(response) {
        const text = await response.text();
        let data;
        try {
            data = JSON.parse(text);
        } catch (_) {
            throw new Error(`HTTP ${response.status} from ${response.url}: expected JSON, received ${response.headers.get("content-type") || "an unknown content type"}. ${text.replace(/\s+/g, " ").slice(0, 160)}`);
        }
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} from ${response.url}: ${data.output || data.detail || data.error || JSON.stringify(data)}`);
        }
        return data;
    }

    async function requestExecutionToken() {
        try {
            const response = await fetch(serviceBase + "/exectoken", {
                method: "GET",
                credentials: "include"
            });
            if (!response.ok) throw new Error("Execution token request failed");
            const body = await response.json();
            return body && body.token ? String(body.token) : "";
        } catch (e) {
            return "";
        }
    }

    async function buildAuthHeaders() {
        const headers = {};
        const token = await pluginTokenPromise;
        if (token) {
            headers["Authorization"] = "Bearer " + token;
        }
        return headers;
    }

    async function buildHeaders() {
        return { "Content-Type": "application/json", ...(await buildAuthHeaders()) };
    }
}

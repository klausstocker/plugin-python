try {
    $ = jQuery;
} catch (e) {}

const CPP_CONFIG_SCRIPT_COMMIT_HASH = "c70dad38cc61";

function configPluginCpp(dtoString) {
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
    const jsonData = { ...(dto.questionConfigDto || {}), ...parseDtoJsonData(dto) };
    if (!Object.keys(jsonData).length) Object.assign(jsonData, parseJsonObject(dtoParams.config) || {});

    const configField = $(config_form_config)[0];
    const pluginTag = dto.tagName || "plugincpp";
    const serviceBase = ((dto.pluginDto && dto.pluginDto.serviceBase) || dto.serviceBase || dtoParams.serviceBase || "/plugincpp").replace(/\/$/, "");
    const pluginTokenPromise = requestExecutionToken();

    const ids = {
        rootClass: "pluginCppConfigForm",
        tabsWrapId: `tabsWrap_${pluginTag}`,
        unitEditorId: `unitEditor_${pluginTag}`,
        previewEditorId: `previewEditor_${pluginTag}`,
        outputId: `sharedOutput_${pluginTag}`,
        btnRunId: `sharedRun_${pluginTag}`,
        btnCompileId: `sharedCompile_${pluginTag}`,
        btnCheckId: `sharedCheck_${pluginTag}`,
        btnScoreId: `sharedScore_${pluginTag}`,
        exampleSelectId: `exampleSelect_${pluginTag}`,
        exampleApplyId: `exampleApply_${pluginTag}`,
        fileListId: `fileList_${pluginTag}`,
        fileUploadId: `fileUpload_${pluginTag}`,
        optRunAtTestId: `optRunAtTest_${pluginTag}`,
        optCompileAtTestId: `optCompileAtTest_${pluginTag}`,
        languageId: `language_${pluginTag}`,
        languageWarningId: `languageWarning_${pluginTag}`,
        cpuTimeId: `cpuTime_${pluginTag}`,
        buildInfoId: `buildInfo_${pluginTag}`,
        helpToggleId: `helpToggle_${pluginTag}`,
        exampleConfirmId: `exampleConfirm_${pluginTag}`,
        exampleConfirmYesId: `exampleConfirmYes_${pluginTag}`,
        exampleConfirmNoId: `exampleConfirmNo_${pluginTag}`,
        outputToggleId: `outputToggle_${pluginTag}`,
        mainSplitId: `mainSplit_${pluginTag}`,
        splitHandleId: `splitHandle_${pluginTag}`
    };

    const state = parseConfig(configField && configField.value ? configField.value : "", jsonData);
    const questionConfigDto = parseQuestionConfigDto(configField && configField.value ? configField.value : "", dto);
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


    function parseDtoJsonData(sourceDto) {
        if (!sourceDto || !sourceDto.jsonData) return {};
        try {
            try {
                return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(sourceDto.jsonData), c => c.charCodeAt(0))));
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
            try {
                return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(rawValue), c => c.charCodeAt(0))));
            } catch (_) { return null; }
        }
    }

    function currentStoredFiles() {
        return state.files || {};
    }

    function parseConfig(rawValue, fallbackData) {
        const parsed = parseJsonObject(rawValue) || {};
        const data = { ...(fallbackData || {}), ...parsed };
        const flags = { ...((fallbackData && fallbackData.evalConfig) || {}), ...(parsed.evalConfig || {}) };
        return {
            language: data.language === "c" ? "c" : "cpp",
            indication: typeof data.indication === "string" ? data.indication : "// Template code\n",
            validation: typeof data.validation === "string" ? data.validation : "// Catch2 unit test code\n",
            files: data.files && typeof data.files === "object" ? data.files : {},
            evalConfig: { runAtTest: flags.runAtTest !== false, lintAtTest: flags.lintAtTest !== false },
            cpuTime: parseCpuTimeValue(data.cpuTime)
        };
    }

    function parseQuestionConfigDto(rawValue, sourceDto) {
        const fallback = sourceDto && sourceDto.questionConfigDto && typeof sourceDto.questionConfigDto === "object"
            ? sourceDto.questionConfigDto : {};
        return { ...fallback, ...jsonData, ...(parseJsonObject(rawValue) || {}) };
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
                                    <h3>Unit test (Catch2, C++17)</h3>
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
                                    <span>Script build: <span data-build-role="script">${escapeHtml(CPP_CONFIG_SCRIPT_COMMIT_HASH)}</span></span>
                                    <span class="build-separator"> | </span>
                                    <span>Server build: <span data-build-role="server">loading...</span></span>
                                </div>
                                <div class="flags-row">
                                    <label for="${ids.cpuTimeId}" title="Maximum processor time in seconds (default: 5). Waiting and sleep do not consume CPU time. Elapsed request time can be longer; Jobe also enforces a wall-clock watchdog at twice the CPU limit.">CPU time limit (seconds)</label>
                                    <input id="${ids.cpuTimeId}" title="CPU seconds, not elapsed seconds. A 5-second CPU limit can take about 10 seconds plus request overhead." type="number" min="1" step="1" class="text-input cpu-time-input" placeholder="5" />
                                    <label class="checkbox-row"><input id="${ids.optRunAtTestId}" type="checkbox" /> enable run</label>
                                    <label class="checkbox-row"><input id="${ids.optCompileAtTestId}" type="checkbox" /> enable compile</label>
                                </div>
                                <div class="flags-row">
                                    <label for="${ids.languageId}">Answer language</label>
                                    <select id="${ids.languageId}" class="text-input language-input">
                                        <option value="cpp">C++17</option><option value="c">C17</option>
                                    </select>
                                </div>
                                <p id="${ids.languageWarningId}" class="language-warning" role="status" hidden></p>
                            </div>
                        </div>

                        <div id="${ids.splitHandleId}" class="split-handle" title="Drag to resize editor/output sections"></div>

                        <div class="shared-actions">
                            <div class="shared-head-row">
                                <div class="btn-row">
                                    <button type="button" id="${ids.btnRunId}" class="cfg-btn" title="Runs the template program. Available in the Template tab; use check for unit tests." disabled>run</button>
                                    <button type="button" id="${ids.btnCompileId}" class="cfg-btn" title="Compiles the template without linking or executing it. Available in the Template tab." disabled>compile</button>
                                    <button type="button" id="${ids.btnCheckId}" class="cfg-btn" title="Runs the Catch2 unit tests against the template code.">check</button>
                                    <button type="button" id="${ids.btnScoreId}" class="cfg-btn" title="Calculates the score from the Catch2 test cases.">score</button>
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
                        <p>Das ausgewählte Beispiel ersetzt Ihren vorhandenen Code und die Dateiliste. Möchten Sie ihn wirklich überschreiben?</p>
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
        const styleId = "plugincpp-config-style";
        if (document.getElementById(styleId)) return;

        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = `
            .pluginCppConfigForm {
                display: flex;
                width: 100%;
                height: 75vh;
                box-sizing: border-box;
                gap: 8px;
            }
            .pluginCppConfigForm .config-main {
                flex: 2;
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-width: 0;
            }
            .pluginCppConfigForm .config-help {
                flex: 1;
                border: 1px solid #ccc;
                padding: 8px;
                overflow: auto;
                min-width: 0;
            }
            .pluginCppConfigForm .config-help.help-collapsed {
                flex: 0 0 auto;
                align-self: flex-start;
                padding: 4px;
                overflow: visible;
            }
            .pluginCppConfigForm .config-help.help-collapsed > :not(.help-head-row),
            .pluginCppConfigForm .config-help.help-collapsed .help-head-row h3 {
                display: none;
            }
            .pluginCppConfigForm .config-help h4 {
                margin: 14px 0 4px;
            }
            .pluginCppConfigForm .config-help p,
            .pluginCppConfigForm .config-help ul {
                margin: 4px 0 8px;
            }
            .pluginCppConfigForm .config-help ul {
                padding-left: 20px;
            }
            .pluginCppConfigForm .confirm-overlay {
                position: fixed;
                inset: 0;
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 16px;
                background: rgba(0, 0, 0, 0.45);
            }
            .pluginCppConfigForm .confirm-overlay[hidden] {
                display: none;
            }
            .pluginCppConfigForm .confirm-dialog {
                width: min(440px, 100%);
                padding: 20px;
                border-radius: 6px;
                background: #fff;
                box-shadow: 0 8px 28px rgba(0, 0, 0, 0.3);
            }
            .pluginCppConfigForm .confirm-dialog h3 {
                margin: 0 0 8px;
            }
            .pluginCppConfigForm .confirm-actions {
                justify-content: flex-end;
                margin-top: 16px;
            }
            .pluginCppConfigForm .confirm-overwrite {
                border-color: #a12622;
                background: #a12622;
            }
            .pluginCppConfigForm .tab-buttons {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            .pluginCppConfigForm .tab-head-row,
            .pluginCppConfigForm .shared-head-row,
            .pluginCppConfigForm .help-head-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }
            .pluginCppConfigForm .help-head-row h3 {
                margin: 0;
            }
            .pluginCppConfigForm .tab-btn,
            .pluginCppConfigForm .cfg-btn {
                border: 1px solid #b8b8b8;
                background: #f0f0f0;
                padding: 6px 14px;
                border-radius: 4px;
                cursor: pointer;
            }
            .pluginCppConfigForm .tab-btn.active {
                background: #dce9ff;
            }
            .pluginCppConfigForm .main-split {
                flex: 1;
                min-height: 0;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .pluginCppConfigForm .tab-panels {
                min-height: 0;
                border: 1px solid #ccc;
                padding: 8px;
            }
            .pluginCppConfigForm .main-split[data-output-hidden="false"] .tab-panels {
                flex: 0 0 65%;
            }
            .pluginCppConfigForm .main-split[data-output-hidden="false"] .shared-actions {
                flex: 1 1 auto;
            }
            .pluginCppConfigForm .main-split[data-output-hidden="true"] .split-handle {
                display: none;
            }
            .pluginCppConfigForm .main-split[data-output-hidden="true"] .tab-panels {
                flex: 1 1 auto;
            }
            .pluginCppConfigForm .main-split[data-output-hidden="true"] .shared-actions {
                flex: 0 0 auto;
                min-height: auto;
            }
            .pluginCppConfigForm .main-split[data-output-hidden="true"] .output-box {
                display: none;
            }
            .pluginCppConfigForm .tab-panel {
                display: none;
                height: 100%;
                min-height: 0;
                flex-direction: column;
                gap: 8px;
            }
            .pluginCppConfigForm .tab-panel.active {
                display: flex;
            }
            .pluginCppConfigForm .tab-title-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
            }
            .pluginCppConfigForm .tab-title-row h3 {
                margin: 0;
            }
            .pluginCppConfigForm .unit-example-controls {
                margin-left: auto;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .pluginCppConfigForm .unit-example-select {
                width: auto;
                min-width: 120px;
                margin: 0;
            }
            .pluginCppConfigForm .editor-box {
                flex: 1;
                min-height: 0;
                border: 1px solid #d0d0d0;
            }
            .pluginCppConfigForm .split-handle {
                height: 8px;
                border: 1px solid #ccc;
                background: #f3f3f3;
                cursor: row-resize;
                border-radius: 4px;
            }
            .pluginCppConfigForm .icon-btn {
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
            .pluginCppConfigForm .shared-actions {
                border: 1px solid #ccc;
                padding: 8px;
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-height: 180px;
            }
            .pluginCppConfigForm .output-box {
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
            .pluginCppConfigForm .request-progress {
                display: block;
                width: 120px;
                height: 4px;
                margin-top: 10px;
                overflow: hidden;
                background: #303830;
                border-radius: 2px;
            }
            .pluginCppConfigForm .request-progress::after {
                content: "";
                display: block;
                width: 40%;
                height: 100%;
                background: #8df58d;
                animation: cpp-request-progress 1.2s linear infinite;
            }
            @keyframes cpp-request-progress {
                from { transform: translateX(-100%); }
                to { transform: translateX(250%); }
            }
            @media (prefers-reduced-motion: reduce) {
                .pluginCppConfigForm .request-progress::after { animation: none; }
            }
            .pluginCppConfigForm .files-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
                min-height: 0;
                height: 100%;
            }
            .pluginCppConfigForm .text-input {
                width: 100%;
                box-sizing: border-box;
                margin: 4px 0 8px;
                font-family: monospace;
            }
            .pluginCppConfigForm .file-list {
                border: 1px solid #d0d0d0;
                min-height: 220px;
                max-height: 100%;
                overflow: auto;
                padding: 6px;
                font-family: monospace;
            }
            .pluginCppConfigForm .file-item {
                padding: 4px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                gap: 8px;
            }
            .pluginCppConfigForm .file-size {
                color: #666;
                font-size: 12px;
            }
            .pluginCppConfigForm .file-item:hover {
                background: #f5f5f5;
            }
            .pluginCppConfigForm .file-item.selected {
                background: #e8f1ff;
                outline: 1px solid #7aa7e9;
            }
            .pluginCppConfigForm .file-help {
                margin: 8px 0 0;
                color: #666;
                font-size: 12px;
            }
            .pluginCppConfigForm .checkbox-row {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                margin: 0;
            }
            .pluginCppConfigForm .flags-row {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            .pluginCppConfigForm .build-info {
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
            .pluginCppConfigForm .build-info.build-mismatch {
                border-color: #d00;
                background: #fff0f0;
            }
            .pluginCppConfigForm .build-info .build-mismatch-text {
                color: #d00;
                font-weight: 700;
            }
            .pluginCppConfigForm .cpu-time-input {
                width: 90px;
                margin: 0;
            }
            .pluginCppConfigForm .language-input {
                width: auto;
                margin: 0;
            }
            .pluginCppConfigForm .language-warning {
                color: #8a4b00;
                margin: 4px 0;
            }
            .pluginCppConfigForm .small-gap {
                gap: 8px;
            }
            .pluginCppConfigForm iframe {
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
        const previewPanel = document.getElementById("tab-preview");
        for (const buttonId of [ids.btnRunId, ids.btnCompileId]) {
            const button = document.getElementById(buttonId);
            if (button) button.disabled = button.dataset.requestPending === "true"
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
        initialUnit = state.validation;
        initialPreview = state.indication;

        if (aceAvailable && window.ace) {
            unitEditor = ace.edit(ids.unitEditorId);
            unitEditor.setTheme("ace/theme/monokai");
            unitEditor.session.setMode("ace/mode/c_cpp");
            unitEditor.session.setValue(initialUnit || "");

            previewEditor = ace.edit(ids.previewEditorId);
            previewEditor.setTheme("ace/theme/monokai");
            previewEditor.session.setMode("ace/mode/c_cpp");
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

        document.querySelector("." + ids.rootClass).querySelectorAll("[data-file-action]").forEach((btn) => {
            btn.onclick = async () => {
                btn.disabled = true;
                try {
                    const action = btn.getAttribute("data-file-action");
                    const name = selectedFileName;

                    if (action === "delete") {
                        if (!name || state.files[name] == null) return;
                        // Uploaded content may be referenced by other questions. Remove only this reference.
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
                } catch (error) {
                    document.getElementById(ids.outputId).textContent = "Error: " + error.message;
                } finally { btn.disabled = false; }
            };
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

    function formatBytes(value) {
        const bytes = Number(value || 0);
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
    }

    async function setupBuildInfo() {
        const buildInfo = document.getElementById(ids.buildInfoId);
        if (!buildInfo) return;

        const scriptHash = CPP_CONFIG_SCRIPT_COMMIT_HASH || "unknown";
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
        const compileAtTest = document.getElementById(ids.optCompileAtTestId);
        const cpuTime = document.getElementById(ids.cpuTimeId);
        const language = document.getElementById(ids.languageId);
        runAtTest.checked = state.evalConfig.runAtTest;
        compileAtTest.checked = state.evalConfig.lintAtTest;
        cpuTime.value = formatCpuTimeValue(state.cpuTime);
        language.value = state.language;
        [runAtTest, compileAtTest, cpuTime, language].forEach((element) => {
            element.oninput = element.onchange = (event) => {
                if (element === language && state.language !== language.value) {
                    const warning = document.getElementById(ids.languageWarningId);
                    warning.textContent = 'Answer language changed. Check the template and test declarations: C answers need extern "C"; C++ answers use C++ linkage. The bundled examples select linkage automatically. See the help for the pattern.';
                    warning.hidden = false;
                }
                saveConfig();
                if (element === cpuTime && event.type === "change") cpuTime.value = formatCpuTimeValue(state.cpuTime);
            };
        });
    }

    function syncOptionsStateFromInputs() {
        const runAtTest = document.getElementById(ids.optRunAtTestId);
        const compileAtTest = document.getElementById(ids.optCompileAtTestId);
        const cpuTime = document.getElementById(ids.cpuTimeId);
        const language = document.getElementById(ids.languageId);
        state.evalConfig.runAtTest = !!(runAtTest && runAtTest.checked);
        state.evalConfig.lintAtTest = !!(compileAtTest && compileAtTest.checked);
        state.cpuTime = parseCpuTimeValue(cpuTime ? cpuTime.value : state.cpuTime);
        state.language = language && language.value === "c" ? "c" : "cpp";
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

        bindRequest(ids.btnRunId, "/run", () => ({ code: getPreviewCode(), questionConfigDto: buildQuestionConfigDtoPayload() }), outputEl, { showTiming: true, label: "Run" });
        bindRequest(ids.btnCompileId, "/compile", () => ({ code: getPreviewCode(), questionConfigDto: buildQuestionConfigDtoPayload() }), outputEl);
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
        const placeholderUnitCode = "// Catch2 unit test code";
        const placeholderPreviewCode = "// Template code";
        const currentUnitCode = getUnitCode().trim();
        const currentPreviewCode = getPreviewCode().trim();
        const exampleUnitCode = String((example && example.validation) || "").trim();
        const examplePreviewCode = String((example && example.indication) || "").trim();

        const unitWouldBeOverwritten = currentUnitCode
            && currentUnitCode !== placeholderUnitCode
            && currentUnitCode !== exampleUnitCode;
        const previewWouldBeOverwritten = currentPreviewCode
            && currentPreviewCode !== placeholderPreviewCode
            && currentPreviewCode !== "// Preview code"
            && currentPreviewCode !== examplePreviewCode;
        return !!(unitWouldBeOverwritten || previewWouldBeOverwritten || Object.keys(state.files || {}).length);
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
                body: JSON.stringify({ index: index, questionConfigDto: buildQuestionConfigDtoPayload() })
            });
            return await readExecutionResponse(response);
        } catch (error) {
            document.getElementById(ids.outputId).textContent = "Error loading example: " + error.message;
            return null;
        }
    }

    function applyExample(example) {
        if (!example) return;
        // Update options after editor callbacks so the previous inputs cannot overwrite them.
        const next = parseConfig(JSON.stringify(example), {});
        state.files = next.files;
        state.validation = next.validation;
        state.indication = next.indication;
        if (editorAccess._setUnitCode) editorAccess._setUnitCode(next.validation);
        if (editorAccess._setPreviewCode) editorAccess._setPreviewCode(next.indication);
        Object.assign(state, next);
        setupFileTab();
        setupOptionsTab();
        document.getElementById(ids.languageWarningId).hidden = true;
        saveConfig();
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
                if (buttonId === ids.btnRunId || buttonId === ids.btnCompileId) updateRunButtonState();
                btn.textContent = oldText;
            }
        });
    }

    function buildQuestionConfigDtoPayload() {
        syncOptionsStateFromInputs();
        return {
            language: state.language,
            cpuTime: parseCpuTimeValue(state.cpuTime),
            files: currentStoredFiles()
        };
    }

    function saveConfig() {
        if (!configField) return;
        syncOptionsStateFromInputs();
        state.indication = getPreviewCode();
        state.validation = getUnitCode();
        Object.assign(questionConfigDto, {
            language: state.language,
            indication: state.indication,
            validation: state.validation,
            files: currentStoredFiles(),
            evalConfig: state.evalConfig,
            linterWeight: 0,
            cpuTime: parseCpuTimeValue(state.cpuTime)
        });
        configField.value = JSON.stringify(questionConfigDto);
        configField.dispatchEvent(new Event("input", { bubbles: true }));
        configField.dispatchEvent(new Event("change", { bubbles: true }));
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

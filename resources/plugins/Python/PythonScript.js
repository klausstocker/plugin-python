try {
    $ = jQuery;
} catch (e) { }

function initPluginPython(dtoString, active) {
    const dto = JSON.parse(dtoString || "{}");
    logDatasetTransfer("runtime init dto", dto);
    let dtoData = {};
    try {
        if (dto.jsonData) {
            try {
                const decoded = atob(dto.jsonData);
                dtoData = JSON.parse(decoded);
            } catch (decodeError) {
                dtoData = JSON.parse(dto.jsonData);
            }
        } else {
            dtoData = {};
        }
    } catch (e) {
        dtoData = {};
    }

    logDatasetTransfer("runtime init jsonData", dtoData);

    const plugin_div = "#" + dto.tagName + "_div";
    const plugin_inp = "." + dto.tagName + "_inp";
    const plugin = {
        name: dto.tagName,
        active: !!active,
        serviceBase: (dto.serviceBase || "/pluginpython").replace(/\/$/, "")
    };
    const pluginToken = (dto.params && dto.params.pluginToken) || "";

    const rootClass = `codeRunner_${plugin.name}`;
    const mainEditorId = `editor_${plugin.name}`;
    const outputId = `output_${plugin.name}`;
    const containerId = `container_${plugin.name}`;
    const splitterId = `splitter_${plugin.name}`;
    const mainPanelId = `mainPanel_${plugin.name}`;
    const outputPanelId = `outputPanel_${plugin.name}`;
    const toggleLayoutButtonId = `toggleLayout_${plugin.name}`;
    const runButtonId = `runButton_${plugin.name}`;
    const lintButtonId = `lintButton_${plugin.name}`;
    const defaultRatio = 2 / 3;
    let orientation = "horizontal";
    let splitRatio = defaultRatio;
    let aceEditor = null;

    const answerField = $(plugin_inp)[0];
    const initialMain = (answerField && answerField.value) || dtoData.indication || "# Write your Python code here\n";
    const linterConfig = dtoData.linterConfig || "";
    const linterWeight = Number(dtoData.linterWeight || 0.0);
    const files = dtoData.files || {};

    // Do not write fallback/indication text into the persisted answer field on render.
    // The hidden answer field is updated only after the student edits the editor below.

    drawLayout();
    ensureStyles();
    setupEditors(initialMain);
    bindActions();

    function drawLayout() {
        const clsName = "." + rootClass;
        if ($(clsName).length > 0) {
            $(clsName).remove();
        }

        $(plugin_div).append(`
            <div class="${rootClass} code-runner-root" data-service-base="${plugin.serviceBase}">
                <div class="container horizontal" id="${containerId}">
                    <div class="panel panel-main" id="${mainPanelId}">
                        <div class="file-info main-header">
                            <span>main.py</span>
                            <button class="layout-toggle-button" id="${toggleLayoutButtonId}" type="button" title="Toggle layout">⇅</button>
                        </div>
                        <div id="${mainEditorId}" class="editor-box"></div>
                    </div>
                    <div class="splitter" id="${splitterId}" role="separator" aria-label="Resize panels"></div>
                    <div class="panel panel-output" id="${outputPanelId}">
                        <div class="file-info output-header">output</div>
                        <div id="${outputId}" class="output-box"></div>
                    </div>
                </div>

                <div class="btn-container">
                    <button class="black-button" id="${runButtonId}" ${plugin.active ? "" : "disabled"}>Run Code</button>
                    <button class="black-button" id="${lintButtonId}" ${plugin.active ? "" : "disabled"}>Lint Code</button>
                </div>
            </div>
        `);
    }

    function ensureStyles() {
        const styleId = "pluginpython-code-runner-style";
        if (document.getElementById(styleId)) return;

        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = `
            .code-runner-root .black-button {
                color: black;
                background-color: #f0f0f0;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                font-size: 14px;
                font-weight: bold;
                margin: 4px 8px 4px 0;
                cursor: pointer;
                border-radius: 5px;
                border: 1px solid #b8b8b8;
                transition: background-color 0.3s ease, color 0.3s ease;
            }
            .code-runner-root .black-button:active {
                background-color: #333333;
                color: #ffffff;
                transform: scale(0.98);
            }
            .code-runner-root .black-button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .code-runner-root .file-info {
                padding: 10px;
                background-color: #f0f0f0;
                font-size: 16px;
                font-weight: bold;
                border-bottom: 1px solid #ccc;
                font-family: monospace;
            }
            .code-runner-root .header-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .code-runner-root .layout-toggle-button {
                margin: 0 8px;
                min-width: 36px;
                height: 32px;
                border: 1px solid #b8b8b8;
                border-radius: 4px;
                background-color: #f0f0f0;
                cursor: pointer;
                font-size: 16px;
                line-height: 1;
            }
            .code-runner-root .container {
                display: flex;
                margin-bottom: 10px;
                height: 340px;
            }
            .code-runner-root .container.vertical {
                flex-direction: column;
            }
            .code-runner-root .panel {
                min-width: 120px;
                min-height: 80px;
                overflow: hidden;
            }
            .code-runner-root .panel-main {
                display: flex;
                flex-direction: column;
                border: 1px solid #d0d0d0;
            }
            .code-runner-root .main-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .code-runner-root .editor-box {
                flex: 1;
                font-size: 16px;
                font-family: monospace;
                border-top: none;
            }
            .code-runner-root .panel-output {
                display: flex;
                flex-direction: column;
                border: 1px solid #d0d0d0;
            }
            .code-runner-root .output-header {
                border-bottom: 1px solid #ccc;
            }
            .code-runner-root .output-box {
                height: 100%;
                width: 100%;
                flex: 1;
                font-size: 16px;
                font-family: monospace;
            }
            .code-runner-root .output-box {
                background-color: black;
                color: rgb(70, 242, 70);
                overflow-y: auto;
                padding: 8px;
                white-space: pre-wrap;
                box-sizing: border-box;
            }
            .code-runner-root .splitter {
                background-color: #d0d0d0;
                flex: 0 0 8px;
            }
            .code-runner-root .container.horizontal .splitter {
                cursor: col-resize;
            }
            .code-runner-root .container.vertical .splitter {
                cursor: row-resize;
            }
            .code-runner-root .btn-container {
                margin-top: 8px;
            }
        `;
        document.head.appendChild(style);
    }

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

    async function setupEditors(initialMainCode) {
        const aceAvailable = await ensureAceLoaded();
        if (!aceAvailable || !window.ace) {
            fallbackTextareas(initialMainCode);
            return;
        }

        const editor = ace.edit(mainEditorId);
        aceEditor = editor;
        editor.setTheme("ace/theme/monokai");
        editor.session.setMode("ace/mode/python");
        editor.getSession().setValue(initialMainCode);

        if (answerField) {
            editor.session.on("change", function () {
                // Persist only after an editor change, not while rendering fallback/indication text.
                answerField.value = editor.getValue();
            });
        }

        plugin.getMainCode = () => editor.getValue();
    }

    function fallbackTextareas(initialMainCode) {
        const mainEl = document.getElementById(mainEditorId);
        mainEl.innerHTML = `<textarea style="width:100%;height:100%;box-sizing:border-box;">${escapeHtml(initialMainCode)}</textarea>`;

        const mainTextArea = mainEl.querySelector("textarea");
        if (answerField) {
            mainTextArea.addEventListener("input", () => {
                // Persist only after student input in the fallback textarea.
                answerField.value = mainTextArea.value;
            });
        }
        plugin.getMainCode = () => mainTextArea.value;
    }

    function bindActions() {
        setupLayoutControls();
        const out = document.getElementById(outputId);

        bindRequest(runButtonId, "/run", () => ({ code: plugin.getMainCode ? plugin.getMainCode() : "", questionConfigDto: { files: files } }), out);
        bindRequest(lintButtonId, "/lint", () => ({ code: plugin.getMainCode ? plugin.getMainCode() : "", questionConfigDto: { linterConfig: linterConfig, linterWeight: linterWeight, files: files } }), out);
    }

    function setupLayoutControls() {
        const container = document.getElementById(containerId);
        const mainPanel = document.getElementById(mainPanelId);
        const outputPanel = document.getElementById(outputPanelId);
        const splitter = document.getElementById(splitterId);
        const toggleBtn = document.getElementById(toggleLayoutButtonId);
        if (!container || !mainPanel || !outputPanel || !splitter || !toggleBtn) return;

        applyLayout();

        toggleBtn.addEventListener("click", () => {
            orientation = orientation === "horizontal" ? "vertical" : "horizontal";
            applyLayout();
        });

        splitter.addEventListener("mousedown", (event) => {
            event.preventDefault();
            const onMove = (moveEvent) => {
                const rect = container.getBoundingClientRect();
                if (orientation === "horizontal") {
                    const raw = (moveEvent.clientX - rect.left) / rect.width;
                    splitRatio = clampRatio(raw);
                } else {
                    const raw = (moveEvent.clientY - rect.top) / rect.height;
                    splitRatio = clampRatio(raw);
                }
                applyLayout();
            };
            const onUp = () => {
                document.removeEventListener("mousemove", onMove);
                document.removeEventListener("mouseup", onUp);
            };
            document.addEventListener("mousemove", onMove);
            document.addEventListener("mouseup", onUp);
        });

        function applyLayout() {
            const isHorizontal = orientation === "horizontal";
            container.classList.toggle("horizontal", isHorizontal);
            container.classList.toggle("vertical", !isHorizontal);
            toggleBtn.textContent = isHorizontal ? "⇅" : "⇄";
            toggleBtn.title = isHorizontal ? "Switch to vertical layout" : "Switch to horizontal layout";

            mainPanel.style.flex = `${splitRatio} 1 0`;
            outputPanel.style.flex = `${1 - splitRatio} 1 0`;

            if (aceEditor && typeof aceEditor.resize === "function") {
                aceEditor.resize();
            }
        }
    }

    function clampRatio(ratio) {
        return Math.min(0.85, Math.max(0.15, ratio || defaultRatio));
    }

    function bindRequest(buttonId, endpoint, bodyBuilder, targetEl) {
        const btn = document.getElementById(buttonId);
        if (!btn) return;

        btn.addEventListener("click", async function () {
            const payload = bodyBuilder();
            logDatasetTransfer(`runtime request ${endpoint} payload`, payload);
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = "Working...";
            try {
                const res = await fetch(plugin.serviceBase + endpoint, {
                    method: "POST",
                    headers: buildHeaders(),
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                targetEl.textContent = (data && data.output) ? data.output : JSON.stringify(data);
            } catch (error) {
                targetEl.textContent = "Error: " + (error && error.message ? error.message : "request failed");
            } finally {
                btn.disabled = !plugin.active;
                btn.textContent = originalText;
            }
        });
    }

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, "&amp;")
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

try {
    $ = jQuery;
} catch (e) { }

const PYTHON_SCRIPT_COMMIT_HASH = "c70dad38cc61";

function initPluginPython(dtoString, active) {
    const dto = JSON.parse(dtoString || "{}");
    const dtoParams = (dto.params && typeof dto.params === "object")
        ? dto.params
        : (dto.pluginDto && dto.pluginDto.params && typeof dto.pluginDto.params === "object" ? dto.pluginDto.params : {});
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


    const plugin_div = "#" + dto.tagName + "_div";
    const plugin_inp = "." + dto.tagName + "_inp";
    const plugin = {
        name: dto.tagName,
        active: !!active,
        serviceBase: ((dto.pluginDto && dto.pluginDto.serviceBase) || dto.serviceBase || "/pluginpython").replace(/\/$/, "")
    };
    const pluginTokenPromise = requestExecutionToken();

    const rootClass = `codeRunner_${plugin.name}`;
    const mainEditorId = `editor_${plugin.name}`;
    const outputId = `output_${plugin.name}`;
    const containerId = `container_${plugin.name}`;
    const splitterId = `splitter_${plugin.name}`;
    const mainPanelId = `mainPanel_${plugin.name}`;
    const outputPanelId = `outputPanel_${plugin.name}`;
    const toggleLayoutButtonId = `toggleLayout_${plugin.name}`;
    const buildInfoId = `buildInfo_${plugin.name}`;
    const runButtonId = `runButton_${plugin.name}`;
    const lintButtonId = `lintButton_${plugin.name}`;
    const defaultRatio = 2 / 3;
    let orientation = "horizontal";
    let splitRatio = defaultRatio;
    let aceEditor = null;

    const answerField = $(plugin_inp)[0];
    const programmingLanguage = normalizeProgrammingLanguage(dtoData.programmingLanguage);
    const defaultMain = dtoData.indication || defaultStarterCode(programmingLanguage);
    const initialMain = (answerField && answerField.value) || defaultMain;
    const linterConfig = dtoData.linterConfig || "";
    const linterWeight = Number(dtoData.linterWeight || 0.0);
    const files = dtoData.files || {};

    // Let LeTTo score the initially rendered question by submitting the visible starter code.
    if (answerField && !answerField.value) {
        answerField.value = defaultMain;
    }

    drawLayout();
    ensureStyles();
    setupEditors(initialMain);
    bindActions();
    setupBuildInfo();

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
                            <span>${sourceFilename(programmingLanguage)}</span>
                            <span class="header-actions">
                                <button class="layout-toggle-button" id="${toggleLayoutButtonId}" type="button" title="Toggle layout">⇅</button>
                                <span id="${buildInfoId}" class="build-info-help" title="Script build: ${escapeHtmlAttr(PYTHON_SCRIPT_COMMIT_HASH)}
Server build: loading...">?</span>
                            </span>
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
            .code-runner-root .header-actions {
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }
            .code-runner-root .layout-toggle-button {
                margin: 0;
                min-width: 36px;
                height: 32px;
                border: 1px solid #b8b8b8;
                border-radius: 4px;
                background-color: #f0f0f0;
                cursor: pointer;
                font-size: 16px;
                line-height: 1;
            }
            .code-runner-root .build-info-help {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 18px;
                height: 18px;
                border: 1px solid #888;
                border-radius: 50%;
                background: #f7f7f7;
                color: #444;
                font-family: sans-serif;
                font-size: 12px;
                font-weight: 700;
                cursor: help;
                line-height: 1;
            }
            .code-runner-root .build-info-help.build-mismatch {
                border-color: #d00;
                background: #fff0f0;
                color: #d00;
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

    function normalizeProgrammingLanguage(language) {
        return ["python", "c", "cpp"].includes(language) ? language : "python";
    }

    function aceModeForLanguage(language) {
        return language === "python" ? "ace/mode/python" : "ace/mode/c_cpp";
    }

    function sourceFilename(language) {
        if (language === "c") return "main.c";
        if (language === "cpp") return "main.cpp";
        return "main.py";
    }

    function defaultStarterCode(language) {
        if (language === "c") return "#include <stdio.h>\n\nint main(void) {\n    return 0;\n}\n";
        if (language === "cpp") return "#include <iostream>\n\nint main() {\n    return 0;\n}\n";
        return "# Write your Python code here\n";
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
        editor.session.setMode(aceModeForLanguage(programmingLanguage));
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

    async function setupBuildInfo() {
        const buildInfo = document.getElementById(buildInfoId);
        if (!buildInfo) return;

        const scriptHash = PYTHON_SCRIPT_COMMIT_HASH || "unknown";
        buildInfo.title = `Script build: ${scriptHash}
Server build: loading...`;

        try {
            const response = await fetch(plugin.serviceBase + "/buildhash", {
                method: "GET",
                headers: await buildAuthHeaders(),
                credentials: "include"
            });
            if (!response.ok) throw new Error("Build hash request failed");

            const body = await response.json();
            const serverHash = body && body.commitHash ? String(body.commitHash) : "unknown";
            const mismatch = serverHash !== scriptHash;
            buildInfo.title = `Script build: ${scriptHash}
Server build: ${serverHash}`;
            buildInfo.classList.toggle("build-mismatch", mismatch);
        } catch (e) {
            buildInfo.title = `Script build: ${scriptHash}
Server build: unavailable`;
            buildInfo.classList.add("build-mismatch");
        }
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
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = "Working...";
            try {
                const res = await fetch(plugin.serviceBase + endpoint, {
                    method: "POST",
                    headers: await buildHeaders(),
                    credentials: "include",
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

    function escapeHtmlAttr(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    async function requestExecutionToken() {
        try {
            const response = await fetch(plugin.serviceBase + "/exectoken", {
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

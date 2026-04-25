try {
    $ = jQuery;
} catch (e) { }

function initPluginPython(dtoString, active) {
    const dto = JSON.parse(dtoString || "{}");
    let dtoData = {};
    try {
        dtoData = dto.jsonData ? JSON.parse(dto.jsonData) : {};
    } catch (e) {
        dtoData = {};
    }

    const plugin_div = "#" + dto.tagName + "_div";
    const plugin_inp = "." + dto.tagName + "_inp";
    const plugin = {
        name: dto.tagName,
        active: !!active,
        serviceBase: (dto.serviceBase || "/pluginpython").replace(/\/$/, "")
    };

    const rootClass = `codeRunner_${plugin.name}`;
    const mainEditorId = `editor_${plugin.name}`;
    const outputId = `output_${plugin.name}`;
    const runButtonId = `runButton_${plugin.name}`;
    const lintButtonId = `lintButton_${plugin.name}`;

    const answerField = $(plugin_inp)[0];
    const initialMain = (answerField && answerField.value) || dtoData.indication || "# Write your Python code here\n";

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
                <div class="file-info">main.py</div>
                <div class="container">
                    <div id="${mainEditorId}" class="editor-box"></div>
                    <div id="${outputId}" class="output-box"></div>
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
            .code-runner-root .container {
                display: flex;
                gap: 8px;
                margin-bottom: 10px;
            }
            .code-runner-root .editor-box,
            .code-runner-root .output-box {
                height: 300px;
                width: 100%;
                font-size: 16px;
                font-family: monospace;
                border: 1px solid #d0d0d0;
            }
            .code-runner-root .output-box {
                background-color: black;
                color: rgb(70, 242, 70);
                overflow-y: auto;
                padding: 8px;
                white-space: pre-wrap;
                box-sizing: border-box;
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

    async function setupEditors(initialMainCode) {
        const aceAvailable = await ensureAceLoaded();
        if (!aceAvailable || !window.ace) {
            fallbackTextareas(initialMainCode);
            return;
        }

        const editor = ace.edit(mainEditorId);
        editor.setTheme("ace/theme/monokai");
        editor.session.setMode("ace/mode/python");
        editor.getSession().setValue(initialMainCode);

        if (answerField) {
            editor.session.on("change", function () {
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
            mainTextArea.addEventListener("input", () => answerField.value = mainTextArea.value);
        }
        plugin.getMainCode = () => mainTextArea.value;
    }

    function bindActions() {
        const out = document.getElementById(outputId);

        bindRequest(runButtonId, "/run", () => ({ code: plugin.getMainCode ? plugin.getMainCode() : "" }), out);
        bindRequest(lintButtonId, "/lint", () => ({ code: plugin.getMainCode ? plugin.getMainCode() : "" }), out);
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
                    headers: { "Content-Type": "application/json" },
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
}

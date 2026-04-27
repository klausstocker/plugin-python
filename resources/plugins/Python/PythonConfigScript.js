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

    const rootClass = "pluginConfigForm";
    const unitEditorId = `unitEditor_${pluginTag}`;
    const unitOutputId = `unitOutput_${pluginTag}`;
    const previewEditorId = `previewEditor_${pluginTag}`;
    const previewOutputId = `previewOutput_${pluginTag}`;

    const unitRunBtnId = `unitRun_${pluginTag}`;
    const unitScoreBtnId = `unitScore_${pluginTag}`;
    const unitLintBtnId = `unitLint_${pluginTag}`;
    const previewRunBtnId = `previewRun_${pluginTag}`;
    const previewLintBtnId = `previewLint_${pluginTag}`;

    const loaded = parseConfig(configField && configField.value ? configField.value : "", jsonData);

    drawForm();
    ensureStyles();
    setupEditors(loaded.validation, loaded.indication);
    bindButtons();
    renderHelp();

    function parseConfig(rawValue, fallbackData) {
        const empty = {
            indication: (fallbackData && fallbackData.indication) || "# Preview code\n",
            validation: (fallbackData && fallbackData.validation) || "# Unit test code\n"
        };

        if (!rawValue) return empty;

        try {
            const parsed = JSON.parse(rawValue);
            return {
                indication: parsed.indication || empty.indication,
                validation: parsed.validation || empty.validation,
                evalConfig: parsed.evalConfig || (fallbackData && fallbackData.evalConfig) || {}
            };
        } catch (e) {
            return {
                indication: rawValue || empty.indication,
                validation: empty.validation,
                evalConfig: (fallbackData && fallbackData.evalConfig) || {}
            };
        }
    }

    function drawForm() {
        const selector = "." + rootClass;
        if ($(selector).length > 0) {
            $(selector).remove();
        }

        $(config_form_div).append(`
            <div class="${rootClass}">
                <div class="config-main">
                    <div class="config-top split-row">
                        <div class="panel">
                            <h3>Config: UnitTest</h3>
                            <div id="${unitEditorId}" class="editor-box"></div>
                            <div class="btn-row">
                                <button id="${unitRunBtnId}" class="cfg-btn">run</button>
                                <button id="${unitScoreBtnId}" class="cfg-btn">score</button>
                                <button id="${unitLintBtnId}" class="cfg-btn">lint</button>
                            </div>
                        </div>
                        <div class="panel">
                            <h3>Unit test output</h3>
                            <pre id="${unitOutputId}" class="output-box"></pre>
                        </div>
                    </div>
                    <div class="config-bottom split-row">
                        <div class="panel">
                            <h3>Preview</h3>
                            <div id="${previewEditorId}" class="editor-box"></div>
                            <div class="btn-row">
                                <button id="${previewRunBtnId}" class="cfg-btn">run</button>
                                <button id="${previewLintBtnId}" class="cfg-btn">lint</button>
                            </div>
                        </div>
                        <div class="panel">
                            <h3>Preview output</h3>
                            <pre id="${previewOutputId}" class="output-box"></pre>
                        </div>
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
            .pluginConfigForm .split-row {
                flex: 1;
                display: flex;
                gap: 10px;
                min-height: 0;
            }
            .pluginConfigForm .panel {
                flex: 1;
                border: 1px solid #ccc;
                padding: 8px;
                display: flex;
                flex-direction: column;
                min-width: 0;
                min-height: 0;
            }
            .pluginConfigForm h3 {
                margin: 0 0 8px 0;
            }
            .pluginConfigForm .editor-box,
            .pluginConfigForm .output-box {
                flex: 1;
                width: 100%;
                min-height: 0;
                border: 1px solid #d0d0d0;
                box-sizing: border-box;
                font-family: monospace;
                font-size: 14px;
            }
            .pluginConfigForm .output-box {
                margin: 0;
                background: #101010;
                color: #8df58d;
                padding: 8px;
                overflow: auto;
                white-space: pre-wrap;
            }
            .pluginConfigForm .btn-row {
                margin-top: 8px;
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            .pluginConfigForm .cfg-btn {
                border: 1px solid #b8b8b8;
                background: #f0f0f0;
                padding: 6px 14px;
                border-radius: 4px;
                cursor: pointer;
                text-transform: lowercase;
            }
            .pluginConfigForm iframe {
                width: 100%;
                height: 60vh;
                border: none;
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

    async function setupEditors(initialUnit, initialPreview) {
        const aceAvailable = await ensureAceLoaded();

        if (aceAvailable && window.ace) {
            const unitEditor = ace.edit(unitEditorId);
            unitEditor.setTheme("ace/theme/monokai");
            unitEditor.session.setMode("ace/mode/python");
            unitEditor.session.setValue(initialUnit || "");

            const previewEditor = ace.edit(previewEditorId);
            previewEditor.setTheme("ace/theme/monokai");
            previewEditor.session.setMode("ace/mode/python");
            previewEditor.session.setValue(initialPreview || "");

            unitEditor.session.on("change", saveConfig);
            previewEditor.session.on("change", saveConfig);

            configPluginPython._getUnitCode = () => unitEditor.getValue();
            configPluginPython._getPreviewCode = () => previewEditor.getValue();
        } else {
            fallbackTextArea(unitEditorId, initialUnit, "_getUnitCode");
            fallbackTextArea(previewEditorId, initialPreview, "_getPreviewCode");
        }

        saveConfig();
    }

    function fallbackTextArea(targetId, value, key) {
        const target = document.getElementById(targetId);
        target.innerHTML = `<textarea style="width:100%;height:100%;box-sizing:border-box;font-family:monospace;">${escapeHtml(value || "")}</textarea>`;
        const ta = target.querySelector("textarea");
        ta.addEventListener("input", saveConfig);
        configPluginPython[key] = () => ta.value;
    }

    function getUnitCode() {
        return configPluginPython._getUnitCode ? configPluginPython._getUnitCode() : "";
    }

    function getPreviewCode() {
        return configPluginPython._getPreviewCode ? configPluginPython._getPreviewCode() : "";
    }

    function saveConfig() {
        if (!configField) return;
        const payload = {
            indication: getPreviewCode(),
            validation: getUnitCode(),
            evalConfig: loaded.evalConfig || {}
        };
        configField.value = JSON.stringify(payload);
    }

    function bindButtons() {
        const unitOutput = document.getElementById(unitOutputId);
        const previewOutput = document.getElementById(previewOutputId);

        bindRequest(unitRunBtnId, "/run", () => ({ code: getUnitCode() }), unitOutput);
        bindRequest(unitLintBtnId, "/lint", () => ({ code: getUnitCode() }), unitOutput);
        bindRequest(unitScoreBtnId, "/check", () => ({ code: getPreviewCode(), testcode: getUnitCode() }), unitOutput);

        bindRequest(previewRunBtnId, "/run", () => ({ code: getPreviewCode() }), previewOutput);
        bindRequest(previewLintBtnId, "/lint", () => ({ code: getPreviewCode() }), previewOutput);
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
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(bodyBuilder())
                });
                const data = await response.json();
                outputEl.textContent = (data && data.output) ? data.output : JSON.stringify(data);
            } catch (error) {
                outputEl.textContent = "Error: " + (error && error.message ? error.message : "request failed");
            } finally {
                btn.disabled = false;
                btn.textContent = oldText;
            }
        });
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
}

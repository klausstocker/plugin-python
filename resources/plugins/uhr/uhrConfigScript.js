try {
    $=jQuery;
} catch (e) {}

/* -----------------------------------------------------------------------------------------------
 *   Lädt den Konfigurationsdialog in das Formular der Plugin-Konfiguration in ein vordefiniertes div-Element "#configform_div" <br>
 *   Das Ergebnis der Konfiguration in ein verstecktes Textfeld der Klasse ".configform_config" übergeben werden
 *   Um Konflikte zu vermeiden werden alle Funktionen als innere Funktionen dieser Funktion realisiert!
 * ----------------------------------------------------------------------------------------------- */
function configPluginUhr(dtoString) {
    // -------------------------- Verbindungskonstante zu LeTTo ---------------------------------------
    // Div Element welches im Konfigurations-Formular liegt - MUSS für LETTO SO HEISSEN!!
    const config_form_div     = "#configform_div";
    // verstecktes Input-Element für die Eingabe - MUSS für LETTO SO HEISSEN !!
    const config_form_config = ".configform_config";
    // ------------------------------------------------------------------------------------------------

    // Dies ist das PluginConfigDto
    let dto  = JSON.parse(dtoString);
    dto.data = JSON.parse(dto.jsonData);
    let plugin = new Object();
    plugin.typ        = dto.typ;
    plugin.name       = dto.tagName;
    plugin.jimagepath = dto.imageUrl;
    plugin.width      = dto.width;
    plugin.height     = dto.height;
    plugin.config     = dto.config;

    // Textfeld in das die Konfiguration geschrieben werden muss
    let config = $(config_form_config)[0];

    // Klasse für das umgebende div des Konfigurationsdialogs welches in das div plugin.divForm platziert wird.
    plugin.configContainer = "pluginConfigForm";

    // Parameter für die Vorschau des Plugins
    let pluginDto = dto.pluginDto;
    plugin.answerFieldClass = pluginDto.tagName + "_inp";
    plugin.divName          = pluginDto.tagName + "_div";

    // Eingabeformular definieren
    drawForm();

    // Event-Handler definieren - muss nach drawForm gemacht werden!!!
    loadEventHandler();

    /* -----------------------------------------------------------------------------------------------
     *   Rendert das Eingabe-Formular für den Plugin-Config-Dialog
     * ----------------------------------------------------------------------------------------------- */
    function drawForm() {
        let formName = "."+plugin.configContainer;
        if ($(formName).length>0)
            $(formName).remove();

        if ($(formName).length==0)
            $(config_form_div).append( ` 
            <style>
                .pluginConfigForm {
                    display: flex;
                    flex-direction: row;
                    width: 100%;
                    height: 75vh; /* 75 Prozent der vollen Höhe des Viewports */
                    box-sizing: border-box;
                }
                .configpane {
                    flex: 1;
                    padding: 10px;
                    overflow: auto;
                    border: 1px solid #ccc;
                }
                .configresizer {
                    width: 5px;
                    cursor: ew-resize;
                    background-color: #ddd;
                    height: 100%;
                }
                iframe {
                    width: 150%;
                    height: 100%;
                    border: none;
                }
            </style>      
            <div class="${plugin.configContainer}" >
                <div class="configpane" id="leftPane">
                    <!-- Konfigurationsbereich -->
                    <h1>Uhr-Plugin</h1>  
                    <input type="text" id="data1" value="${plugin.config}"/>   
                    <button id="sendbutton">OK</button> <br>
                    vars: <input typ="text" value="${dto.params['vars']}" size="40" readonly/><br>
                    
                </div>
                <div class="configresizer" id="resizerLeft"></div>
                <div class="configpane" id="centerPane">
                    <!-- Vorschaubereich -->
                    <h3>preview</h3>
                    <textarea class="${plugin.answerFieldClass}" id="vorschau_div_0" name="configVorschau" th:text="" rows="2" cols="60"></textarea>
                    <div id="${plugin.divName}" style="width:100%"></div>                    
                </div>
                <div class="configresizer" id="resizerRight"></div>
                <div class="configpane" id="rightPane">
                    <!-- Help -->
                    <a href="https://doc.letto.at/wiki/Plugins" target="_blank">Wiki-Plugins</a>
                    <div id="configPluginHelp"></div>
                    <div id="configPluginWiki"></div>
                </div>
            </div>`
            );

        // Vorschau
        vorschau();

        // Help eintragen
        if (dto.params['help']!=null) {
            const helpElement = document.getElementById('configPluginHelp');
            helpElement.innerHTML = dto.params['help'];
        }

        if (dto.params['wikiurl']!=null) {
            const wikiElement = document.getElementById('configPluginWiki');
            wikiElement.style.height = '75vh';
            wikiElement.innerHTML = '<iframe src="'+dto.params['wikiurl']+'"></iframe>';
        }

        // Resizer
        const resizers = document.querySelectorAll('.configresizer');
        let currentResizer;

        for (let resizer of resizers) {
            resizer.addEventListener('mousedown', function(e) {
                currentResizer = e.target;
                document.addEventListener('mousemove', resize);
                document.addEventListener('mouseup', stopResize);
            });
        }

        // Funktion für die zwei Resizer zwischen den drei Spalten des Dialogs
        function resize(e) {
            const leftPane = currentResizer.previousElementSibling;
            const rightPane = currentResizer.nextElementSibling;

            if (currentResizer.id === 'resizerLeft') {
                const newWidth = e.clientX - leftPane.getBoundingClientRect().left;
                leftPane.style.flex = `0 0 ${newWidth}px`;
            } else if (currentResizer.id === 'resizerRight') {
                const newWidth = rightPane.getBoundingClientRect().right-e.clientX;;
                rightPane.style.flex = `0 0 ${newWidth}px`;
            }
        }

        // Beendet den Resize-Vorgang
        function stopResize() {
            document.removeEventListener('mousemove', resize);
            document.removeEventListener('mouseup', stopResize);
        }
    }

    /* -----------------------------------------------------------------------------------------------
     *   Eventhandler für die Buttons und aktive Felder laden
     * ----------------------------------------------------------------------------------------------- */
    function loadEventHandler(){

        $( "#data1" ).on( "input", function() {
            loadDataConfigUhr();
        });
        $( "#sendbutton" ).on( "click", function(event) {
            event.preventDefault();
            loadDataConfigUhr();
        } );
    }

    /* -----------------------------------------------------------------------------------------------
     *   Trägt die Konfiguration im Hauptformular ein - Schnittstelle des Ergebnisses zu LeTTo!!!
     * ----------------------------------------------------------------------------------------------- */
    function loadDataConfigUhr() {
        const data   = $('#data1')[0].value;
        config.value = data;
        vorschau();
    }

    /* -----------------------------------------------------------------------------------------------
     *   Holt vom Server über eine ajax-Request ein neues PluginDto
     * ----------------------------------------------------------------------------------------------- */
    function vorschau() {
        // Anfrage am Rest-Endpoint
        const restUri   = dto.pluginDtoUri;
        const restToken = dto.pluginDtoToken;
        try {
            if (restToken===null || restToken==="") {
                $.ajax({
                    contentType: 'application/json',
                    url: restUri,
                    data: JSON.stringify({typ: plugin.typ,
                           name: plugin.name,
                           config: config.value,
                           params:'',
                           nr: 0,
                           configurationID: dto.configurationID
                    }),
                    type: 'POST',
                    dataType: 'json',
                    error: function(xhr, status, error) {
                        // Code, der bei einem Fehler ausgeführt wird
                        console.error(error);
                    }
                }).then(function (data) {
                    try {
                        if (data.tagName != null) {
                            let pluginDto = data;
                            initPluginUhr(JSON.stringify(pluginDto),true);
                        }
                    } catch (error) {
                    }
                });
            } else {
            }
        } catch (error) {}
    }

}

import os
import re
import math
import base64
import io
import asyncio
import logging
import shutil
import httpx
import platform
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, APIRouter, Body
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ConfigDict
from PIL import Image, ImageDraw
from dataclasses import dataclass

# --------------------------
# CONFIGURATION
# --------------------------
# Der Servicepath muss in der nginx-Konfiguration auf den Docker-Container des Plugins gesetzt werden -> siehe proxy/pluginpython.conf
CONF_STANDARD_SERVICEPATH = "/pluginpython"
# Name des Plugin-Service
CONF_APPLICATION_NAME = "pluginpython"
# Name des Services wie es am Setup registriert wird
CONF_PLUGIN_NAME = "letto-pluginpython"
# Author des Plugins
CONF_PLUGIN_AUTHOR = "Klaus Stocker"
# Lizenz des Plugins
CONF_PLUGIN_LICENSE = "OpenSource"
# Name des Plugins wie es in Letto erscheint
CONF_PLUGIN = "Python"
# Version des Plugins
CONF_VERSION = "1.0"
# Java-Script function für die Initialisierung des Plugins wenn es im Java-Script modus laufen sollte
CONF_INIT_JS = "initPluginUhrPy"
# Java-Script function für die Konfiguration des Plugins wenn es im Java-Script konfiguriert werden sollte
CONF_CONFIG_JS = "configPluginUhrPy"
# Hilfe als HTML-Datei
CONF_HELPFILES = ["plugins/uhr/UhrPy.html"]
# Javascript Dateien die für dieses Plugin von LeTTo eingebunden werden müssen
CONF_JSLIBS = ["plugins/uhr/uhrPyScript.js", "plugins/uhr/uhrPyConfigScript.js"]
# Namen der Wiki-Seite wenn eine Doku am LeTTo-Wiki vorliegt
CONF_wikiHelp = "Plugins"
# Hilfe-URL für die Beschreibung des Plugins
CONF_helpUrl=""
# Gibt an ob die Standard-Plugin-Configuration verwendet werden soll
CONF_defaultPluginConfig = False
# Breite des zu erzeugenden Bildes
CONF_width = 500
# Höhe des zu erzeugenden Bildes
CONF_height = 500
# Größe des Bildes in Prozent
CONF_imageWidthProzent = 100
# True wenn das Plugin CalcErgebnis und VarHash als JSON verarbeiten kann
CONF_math = False
# Javascript Libraries für das Plugin
CONF_javascriptLibs = {"plugins/plugintools.js"}
# Name der JAVA-Script Methode zur Plugin-Initialisierung für die interaktive Ergebniseingabe
CONF_initPluginJS = ""
# gibt an ob das Plugin eine Java-Script Schnittstelle bei der Beispieldarstellung hat
CONF_javaScript = False
# Plugin ist stateless und liefert bei gleicher Angabe immer das gleiche Verhalten
CONF_cacheable = True
# Gibt an ob im Plugin die Frage benötigt wird
CONF_useQuestion = True
# gibt an ob die Datensatz-Variable ohne Konstante benötigt werden
CONF_useVars = True
# gibt an ob die Datensatz-Variable mit Konstanten benötigt werden
CONF_useCVars = True
# gibt an ob die Maxima-Durchrechnungen ohne eingesetzte Datensätze benötigt werden
CONF_useMaximaVars = True
# gibt an ob die Maxima-Durchrechnungen mit eingesetzten Datensätzen benötigt werden
CONF_useMVars = True
# Konfigurations-Mode für die Konfiguration des Plugins
CONF_configurationMode = 2
# Gibt an, ob im Plugin-Konfig-Dialog Datensätze hinzugefügt werden können. => Button AddDataset in Fußzeile des umgebenden Dialogs, (nicht vom Plugin)
CONF_addDataSet = True
# Gibt an, ob das Plugin über den Browser direkt erreichbar ist
CONF_externUrl = False
# Gibt an ob im Plugin bei der Konfiguration die Maxima-Berechnung durchlaufen werden kann. => Button Maxima in Fußzeile des umgebenden Dialogs, (nicht vom Plugin)
CONF_calcMaxima = True
# Name der JAVA-Script Methode zur Configuration des Plugins
CONF_configPluginJS = "configPlugin"
# URL des Plugin-Services für die direkte Kommunikation
CONF_pluginServiceURL = ""

# ----------------------------------
# Environment aus der yml-Datei
# ----------------------------------
LETTO_SETUP_URI = os.getenv("letto_setup_uri", os.getenv("LETTO_SETUP_URI", "http://letto-setup.nw-letto:8096")).rstrip(
    "/")
LETTO_SETUP_USER = "user"
LETTO_SETUP_PASSWORD = os.getenv("letto_user_user_password", os.getenv("LETTO_USER_USER_PASSWORD", ""))
PLUGIN_ENDPOINT_NAME = os.getenv("PLUGIN_ENDPOINT_NAME", "pluginpython")
PLUGIN_REGISTER_ON_READY = os.getenv("PLUGIN_REGISTER_ON_READY", "true").lower() == "true"
PLUGIN_REGISTER_RETRIES = int(os.getenv("PLUGIN_REGISTER_RETRIES", "30"))
PLUGIN_REGISTER_DELAY_SECONDS = float(os.getenv("PLUGIN_REGISTER_DELAY_SECONDS", "1.0"))
NW_LETTO_ADDRESS = os.getenv("network_letto_address", os.getenv("NETWORK_LETTO_ADDRESS", "letto-pluginpython"))
DOCKER_CONTAINER_NAME = os.getenv("docker_container_name", os.getenv("DOCKER_CONTAINER_NAME", "letto-pluginpython"))
LETTO_PLUGIN_URI_INTERN = os.getenv("letto_plugin_uri_intern",
                                    os.getenv("LETTO_PLUGIN_URI_INTERN", f"http://{NW_LETTO_ADDRESS}.nw-letto:8080"))
LETTO_PLUGIN_URI_EXTERN = os.getenv("letto_plugin_uri_extern", os.getenv("LETTO_PLUGIN_URI_EXTERN", ""))
SETUP_ENDPOINT_REGISTER = "/config/auth/user/registerplugin"               # Endpoint im Setup, an dem die Registrierung erfolgt

# --------------------------
# Paths (match Java project)
# --------------------------
SERVICE_NAME = CONF_APPLICATION_NAME
SERVICEPATH = os.getenv("SERVICEPATH", CONF_STANDARD_SERVICEPATH).rstrip("/")  # external prefix used by reverse proxy
LOCAL_API = "/open"  # internal api base
EXTERN_OPEN = f"{SERVICEPATH}/api/open"  # external open base
PING = "/ping"
PINGOPEN = f"{SERVICEPATH}/open/ping"
INFO = "/info"
INFO_OPEN = f"{SERVICEPATH}/open/info"

# --------------------------
# Logging
# --------------------------
logger = logging.getLogger("plugin-registration")
logging.basicConfig(level=logging.INFO)

_registration_task = None


# --------------------------
# Utilities
# --------------------------
def get_system_info():
    # OS
    os_name = platform.system()
    os_version = platform.version()

    # IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return {
        "bs": f"{os_name} {os_version}",
        "ip": ip
    }


def parse_time_seconds(s: str) -> float:
    """
    Java Datum.parseTime:
      - HH:MM
      - HH:MM:SS
      - HH:MM:SS.mmm...
    -> seconds (float)
    """
    s = (s or "").strip()
    m = re.match(r"^(\d+):(\d+)$", s)
    if m:
        h = float(m.group(1))
        mi = float(m.group(2))
        return h * 3600.0 + mi * 60.0
    m = re.match(r"^(\d+):(\d+):(\d+\.?\d*)$", s)
    if m:
        h = float(m.group(1))
        mi = float(m.group(2))
        sec = float(m.group(3))
        return h * 3600.0 + mi * 60.0 + sec
    raise ValueError("invalid time format")


def equals_with_tolerance(a: float, b: float, toleranz: float, mode: str) -> bool:
    # mode: "RELATIV" or "ABSOLUT"
    if mode == "ABSOLUT":
        return abs(a - b) <= toleranz
    # RELATIV (default)
    ref = max(abs(a), abs(b), 1e-12)
    return abs(a - b) <= toleranz * ref


def read_resource_text(rel_path: str) -> str:
    """
    Reads from ./resources (project root) at runtime inside container.
    We keep it file-based (no pkg resources) to make copying easy.
    """
    base = os.getenv("RESOURCE_DIR", "/app/resources")
    path = os.path.join(base, rel_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"@ERROR: resource not found: {rel_path}"


def _copy_tree_contents(src_dir: str, dst_dir: str) -> None:
    if not os.path.isdir(src_dir):
        logger.warning("Resource-Quelle existiert nicht: %s", src_dir)
        return
    os.makedirs(dst_dir, exist_ok=True)
    for entry in os.listdir(src_dir):
        src = os.path.join(src_dir, entry)
        dst = os.path.join(dst_dir, entry)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)


def sync_resources_for_webserver() -> None:
    """
    Kopiert Ressourcen in Host-Volumes, damit Proxy/Webserver direkt darauf zugreifen kann.
    Quelle: ${RESOURCE_DIR}/plugins
    Ziele:
      - letto_pathPlugins / LETTO_PATH_PLUGINS
      - letto_pathImages / LETTO_PATH_IMAGES + "/plugins"
    """
    resource_dir = os.getenv("RESOURCE_DIR", "/app/resources")
    source_plugins_dir = os.path.join(resource_dir, "plugins")

    plugin_target = os.getenv("letto_pathPlugins", os.getenv("LETTO_PATH_PLUGINS", "")).strip()
    image_base = os.getenv("letto_pathImages", os.getenv("LETTO_PATH_IMAGES", "")).strip()
    image_plugins_target = os.path.join(image_base, "plugins") if image_base else ""

    targets = [path for path in [plugin_target, image_plugins_target] if path]
    if not targets:
        logger.info("Kein Zielpfad für Web-Ressourcen gesetzt (letto_pathPlugins/letto_pathImages).")
        return

    for target in targets:
        try:
            _copy_tree_contents(source_plugins_dir, target)
            logger.info("Plugin-Ressourcen nach %s synchronisiert.", target)
        except Exception as ex:
            logger.warning("Konnte Ressourcen nicht nach %s kopieren: %s", target, ex)


def draw_clock_png(hh: int, mm: int, size: int = 320, bgcolor: str = "white") -> bytes:
    # Background color mapping similar to Java (white, black, red, green, blue, yellow)
    bg_map = {
        "white": (255, 255, 255, 255),
        "black": (0, 0, 0, 255),
        "red": (255, 0, 0, 255),
        "green": (0, 255, 0, 255),
        "blue": (0, 0, 255, 255),
        "yellow": (255, 255, 0, 255),
    }
    bg = bg_map.get(bgcolor.lower(), (255, 255, 255, 255))

    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = int(size * 0.45)

    # face fill + outline
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=bg, outline=(0, 0, 0, 255), width=max(2, size // 100))

    # ticks + numbers
    for i in range(1, 13):
        alpha = math.pi / 2 - 2 * math.pi / 12.0 * i
        x1 = cx + int(r * 0.90 * math.cos(alpha))
        y1 = cy - int(r * 0.90 * math.sin(alpha))
        x2 = cx + int(r * 1.00 * math.cos(alpha))
        y2 = cy - int(r * 1.00 * math.sin(alpha))
        d.line((x1, y1, x2, y2), fill=(0, 0, 255, 255), width=max(3, size // 90))

    # hands
    minute_ang = math.pi / 2 - 2 * math.pi * (mm / 60.0)
    hour_ang = math.pi / 2 - 2 * math.pi * ((hh % 12) / 12.0 + (mm / 720.0))

    def hand(angle: float, length: float, width: int):
        x = cx + int(length * math.cos(angle))
        y = cy - int(length * math.sin(angle))
        d.line((cx, cy, x, y), fill=(0, 0, 0, 255), width=width)

    hand(hour_ang, r * 0.55, max(5, size // 60))
    hand(minute_ang, r * 0.80, max(4, size // 80))
    d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(0, 0, 0, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def png_b64(png: bytes) -> str:
    return base64.b64encode(png).decode("ascii")

# --------------------------
# DTOs (match Java field names)
# --------------------------

class JavascriptLibrary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    library: Optional[str] = None
    name: Optional[str] = None
    globalName: Optional[str] = None
    local: Optional[str] = "LOCAL"
    js_code: Optional[str] = ""

class PluginGeneralInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = ""
    version: Optional[str] = "1.0"
    wikiHelp: Optional[str] = "Plugins"
    helpUrl: Optional[str] = ""
    help: Optional[str] = ""
    defaultPluginConfig: bool = True
    math: bool = False
    pluginType: Optional[str] = "python.PluginDemo"
    initPluginJS: Optional[str] = CONF_INIT_JS
    javaScript: bool = True
    javascriptLibraries: Optional[List[JavascriptLibrary]] = Field(default_factory=list)
    javascriptLibrariesLocal: Optional[List[JavascriptLibrary]] = Field(default_factory=list)
    inputElement: Optional[str] = "TextField"
    cacheable: bool = True
    useVars: bool = True
    useCVars: bool = True
    useVarsMaxima: bool = True
    useMVars: bool = True
    pluginServiceURL: Optional[str] = ""


class PluginGeneralInfoList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pluginInfos: Optional[List[PluginGeneralInfo]] = Field(default_factory=list)


class ImageInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: Optional[str] = ""
    pluginType: Optional[str] = ""
    filename: Optional[str] = ""
    url: Optional[str] = ""
    width: int = 0
    height: int = 0
    unit: Optional[str] = "none"     # Einheit none,px,pt,cm,percent,em
    imageWidth: int = 100
    style: Optional[str] = ""
    alternate: Optional[str] = "plugin image"
    title: Optional[str] = ""
    lifetime: int = 0


class ImageUrlDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    imageUrl: Optional[str] = None
    imageInfo: Optional[ImageInfoDto] = None
    error: Optional[str] = None


class ImageBase64Dto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    base64Image: Optional[str] = None
    imageInfoDto: Optional[ImageInfoDto] = None
    error: Optional[str] = None


class CalcErgebnisDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    string: Optional[str] = None
    json_value: Optional[str] = Field(default=None, alias="json")
    type: Optional[str] = "STRING"


class ToleranzDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    toleranz: float = 1e-10
    mode: Optional[str] = "RELATIV"


class CalcParamsDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    optmode: Optional[str] = None
    toleranz: Optional[ToleranzDto] = None
    rekursiv: bool = True
    symbolicMode: bool = False
    showpotenz: Optional[str] = "AUTO"           # AUTO, POW, SQRT
    calcmode: Optional[str] = "MAXIMA"           # MAXIMA, LOESUNG, ERGEBNIS, VIEW
    ausmultiplizieren: bool = True
    herausheben: bool = True
    forceOpt: bool = True


class VarDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    calcErgebnisDto: Optional[CalcErgebnisDto] = None
    ze: Optional[str] = None
    cp: Optional[CalcParamsDto] = None


class VarHashDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    vars: Optional[Dict[str, VarDto]] = Field(default_factory=dict)

    def to_java_string(self) -> str:
        parts = []
        if self.calcErgebnisDto is not None:
            parts.append(f"calcErgebnisDto={self.calcErgebnisDto}")
        if self.ze is not None:
            parts.append(f"ze={self.ze}")
        if self.cp is not None:
            parts.append(f"cp={self.cp}")
        return ",".join(parts)

class PluginSubQuestionDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None           # Name der SubQuestion
    points: float = 0.0                  # die erreichbare Punkteanzahl einer Teilfrage


class PluginQuestionDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int = 0
    name: Optional[str] = None
    maximaDefs: Optional[str] = None
    moodlemac: Optional[str] = None
    points: float = 0.0
    subQuestions: Optional[List[PluginSubQuestionDto]] = Field(default_factory=list)
    maxima: Optional[str] = None
    images: Optional[List[str]] = Field(default_factory=list)
    imagesContent: Optional[List[str]] = Field(default_factory=list)
    dsNr: int = 0
    vars: Optional[VarHashDto] = None
    cvars: Optional[VarHashDto] = None
    varsMaxima: Optional[VarHashDto] = None
    mvars: Optional[VarHashDto] = None


class PluginMaximaCalcModeDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    maxima: bool = False
    preCalc: bool = False


class PluginRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = None
    name: Optional[str] = ""
    config: Optional[str] = ""
    params: Optional[str] = ""
    q: Optional[PluginQuestionDto] = None
    pluginMaximaCalcMode: Optional[PluginMaximaCalcModeDto] = None


class PluginParserRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = ""
    name: Optional[str] = ""
    config: Optional[str] = ""
    vars: Optional[VarHashDto] = None
    cp: Optional[CalcParamsDto] = None
    p: Optional[List[CalcErgebnisDto]] = Field(default_factory=list)


class PluginEinheitRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = ""
    name: Optional[str] = ""
    config: Optional[str] = ""
    p: Optional[List[str]] = Field(default_factory=list)

class PluginAnswerDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ergebnis: Optional[CalcErgebnisDto] = None
    answerText: Optional[str] = ""
    ze: Optional[str] = ""

class PluginScoreInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schuelerErgebnis: Optional[CalcErgebnisDto] = None
    zielEinheit: Optional[str] = ""
    punkteIst: float = 0.0
    punkteSoll: float = 0.0
    status: Optional[str] = "FALSCH"    # NotScored,OK,FALSCH,TEILWEISE_OK,EINHEITENFEHLER,OK_Lehrer,FALSCH_Lehrer,TEILWEISE_OK_Lehrer,EINHEITENFEHLER_Lehrer,ANGABEFEHLER_EH,PARSERFEHLER_SYSTEM,NichtEntschieden,MEHRFACHANTWORT_OK,MEHRFACHANTWORT_OK_LEHRER,MEHRFACHANTWORT_TW_RICHTIG,MEHRFACHANTWORT_TW_RICHTIG_LEHRER
    htmlScoreInfo: Optional[str] = ""
    feedback: Optional[str] = ""

class PluginDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    imageUrl: Optional[str] = ""      # Url eines eingebetteten Bildes - meist base64 codiert
    pig: bool = False                 # True wenn das Plugin über ein PIG-Tag direkt in der Frage eingebunden ist
    result: bool = False              # True wenn Plugin in einer Subquestion definiert ist
    tagName: Optional[str] = ""       # Eindeutiger Bezeichner des PluginTags
    width: int = CONF_width           # Breite des Plugin-Bereiches in Pixel
    height: int = CONF_height          # Höhe des Plugin-Bereiches in Pixel
    params: Optional[Dict[str, str]] = Field(default_factory=dict)   # Parameter welche vom Plugin an Javascript weitergegeben werden sollen, wird von LeTTo nicht verwendet
    jsonData: Optional[str] = None    # JSON-String welcher vom Plugin an Javascript weitergegeben werden soll, wird von LeTTo nicht verwendet

class LoadPluginRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = None
    name: Optional[str] = ""
    config: Optional[str] = ""
    params: Optional[str] = ""
    q: Optional[PluginQuestionDto] = None
    nr: int = 0
    configurationID: Optional[str] = None


class PluginRenderLatexRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = None
    name: Optional[str] = ""
    config: Optional[str] = ""
    pluginDto: Optional[PluginDto] = None
    answer: Optional[str] = ""
    mode: Optional[str] = "default"


class PluginRenderResultRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = None
    name: Optional[str] = ""
    config: Optional[str] = ""
    tex: bool = False
    pluginDto: Optional[PluginDto] = None
    antwort: Optional[str] = ""
    toleranz: Optional[ToleranzDto] = None
    varsQuestion: Optional[VarHashDto] = None
    answerDto: Optional[PluginAnswerDto] = None
    grade: float = 1.0


class PluginRenderDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source: Optional[str] = ""
    images: Optional[Dict[str, str]] = Field(default_factory=dict)


class PluginScoreRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = None
    name: Optional[str] = ""
    config: Optional[str] = ""
    pluginDto: Optional[PluginDto] = None
    antwort: Optional[str] = ""
    toleranz: Optional[ToleranzDto] = None
    varsQuestion: Optional[VarHashDto] = None
    answerDto: Optional[PluginAnswerDto] = None
    grade: float = 1.0


class PluginAngabeRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = None
    name: Optional[str] = ""
    config: Optional[str] = ""
    text: Optional[str] = ""
    q: Optional[PluginQuestionDto] = None


class PluginUpdateJavascriptRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = ""            # Typ des Plugins
    name: Optional[str] = ""           # Name des Plugins in der Frage
    config: Optional[str] = ""         # Konfigurationsstring des Plugins
    pluginDef: Optional[str] = ""      # akt. Plugin-Definition
    jsResult: Optional[str] = ""       # Rückgabe von Javascript

class PluginDatasetDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = ""
    bereich: Optional[str] = ""
    einheit: Optional[str] = ""
    useTemplate: bool = False

class PluginDatasetListDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    datasets: Optional[List[PluginDatasetDto]] = Field(default_factory=list)

class PluginConfigurationInfoRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = None
    name: Optional[str] = ""
    config: Optional[str] = ""
    configurationID: Optional[str] = None
    timeout: int = 300


class PluginConfigurationInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    configurationID: Optional[str] = ""         # Konfigurations ID
    configurationMode: int = 0        # Konfigurations-Mode 0..String, 1..JSF, 2..Javascript, 3..Url
    useQuestion: bool = True          # Gibt an ob im Plugin für die Konfiguration die Frage benötigt wird
    useVars: bool = True              # Gibt an ob im Plugin für die Konfiguration der Vars Varhash benötigt wird
    useCVars: bool = True             # Gibt an ob im Plugin für die Konfiguration der cVars Varhash benötigt wird
    useMaximaVars: bool = True        # Gibt an ob im Plugin für die Konfiguration der MaximaVars Varhash benötigt wird
    useMVars: bool = True             # Gibt an ob im Plugin für die Konfiguration der MVars Varhash benötigt wird
    addDataSet: bool = False          # Gibt an, ob im Plugin-Konfig-Dialog Datensätze hinzugefügt werden können  => Button AddDataset in Fußzeile des umgebenden Dialogs, (nicht vom Plugin)
    calcMaxima: bool = False          # Gibt an ob im Plugin bei der Konfiguration die Maxima-Berechnung durchlaufen werden kann. => Button Maxima in Fußzeile des umgebenden Dialogs, (nicht vom Plugin)
    externUrl: bool = False           # Gibt an, ob das Plugin über den Browser direkt erreichbar ist
    javaScriptMethode: Optional[str] = None     # Java-Script-Methode, die beim Konfigurieren des Plugins aufgerufen wird.
    configurationUrl: Optional[str] = ""        # Konfigurations-URL für den Konfigurationsdialog im Mode CONFIGMODE_URL


class PluginConfigurationRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = ""
    configurationID: Optional[str] = ""

class PluginConfigDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = ""                                        # Typ des Plugins
    name: Optional[str] = ""                                       # Name des Plugins im Dialog
    config: Optional[str] = ""                                     # Konfigurationsstring
    tagName: Optional[str] = "plugintag"                           # Eindeutiger Bezeichner des PluginTags
    width: int = CONF_width                                        # Breite des Plugin-Bereiches in Pixel
    height: int = CONF_height                                      # Höhe des Plugin-Bereiches in Pixel
    configurationID: Optional[str] = ""                            # Configuration-ID
    errorMsg: Optional[str] = None                                 # Fehlermeldung wenn das DTO nicht korrekt erzeugt wurde
    pluginDto: Optional[PluginDto] = None                          # PluginDto für die Initialisierung des Plugins
    pluginDtoUri: Optional[str] = ""                               # Uri am Question-Service für das PluginDto
    pluginDtoToken: Optional[str] = ""                             # Token welcher an der pluginDtoUri benötigt wird
    params: Optional[Dict[str, Any]] = Field(default_factory=dict) # Parameter welche vom Plugin an Javascript weitergegeben werden sollen
    jsonData: Optional[str] = None                                 # JSON-String welcher vom Plugin an Javascript weitergegeben werden soll

class PluginSetConfigurationDataRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: Optional[str] = ""
    configurationID: Optional[str] = None
    configuration: Optional[str] = ""
    questionDto: Optional[PluginQuestionDto] = None


class AdminInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    applicationname: Optional[str] = CONF_APPLICATION_NAME
    pid: int = 0
    applicationhome: Optional[str] = ""
    startupDate: int = 0
    uptime: int = 0
    version: Optional[str] = "python"
    servername: Optional[str] = ""
    system: Optional[str] = ""
    encoding: Optional[str] = ""
    javaVersion: Optional[str] = ""
    ip: Optional[str] = ""
    dockerName: Optional[str] = ""
    uriIntern: Optional[str] = ""
    uriInternEnabled: bool = True
    uriExtern: Optional[str] = ""
    uriExternEnabled: bool = True


class ServiceInfoDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    serviceName: Optional[str] = CONF_APPLICATION_NAME
    version: Optional[str] = CONF_VERSION
    author: Optional[str] = "LeTTo"
    license: Optional[str] = ""
    endpoints: Optional[str] = ""
    jarfilename: Optional[str] = ""
    starttime: Optional[str] = ""
    adminInfoDto: Optional[AdminInfoDto] = None
    jarLibs: Optional[List[str]] = Field(default_factory=list)


# --------------------------
# Plugin: die eigentliche Pluginklasse
# --------------------------
class PluginDemo:
    VERSION = CONF_VERSION
    HELPFILES = CONF_HELPFILES
    JSLIBS = CONF_JSLIBS
    INIT_JS = CONF_INIT_JS
    CONFIG_JS = CONF_CONFIG_JS

    def __init__(self, name: str, params: str):
        self.name = name or ""
        self.config = params or ""
        # defaults
        self.imageWidthProzent = 100
        self.bgcolor = "white"
        self.configMessage = ""
        # configuration modes from Java PluginConfigurationInfoDto
        self.CONFIGMODE_STRING = 0
        self.CONFIGMODE_JSF = 1
        self.CONFIGMODE_JAVASCRIPT = 2
        self.CONFIGMODE_URL = 3
        self.configurationMode = self.CONFIGMODE_JAVASCRIPT

        # parse semicolon params like in Java
        for p in (self.config.split(";") if self.config else []):
            p = p.strip()
            if not p:
                continue
            m = re.match(r"^[wW](\d+)\s*$", p)
            if m:
                self.imageWidthProzent = max(1, min(100, int(m.group(1))))
                continue
            key = p.replace(" ", "")
            if key == "mode=iframe":
                self.configurationMode = self.CONFIGMODE_URL
            elif key == "mode=string":
                self.configurationMode = self.CONFIGMODE_STRING
            elif key == "mode=jsf":
                self.configurationMode = self.CONFIGMODE_JSF
            elif key == "mode=js":
                self.configurationMode = self.CONFIGMODE_JAVASCRIPT
            else:
                self._parse_param(p)

    def _config_message(self, msg: str) -> None:
        self.configMessage = (self.configMessage + ", " if self.configMessage else "") + msg

    def _parse_param(self, p: str) -> None:
        # bgcolor=...
        m = re.match(r"^\s*bgcolor\s*=\s*([a-zA-Z]+)\s*$", p)
        if m:
            color = m.group(1).lower()
            allowed = {"white", "black", "red", "green", "blue", "yellow"}
            if color in allowed:
                self.bgcolor = color
            else:
                self._config_message(f"bgcolor {color} not allowed")

    def get_help(self) -> str:
        parts: List[str] = []
        for hf in self.HELPFILES or []:
            msg = read_resource_text(hf)
            if msg:
                parts.append(msg)
        help_text = "".join(parts).strip()
        if not help_text:
            help_text = "<h1>Plugin-Template</h1>Help ist noch nicht konfiguriert!"
        return help_text

    def plugin_general_info(self, typ: str) -> PluginGeneralInfo:
        # local JS libs are embedded as content in javascriptLibrariesLocal
        libs_local = []
        for lib in self.JSLIBS:
            libs_local.append(JavascriptLibrary(name=lib, local="JAVASCRIPT", js_code=read_resource_text(lib)))
        # help_text = read_resource_text(self.HELPFILES[0])
        help_text = self.get_help()
        return PluginGeneralInfo(
            typ=typ,
            version=self.VERSION,
            wikiHelp="Plugins",
            help=help_text,
            pluginType="python.PluginDemo",
            initPluginJS=self.INIT_JS,
            javaScript=True,
            javascriptLibrariesLocal=libs_local
        )

    def get_image_base64(self, params: str, q: Optional[PluginQuestionDto]) -> ImageBase64Dto:
        # determine a "correct" time from q.vars if present, else use current system time (HH:MM)
        hh = datetime.now().hour
        mm = datetime.now().minute
        # allow override in params: time=HH:MM
        m = re.search(r"time\s*=\s*([0-9]{1,2}:[0-9]{1,2})", params or "")
        if m:
            try:
                hh_s, mm_s = m.group(1).split(":")
                hh = int(hh_s) % 24
                mm = int(mm_s) % 60
            except Exception:
                pass
        png = draw_clock_png(hh, mm, 320, bgcolor=self.bgcolor)
        return ImageBase64Dto(base64Image=png_b64(png), imageInfoDto=ImageInfoDto(filename="", url=""), error=self.configMessage)

    def get_html(self, params: str, q: Optional[PluginQuestionDto]) -> str:
        # keep it simple: LeTTo JS renders the image from PluginDto; still return a helpful HTML snippet
        return (
            '<div class="letto-plugin-uhr">'
            '<div class="letto-plugin-uhr-hint">Gib die Zeit im Format HH:MM ein.</div>'
            '</div>'
        )

    def get_angabe(self) -> str:
        return "Stelle die Uhr ab und gib die Zeit im Format HH:MM ein."

    def score(self, antwort: str, toleranz: Optional[ToleranzDto], answerDto: Optional[PluginAnswerDto],
              grade: float) -> PluginScoreInfoDto:
        ze = answerDto.ze if answerDto else ""
        correct_text = answerDto.answerText if answerDto else ""
        # default result = wrong
        info = PluginScoreInfoDto(
            schuelerErgebnis=CalcErgebnisDto(string=antwort),
            zielEinheit=ze,
            punkteIst=0.0,
            punkteSoll=float(grade),
            status="FALSCH",
            htmlScoreInfo=f"Wert:{antwort}",
            feedback=""
        )
        try:
            richtig = parse_time_seconds(correct_text or "")
            eingabe = parse_time_seconds(antwort or "")
            if toleranz is not None:
                t: float = float(toleranz.toleranz)
                mode: str = toleranz.mode or "RELATIV"
            else:
                t = 1e-10
                mode = "RELATIV"
            if equals_with_tolerance(richtig, eingabe, t, mode  or ""):
                info.punkteIst  = float(grade)
                info.status  = "OK"
        except ValueError:
            pass
        return info


# --------------------------
# Plugin registry (like StartupConfiguration.registerPlugin)
# --------------------------
REGISTERED_PLUGINS: Dict[str, str] = {
    CONF_PLUGIN: "Plugin Python",
}

def create_plugin(typ: str, name: str, params: str) -> Optional[PluginDemo]:
    if typ == CONF_PLUGIN:
        return PluginDemo(name, params)
    return None


def _build_service_base_urls() -> dict:
    """
    Erzeugt die öffentlichen URLs, unter denen das Setup dieses Service erreicht.
    PLUGIN_PUBLIC_URL muss die aus dem Docker-Netz erreichbare URL sein,
    z.B. http://pluginuhr-python:8080
    """
    base = LETTO_PLUGIN_URI_INTERN.rstrip("/")
    return {
        "root": base,
        "ping": f"{base}/ping",
        "pluginlist": f"{base}/open/pluginlist",
        "generalinfolist": f"{base}/open/generalinfolist",
        "generalinfo": f"{base}/open/generalinfo",
        "reloadplugindto": f"{base}{CONF_STANDARD_SERVICEPATH}/api/open/reloadplugindto",
        "info": f"{base}/info",
    }


async def _wait_until_service_is_ready() -> dict:
    """
    Wartet, bis das Service von außen wirklich erreichbar ist.
    Das Setup ruft direkt nach der Registrierung synchron weitere Endpoints auf.
    """
    urls = _build_service_base_urls()

    async with httpx.AsyncClient(timeout=3.0) as client:
        for attempt in range(1, PLUGIN_REGISTER_RETRIES + 1):
            try:
                ping_ok = (await client.get(urls["ping"])).status_code == 200
                pluginlist_ok = (await client.get(urls["pluginlist"])).status_code == 200
                generalinfolist_ok = (await client.get(urls["generalinfolist"])).status_code == 200
                generalinfo_ok = (
                                     await client.post(
                                         urls["generalinfo"],
                                         content="Uhr",
                                         headers={"Content-Type": "text/plain; charset=utf-8"},
                                     )
                                 ).status_code == 200

                if ping_ok and pluginlist_ok and generalinfolist_ok and generalinfo_ok:
                    logger.info("Service ist vollständig erreichbar und bereit für Setup-Registrierung")
                    return urls
            except Exception as ex:
                logger.info("Service noch nicht bereit (%s/%s): %s", attempt, PLUGIN_REGISTER_RETRIES, ex)

            await asyncio.sleep(PLUGIN_REGISTER_DELAY_SECONDS)

    raise RuntimeError("Service wurde vor der Registrierung nicht rechtzeitig erreichbar")


# --------------------------
# Plugin am Setup registrieren
# --------------------------
SERVICE_START_TIME = int(time.time())  # entspricht System.currentTimeMillis()/1000

def now_time_int() -> int:
    return int(time.time())

def now_time_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def _build_registration_payload(urls: dict, info: dict) -> dict:
    last_registration_time = now_time_int()
    htmlServiceStart_time = datetime.fromtimestamp(SERVICE_START_TIME).strftime("%d.%m.%Y %H:%M:%S")
    htmlLastRegistration_time = now_time_str()
    return {
        "name": CONF_PLUGIN_NAME,                # Name des Services
        "version": CONF_VERSION,                 # Version des Services
        "author": CONF_PLUGIN_AUTHOR,            # Information über den Autor des Services
        "license": CONF_PLUGIN_LICENSE,          # Information über die Lizenz des Services
        "bs": info.get("bs", ""),    # Betriebssystem auf dem das Service läuft
        "ip": info.get("ip", ""),    # IP des Services
        "encoding": "UTF-8",                     # Zeichen-Encoding
        "programmingLanguage": "python",         # Programmiersprache in der das Service Programmiert wurde
        "nwLettoAddress": NW_LETTO_ADDRESS,
        # Adresse innerhalb des Docker-Netzwerkes nw-letto, wenn das Service dort direkt erreichbar ist
        # Name des Docker-Containers, dieser muss eindeutig sein!!
        # Bei externen Services auf anderen Servcern gibt es keinen dockerName, dann muss die externe URI eindeutig sein
        "dockerName": DOCKER_CONTAINER_NAME,
        # interne URI mit der auf das Service ohne Authentifizierung zugegriffen werden kann.
        # die URI muss protokoll://adresse:port/basisendpunkt enthalten woran dann die Standard-Plugin-Endpoints angehängt werden.
        # Ist die uriIntern nicht gesetzt dann wird wenn extern=True ist auf der uriExtern verbunden.
        # Läuft das Service also auf einem Fremdserver muss Benutzername und Passwort angegeben sein um sich am Fremdserver zu authentifizieren oder alle Endpunkte müssen offen sein.
        "uriIntern": LETTO_PLUGIN_URI_INTERN + "/open",
        "extern": False,     # Service ist von Extern (Browser) direkt erreichbar
        # externe URI mit der vom Browser auf das Service zugegriffen werden kann (wenn extern=true)
        # Hier muss die gesamte absolute Basis-URI angegeben werden unter der die Plugin-Endpoints liegen
        "uriExtern": LETTO_PLUGIN_URI_EXTERN,
        "plugin": True,      # Gibt an ob es sich bei dem Service um ein Plugin handelt
        "scalable": False,   # Gibt an ob das Service skalierbar (mehrfach vorkommen kann) ist
        "stateless": True,   # Gibt an ob das Service nur Stateless-Endpoints hat
        "username": "",      # Benutzername wenn das Service mit einer User-Authentifizierung am Plugin anmelden muss
        "password": "",      # Passwort wenn das Service mit einer User-Authentifizierung am Plugin anmelden muss
        "usePluginToken": False,
        # Wenn hier True steht, dann muss für das Plugin ein Token verwendet werden, der in der Schule gespeichert ist. Dieser Token muss für die Authentifizierung am Plugin verwendet werden. - Ist noch nicht implementiert.
        "serviceStartTime": SERVICE_START_TIME,  # Datum und Uhrzeit an der das Service gestartet wurde als DateInteger
        "lastRegistrationTime": last_registration_time,  # Datum und Uhrzeit der letzten Service-Registratur
        "params": {},  # zusätzliche nicht weiter definierte Parameter des Plugins
        "htmlServiceStartTime": htmlServiceStart_time,
        "htmlLastRegistrationTime": htmlLastRegistration_time
    }


async def register_plugin_in_setup() -> None:
    logger.info("waiting for registration process!")
    if not PLUGIN_REGISTER_ON_READY:
        logger.info("PLUGIN_REGISTER_ON_READY=false -> keine Registrierung")
        return

    if not LETTO_SETUP_URI:
        logger.warning("letto_setup_uri/LETTO_SETUP_URI ist nicht gesetzt -> Registrierung übersprungen")
        return

    urls = await _wait_until_service_is_ready()
    systeminfo = get_system_info()
    payload = _build_registration_payload(urls, systeminfo)
    register_url = f"{LETTO_SETUP_URI}{SETUP_ENDPOINT_REGISTER}"
    auth = httpx.BasicAuth(LETTO_SETUP_USER, LETTO_SETUP_PASSWORD)

    logger.info("trying to register plugin: %s", register_url)
    async with httpx.AsyncClient(timeout=10.0, auth=auth) as client:
        for attempt in range(1, PLUGIN_REGISTER_RETRIES + 1):
            try:
                response = await client.post(register_url, json=payload)
                if 200 <= response.status_code < 300:
                    logger.info("Plugin erfolgreich beim Setup registriert: %s", register_url)
                    return

                logger.warning(
                    "Registrierung fehlgeschlagen (%s/%s), HTTP %s: %s",
                    attempt,
                    PLUGIN_REGISTER_RETRIES,
                    response.status_code,
                    response.text,
                )
            except Exception as ex:
                logger.warning(
                    "Fehler bei Registrierung (%s/%s): %s",
                    attempt,
                    PLUGIN_REGISTER_RETRIES,
                    ex,
                )

            await asyncio.sleep(PLUGIN_REGISTER_DELAY_SECONDS)

    raise RuntimeError("Plugin konnte nicht beim Setup registriert werden")

# ------------------------------------------
# Zustandsverarbeitung für die Konfiguration
# ------------------------------------------
@dataclass
class PluginConfigurationState:
    configurationID: str                                                         # Konfigurations ID
    typ: str = ""                                                                # Typ des Plugins
    name: str = ""                                                               # Name des Plugins
    config: str = ""                                                             # Configurationsstring des Plugins
    pluginDemo: Optional[PluginDemo] = None                                      # Plugin das gerade bearbeitet wird
    pluginConfigurationInfoDto: Optional[PluginConfigurationInfoDto] = None      # Plugin Configurations-Information
    pluginConfigDto: Optional[PluginConfigDto] = None                            # PluginConfigDto welches aktuell gültig ist
    questionDto: Optional[PluginQuestionDto] = None                              # PluginQuestionDto der Frage welche zu dem Plugin gehört
    timeout: int = 300
    lastAccessTime: int = 0

    def touch(self) -> None:
        self.lastAccessTime = int(time.time())

    def is_expired(self) -> bool:
        if self.timeout <= 0:
            return False
        return (int(time.time()) - self.lastAccessTime) > self.timeout

CONFIG_STATES: Dict[str, PluginConfigurationState] = {}

def cleanup_configuration_states() -> None:
    expired_ids = [cid for cid, state in CONFIG_STATES.items() if state.is_expired()]
    for cid in expired_ids:
        del CONFIG_STATES[cid]


def get_configuration_state(configuration_id: Optional[str]) -> Optional[PluginConfigurationState]:
    if not configuration_id:
        return None

    cleanup_configuration_states()
    state = CONFIG_STATES.get(configuration_id)
    if not state:
        return None

    if state.is_expired():
        del CONFIG_STATES[configuration_id]
        return None

    state.touch()
    return state

def create_or_update_configuration_state(
    configuration_id: str,
    typ: str = "",
    name: str = "",
    config: str = "",
    plugin_Demo: Optional[PluginDemo] = None,
    question_dto: Optional[PluginQuestionDto] = None,
    timeout: int = 300,
) -> PluginConfigurationState:
    cleanup_configuration_states()

    state = CONFIG_STATES.get(configuration_id)

    if state is None:
        state = PluginConfigurationState(
            configurationID=configuration_id,
            typ=typ or "",
            name=name or "",
            config=config or "",
            pluginDemo = plugin_Demo,
            timeout=timeout,
            lastAccessTime=int(time.time()),
        )
        CONFIG_STATES[configuration_id] = state
    if typ is not None:
        state.typ = typ or state.typ
    if name is not None:
        state.name = name or state.name
    if config is not None:
        state.config = config
    if plugin_Demo is not None:
        state.pluginDemo = plugin_Demo
    if question_dto is not None:
        state.questionDto = question_dto
    if timeout:
        state.timeout = timeout

    if state.pluginConfigDto is None:
        state.pluginConfigDto = PluginConfigDto()

    state.pluginConfigDto.configurationID = configuration_id
    state.pluginConfigDto.typ = state.typ
    state.pluginConfigDto.name = state.name
    state.pluginConfigDto.config = state.config
    state.pluginConfigDto.tagName = state.name or "plugintag"
    state.pluginConfigDto.pluginDtoUri = LETTO_PLUGIN_URI_EXTERN + EXTERN_OPEN + "/reloadplugindto"
    state.pluginConfigDto.pluginDtoToken = ""

    if state.pluginConfigDto.params is None:
        state.pluginConfigDto.params = {}

    state.pluginConfigDto.params["config"] = state.config

    if state.pluginDemo is not None:
        state.pluginConfigDto.params["help"] = state.pluginDemo.get_help()

        state.pluginConfigurationInfoDto = PluginConfigurationInfoDto(
            configurationID=configuration_id,
            configurationMode=state.pluginDemo.configurationMode,
            useQuestion=CONF_useQuestion,
            useVars=CONF_useVars,
            useCVars=CONF_useCVars,
            useMaximaVars=CONF_useMaximaVars,
            useMVars=CONF_useMVars,
            addDataSet=CONF_addDataSet,
            calcMaxima=CONF_calcMaxima,
            externUrl=CONF_externUrl,
            javaScriptMethode="configPlugin",
            configurationUrl=LETTO_PLUGIN_URI_EXTERN or "",
        )

    if state.questionDto is not None:
        state.pluginConfigDto.params["vars"] = (
            state.questionDto.vars.to_java_string()
            if state.questionDto.vars is not None
            else "null"
        )

    state.touch()
    return state


# --------------------------
# FastAPI app
# --------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _registration_task
    sync_resources_for_webserver()

    if PLUGIN_REGISTER_ON_READY:
        _registration_task = asyncio.create_task(register_plugin_in_setup())

    yield


app = FastAPI(
    title="LeTTo Plugin Python",
    version=CONF_VERSION,
    lifespan=lifespan,
)


def mount_internal_open(router_prefix: str) -> APIRouter:
    r = APIRouter(prefix=router_prefix)

    @r.get("/pluginlist")
    def plugin_list():
        return list(REGISTERED_PLUGINS.keys())

    @r.get("/generalinfolist", response_model=PluginGeneralInfoList)
    def general_info_list():
        lst = [create_plugin(t, "", "").plugin_general_info(t) for t in REGISTERED_PLUGINS.keys()]
        return PluginGeneralInfoList(pluginInfos=lst)

    @r.post("/generalinfo", response_model=PluginGeneralInfo)
    def general_info(plugintyp: str = Body(..., embed=False)):
        pi = create_plugin(plugintyp, "", "")
        if not pi:
            return PluginGeneralInfo(typ=plugintyp)
        return pi.plugin_general_info(plugintyp)

    @r.post("/gethtml", response_class=PlainTextResponse)
    def get_html(req: PluginRequestDto):
        pi = create_plugin(req.typ or "", req.name or "", req.config or "")
        return "" if not pi else pi.get_html(req.params or "", req.q)

    @r.post("/angabe", response_class=PlainTextResponse)
    def get_angabe(req: PluginRequestDto):
        pi = create_plugin(req.typ or "", req.name or "", req.config or "")
        return "" if not pi else pi.get_angabe()

    @r.post("/generatedatasets", response_model=PluginDatasetListDto)
    def generate_datasets(req: PluginRequestDto):
        return PluginDatasetListDto(datasets=[])

    @r.post("/maxima", response_class=PlainTextResponse)
    def maxima(req: PluginRequestDto):
        return ""

    @r.post("/image", response_model=ImageBase64Dto)
    def image(req: PluginRequestDto):
        pi = create_plugin(req.typ or "", req.name or "", req.config or "")
        return ImageBase64Dto(error="unknown plugin") if not pi else pi.get_image_base64(req.params or "", req.q)

    @r.post("/imagetemplates")
    def image_templates(req: PluginRequestDto):
        # PluginUhr.getImageTemplates returns Vector<String[]>
        return [["default", "[PIG PluginVomTester \"\"]","Uhrblatt"]]

    @r.post("/parserplugin", response_model=CalcErgebnisDto)
    def parser_plugin(req: PluginParserRequestDto):
        # Java returns null; keep null-ish
        return CalcErgebnisDto(string=None, type="STRING")

    @r.post("/parserplugineinheit", response_class=PlainTextResponse)
    def parser_plugin_einheit(req: PluginEinheitRequestDto):
        return ""

    @r.post("/score", response_model=PluginScoreInfoDto)
    def score(req: PluginScoreRequestDto):
        pi = create_plugin(req.typ or "", req.name or "", req.config or "")
        if not pi:
            return PluginScoreInfoDto()
        return pi.score(req.antwort or "", req.toleranz, req.answerDto, req.grade)

    @r.post("/getvars")
    def get_vars(req: PluginRequestDto):
        # PluginUhr.getVars returns Vector<String> empty
        return []

    @r.post("/modifyangabe", response_class=PlainTextResponse)
    def modify_angabe(req: PluginAngabeRequestDto):
        return req.text

    @r.post("/modifyangabetextkomplett", response_class=PlainTextResponse)
    def modify_angabe_textkomplett(req: PluginAngabeRequestDto):
        return req.text

    @r.post("/updatepluginstringjavascript", response_class=PlainTextResponse)
    def update_pluginstring_javascript(req: PluginUpdateJavascriptRequestDto):
        return req.pluginstring

    @r.post("/loadplugindto", response_model=PluginDto)
    def load_plugin_dto(req: LoadPluginRequestDto):
        pi = create_plugin(req.typ or "", req.name or "", req.config or "")
        if not pi:
            return PluginDto()
        # Mimic Java PluginDto constructor behavior: embed image (base64) as data url
        img = pi.get_image_base64(req.params or "", req.q)
        tag_name = f"{(req.q.id if req.q else 0)}_{req.name}_{req.nr}"
        return PluginDto(tagName=tag_name or "", imageUrl="data:image/png;base64," + (img.base64Image or ""), width=CONF_width, height=CONF_height)

    @r.post("/renderlatex", response_model=PluginRenderDto)
    def render_latex(req: PluginRenderLatexRequestDto):
        # keep empty like BasePlugin default
        return PluginRenderDto()

    @r.post("/renderpluginresult", response_model=PluginRenderDto)
    def render_plugin_result(req: PluginRenderResultRequestDto):
        # BasePlugin default: returns html showing image + input; we provide minimal html.
        pi = create_plugin(req.typ or "", req.name or "", req.config or "")
        if not pi:
            return PluginRenderDto(source="")
        if req.tex:
            return PluginRenderDto(source="")
        html = pi.get_html("", None)
        if req.antwort:
            html += f"<div>Wert:{req.antwort}</div>"
        return PluginRenderDto(source=html)

    # Liefert die Informationen welche notwendig sind um einen Konfigurationsdialog zu starten<br>
    # Ist die configurationID gesetzt wird eine Konfiguration gestartet und damit auch die restlichen Endpoints für die Konfiguration aktiviert.
    # LeTTo/Plugintester muss die configurationID für jeden Konfigurationsdialog eindeutig setzen, sie dient als Zustandsdefinition
    # Die Konfiguration ist NICHT stateless - der Zustand muss über die configurationID beidseitig gespeichert werden.
    # Nach längerer Untätigkeit sollte der Zustand der ConfigurationID wieder entfernt werden (z.B. über die timeout Angabe) damit es nicht zu einem Speicherüberlauf am Plugin-Service kommt<br>
    # Im Zustand müssen typ,name und config gespeichert werden<br>
    # Die Konfiguration kann über die configurationID jederzeit über open-Endpoints mit den restlichen Endpoints abgefragt und verändert werden<br>
    # Die configurationID wird also als Authentifizierung an den Open-Endpoints verwendet.<br>
    @r.post("/configurationinfo", response_model=PluginConfigurationInfoDto)
    def configuration_info(req: PluginConfigurationInfoRequestDto):
        pi = create_plugin(req.typ or "", req.name or "", req.config or "")
        if not pi:
            return PluginConfigurationInfoDto(
                configurationID=req.configurationID or "",
                configurationMode=0,
            )

        cid = req.configurationID or ""
        if cid:
            create_or_update_configuration_state(
                configuration_id=cid,
                typ=req.typ or "",
                name=req.name or "",
                config=req.config or "",
                plugin_Demo=pi,
                question_dto=None,
                timeout=req.timeout or 300,
            )

        return PluginConfigurationInfoDto(
            configurationID=cid,
            configurationMode=pi.configurationMode,
            useQuestion=True,
            useVars=True,
            useCVars=True,
            useMaximaVars=True,
            useMVars=True,
            addDataSet=False,
            calcMaxima=False,
            externUrl=False,
            javaScriptMethode=pi.CONFIG_JS,
            configurationUrl="", # URL mode not implemented here
        )

    @r.post("/setconfigurationdata", response_model=PluginConfigDto)
    def set_configuration_data(req: PluginSetConfigurationDataRequestDto):
        state = get_configuration_state(req.configurationID)
        if state is None:
            return PluginConfigDto(
                configurationID=req.configurationID or "",
                typ=req.typ or "",
                errorMsg="configurationID unknown or expired",
            )

        updated_state = create_or_update_configuration_state(
            configuration_id=state.configurationID,
            typ=req.typ or state.typ,
            name=state.name,
            config=req.configuration if req.configuration is not None else state.config,
            plugin_Demo=state.pluginDemo,
            question_dto=req.questionDto if req.questionDto is not None else state.questionDto,
            timeout=state.timeout,
        )

        updated_state.pluginConfigDto.pluginDto = load_plugin_dto(
            LoadPluginRequestDto(
                typ=updated_state.typ or "",
                name=updated_state.name or "",
                config=updated_state.config or "",
                q=updated_state.questionDto or None,
                configurationID=updated_state.configurationID,
            )
        )

        return updated_state.pluginConfigDto

    @r.post("/getconfiguration", response_class=PlainTextResponse)
    def get_configuration(req: PluginConfigurationRequestDto):
        state = get_configuration_state(req.configurationID)
        if state is None:
            return ""
        return state.config or ""

    @r.post("/reloadplugindto", response_model=PluginDto)
    def reload_plugin_dto(req: LoadPluginRequestDto):
        effective_typ = req.typ or ""
        effective_name = req.name or ""
        effective_config = req.config or ""
        effective_question = req.q

        if req.configurationID:
            state = get_configuration_state(req.configurationID)
            if state is not None:
                effective_typ = state.typ or effective_typ
                effective_name = state.name or effective_name
                effective_config = state.config or effective_config
                effective_question = state.questionDto or effective_question

        pi = create_plugin(effective_typ, effective_name, effective_config)
        if not pi:
            return PluginDto()

        img = pi.get_image_base64("", effective_question)
        tag_name = f"{(effective_question.id if effective_question else 0)}_{effective_name}_{req.nr or 0}"

        return PluginDto(
            tagName=tag_name or "",
            imageUrl="data:image/png;base64," + (img.base64Image or ""),
            width=CONF_width,
            height=CONF_height,
            params={"config": effective_config},
        )

    return r


# Info endpoints (both internal and external convenience)
@app.get(PING, response_class=PlainTextResponse)
def ping():
    return "pong"


PING_SERVICEPATH: str = f"{SERVICEPATH}{PING}"
@app.get(PING_SERVICEPATH, response_class=PlainTextResponse)
def ping_servicepath() -> str:
    return "pong"


@app.get(PINGOPEN, response_class=PlainTextResponse)
def ping_open():
    return "pong"


@app.get(INFO, response_model=ServiceInfoDTO)
def info():
    return ServiceInfoDTO(
        serviceName="pluginpython",
        version="python",
        author="LeTTo",
        starttime=datetime.now().isoformat(),
        adminInfoDto=AdminInfoDto(applicationname="pluginpython"),
    )


@app.get(INFO_OPEN, response_model=ServiceInfoDTO)
def info_open():
    return info()

@app.get("/version", response_class=PlainTextResponse)
def version():
    return CONF_VERSION

# Mount internal open API at /open and (for proxy setups) also under /pluginpython/open
app.include_router(mount_internal_open(LOCAL_API))
app.include_router(mount_internal_open(f"{SERVICEPATH}/open"))

# External open controller forwards to internal reload/pluginlist etc in Java; we expose the same subset
extern_router = APIRouter(prefix=EXTERN_OPEN)

@extern_router.get("/pluginlist")
def extern_pluginlist():
    return list(REGISTERED_PLUGINS.keys())


@extern_router.get("/generalinfolist", response_model=PluginGeneralInfoList)
def extern_generalinfolist():
    lst = [create_plugin(t, "", "").plugin_general_info(t) for t in REGISTERED_PLUGINS.keys()]
    return PluginGeneralInfoList(pluginInfos=lst)


@extern_router.post("/generalinfo", response_model=PluginGeneralInfo)
def extern_generalinfo(plugintyp: str = Body(..., embed=False)):
    pi = create_plugin(plugintyp, "", "")
    if not pi:
        return PluginGeneralInfo(typ=plugintyp)
    return pi.plugin_general_info(plugintyp)


@extern_router.post("/reloadplugindto", response_model=PluginDto)
def extern_reload(req: LoadPluginRequestDto):
    # Use the /open implementation semantics
    pi = create_plugin(req.typ or "", req.name or "", req.config or "")
    if not pi:
        return PluginDto()
    img = pi.get_image_base64(req.params or "", req.q)
    tag_name = f"{(req.q.id if req.q else 0)}_{req.name}_{req.nr}"
    return PluginDto(tagName=tag_name or "", imageUrl="data:image/png;base64," + (img.base64Image or ""), width=CONF_width, height=CONF_height)


app.include_router(extern_router)

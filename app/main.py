import os
import re
import math
import base64
import io
import asyncio
import logging
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

# --------------------------
# CONFIGURATION
# --------------------------
# Der Servicepath muss in der nginx-Konfiguration auf den Docker-Container des Plugins gesetzt werden -> siehe proxy/plugindemopython.conf
CONF_STANDARD_SERVICEPATH = "/plugindemopython"
# Name des Plugin-Service
CONF_APPLICATION_NAME = "plugindemopython"
# Name des Services wie es am Setup registriert wird
CONF_PLUGIN_NAME = "letto-plugindemopython"
# Author des Plugins
CONF_PLUGIN_AUTHOR = "LeTTo GmbH"
# Lizenz des Plugins
CONF_PLUGIN_LICENSE = "OpenSource"
# Name des Plugins wie es in Letto erscheint
CONF_PLUGIN = "UhrPy"
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

# ----------------------------------
# Environment aus der yml-Datei
# ----------------------------------
LETTO_SETUP_URI = os.getenv("letto_setup_uri", os.getenv("LETTO_SETUP_URI", "http://letto-setup.nw-letto:8096")).rstrip(
    "/")
LETTO_SETUP_USER = "user";
LETTO_SETUP_PASSWORD = os.getenv("letto_user_user_password", os.getenv("LETTO_USER_USER_PASSWORD", ""))
PLUGIN_ENDPOINT_NAME = os.getenv("PLUGIN_ENDPOINT_NAME", "plugindemo")
PLUGIN_REGISTER_ON_READY = os.getenv("PLUGIN_REGISTER_ON_READY", "true").lower() == "true"
PLUGIN_REGISTER_RETRIES = int(os.getenv("PLUGIN_REGISTER_RETRIES", "30"))
PLUGIN_REGISTER_DELAY_SECONDS = float(os.getenv("PLUGIN_REGISTER_DELAY_SECONDS", "1.0"))
NW_LETTO_ADDRESS = os.getenv("network_letto_address", os.getenv("NETWORK_LETTO_ADDRESS", "letto-plugindemopython"))
DOCKER_CONTAINER_NAME = os.getenv("docker_container_name", os.getenv("DOCKER_CONTAINER_NAME", "letto-plugindemopython"))
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
        h = float(m.group(1));
        mi = float(m.group(2))
        return h * 3600.0 + mi * 60.0
    m = re.match(r"^(\d+):(\d+):(\d+\.?\d*)$", s)
    if m:
        h = float(m.group(1));
        mi = float(m.group(2));
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
    library: str = ""
    name: str = ""
    globalName: str = ""
    local: str = "LOCAL"
    js_code: str = ""

class PluginGeneralInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str = ""
    version: str = "1.0"
    wikiHelp: str = "Plugins"
    helpUrl: str = ""
    help: str = ""
    defaultPluginConfig: bool = True
    math: bool = False
    pluginType: str = "python.PluginDemo"
    initPluginJS: str = CONF_INIT_JS
    javaScript: bool = True
    javascriptLibraries: List[JavascriptLibrary] = Field(default_factory=list)
    javascriptLibrariesLocal: List[JavascriptLibrary] = Field(default_factory=list)
    inputElement: str = "TextField"
    cacheable: bool = True
    useVars: bool = True
    useCVars: bool = True
    useVarsMaxima: bool = True
    useMVars: bool = True
    pluginServiceURL: str = ""


class PluginGeneralInfoList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pluginInfos: List[PluginGeneralInfo] = Field(default_factory=list)


class ImageInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: str = ""
    pluginType: str = ""
    filename: str = ""
    url: str = ""
    width: int = 0
    height: int = 0
    unit: str = "none"     # Einheit none,px,pt,cm,percent,em
    imageWidth: int = 100
    style: str = ""
    alternate: str = "plugin image"
    title: str = ""
    lifetime: int = 0




class ImageUrlDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    imageUrl: str = ""
    imageInfo: Optional[ImageInfoDto] = None
    error: str = ""


class ImageBase64Dto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    base64Image: str = ""
    imageInfoDto: Optional[ImageInfoDto] = None
    error: str = ""


class PluginQuestionDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int = 0
    vars: Optional[Dict[str, Any]] = None


class PluginRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    name: str = ""
    config: str = ""
    params: str = ""
    q: Optional[PluginQuestionDto] = None
    pluginMaximaCalcMode: Optional[Dict[str, Any]] = None


class PluginParserRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    params: List[str] = Field(default_factory=list)


class PluginEinheitRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    params: List[str] = Field(default_factory=list)


class CalcErgebnisDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    string: Optional[str] = None
    json: Optional[str] = None
    type: str = "STRING"


class PluginAnswerDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ergebnis: Optional[CalcErgebnisDto] = None
    answerText: str = ""
    ze: str = ""


class ToleranzDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    toleranz: float = 1e-10
    mode: str = "RELATIV"


class PluginScoreInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schuelerErgebnis: Optional[CalcErgebnisDto] = None
    zielEinheit: str = ""
    punkteIst: float = 0.0
    punkteSoll: float = 0.0
    status: str = "FALSCH"    # NotScored,OK,FALSCH,TEILWEISE_OK,EINHEITENFEHLER,OK_Lehrer,FALSCH_Lehrer,TEILWEISE_OK_Lehrer,EINHEITENFEHLER_Lehrer,ANGABEFEHLER_EH,PARSERFEHLER_SYSTEM,NichtEntschieden,MEHRFACHANTWORT_OK,MEHRFACHANTWORT_OK_LEHRER,MEHRFACHANTWORT_TW_RICHTIG,MEHRFACHANTWORT_TW_RICHTIG_LEHRER
    htmlScoreInfo: str = ""
    feedback: str = ""

class PluginDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    imageUrl: str = ""                # Url eines eingebetteten Bildes - meist base64 codiert
    pig: bool = False                 # True wenn das Plugin über ein PIG-Tag direkt in der Frage eingebunden ist
    result: bool = False              # True wenn Plugin in einer Subquestion definiert ist
    tagName: str = ""                 # Eindeutiger Bezeichner des PluginTags
    width: int = 500                  # Breite des Plugin-Bereiches in Pixel
    height: int = 500                 # Höhe des Plugin-Bereiches in Pixel
    params: Dict[str, str] = Field(default_factory=dict)   # Parameter welche vom Plugin an Javascript weitergegeben werden sollen, wird von LeTTo nicht verwendet
    jsonData: Optional[str] = None                         # JSON-String welcher vom Plugin an Javascript weitergegeben werden soll, wird von LeTTo nicht verwendet

class LoadPluginRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    name: str = ""
    config: str = ""
    params: str = ""
    q: Optional[PluginQuestionDto] = None
    nr: int = 0
    configurationID: Optional[str] = None


class PluginRenderLatexRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    name: str = ""
    config: str = ""
    pluginDto: Optional[PluginDto] = None
    answer: str = ""
    mode: str = "default"


class PluginRenderResultRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    name: str = ""
    config: str = ""
    tex: bool = False
    pluginDto: Optional[PluginDto] = None
    antwort: str = ""
    toleranz: Optional[ToleranzDto] = None
    varsQuestion: Optional[Dict[str, Any]] = None
    answerDto: Optional[PluginAnswerDto] = None
    grade: float = 1.0


class PluginRenderDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source: str = ""
    images: Dict[str, str] = Field(default_factory=dict)


class PluginScoreRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    name: str = ""
    config: str = ""
    pluginDto: Optional[PluginDto] = None
    antwort: str = ""
    toleranz: Optional[ToleranzDto] = None
    varsQuestion: Optional[Dict[str, Any]] = None
    answerDto: Optional[PluginAnswerDto] = None
    grade: float = 1.0


class PluginAngabeRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    name: str = ""
    config: str = ""
    text: str = ""
    q: Optional[PluginQuestionDto] = None


class PluginUpdateJavascriptRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pluginstring: str = ""
    data: str = ""

class PluginDatasetDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    bereich: str = ""
    einheit: str = ""
    useTemplate: bool = False

class PluginDatasetListDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    datasets: List[PluginDatasetDto] = Field(default_factory=list)

class PluginConfigurationInfoRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    name: str = ""
    config: str = ""
    configurationID: Optional[str] = None
    timeout: int = 300


class PluginConfigurationInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    configurationID: str = ""         # Konfigurations ID
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
    configurationUrl: str = ""                  # Konfigurations-URL für den Konfigurationsdialog im Mode CONFIGMODE_URL


class PluginConfigurationRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    configurationID: str


class PluginConfigDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str = ""                                        # Typ des Plugins
    name: str = ""                                       # Name des Plugins im Dialog
    config: str = ""                                     # Konfigurationsstring
    tagName: str = ""                                    # Eindeutiger Bezeichner des PluginTags
    width: int = 500                                     # Breite des Plugin-Bereiches in Pixel
    height: int = 500                                    # Höhe des Plugin-Bereiches in Pixel
    configurationID: str = ""                            # Configuration-ID
    errorMsg: str = ""                                   # Fehlermeldung wenn das DTO nicht korrekt erzeugt wurde
    pluginDto: Optional[PluginDto] = None                # PluginDto für die Initialisierung des Plugins
    pluginDtoUri: str = ""                               # Uri am Question-Service für das PluginDto
    pluginDtoToken: str = ""                             # Token welcher an der pluginDtoUri benötigt wird
    params: Dict[str, Any] = Field(default_factory=dict) # Parameter welche vom Plugin an Javascript weitergegeben werden sollen
    jsonData: str = ""                    # JSON-String welcher vom Plugin an Javascript weitergegeben werden soll

class PluginSetConfigurationDataRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    configurationID: str
    configuration: str = ""
    questionDto: Optional[PluginQuestionDto] = None


class AdminInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    applicationname: str = CONF_APPLICATION_NAME
    pid: int = 0
    applicationhome: str = ""
    startupDate: int = 0
    uptime: int = 0
    version: str = "python"
    servername: str = ""
    system: str = ""
    encoding: str = ""
    javaVersion: str = ""
    ip: str = ""
    dockerName: str = ""
    uriIntern: str = ""
    uriInternEnabled: bool = True
    uriExtern: str = ""
    uriExternEnabled: bool = True


class ServiceInfoDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    serviceName: str = CONF_APPLICATION_NAME
    version: str = CONF_VERSION
    author: str = "LeTTo"
    license: str = ""
    endpoints: str = ""
    jarfilename: str = ""
    starttime: str = ""
    adminInfoDto: Optional[AdminInfoDto] = None
    jarLibs: List[str] = Field(default_factory=list)


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

    def plugin_general_info(self, typ: str) -> PluginGeneralInfo:
        # local JS libs are embedded as content in javascriptLibrariesLocal
        libs_local = []
        for lib in self.JSLIBS:
            libs_local.append(JavascriptLibrary(name=lib, local="JAVASCRIPT", js_code=read_resource_text(lib)))
        help_text = read_resource_text(self.HELPFILES[0])
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
            richtig = parse_time_seconds(correct_text)
            eingabe = parse_time_seconds(antwort)
            t = toleranz.toleranz if toleranz else 1e-10
            mode = (toleranz.mode if toleranz else "RELATIV")
            if equals_with_tolerance(richtig, eingabe, t, mode):
                info.score = float(grade)
                info.scoreMode = "OK"
        except Exception:
            pass
        return info


# --------------------------
# Plugin registry (like StartupConfiguration.registerPlugin)
# --------------------------
REGISTERED_PLUGINS: Dict[str, str] = {
    CONF_PLUGIN: "Plugin-Demo Python",
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
                logger.info("ping:"+ping_ok+" pinglist:"+pluginlist_ok+" generalinfolist:"+generalinfolist_ok+" generalinfo:"+generalinfo_ok)
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
        # Ist die uriIntern nicht gesetzt dann wird wenn extern=true ist auf der uriExtern verbunden.
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
        # Wenn hier true steht, dann muss für das Plugin ein Token verwendet werden, der in der Schule gespeichert ist. Dieser Token muss für die Authentifizierung am Plugin verwendet werden. - Ist noch nicht implementiert.
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


# --------------------------
# FastAPI app
# --------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _registration_task

    if PLUGIN_REGISTER_ON_READY:
        _registration_task = asyncio.create_task(register_plugin_in_setup())

    yield


app = FastAPI(
    title="LeTTo Plugin Demo (Python)",
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
        pi = create_plugin(req.typ, req.name, req.config)
        return "" if not pi else pi.get_html(req.params, req.q)

    @r.post("/angabe", response_class=PlainTextResponse)
    def get_angabe(req: PluginRequestDto):
        pi = create_plugin(req.typ, req.name, req.config)
        return "" if not pi else pi.get_angabe()

    @r.post("/generatedatasets", response_model=PluginDatasetListDto)
    def generate_datasets(req: PluginRequestDto):
        return PluginDatasetListDto(datasets=[])

    @r.post("/maxima", response_class=PlainTextResponse)
    def maxima(req: PluginRequestDto):
        return ""

    @r.post("/image", response_model=ImageBase64Dto)
    def image(req: PluginRequestDto):
        pi = create_plugin(req.typ, req.name, req.config)
        return ImageBase64Dto(error="unknown plugin") if not pi else pi.get_image_base64(req.params, req.q)

    @r.post("/imagetemplates")
    def image_templates(req: PluginRequestDto):
        # PluginUhr.getImageTemplates returns Vector<String[]>
        return [["default", "320x320"]]

    @r.post("/parserplugin", response_model=CalcErgebnisDto)
    def parser_plugin(req: PluginParserRequestDto):
        # Java returns null; keep null-ish
        return CalcErgebnisDto(string=None, type="STRING")

    @r.post("/parserplugineinheit", response_class=PlainTextResponse)
    def parser_plugin_einheit(req: PluginEinheitRequestDto):
        return ""

    @r.post("/score", response_model=PluginScoreInfoDto)
    def score(req: PluginScoreRequestDto):
        pi = create_plugin(req.typ, req.name, req.config)
        if not pi:
            return PluginScoreInfoDto()
        return pi.score(req.antwort, req.toleranz, req.answerDto, req.grade)

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
        pi = create_plugin(req.typ, req.name, req.config)
        if not pi:
            return PluginDto()
        # Mimic Java PluginDto constructor behavior: embed image (base64) as data url
        img = pi.get_image_base64(req.params, req.q)
        tag_name = f"{(req.q.id if req.q else 0)}_{req.name}_{req.nr}"
        return PluginDto(tagName=tag_name, imageUrl="data:image/png;base64," + img.base64Image, width=360, height=360)

    @r.post("/renderlatex", response_model=PluginRenderDto)
    def render_latex(req: PluginRenderLatexRequestDto):
        # keep empty like BasePlugin default
        return PluginRenderDto()

    @r.post("/renderpluginresult", response_model=PluginRenderDto)
    def render_plugin_result(req: PluginRenderResultRequestDto):
        # BasePlugin default: returns html showing image + input; we provide minimal html.
        pi = create_plugin(req.typ, req.name, req.config)
        if not pi:
            return PluginRenderDto(source="")
        if req.tex:
            return PluginRenderDto(source="")
        html = pi.get_html("", None)
        if req.antwort:
            html += f"<div>Wert:{req.antwort}</div>"
        return PluginRenderDto(source=html)

    # configuration endpoints (simplified)
    _CONFIG: Dict[str, str] = {}

    @r.post("/configurationinfo", response_model=PluginConfigurationInfoDto)
    def configuration_info(req: PluginConfigurationInfoRequestDto):
        pi = create_plugin(req.typ, req.name, req.config)
        if not pi:
            return PluginConfigurationInfoDto(configurationID=req.configurationID or "", configurationMode=0)
        cid = req.configurationID or ""
        if cid:
            _CONFIG.setdefault(cid, req.config or "")
        return PluginConfigurationInfoDto(
            configurationID=cid,
            configurationMode=pi.configurationMode,
            javaScriptMethode=pi.CONFIG_JS,
            configurationUrl="",  # URL mode not implemented here
        )

    @r.post("/setconfigurationdata", response_model=PluginConfigDto)
    def set_configuration_data(req: PluginSetConfigurationDataRequestDto):
        _CONFIG[req.configurationID] = req.configuration
        return PluginConfigDto(configurationID=req.configurationID, params={"config": req.configuration})

    @r.post("/getconfiguration", response_class=PlainTextResponse)
    def get_configuration(req: PluginConfigurationRequestDto):
        return _CONFIG.get(req.configurationID, "")

    @r.post("/reloadplugindto", response_model=PluginDto)
    def reload_plugin_dto(req: LoadPluginRequestDto):
        return load_plugin_dto(req)

    return r


# Info endpoints (both internal and external convenience)
@app.get(PING, response_class=PlainTextResponse)
def ping():
    return "pong"


@app.get(f"{SERVICEPATH}{PING}", response_class=PlainTextResponse)
def ping_servicepath():
    return "pong"


@app.get(PINGOPEN, response_class=PlainTextResponse)
def ping_open():
    return "pong"


@app.get(INFO, response_model=ServiceInfoDTO)
def info():
    return ServiceInfoDTO(
        serviceName="plugindemo",
        version="python",
        author="LeTTo",
        starttime=datetime.now().isoformat(),
        adminInfoDto=AdminInfoDto(applicationname="plugindemo"),
    )


@app.get(INFO_OPEN, response_model=ServiceInfoDTO)
def info_open():
    return info()


# Mount internal open API at /open and (for proxy setups) also under /plugindemo/open
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
    return PluginGeneralInfoList(list=lst)


@extern_router.post("/generalinfo", response_model=PluginGeneralInfo)
def extern_generalinfo(plugintyp: str = Body(..., embed=False)):
    pi = create_plugin(plugintyp, "", "")
    if not pi:
        return PluginGeneralInfo(typ=plugintyp)
    return pi.plugin_general_info(plugintyp)


@extern_router.post("/reloadplugindto", response_model=PluginDto)
def extern_reload(req: LoadPluginRequestDto):
    # Use the /open implementation semantics
    pi = create_plugin(req.typ, req.name, req.config)
    if not pi:
        return PluginDto()
    img = pi.get_image_base64(req.params, req.q)
    tag_name = f"{(req.q.id if req.q else 0)}_{req.name}_{req.nr}"
    return PluginDto(tagName=tag_name, imageUrl="data:image/png;base64," + img.base64Image, width=360, height=360)


app.include_router(extern_router)

import os
import re
import math
import base64
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, APIRouter, Body
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ConfigDict

from PIL import Image, ImageDraw

# --------------------------
# Paths (match Java project)
# --------------------------
SERVICEPATH = os.getenv("SERVICEPATH", "/plugindemo").rstrip("/")  # external prefix used by reverse proxy
LOCAL_API = "/open"                                               # internal api base
EXTERN_OPEN = f"{SERVICEPATH}/api/open"                           # external open base
PING = "/ping"
PINGOPEN = f"{SERVICEPATH}/open/ping"
INFO = "/info"
INFO_OPEN = f"{SERVICEPATH}/open/info"

# --------------------------
# Utilities
# --------------------------

def now_time_str() -> str:
    return datetime.now().strftime("%H:%M:%S")

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
        h = float(m.group(1)); mi = float(m.group(2))
        return h * 3600.0 + mi * 60.0
    m = re.match(r"^(\d+):(\d+):(\d+\.?\d*)$", s)
    if m:
        h = float(m.group(1)); mi = float(m.group(2)); sec = float(m.group(3))
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
    name: str = ""
    content: str = ""
    local: bool = True

class PluginGeneralInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str = ""
    version: str = "1.0"
    wikiHelp: str = "Plugins"
    helpUrl: str = ""
    help: str = ""
    defaultPluginConfig: bool = True
    math: bool = False
    pluginType: str = "python.PluginUhr"
    initPluginJS: str = "initPluginUhr"
    javaScript: bool = True
    javascriptLibraries: List[JavascriptLibrary] = Field(default_factory=list)
    javascriptLibrariesLocal: List[JavascriptLibrary] = Field(default_factory=list)
    inputElement: str = "TextField"
    cacheable: bool = True
    width: int = 360
    height: int = 360
    useQuestion: bool = True
    useVars: bool = True
    useCVars: bool = True
    useVarsMaxima: bool = True
    useMVars: bool = True
    pluginServiceURL: str = ""

class PluginGeneralInfoList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    list: List[PluginGeneralInfo] = Field(default_factory=list)

class ImageInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filename: str = ""
    url: str = ""

class ImageUrlDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    imageUrl: str = ""
    imageInfo: Optional[ImageInfoDto] = None
    error: str = ""

class ImageBase64Dto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    base64Image: str = ""
    width: int = 320
    height: int = 320
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
    value: Optional[str] = None
    unit: Optional[str] = None
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
    ergebnis: Optional[CalcErgebnisDto] = None
    ze: str = ""
    score: float = 0.0
    maxScore: float = 0.0
    scoreMode: str = "FALSCH"
    feedback: str = ""
    htmlScoreInfo: str = ""

class PluginDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tagName: str = ""
    imageUrl: str = ""
    width: int = 360
    height: int = 360
    params: Dict[str, str] = Field(default_factory=dict)
    jsonData: Optional[str] = None

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
    html: str = ""
    latex: str = ""
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

class PluginDatasetListDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    list: List[Any] = Field(default_factory=list)

class PluginConfigurationInfoRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    typ: str
    name: str = ""
    config: str = ""
    configurationID: Optional[str] = None
    timeout: int = 300

class PluginConfigurationInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    configurationID: str = ""
    configurationMode: int = 0
    useQuestion: bool = True
    useVars: bool = True
    useCVars: bool = True
    useVarsMaxima: bool = True
    useMVars: bool = True
    configString: str = ""
    calcMaxima: bool = False
    externUrl: bool = False
    javaScriptMethode: Optional[str] = None
    configurationUrl: str = ""

class PluginConfigurationRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    configurationID: str

class PluginConfigDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    configurationID: str = ""
    typ: str = ""
    name: str = ""
    config: str = ""
    pluginDto: Optional[PluginDto] = None
    tagName: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)

class PluginSetConfigurationDataRequestDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    configurationID: str
    configuration: str = ""
    questionDto: Optional[PluginQuestionDto] = None

class AdminInfoDto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    applicationname: str = "plugindemo"
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
    serviceName: str = "plugindemo"
    version: str = "python"
    author: str = "LeTTo"
    license: str = ""
    endpoints: str = ""
    jarfilename: str = ""
    starttime: str = ""
    adminInfoDto: Optional[AdminInfoDto] = None
    jarLibs: List[str] = Field(default_factory=list)

# --------------------------
# Plugin: Uhr
# --------------------------

class PluginUhr:
    """
    Python port of at.letto.plugins.plugin.uhr.PluginUhr (relevant behavior for REST endpoints).
    """
    VERSION = "1.0"
    HELPFILES = ["plugins/uhr/Uhr.html"]
    JSLIBS = ["plugins/uhr/uhrScript.js", "plugins/uhr/uhrConfigScript.js"]
    INIT_JS = "initPluginUhr"
    CONFIG_JS = "configPluginUhr"

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
            allowed = {"white","black","red","green","blue","yellow"}
            if color in allowed:
                self.bgcolor = color
            else:
                self._config_message(f"bgcolor {color} not allowed")

    def plugin_general_info(self, typ: str) -> PluginGeneralInfo:
        # local JS libs are embedded as content in javascriptLibrariesLocal
        libs_local = []
        for lib in self.JSLIBS:
            libs_local.append(JavascriptLibrary(name=lib, content=read_resource_text(lib), local=True))
        help_text = read_resource_text(self.HELPFILES[0])
        return PluginGeneralInfo(
            typ=typ,
            version=self.VERSION,
            wikiHelp="Plugins",
            help=help_text,
            pluginType="python.PluginUhr",
            initPluginJS=self.INIT_JS,
            javaScript=True,
            javascriptLibrariesLocal=libs_local,
            width=360,
            height=360,
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
        return ImageBase64Dto(base64Image=png_b64(png), width=320, height=320, error=self.configMessage)

    def get_html(self, params: str, q: Optional[PluginQuestionDto]) -> str:
        # keep it simple: LeTTo JS renders the image from PluginDto; still return a helpful HTML snippet
        return (
            '<div class="letto-plugin-uhr">'
            '<div class="letto-plugin-uhr-hint">Gib die Zeit im Format HH:MM ein.</div>'
            '</div>'
        )

    def get_angabe(self) -> str:
        return "Stelle die Uhr ab und gib die Zeit im Format HH:MM ein."

    def score(self, antwort: str, toleranz: Optional[ToleranzDto], answerDto: Optional[PluginAnswerDto], grade: float) -> PluginScoreInfoDto:
        ze = answerDto.ze if answerDto else ""
        correct_text = answerDto.answerText if answerDto else ""
        # default result = wrong
        info = PluginScoreInfoDto(
            ergebnis=CalcErgebnisDto(value=antwort, unit=None, type="STRING"),
            ze=ze,
            score=0.0,
            maxScore=float(grade),
            scoreMode="FALSCH",
            feedback="",
            htmlScoreInfo=f"Wert:{antwort}",
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
    "Uhr1": "PluginUhr",
}

def create_plugin(typ: str, name: str, params: str) -> Optional[PluginUhr]:
    if typ == "Uhr1":
        return PluginUhr(name, params)
    return None

# --------------------------
# FastAPI app
# --------------------------
app = FastAPI(title="plugindemo (python)", version="1.0-python")

def mount_internal_open(router_prefix: str) -> APIRouter:
    r = APIRouter(prefix=router_prefix)

    @r.get("/pluginlist")
    def plugin_list():
        return list(REGISTERED_PLUGINS.keys())

    @r.get("/generalinfolist", response_model=PluginGeneralInfoList)
    def general_info_list():
        lst = [create_plugin(t, "", "").plugin_general_info(t) for t in REGISTERED_PLUGINS.keys()]
        return PluginGeneralInfoList(list=lst)

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
        return PluginDatasetListDto(list=[])

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
        return CalcErgebnisDto(value=None, unit=None, type="STRING")

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
            return PluginRenderDto(html="")
        if req.tex:
            return PluginRenderDto(latex="")
        html = pi.get_html("", None)
        if req.antwort:
            html += f"<div>Wert:{req.antwort}</div>"
        return PluginRenderDto(html=html)

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

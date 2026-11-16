
function drawCanvas(plugin) {
    let clsName = "." + plugin.canvas;
    if ($(clsName).length>0)
        $(clsName).remove();

    if ($(clsName).length==0)
        $(plugin.divName).append( `       
            <div class="${plugin.canvas}" >
                <canvas class="${plugin.canvasLine} lettoimage" id="${plugin.canvasLine}"></canvas>
            </div>`
        );
}

/**
 * Je Plugin (plugin.name): Grafik wurde mit dem Button links oben vergrößert. Standard ist die kleinere
 * Darstellung. Der Zustand bleibt beim Neuaufbau der Frage (zB nach dem Prüfen) erhalten.
 */
var pluginImageLarge = {};

/**
 * Button links oben im Plugin: zwischen kleiner (Standard) und großer Darstellung umschalten
 * @param smallProzent  Bildbreite in Prozent für die kleine Darstellung
 */
function togglePluginImageSize(plugin, dto, smallProzent) {
    pluginImageLarge[plugin.name] = !pluginImageLarge[plugin.name];
    imagescale(plugin, dto, smallProzent);
}

/**
 * Bestimmt die Darstellungsgröße des Plugins:<br>
 * klein (Standard): scaleprozent der Containerbreite, aber nicht über die Originalgröße (mindestens 500px),
 * sonst wirkt die Grafik gezoomt und unscharf<br>
 * groß (Button links oben): volle Containerbreite
 */
function imagescale(plugin, dto, scaleprozent) {
    if (!scaleprozent || (!scaleprozent>1)) scaleprozent=100;
    const large = !!pluginImageLarge[plugin.name];
    if (large) scaleprozent = 100;
    try {
        plugin.iw = $(plugin.divName).innerWidth();
    } catch (e) { }
    if (!plugin.iw) plugin.iw=500;
    try {
        let iw1 = $(window).innerwidth();
        if (iw1!=null && iw1>0 && iw1<plugin.iw) plugin.iw = iw1;
    } catch (e) { }
    try {
        let iw2 = document.getElementById('questionForm').clientWidth;
        if (iw2!=null && iw2>0 && iw2<plugin.iw) plugin.iw = iw2;
    } catch (e) { }
    let iw = plugin.iw;
    if (iw<300) iw=300;
    plugin.scaleprozent = scaleprozent;
    plugin.scale  =  iw/dto.width*scaleprozent*0.01;
    if (!large) {
        // Kleine Darstellung: nicht über die Originalgröße (mindestens 500px) vergrößern
        const maxWidth = Math.max(dto.width || 0, 500);
        if (dto.width && dto.width * plugin.scale > maxWidth) plugin.scale = maxWidth / dto.width;
    }
    plugin.width  = dto.width  * plugin.scale;
    plugin.height = dto.height * plugin.scale;
    try {
        document.getElementById(plugin.canvasLine).setAttribute("width", plugin.width + "px");
        document.getElementById(plugin.canvasLine).setAttribute("height", plugin.height + "px");
    } catch (e) {

    }
}

function drawLine(ctx, x1, y1, x2, y2, width) {
    ctx.beginPath();
    ctx.moveTo(x1 , y1);
    ctx.lineTo(x2, y2);
    ctx.lineWidth = width;
    ctx.stroke();
}

function drawText(ctx, x, y, text) {
    ctx.font = '48px serif';
    ctx.lineWidth = 1;
    ctx.fillText(text, x, y);
}

function drawTextCS(ctx, x, y, text, size, color, hcenter, vcenter) {
    let oldfont = ctx.font;
    let oldfillstyle = ctx.fillStyle;
    ctx.font = size+'px serif';
    let tw = ctx.measureText(text).width;
    let th = size*0.7;
    if (hcenter) x-=tw/2;
    if (vcenter) y+=th/2;
    ctx.fillStyle = color;
    ctx.fillText(text, x,y);
    ctx.font = oldfont;
    ctx.fillStyle = oldfillstyle;
}

function drawZoomIcon(ctx, x, y, size) {
    let a=size/5.0;
    ctx.fillStyle = "lightgray";
    ctx.strokeStyle="black";
    ctx.fillRect(x,y,size,size);
    let w = size/10.0
    ctx.lineWidth = w;
    drawLine(ctx,x+a,y+a,x+a,y+2*a,w);
    drawLine(ctx,x+a,y+a,x+2*a,y+a,w);
    drawLine(ctx,x+4*a,y+a,x+4*a,y+2*a,w);
    drawLine(ctx,x+4*a,y+a,x+3*a,y+a,w);
    drawLine(ctx,x+a,y+4*a,x+a,y+3*a,w);
    drawLine(ctx,x+a,y+4*a,x+2*a,y+4*a,w);
    drawLine(ctx,x+4*a,y+4*a,x+4*a,y+3*a,w);
    drawLine(ctx,x+4*a,y+4*a,x+3*a,y+4*a,w);
}

function drawResetIcon(ctx, x, y, size) {
    let a=size/5.0;
    ctx.fillStyle = "lightgray";
    ctx.strokeStyle="black";
    ctx.fillRect(x,y,size,size);
    let w = size/10.0
    ctx.lineWidth = w;
    drawLine(ctx,x+a,y+a,x+4*a,y+4*a,w);
    drawLine(ctx,x+a,y+4*a,x+4*a,y+a,w);
}

function drawLine(ctx,x1,y1,x2,y2,width,color) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    ctx.stroke();
}

function drawArrow(ctx,x1,y1,x2,y2,width,color) {
    let dy = y2-y1;
    let dx = x2-x1;
    let arg = Math.atan2(dy,dx);
    let abs = Math.sqrt(dx*dx+dy*dy);
    ctx.translate(x1,y1);
    ctx.rotate(arg);
    ctx.beginPath();
    ctx.moveTo(0,0);
    ctx.lineTo(abs, 0);
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    ctx.stroke();
    let w = width*2
    if (abs>w*3) {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(abs,0);
        ctx.lineTo(abs - 3 * w, w);
        ctx.lineTo(abs - 3 * w, -w);
        ctx.closePath();
        ctx.fill();
    }
    ctx.rotate(-arg);
    ctx.translate(-x1,-y1);
}

function drawCircle(ctx,mx,my,r,width,color) {
    ctx.beginPath();
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    ctx.arc(mx,my,r,0,2*Math.PI);
    ctx.stroke();
}

function drawRect(ctx,x,y,w,h,width,color) {
    ctx.beginPath();
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    ctx.rect(x,y,w,h);
    ctx.stroke();
}

function fillRect(ctx,x,y,w,h,color) {
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.rect(x,y,w,h);
    ctx.fill();
}

function fillPolygon(ctx,x,y,anzahl,color) {
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.moveTo(x[0],y[0]);
    for (let i=1;i<anzahl;i++) {
        ctx.lineTo(x[i],y[i]);
    }
    ctx.closePath();
    ctx.fill();
}

function fillCircle(ctx,mx,my,r,color,transparency) {
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.arc(mx,my,r,0,2*Math.PI);
    let a = ctx.globalAlpha;
    if (transparency>=0)
        ctx.globalAlpha=transparency;
    ctx.fill();
    ctx.globalAlpha=a;
}

function openImageJS(imagepath) {
    var params = [
        { name : 'imgLink',  value : lnk }
    ];
    showImageDetail(params);
}

function vex(x,y) {
    if (x.length===2 && y.length===2) {
        return  x[0]*y[1]-x[1]*y[0];
    } else  if (x.length===3 && y.length===3) {
        return [x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]];
    } else return x*y;
}

function vin(x,y) {
    let e = 0;
    if (x.length=y.length) {
        for (let i=0;i<x.length;i++) {
            e += x[i]*y[i];
        }
        return e;
    }
}

function vabs(x) {
    let e=0;
    for (let i=0;i<x.length;i++) {
        e += x[i]*x[i];
    }
    return Math.sqrt(e);
}

function vneg(x) {
    let e=[];
    for (let i=0;i<x.length;i++) {
        e.push(-x[i]);
    }
    return e;
}

function vadd(x,y) {
    let e=[];
    for (let i=0;i<x.length;i++) {
        e.push(x[i]+y[i]);
    }
    return e;
}

function vsub(x,y) {
    return vadd(x,vneg(y));
}

function numberToString(number) {
    if (Math.abs(number)<1e-30) return "0.0";
    if (Math.abs(number)>1e5) return number.toExponential(4);
    if (Math.abs(number)<1e-2) return number.toExponential(4);
    if (Math.abs(number)>=1000) return number.toFixed(0);
    if (Math.abs(number)>=100) return number.toFixed(1);
    if (Math.abs(number)>=10) return number.toFixed(2);
    if (Math.abs(number)>=1) return number.toFixed(3);
    if (Math.abs(number)>=0.1) return number.toFixed(4);
    if (Math.abs(number)>=0.01) return number.toFixed(5);
    return number.toFixed(4);
}

function drawFadenkreuz(ctx,cx,cy,width,height,scale) {
    try {
        drawLine(ctx,0, cy, width, cy, 1/scale,"magenta");
        drawLine(ctx, cx, 0, cx, height, 1/scale,"magenta");

        ctx.font = '16px serif';
        let s = "(" + Math.trunc(cx) + "/" + Math.trunc(cy) + ")";
        let tw = ctx.measureText(s).width+8;
        let tws = tw/scale;
        let twh = 20/scale;
        let x = cx > width - tws ? cx - tws : cx + 2;
        let y = cy < twh ? cy + twh+4 : cy - 3;
        ctx.translate(x,y);
        ctx.transform(1/scale,0,0,1/scale,0,0);
        ctx.fillStyle = "white";
        ctx.fillRect(4,-20,tw,20);
        drawRect(ctx,4,-20,tw,20,1,"gray");
        ctx.fillStyle = "gray";
        ctx.fillText(s, 8, -5);
        ctx.transform(scale,0,0,scale,0,0);
        ctx.translate(-x,-y);
    } catch (e) {}
}

/**
 * Ersetzt alle Semikolons außerhalb von Anführungszeichen durch Zeilenumbrüche.
 * @param   str
 * @returns {string}
 */
function semicolonsToNewlinesOutsideQuotes(str) {
    let inQuotes = false;
    let out = "";
    for (let i = 0; i < str.length; i++) {
        const ch = str[i];
        const prev = i > 0 ? str[i - 1] : "";

        if (ch === '"' && prev !== '\\') { // nicht escaped
            inQuotes = !inQuotes;
            out += ch;
            continue;
        }

        out += (ch === ';' && !inQuotes) ? "\n" : ch;
    }
    return out;
}

/**
 * Ersetzt alle Zeilenumbrüche durch Semikolons.
 * @param   str
 * @returns {string}
 */
function newlinesToSemicolons(str) {
    return (str ?? "")
        .replace(/\r\n/g, "\n")
        .replace(/\r/g, "\n")
        .replace(/\n/g, ";");
}


/* ------------------------------------------------------------------------------------------------
 *  Umgebung der LeTTo-App für Plugins (window.LeTTo, gesetzt von PluginUmgebungService der App)
 *  Felder: theme, dunkel, kontrast, farben {text, hintergrund, primary, rahmen},
 *          pruefen, pruefenButtons, modus
 *  Bei jeder Änderung löst die App das Ereignis 'letto-umgebung' auf window aus.
 *  Außerhalb der App (z.B. main) fehlt window.LeTTo: dann liefern die Funktionen Standardwerte,
 *  pruefen ist dann null (unbekannt).
 * ------------------------------------------------------------------------------------------------ */

/** Aktuelle Umgebung der App (Design, Prüfen-Buttons) */
function lettoUmgebung() {
    const standard = {
        theme: 'default', dunkel: false, kontrast: false,
        farben: {text: '', hintergrund: '', primary: '', rahmen: ''},
        pruefen: null, pruefenButtons: [], modus: ''
    };
    try {
        if (window.LeTTo && typeof window.LeTTo === 'object') return Object.assign({}, standard, window.LeTTo);
    } catch (e) { }
    return standard;
}

/** Name des gewählten Designs (default, theme-soft-light, theme-soft-dark, theme-dark, theme-high-contrast) */
function lettoTheme() {
    return lettoUmgebung().theme;
}

/** true bei dunklem Design */
function lettoDunkel() {
    return lettoUmgebung().dunkel === true;
}

/** true, wenn zur aktuellen Frage ein Prüfen-Button angezeigt wird, null wenn unbekannt (außerhalb der App) */
function lettoPruefen() {
    return lettoUmgebung().pruefen;
}

/**
 * Funktion bei jeder Änderung der Umgebung (Design, Prüfen-Buttons) aufrufen
 * @param callback  Funktion mit der Umgebung als Parameter
 * @return Funktion zum Abmelden
 */
function lettoOnUmgebung(callback) {
    const f = (e) => { try { callback(e && e.detail ? e.detail : lettoUmgebung()); } catch (ex) { } };
    window.addEventListener('letto-umgebung', f);
    return () => window.removeEventListener('letto-umgebung', f);
}

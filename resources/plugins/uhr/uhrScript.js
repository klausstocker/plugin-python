try {
    $=jQuery;
} catch (e) {}

/* -----------------------------------------------------------------------------------------------
 *   Lädt das Plugin in ein vordefiniertes div-Element "#" + plugin.name+"_div"
 *   Das Ergebnis einer Eingabe muss in ein verstecktes Textfeld der Klasse "." + plugin.name + "_inp" übergeben werden
 *   LeTTo schickt als Parameter das PluginDto als json-String mit
 *   Ist aktiv auf false, dann darf keine Eingabe vorgenommen werden können (Lösungsansicht eines Tests in LeTTo)
 *   Um Konflikte zu vermeiden werden alle Funktionen als innere Funktionen dieser Funktion realisiert!
 * ----------------------------------------------------------------------------------------------- */
function initPluginUhr(dtoString, active) {
    let dto = JSON.parse(dtoString);
    dto.data = JSON.parse(dto.jsonData);
    let plugin = new Object();

    // -------------------------- Verbindungskonstante zu LeTTo ---------------------------------------
    // Div Element in das das Plugin gerendert werden muss - IST VON LETTO VORGEGEBEN und MUSS SO GESETZT SEIN
    const plugin_div = "#" + dto.tagName+"_div"
    // verstecktes Input-Element für die Schülereingabe im Plugins - IST VON LETTO VORGEGEBEN und MUSS SO GESETZT SEIN
    const plugin_inp = "." + dto.tagName + "_inp"
    // -----------------------------------------------------------------------------------------------

    plugin.name = dto.tagName;
    plugin.jimagepath = dto.imageUrl;
    plugin.width = dto.width;
    plugin.height = dto.height;
    plugin.canvas = "canvasContainer"+plugin.name;
    plugin.canvasLine = "canvasLine"+plugin.name;
    plugin.active = active;

    drawCanvas(plugin);

    document.getElementById(plugin.canvasLine).setAttribute("width",plugin.width+"px");
    document.getElementById(plugin.canvasLine).setAttribute("height",plugin.height+"px");
    initUhr();

    // Platziert das Plugin in ein vordefiniertes div-Element $(clsName) - hier als canvas Element
    function drawCanvas(plugin) {
        let clsName = "." + plugin.canvas;
        if ($(clsName).length>0)
            $(clsName).remove();

        if ($(clsName).length==0)
            $(plugin_div).append( `       
            <div class="${plugin.canvas}" >
                <canvas class="${plugin.canvasLine} lettoimage" id="${plugin.canvasLine}"></canvas>
            </div>`
            );
    }

    // Zeichnet das Plugin in das zuvor erstellte Canvas-Element
    function initUhr() {
        let imagepath = dto.imageUrl;
        let width  = plugin.width;
        let height = plugin.height;
        let xMiddle   = width/2;
        let yMiddle   = height/2;
        let radius    = Math.min(width,height)*0.48;
        let time_string = "";
        let cx = -1;
        let cy = -1;

        let img = new Image();
        let c = document.getElementById(plugin.canvasLine);

        // Hier wird die Antwort der Plugineingabe als String oder json gespeichert und dann an den Scorer übergeben
        let a = $(plugin_inp)[0];

        if (c==null || a==null) return;
        let angle = parseTime(a.value);
        let anglecursor = angle;
        if (isNaN(angle))
            angle=0;
        let ctx = c.getContext("2d");
        drawClockwithLineFromAngle(angle);

        //listener for clicks on svg, and therefore image
        if (plugin.active) {
            $("."+plugin.canvas).mousemove(function (e) {
                cx = e.pageX-getImgCoordinates().x;
                cy = e.pageY-getImgCoordinates().y;
                if (calcDistanceToCenter(e.pageX, e.pageY) <= radius) {
                    anglecursor = calcAngleToCenter(e.pageX, e.pageY);
                    drawClockwithLineFromAngle(angle, anglecursor);
                }
            });
            $("."+plugin.canvas).mousedown(function (e) {
                cx = e.pageX-getImgCoordinates().x;
                cy = e.pageY-getImgCoordinates().y;
                if (cx+20>width && cy+20>height) {
                    try {
                        openImg(imagepath);
                    } catch (ex) {}
                } else if (calcDistanceToCenter(e.pageX, e.pageY) <= radius) {
                    angle = calcAngleToCenter(e.pageX, e.pageY);
                    anglecursor=angle;
                    drawClockwithLineFromAngle(angle, anglecursor);
                    a.value = time_string;
                }
            });
            $("."+plugin.canvas).mouseleave(function (e) {
                cx = e.pageX-getImgCoordinates().x;
                cy = e.pageY-getImgCoordinates().y;
                anglecursor=null;
                drawClockwithLineFromAngle(angle, anglecursor);
            });
        }

        /**
         * Zeichnen der ganzen Uhr mit Zeiger, das Bild wird geladen,
         * wenn es noch nicht im Speicher ist
         * @param angle     Winkel des Zeigers der Uhr
         */
        function drawClockwithLineFromAngle(angle, anglecursor) {
            ctx.clearRect(0,0, width, height);
            if (img.loadComplete) {
                ctx.drawImage(img, 0, 0, width, height);
                draw(angle,anglecursor);
                return;
            }
            /*img.src = localMode ?
                "https://i.pinimg.com/originals/5b/68/be/5b68bede64bad2affa5c4b98f330f0ef.jpg" :
                "https://" + window.location.host + "/letto/javax.faces.resource/uhr.gif.jsf?ln=bitmaps";*/
            img.src = imagepath;
            img.onload = function(){
                img.loadComplete=true;
                ctx.drawImage(img, 0, 0, width, height);
                draw(angle,anglecursor);
            }
        }
        /**
         * Zeichnen des Zeigers der Uhr in einem bestimmten Winkel
         * @param angle     Winkel in Radiant
         */
        function draw(angle,anglecursor) {
            ctx.fillStyle = "lightgray";
            ctx.strokeStyle="black";
            ctx.fillRect(plugin.width-20,plugin.height-20,20,20);
            ctx.lineWidth = 2;
            drawLine(width-16,width-16,width-16,width-12,2);
            drawLine(width-16,width-16,width-12,width-16,2);
            drawLine(width-4,width-16,width-4,width-12,2);
            drawLine(width-4,width-16,width-8,width-16,2);
            drawLine(width-16,width-4,width-16,width-8,2);
            drawLine(width-16,width-4,width-12,width-4,2);
            drawLine(width-4,width-4,width-4,width-8,2);
            drawLine(width-4,width-4,width-8,width-4,2);

            ctx.strokeStyle="black";
            let s = drawTime(angle);
            ctx.fillStyle = "black";
            drawText(xMiddle+3 , yMiddle-3, s);
            time_string = s;

            ctx.strokeStyle="blue";
            ctx.text
            if (angle!=anglecursor && anglecursor!=null) {
                s = drawTime(anglecursor);
                ctx.fillStyle = "blue";
                drawText(xMiddle+3 , yMiddle+50, s);
            }
            /*
            ctx.strokeStyle="black";
            drawLine(0,cy,width,cy,1);
            drawLine(cx,0,cx,height,1);
            ctx.font = '16px serif';
            ctx.fillText("("+Math.trunc(cx)+"|"+Math.trunc(cy)+")", cx, cy); */
        }

        function drawTime(angle) {
            if (angle < 0) angle += 2*Math.PI;
            let sek  = (1.0-2.0*angle/Math.PI)*3.0*3600.0;
            if (sek<0) sek += 12*3600;
            sek = Math.round(sek);
            let hour = Math.trunc(sek/3600.0);
            if (hour<1) hour+=12;
            let m    = Math.trunc((sek%3600)/60);

            let pointH = calcPointFromAngle(angle,radius*0.5);
            let pointM = calcPointFromAngle(Math.PI/2-m*2*Math.PI/60,radius*0.8);
            let imgCoordinates = getImgCoordinates();
            drawLine(xMiddle , yMiddle, pointH.x - imgCoordinates.x, pointH.y - imgCoordinates.y,7);
            drawLine(xMiddle , yMiddle, pointM.x - imgCoordinates.x, pointM.y - imgCoordinates.y,3);
            let s    = ''+(hour<10?' ':'')+hour+":"+(m<10?'0':'')+m;
            return s;
        }

        /**
         * Wandelt eine Zeit 10:32 in einen Winkel in Radianten um
         * @param time Zeit als String
         */
        function parseTime(time) {
            time_array = time.split(":");
            if (time_array.length<2) return Math.PI/2.0;
            h = time_array[0];
            m = time_array[1];
            if (time_array.length>2) s = time_array[2];
            else s = '0';
            h = parseFloat(h);
            m = parseFloat(m);
            s = parseFloat(s);
            time_sek = s+m*60+h*3600;
            arg = Math.PI/2-time_sek/12.0/3600.0*2.0*Math.PI;
            if (arg<0) arg+=2*Math.PI;
            return arg;
        }

        /**
         * Berechnet aus dem angegebenen Winkel die Uhrzeit
         * @param angle        Winkel
         * @returns {string}   Uhrzeit
         */
        function timestring(angle) {
            let hour = 14-angle*12/2/Math.PI;
            let h    = ((Math.trunc(hour)))%12+1;
            let m    = Math.trunc((hour-Math.trunc(hour))*60);
            let s    = ''+(h<10?' ':'')+h+":"+(m<10?'0':'')+m;
            return s;
        }

        /**
         * Zeichnen einer Linie
         * @param x1    x-Punkt1
         * @param y1    y-Punkt1
         * @param x2    x-Punkt2
         * @param y2    y-Punkt2
         */
        function drawLine(x1, y1, x2, y2, width) {
            ctx.beginPath();
            ctx.moveTo(x1 , y1);
            ctx.lineTo(x2, y2);
            ctx.lineWidth = width;
            ctx.stroke();
        }

        function drawText(x,y,text) {
            ctx.font = '48px serif';
            ctx.lineWidth = 1;
            ctx.fillText(text, x, y);
        }

        /**
         *
         * @returns coordinates of left-upper corner of image
         */
        function getImgCoordinates() {
            const offs = $("." + plugin.canvas).offset();
            return {
                x: offs.left,
                y: offs.top
            };
        }

        /**
         *
         * @returns returns the coordinagtes of the center of the image
         */
        function getImgCenterCoordinates() {
            let imgCoordinates = getImgCoordinates();
            return {
                x: imgCoordinates.x + xMiddle,
                y: imgCoordinates.y + yMiddle
            }
        }

        /**
         * calculates the distance of a point to the center of an image
         * @param xAbsolute   the x-coordinate of the point
         * @param yAbsolute   the y-coordinate of the point
         * @returns {number}  the distance
         */
        function calcDistanceToCenter(xAbsolute, yAbsolute) {
            let imgCenterCoordinates = getImgCenterCoordinates();
            return Math.sqrt(Math.pow(imgCenterCoordinates.x - xAbsolute, 2) + Math.pow(imgCenterCoordinates.y - yAbsolute, 2));
        }


        function calcAngleToCenter(x, y) {
            let center = getImgCenterCoordinates();
            let angle  = calcAngleOfVectors(1,0,x-center.x, y-center.y);
            if (angle < 0) {
                return -angle;
            } else {
                return Math.PI + (Math.PI-angle);
            }
        }

        function calcAngleOfVectors(x1, y1, x2, y2) {
            return Math.atan2(y2-y1, x2-x1);
        }

        function calcPointFromAngle(angle,radius) {
            let center = getImgCenterCoordinates();
            let xPoint = center.x+Math.cos(angle) * radius;
            let yPoint = center.y-Math.sin(angle) * radius;
            return {
                x: xPoint,
                y: yPoint
            }
        }
    }

}




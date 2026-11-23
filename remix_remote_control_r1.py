"""Read-only LAN mock viewer for RemiX Duo. No Smaart commands."""
import json, math, secrets, socket, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QHBoxLayout
from PyQt6.QtCore import Qt

HTML = """<!doctype html><html lang="vi"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{background:#07121c;color:#e5f7ff;font:15px system-ui;margin:15px}button{background:#15354b;color:white;border:1px solid #39758c;border-radius:8px;padding:10px}canvas{width:100%;height:190px;background:#0b1d29;border:1px solid #284356;border-radius:8px}h3{color:#64dfef}.tag{color:#8cffae}</style>
<h2>RemiX Duo Â· Smaart Remote</h2><p class="tag">MOCK DATA Â· READ ONLY Â· KHÃ”NG PHáº¢I SMAART LIVE</p>
<button onclick="mode='native';render()">Native HTML</button> <button onclick="mode='mirror';render()">Desktop Mirror</button>
<div id="content"></div>
<script>let mode='native';let tick=0;function plot(id,color,kind){let c=document.getElementById(id),x=c.getContext('2d');c.width=c.clientWidth*devicePixelRatio;c.height=190*devicePixelRatio;x.scale(devicePixelRatio,devicePixelRatio);let w=c.clientWidth,h=190;x.strokeStyle='#284153';for(let i=1;i<6;i++){x.beginPath();x.moveTo(0,i*h/6);x.lineTo(w,i*h/6);x.stroke()}x.strokeStyle=color;x.lineWidth=2;x.beginPath();for(let i=0;i<w;i++){let t=i/w,y=kind===0?90+24*Math.sin(13*t+tick*.06)+12*Math.sin(38*t):kind===1?95+65*Math.sin(10*t+tick*.04):100+35*Math.sin(24*t+tick*.07);if(i===0)x.moveTo(i,y);else x.lineTo(i,y)}x.stroke()}function render(){document.getElementById('content').innerHTML=mode==='mirror'?'<h3>Desktop Mirror</h3><p>ChÆ°a cáº¥u hÃ¬nh VNC. KhÃ´ng báº­t Ä‘iá»u khiá»ƒn tá»« xa.</p>':'<h3>TF Magnitude (mock)</h3><canvas id="mag"></canvas><h3>TF Phase (mock)</h3><canvas id="phase"></canvas><h3>RTA (mock)</h3><canvas id="rta"></canvas>';draw()}function draw(){if(mode!=='native')return;plot('mag','#61f5d0',0);plot('phase','#b49bff',1);plot('rta','#f7b95b',2)}setInterval(()=>{tick++;draw()},120);render()</script></html>"""

def lan_ip():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        s.connect(('192.0.2.1',80))
        return s.getsockname()[0]
    except OSError:return '127.0.0.1'
    finally:s.close()

class RemoteServer:
    def __init__(self):
        self.httpd=None
        self.token=secrets.token_urlsafe(24)
    def start(self):
        if self.httpd:return self.url
        token=self.token
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed=urlparse(self.path)
                supplied=parse_qs(parsed.query).get('token',[''])[0]
                if not secrets.compare_digest(supplied,token):
                    self.send_error(403);return
                if parsed.path!='/':
                    self.send_error(404);return
                body=HTML.encode('utf-8')
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
                self.end_headers();self.wfile.write(body)
            def log_message(self,*args):pass
        self.httpd=ThreadingHTTPServer(('0.0.0.0',0),Handler)
        self.httpd.daemon_threads=True
        threading.Thread(target=self.httpd.serve_forever,daemon=True).start()
        self.url=f'http://{lan_ip()}:{self.httpd.server_port}/?token={self.token}'
        return self.url
    def stop(self):
        if self.httpd:
            server=self.httpd;self.httpd=None
            threading.Thread(target=server.shutdown,daemon=True).start()
            server.server_close()
        self.token=secrets.token_urlsafe(24)

class RemoteControlPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.server=RemoteServer()
        self.setFixedHeight(450)
        layout=QVBoxLayout(self);layout.setContentsMargins(6,8,6,8)
        for title in ('SMAART REMOTE LAN','READ ONLY / MOCK DATA'):
            lab=QLabel(title);lab.setWordWrap(True);layout.addWidget(lab)
        self.start_btn=QPushButton('BAT QR LAN');layout.addWidget(self.start_btn)
        self.stop_btn=QPushButton('DUNG LAN');layout.addWidget(self.stop_btn)
        self.status=QLabel('LAN chua khoi dong');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.qr=QLabel('QR xuat hien khi bat LAN');self.qr.setWordWrap(True)
        self.qr.setAlignment(Qt.AlignmentFlag.AlignCenter);self.qr.setFixedSize(158,158);layout.addWidget(self.qr,alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
    def start(self):
        try:
            url=self.server.start()
            self.status.setText('LAN ACTIVE / MOCK DATA\nScan QR with tablet')
            try:
                import qrcode
                from PyQt6.QtGui import QImage,QPixmap
                from io import BytesIO
                bio=BytesIO();qrcode.make(url).save(bio,format='PNG')
                img=QImage.fromData(bio.getvalue(),'PNG')
                self.qr.setPixmap(QPixmap.fromImage(img).scaled(150,150,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation))
            except ImportError:self.qr.setText('Missing qrcode[pil]')
        except Exception as e:self.status.setText('LAN error: '+str(e))
    def stop(self):
        self.server.stop();self.status.setText('LAN da dung');self.qr.clear()


    def closeEvent(self,event):
        self.stop()
        super().closeEvent(event)

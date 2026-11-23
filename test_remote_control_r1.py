import os,urllib.request,urllib.error
os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtWidgets import QApplication
from remix_remote_control_r1 import RemoteServer,RemoteControlPage
app=QApplication([])
page=RemoteControlPage()
page.start()
url=page.server.url
assert urllib.request.urlopen(url,timeout=4).status==200
try:
    urllib.request.urlopen(url.split('?')[0],timeout=4)
    raise AssertionError('missing token accepted')
except urllib.error.HTTPError as exc:
    assert exc.code==403
page.stop()
assert page.server.httpd is None
print('PASS: Qt page, LAN mock HTTP 200, missing token 403, stop')


import os
import json
import subprocess
import threading
from flask import Flask, request, render_template_string, redirect

app = Flask(__name__)

# متغیرهای گلوبال برای ذخیره وضعیت
CURRENT_UUID = "default-uuid-here"
CURRENT_PATH = "/vless"
XRAY_TUNNEL_URL = "waiting-for-tunnel..."
XRAY_PROCESS = None

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Xray VLESS Panel</title>
    <style>
        body { font-family: sans-serif; padding: 20px; max-width: 800px; margin: auto; }
        .box { border: 1px solid #ccc; padding: 15px; margin: 10px 0; border-radius: 5px; }
        code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
        input { padding: 8px; width: 300px; }
        button { padding: 8px 15px; }
    </style>
</head>
<body>
    <h1>Xray VLESS Panel</h1>
    
    <div class="box">
        <h2>Current Configuration</h2>
        <p><b>Server:</b> <code>{{ tunnel_url }}</code></p>
        <p><b>UUID:</b> <code>{{ uuid }}</code></p>
        <p><b>Path:</b> <code>{{ path }}</code></p>
        <p><b>SNI:</b> <code>{{ tunnel_url }}</code></p>
        
        <h3>VLESS Link (Copy this):</h3>
        <textarea rows="4" cols="80" readonly>vless://{{ uuid }}@{{ tunnel_url }}:443?encryption=none&security=tls&type=ws&host={{ tunnel_url }}&path={{ path }}&sni={{ tunnel_url }}#Xray-GitHub</textarea>
    </div>
    
    <div class="box">
        <h2>Update Configuration</h2>
        <form method="POST">
            <label>UUID:</label><br>
            <input type="text" name="uuid" value="{{ uuid }}"><br><br>
            <label>WS Path:</label><br>
            <input type="text" name="path" value="{{ path }}"><br><br>
            <button type="submit">Update & Restart Xray</button>
        </form>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    global CURRENT_UUID, CURRENT_PATH, XRAY_TUNNEL_URL
    
    if request.method == 'POST':
        new_uuid = request.form.get('uuid', CURRENT_UUID)
        new_path = request.form.get('path', CURRENT_PATH)
        
        CURRENT_UUID = new_uuid
        CURRENT_PATH = new_path
        
        # به‌روزرسانی کانفیگ و ری‌استارت Xray
        update_xray_config(new_uuid, new_path)
        
        return redirect('/')
    
    return render_template_string(HTML, 
        tunnel_url=XRAY_TUNNEL_URL,
        uuid=CURRENT_UUID,
        path=CURRENT_PATH
    )

def update_xray_config(uuid, path):
    """کانفیگ Xray را به‌روزرسانی و پروسه را ری‌استارت می‌کند."""
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": 8080,
            "listen": "127.0.0.1",
            "protocol": "vless",
            "settings": {
                "clients": [{"id": uuid}],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "ws",
                "wsSettings": {"path": path}
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }
    
    with open('/tmp/xray/config.json', 'w') as f:
        json.dump(config, f)
    
    # Kill و restart Xray (ساده‌ترین روش)
    subprocess.run(['pkill', '-f', 'xray run'], capture_output=True)
    subprocess.Popen(['xray', 'run', '-c', '/tmp/xray/config.json'])

def watch_xray_tunnel():
    """لاگ تونل Xray را می‌خواند و URL را استخراج می‌کند."""
    global XRAY_TUNNEL_URL
    log_file = '/tmp/xray_tunnel.log'
    
    while True:
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if 'trycloudflare.com' in line:
                        # استخراج URL از لاگ [citation:19]
                        import re
                        match = re.search(r'https://[^\s"\'<>|,]+trycloudflare\.com', line)
                        if match:
                            XRAY_TUNNEL_URL = match.group(0).replace('https://', '')
                            break
        except FileNotFoundError:
            pass
        import time
        time.sleep(5)

if __name__ == '__main__':
    # شروع thread برای پایش تونل
    threading.Thread(target=watch_xray_tunnel, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)

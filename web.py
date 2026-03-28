import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import random
import cv2
import numpy as np
from flask import Response
import requests
import time
import socket
from collections import deque

# 🚀 解决特定网络环境下的 socket 闪退问题
socket.getfqdn = lambda name="": "localhost"

# 初始化 App
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

# ==========================================
# 🎨 深度定制：硬核科幻边框 CSS
# ==========================================
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>ISAR-V 智能指挥舱</title>
        {%favicon%}
        {%css%}
        <style>
            * { box-sizing: border-box; }
            body { 
                /* 改为 auto 允许在屏幕过小时滚动，防止挤压崩溃 */
                overflow-x: hidden; 
                overflow-y: auto;
                background-color: #030816; 
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                margin: 0; padding: 0;
                /* ✅ 核心修复：强制提高基础字号，解决 100% 缩放看不清字的问题 */
                font-size: 16px; 
            }
            @media (min-width: 1920px) {
                body { font-size: 18px; } /* 在 1080p 以上大屏进一步放大字号 */
            }
            .cyber-grid {
                position: fixed; width: 200%; height: 200%; top: -50%; left: -50%;
                background-image: 
                    linear-gradient(rgba(0, 243, 255, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 243, 255, 0.03) 1px, transparent 1px);
                background-size: 40px 40px;
                transform: perspective(600px) rotateX(60deg);
                animation: grid-move 20s linear infinite;
                z-index: 0; pointer-events: none;
            }
            @keyframes grid-move {
                from { transform: perspective(600px) rotateX(60deg) translateY(0); }
                to { transform: perspective(600px) rotateX(60deg) translateY(40px); }
            }
            .tech-card {
                position: relative;
                background:
                    linear-gradient(to right, #00f3ff 2px, transparent 2px) 0 0,
                    linear-gradient(to bottom, #00f3ff 2px, transparent 2px) 0 0,
                    linear-gradient(to left, #00f3ff 2px, transparent 2px) 100% 0,
                    linear-gradient(to bottom, #00f3ff 2px, transparent 2px) 100% 0,
                    linear-gradient(to right, #00f3ff 2px, transparent 2px) 0 100%,
                    linear-gradient(to top, #00f3ff 2px, transparent 2px) 0 100%,
                    linear-gradient(to left, #00f3ff 2px, transparent 2px) 100% 100%,
                    linear-gradient(to top, #00f3ff 2px, transparent 2px) 100% 100%;
                background-repeat: no-repeat;
                background-size: 15px 15px; 
                background-color: rgba(6, 14, 30, 0.6); 
                border: 1px solid rgba(0, 243, 255, 0.1); 
                padding: 8px; box-shadow: inset 0 0 20px rgba(0, 243, 255, 0.02);
                height: 100%; display: flex; flex-direction: column;
            }
            .tech-card-main {
                position: relative; background-color: rgba(4, 10, 24, 0.8);
                border: 1px solid rgba(0, 243, 255, 0.4);
                box-shadow: 0 0 15px rgba(0, 243, 255, 0.15), inset 0 0 30px rgba(0, 243, 255, 0.05);
                padding: 10px; height: 100%; display: flex; flex-direction: column;
            }
            .tech-title {
                color: #e2e8f0; font-size: 0.8rem; text-align: center;
                padding-bottom: 4px; margin-bottom: 2px;
                border-bottom: 1px dashed rgba(0, 243, 255, 0.2);
                letter-spacing: 1px; flex-shrink: 0; 
            }
            .tech-title-main {
                color: #00f3ff; font-size: 0.95rem; text-align: center; font-weight: 600;
                letter-spacing: 2px; padding: 4px;
                border-bottom: 1px solid rgba(0, 243, 255, 0.5);
                background: linear-gradient(90deg, transparent, rgba(0, 243, 255, 0.15), transparent);
                margin-bottom: 8px; flex-shrink: 0;
            }
            .chart-container { flex-grow: 1; min-height: 0; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ==========================================
# 🌟 数据源配置
# ==========================================
ESP32_DATA_URL = "http://10.86.153.41/data"
K230_STREAM_URL = "http://10.149.25.97:8080"

# 历史数据队列
temp_q = deque(maxlen=25)
hum_q = deque(maxlen=25)
real_pres_q = deque(maxlen=25)
oxy_q = deque(maxlen=25)
mock_pres_q = deque(maxlen=25)


def generate_frames():
    offline_img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(offline_img, "K230 CAMERA OFFLINE", (120, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    _, buf = cv2.imencode('.jpg', offline_img)
    offline_frame = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'
    while True:
        try:
            res = requests.get(K230_STREAM_URL, stream=True, timeout=2)
            if res.status_code == 200:
                bytes_data = b''
                for chunk in res.iter_content(chunk_size=131072):
                    bytes_data += chunk
                    while True:
                        a = bytes_data.find(b'\xff\xd8')
                        b = bytes_data.find(b'\xff\xd9')
                        if a != -1 and b != -1 and b > a:
                            jpg = bytes_data[a:b + 2]
                            bytes_data = bytes_data[b + 2:]
                            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if frame is not None:
                                planar = frame.flatten().reshape(3, 480, 640)
                                restored = planar.transpose(1, 2, 0)
                                restored_bgr = restored[..., ::-1]
                                ret, buffer = cv2.imencode('.jpg', restored_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                        else:
                            break
            else:
                yield offline_frame; time.sleep(1)
        except:
            yield offline_frame; time.sleep(1)


@app.server.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ==========================================
# 📐 页面布局
# ==========================================
CHART_HEIGHT = "32vh"
MAIN_MEDIA_HEIGHT = "68vh"

app.layout = html.Div([
    html.Div(className="cyber-grid"),
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0),
    # ✅ 核心修复：解除 100vh 的强行高度限制，改为 minHeight 并增加上下内边距
    dbc.Container([
        dbc.Row([
            dbc.Col(html.Div([
                html.H3("ISAR-V 智能搜救多维可视化指挥舱",
                        style={"color": "#fff", "fontWeight": "600", "letterSpacing": "3px",
                               "textShadow": "0 0 10px rgba(0, 243, 255, 0.8)", "margin": "1vh 0 0.5vh 0"}),
                html.Div("GLOBAL SENSOR NETWORK // SECURE UPLINK ESTABLISHED",
                         style={"color": "#00f3ff", "fontSize": "0.65rem", "letterSpacing": "3px"})
            ], className="text-center mb-2"), width=12)
        ], style={"position": "relative", "zIndex": 1}),

        dbc.Row([
            dbc.Col(html.Div([html.Div("🚀 巡航速度", style={"color": "#a0aec0", "fontSize": "0.75rem"}),
                              html.Div(id="speed-text",
                                       style={"color": "#00f3ff", "fontSize": "1.3rem", "fontWeight": "bold"})],
                             className="tech-card text-center"), width=3),
            dbc.Col(html.Div([html.Div("🔋 系统能源", style={"color": "#a0aec0", "fontSize": "0.75rem"}),
                              html.Div(id="battery-text",
                                       style={"color": "#00f3ff", "fontSize": "1.3rem", "fontWeight": "bold"})],
                             className="tech-card text-center"), width=3),
            dbc.Col(html.Div([html.Div("🌡️ 核心温度", style={"color": "#a0aec0", "fontSize": "0.75rem"}),
                              html.Div(id="temp-text",
                                       style={"color": "#00f3ff", "fontSize": "1.3rem", "fontWeight": "bold"})],
                             className="tech-card text-center"), width=3),
            dbc.Col(html.Div([html.Div("💧 环境湿度", style={"color": "#a0aec0", "fontSize": "0.75rem"}),
                              html.Div(id="env-text",
                                       style={"color": "#00f3ff", "fontSize": "1.3rem", "fontWeight": "bold"})],
                             className="tech-card text-center"), width=3),
        ], className="mb-2", style={"position": "relative", "zIndex": 1}),

        dbc.Row([
            dbc.Col([
                html.Div([html.Div("温湿度趋势", className="tech-title"), html.Div(
                    dcc.Graph(id='chart-temp-hum', config={'displayModeBar': False}, style={"height": "100%"}),
                    className="chart-container")], className="tech-card mb-2", style={"height": CHART_HEIGHT}),
                html.Div([html.Div("实时气压 (hPa)", className="tech-title"), html.Div(
                    dcc.Graph(id='chart-pressure-real', config={'displayModeBar': False}, style={"height": "100%"}),
                    className="chart-container")], className="tech-card", style={"height": CHART_HEIGHT})
            ], width=2),

            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Div("算法实时监控流", className="tech-title-main"),
                            # ✅ 核心修复：视频框改用 flex 居中，防止浏览器缩放时错位
                            html.Div([
                                html.Img(src="/video_feed",
                                         style={"width": "100%", "height": "100%", "objectFit": "contain"}),
                                html.Div(style={"position": "absolute", "top": 0, "left": 0, "width": "100%",
                                                "height": "100%",
                                                "background": "linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%)",
                                                "backgroundSize": "100% 4px", "pointerEvents": "none"})
                            ], style={"position": "relative", "flexGrow": "1", "display": "flex",
                                      "alignItems": "center", "justifyContent": "center",
                                      "border": "1px solid rgba(0,243,255,0.2)", "backgroundColor": "#020617",
                                      "overflow": "hidden"}),
                            # 顺便放大了底部文字的 rem 基数
                            html.Div(id="fps-text", className="text-center pt-1",
                                     style={"color": "#00f3ff", "fontSize": "1rem", "flexShrink": "0"})
                        ], className="tech-card-main", style={"height": MAIN_MEDIA_HEIGHT})
                    ], width=6, className="pe-1"),

                    dbc.Col([
                        html.Div([
                            html.Div("灾区真实地貌卫星拓扑", className="tech-title-main"),
                            # ✅ 核心修复：地图框强制占满 100% 宽，且设置 overflow: hidden 防溢出
                            html.Div([
                                dcc.Graph(id='live-map', config={'displayModeBar': False},
                                          style={"height": "100%", "width": "100%"})
                            ], style={"flexGrow": "1", "position": "relative",
                                      "border": "1px solid rgba(0,243,255,0.2)", "overflow": "hidden"}),
                            html.Div("搜救车实时轨迹追踪", className="text-center pt-1",
                                     style={"color": "#00f3ff", "fontSize": "1rem", "flexShrink": "0"})
                        ], className="tech-card-main", style={"height": MAIN_MEDIA_HEIGHT})
                    ], width=6, className="ps-1"),
                ])
            ], width=8),

            dbc.Col([
                html.Div([html.Div("氧气浓度监测", className="tech-title"), html.Div(
                    dcc.Graph(id='chart-oxygen', config={'displayModeBar': False}, style={"height": "100%"}),
                    className="chart-container")], className="tech-card mb-2", style={"height": CHART_HEIGHT}),
                html.Div([html.Div("模拟压强监测 (kPa)", className="tech-title"), html.Div(
                    dcc.Graph(id='chart-pressure', config={'displayModeBar': False}, style={"height": "100%"}),
                    className="chart-container")], className="tech-card", style={"height": CHART_HEIGHT})
            ], width=2),
        ], style={"position": "relative", "zIndex": 1}),
    ], fluid=True, className="px-4",
        style={"minHeight": "100vh", "paddingTop": "2vh", "paddingBottom": "2vh", "display": "flex",
               "flexDirection": "column", "justifyContent": "center"})
])


# ==========================================
# 📊 UI 回调逻辑
# ==========================================
@app.callback(
    [Output("speed-text", "children"), Output("battery-text", "children"), Output("temp-text", "children"),
     Output("env-text", "children"), Output("fps-text", "children"),
     Output("chart-temp-hum", "figure"), Output("chart-pressure-real", "figure"),
     Output("chart-oxygen", "figure"), Output("chart-pressure", "figure"),
     Output("live-map", "figure"), Output("temp-text", "style"), Output("env-text", "style")],
    [Input("interval-component", "n_intervals")]
)
def update_metrics(n):
    if n is None: n = 0

    speed = f"{1.2 + random.uniform(-0.05, 0.05):.2f} M/S"
    battery = f"{max(0, 92 - n // 60)} %"
    fps = f"算法实时帧率: {28 + random.uniform(-2, 2):.1f} FPS"

    normal_style = {"color": "#00f3ff", "fontSize": "1.3rem", "fontWeight": "bold"}
    error_style = {"color": "#f43f5e", "fontSize": "1.3rem", "fontWeight": "bold"}
    current_temp_style = normal_style
    current_env_style = normal_style

    # --- 1. 获取 ESP32 真实数据 ---
    temp_val, hum_val, real_pres_val, o2_val = 25.0, 55.0, 1013.25, 20.9
    try:
        response = requests.get(ESP32_DATA_URL, timeout=0.5)
        if response.status_code == 200:
            esp_data = response.json()
            temp_val = float(esp_data.get('temperature', 25.0))
            hum_val = float(esp_data.get('humidity', 55.0))
            real_pres_val = float(esp_data.get('pressure', 1013.25))
            o2_val = float(esp_data.get('o2_concentration', 20.9))
            temp_str, env_str = f"{temp_val:.1f} °C", f"{hum_val:.1f} %"
        else:
            temp_str, env_str = "ERROR", "ERROR"
            current_temp_style, current_env_style = error_style, error_style
    except:
        temp_str, env_str = "OFFLINE", "OFFLINE"
        current_temp_style, current_env_style = error_style, error_style

    # --- 2. 更新队列 ---
    temp_q.append(temp_val)
    hum_q.append(hum_val)
    real_pres_q.append(real_pres_val)
    oxy_q.append(o2_val)
    mock_pres_q.append(101.32 + random.uniform(-0.01, 0.01))

    # --- 3. 生成图表 ---
    def dark_plot(fig, show_x=False, y_range=None):
        fig.update_layout(
            template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=25, r=10, t=10, b=25 if show_x else 10),
            font={"color": "#a0aec0", "size": 10},
            xaxis=dict(showgrid=False, visible=show_x, color="#475569"),
            yaxis=dict(showgrid=True, gridcolor='rgba(0, 243, 255, 0.1)', color="#475569", range=y_range)
        )
        return fig

    # 温湿度图表 (带图例)
    fig_th = dark_plot(go.Figure())
    fig_th.add_trace(go.Scatter(y=list(temp_q), mode='lines', name='温度 (°C)', line=dict(color='#f43f5e', width=2)))
    fig_th.add_trace(go.Scatter(y=list(hum_q), mode='lines', name='湿度 (%)', line=dict(color='#00f3ff', width=2)))
    fig_th.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=9, color="#a0aec0"),
            bgcolor="rgba(0,0,0,0)"
        )
    )

    # 真实气压图表 (动态 Y 轴上限)
    current_max_pres = max(real_pres_q) if len(real_pres_q) > 0 else 1013.25
    y_upper_limit = current_max_pres * 1.35

    fig_real_pres = dark_plot(go.Figure(), y_range=[0, y_upper_limit])
    fig_real_pres.add_trace(
        go.Scatter(y=list(real_pres_q), fill='tozeroy', name='气压 (hPa)', line=dict(color='#10b981', width=2),
                   fillcolor='rgba(16, 185, 129, 0.25)'))
    fig_real_pres.update_layout(showlegend=False)

    # 氧气仪表盘
    fig_oxy = go.Figure(go.Indicator(
        mode="gauge+number", value=o2_val,
        number={'suffix': "%", 'font': {'color': '#00f3ff', 'size': 20}},
        gauge={'axis': {'range': [15, 25]}, 'bar': {'color': "#00f3ff"},
               'steps': [{'range': [15, 19.5], 'color': "rgba(244,63,94,0.4)"}]}
    ))
    fig_oxy.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          margin=dict(l=20, r=20, t=20, b=20))

    # 右侧模拟气压
    fig_pres = dark_plot(go.Figure(), show_x=True, y_range=[101.2, 101.4])
    fig_pres.add_trace(go.Bar(y=list(mock_pres_q), marker_color='#8b5cf6', name="模拟气压"))
    fig_pres.update_layout(showlegend=False)

    # 卫星地图
    START_LAT = 40.6165
    START_LON = 120.7665
    current_lat = START_LAT + (n * 0.00001) % 0.01
    current_lon = START_LON + (n * 0.000005) % 0.01

    map_fig = go.Figure(go.Scattermapbox(
        lat=[current_lat], lon=[current_lon], mode='markers+text',
        marker=go.scattermapbox.Marker(size=16, color='#f43f5e', opacity=1),
        text=['<b>ISAR-V 目标锁定</b>'], textposition="bottom right",
        textfont=dict(color="#f43f5e", size=14, family="sans-serif")
    ))

    map_fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            center=dict(lat=current_lat, lon=current_lon),
            zoom=16,
            layers=[dict(
                sourcetype="raster",
                source=["https://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}"],
                type="raster",
                below="traces"
            )]
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', uirevision='constant'
    )

    return speed, battery, temp_str, env_str, fps, fig_th, fig_real_pres, fig_oxy, fig_pres, map_fig, current_temp_style, current_env_style


if __name__ == '__main__':
    # ⚠️ 关键修改点：增加了 host='0.0.0.0' 以允许云端容器的外网访问
    app.run(host='0.0.0.0', debug=False, threaded=True, port=8050)
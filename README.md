# PDD采集器 - WebView前端版本

## 项目概述

本项目是一个基于WebView的PDD数据采集器，具有以下特点：

- 现代化界面: 使用HTML/CSS/JavaScript构建的现代化用户界面
- WebView集成: 通过pywebview将前端界面嵌入到EXE中
- 实时通信: JavaScript与Python之间的双向通信
- 专业安装包: 包含WebView2运行时检测和安装

## 文件结构

```
├── enhanced_webview.py    # 增强版WebView启动器和JS桥接
├── ui_webview.py          # 基础WebView启动器和JS桥接
├── license_client.py      # 许可证HTTP客户端
├── webui/                 # 前端文件
│   ├── index.html        # 主界面
│   ├── style.css         # 样式文件
│   └── enhanced-app.js   # 前端逻辑
└── requirements.txt      # 依赖
```

## 联调接口

### JS→Python（PyWebView bridge）
- `getMachineHash() -> string`
- `pickDirectory() -> {status, path?, message?}`
- `activate(code) -> {status, license_id?, expires_at?, message?}`
- `validate() -> {status, license_id?, session_token?, expires_at?, message?}`
- `startScrape(params) -> {status, message?}`
- `stopScrape() -> {status, message?}`
- `getState() -> state`
- `openFolder(path?) -> {status, message?}`
- `exportData() -> {status, file_path?, file_size?, message?}`
- `exitApp() -> {status}`

### Python→JS（evaluate_js 回调）
- `window.__onProgress(info)`
- `window.__onItem(item)`
- `window.__onStatus(status)`

### HTTP（心跳）
- POST `/sessions/heartbeat` `{license_id, machine_hash, session_token}` 每30秒

### 状态码建议
- `OK | ERROR | NO_KEY | NO_EXPORT_DIR | ALREADY_RUNNING | EXPIRED | INVALID | BOUND_OTHER | NOT_RUNNING`

## 运行
```bash
pip install -r requirements.txt
python enhanced_webview.py
```

## 注意
- 该仓库仅包含前端与桥接代码；完整采集实现与后端接口由后端工程负责。

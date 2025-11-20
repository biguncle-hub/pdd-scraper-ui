#!/usr/bin/env python3
"""
增强版WebView启动器 - 集成完整的后端功能
"""
import threading
import json
import os
import time
import webview
from datetime import datetime
from pdd_scraper import run_scraper, DEFAULT_KEYWORD, DEFAULT_PRICE_THRESHOLD, DEFAULT_PINNED_THRESHOLD, DEFAULT_REVIEWS_THRESHOLD
from license_client import get_machine_hash, activate as lic_activate, validate as lic_validate, HeartbeatThread, end_session, load_license_state, save_license_state

class EnhancedBridge:
    """增强版桥接类，提供更多功能和更好的错误处理"""
    
    def __init__(self, window):
        self.window = window
        self.mac = get_machine_hash()
        self.session = {"license_id": None, "token": None}
        self.hb_thread = None
        self.stop_event = threading.Event()
        self.scraping_thread = None
        
        # 应用状态
        self.state = {
            "keyword": DEFAULT_KEYWORD,
            "price": DEFAULT_PRICE_THRESHOLD,
            "pinned": DEFAULT_PINNED_THRESHOLD,
            "reviews": DEFAULT_REVIEWS_THRESHOLD,
            "exportDir": "",
            "outfile": "",
            "status": "idle",
            "visited": 0,
            "collected": 0,
            "filtered": 0,
            "list_count": 0,
            "batch_progress": "0/0",
            "avg_price": 0.0,
            "avg_pinned": 0.0,
            "start_time": None,
            "items": []  # 存储采集结果
        }
        
        # 统计数据
        self._sum_price = 0.0
        self._sum_pinned = 0.0
        self._sum_count = 0
        
        # 初始化
        self._init_config()
    
    def _init_config(self):
        """初始化配置"""
        try:
            config_dir = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "PDDScraper")
            os.makedirs(config_dir, exist_ok=True)
            
            config_file = os.path.join(config_dir, "app.ini")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'export_dir=' in content:
                        export_dir = content.split('export_dir=')[1].strip()
                        if os.path.exists(export_dir):
                            self.state["exportDir"] = export_dir
        except Exception as e:
            print(f"配置初始化失败: {e}")
    
    def getMachineHash(self):
        """获取机器码"""
        return self.mac
    
    def getSystemInfo(self):
        """获取系统信息"""
        import platform
        return {
            "platform": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
    
    def pickDirectory(self):
        """选择导出目录"""
        try:
            path = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if path and isinstance(path, list):
                path = path[0]
            if path:
                self.state["exportDir"] = path
                
                # 保存配置
                config_dir = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "PDDScraper")
                os.makedirs(config_dir, exist_ok=True)
                
                config_file = os.path.join(config_dir, "app.ini")
                with open(config_file, "w", encoding="utf-8") as f:
                    f.write(f"[client]\nexport_dir={path}")
                
                return {"status": "OK", "path": path}
            return {"status": "CANCELLED"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def activate(self, code):
        """激活许可证"""
        try:
            result = lic_activate(code, self.mac)
            if result.get("status") == "OK":
                save_license_state({"license_key": code, "license_id": result.get("license_id")})
                self.session["license_id"] = result.get("license_id")
            return result
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def validate(self):
        """验证许可证"""
        try:
            st = load_license_state()
            key = st.get("license_key")
            if not key:
                return {"status": "NO_KEY"}
            
            result = lic_validate(key, self.mac)
            if result.get("status") == "OK":
                self.session["license_id"] = result.get("license_id")
                self.session["token"] = result.get("session_token")
                
                # 启动心跳线程
                if self.hb_thread:
                    try:
                        self.hb_thread.stop()
                    except Exception:
                        pass
                
                self.hb_thread = HeartbeatThread(
                    result.get("license_id"), 
                    self.mac, 
                    result.get("session_token"), 
                    interval=30
                )
                self.hb_thread.start()
            
            return result
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def endSession(self):
        """结束会话"""
        if not (self.session.get("license_id") and self.session.get("token")):
            return {"status": "NO_SESSION"}
        
        try:
            result = end_session(self.session["license_id"], self.mac, self.session["token"])
            if result.get("status") == "OK":
                if self.hb_thread:
                    try:
                        self.hb_thread.stop()
                    except Exception:
                        pass
                self.session["token"] = None
            return result
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def startScrape(self, params):
        """开始采集"""
        try:
            # 验证参数
            self.state["keyword"] = (params.get("keyword") or DEFAULT_KEYWORD).strip()
            self.state["price"] = float(params.get("price") or DEFAULT_PRICE_THRESHOLD)
            self.state["pinned"] = float(params.get("pinned") or DEFAULT_PINNED_THRESHOLD)
            self.state["reviews"] = int(params.get("reviews") or DEFAULT_REVIEWS_THRESHOLD)
            self.state["exportDir"] = params.get("exportDir") or self.state.get("exportDir") or ""
        except Exception as e:
            return {"status": "ERROR", "message": f"参数错误: {str(e)}"}
        
        if not self.state["exportDir"]:
            return {"status": "NO_EXPORT_DIR", "message": "请选择导出目录"}
        
        # 验证许可证
        st = load_license_state()
        if not st.get("license_key"):
            return {"status": "NO_KEY", "message": "未找到激活码"}
        
        try:
            result = lic_validate(st["license_key"], self.mac)
        except Exception as e:
            return {"status": "ERROR", "message": f"许可证验证失败: {str(e)}"}
        
        if result.get("status") != "OK":
            return result
        
        # 检查是否已在运行
        if self.scraping_thread and self.scraping_thread.is_alive():
            return {"status": "ALREADY_RUNNING", "message": "采集已在进行中"}
        
        # 重置状态
        self.stop_event.clear()
        self.state["status"] = "running"
        self.state["start_time"] = datetime.now()
        self.state["visited"] = 0
        self.state["collected"] = 0
        self.state["filtered"] = 0
        self.state["list_count"] = 0
        self.state["batch_progress"] = "0/0"
        self.state["items"] = []
        self._sum_price = 0.0
        self._sum_pinned = 0.0
        self._sum_count = 0
        
        # 设置输出文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(self.state["exportDir"], f"pdd_results_{timestamp}.xlsx")
        self.state["outfile"] = out_path
        
        def on_item(item):
            """处理单个商品项"""
            try:
                # 更新统计数据
                price = float(item.get("price") or 0)
                pinned = float(item.get("pinned") or 0)
                
                self._sum_price += price
                self._sum_pinned += pinned
                self._sum_count += 1
                
                self.state["avg_price"] = self._sum_price / max(1, self._sum_count)
                self.state["avg_pinned"] = self._sum_pinned / max(1, self._sum_count)
                
                # 添加到结果列表
                self.state["items"].append(item)
                if len(self.state["items"]) > 100:  # 限制内存使用
                    self.state["items"].pop(0)
                
                # 发送到前端
                self.window.evaluate_js(f"window.__onItem && window.__onItem({json.dumps(item)})")
                
            except Exception as e:
                print(f"处理商品项失败: {e}")
        
        def on_progress(info):
            """处理进度更新"""
            try:
                self.state.update({
                    "visited": info.get("visited", 0),
                    "collected": info.get("collected", 0),
                    "filtered": info.get("filtered", 0),
                    "list_count": info.get("list_count", 0),
                    "batch_progress": info.get("batch_progress", "0/0"),
                })
                
                # 计算运行时间
                if self.state["start_time"]:
                    run_time = (datetime.now() - self.state["start_time"]).total_seconds()
                    info["run_time"] = int(run_time)
                
                info["avg_price"] = self.state["avg_price"]
                info["avg_pinned"] = self.state["avg_pinned"]
                info["outfile"] = self.state.get("outfile", "")
                
                # 发送到前端
                self.window.evaluate_js(f"window.__onProgress && window.__onProgress({json.dumps(info)})")
                
            except Exception as e:
                print(f"处理进度失败: {e}")
        
        def worker():
            """采集工作线程"""
            try:
                run_scraper(
                    self.state["keyword"],
                    self.state["price"],
                    self.state["pinned"],
                    self.state["reviews"],
                    on_item=on_item,
                    on_progress=on_progress,
                    stop_event=self.stop_event,
                    output_path=out_path
                )
            except Exception as e:
                print(f"采集线程异常: {e}")
                self.state["status"] = "error"
                try:
                    self.window.evaluate_js("window.__onStatus && window.__onStatus('error')")
                except Exception:
                    pass
            finally:
                self.state["status"] = "idle"
                try:
                    self.window.evaluate_js("window.__onStatus && window.__onStatus('idle')")
                except Exception:
                    pass
        
        # 启动采集线程
        self.scraping_thread = threading.Thread(target=worker, daemon=True)
        self.scraping_thread.start()
        
        return {"status": "OK", "message": "采集已开始"}
    
    def stopScrape(self):
        """停止采集"""
        if self.state["status"] != "running":
            return {"status": "NOT_RUNNING", "message": "采集未在运行"}
        
        self.stop_event.set()
        self.state["status"] = "stopped"
        
        try:
            self.window.evaluate_js("window.__onStatus && window.__onStatus('stopped')")
        except Exception:
            pass
        
        return {"status": "OK", "message": "采集已停止"}
    
    def getState(self):
        """获取当前状态"""
        s = dict(self.state)
        s["now"] = datetime.now().isoformat()
        s["machine_hash"] = self.mac
        s["is_activated"] = bool(load_license_state().get("license_key"))
        s["session_active"] = bool(self.session.get("token"))
        return s
    
    def getResults(self, limit=50):
        """获取采集结果"""
        items = self.state["items"][-limit:]  # 获取最新的结果
        return {
            "items": items,
            "total": len(self.state["items"]),
            "collected": self.state["collected"],
            "filtered": self.state["filtered"]
        }
    
    def clearResults(self):
        """清空结果"""
        self.state["items"] = []
        return {"status": "OK"}
    
    def openFolder(self, path=None):
        """打开文件夹"""
        try:
            p = path or self.state.get("outfile") or self.state.get("exportDir")
            if not p:
                return {"status": "NO_PATH", "message": "未找到路径"}
            
            if os.path.isfile(p):
                os.startfile(os.path.dirname(p))
            else:
                os.startfile(p)
            
            return {"status": "OK", "message": "已打开文件夹"}
        except Exception as e:
            return {"status": "ERROR", "message": f"打开文件夹失败: {str(e)}"}
    
    def exportData(self, format="excel"):
        """导出数据"""
        try:
            if not self.state["outfile"] or not os.path.exists(self.state["outfile"]):
                return {"status": "NO_FILE", "message": "没有找到导出文件"}
            
            return {
                "status": "OK",
                "file_path": self.state["outfile"],
                "file_size": os.path.getsize(self.state["outfile"])
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"导出失败: {str(e)}"}

def main():
    """主函数"""
    html_path = os.path.join(os.path.dirname(__file__), "webui", "index.html")
    
    # 创建窗口
    window = webview.create_window(
        "拼多多采集（授权版）- 增强版",
        html_path,
        width=1200,
        height=920,
        min_size=(1100, 820),
        resizable=True,
        fullscreen=False,
        on_top=False
    )
    
    # 创建桥接API并暴露给前端
    api = EnhancedBridge(window)
    try:
        window.expose(api.getMachineHash)
        window.expose(api.getSystemInfo)
        window.expose(api.pickDirectory)
        window.expose(api.activate)
        window.expose(api.validate)
        window.expose(api.endSession)
        window.expose(api.startScrape)
        window.expose(api.stopScrape)
        window.expose(api.getState)
        window.expose(api.getResults)
        window.expose(api.clearResults)
        window.expose(api.openFolder)
        window.expose(api.exportData)
        window.expose(api.exitApp)
    except Exception:
        pass
    
    # 启动WebView
    webview.start(
        http_server=True,
        gui="edgechromium",
        debug=False,
        private_mode=False,
        storage_path=None
    )

if __name__ == "__main__":
    main()

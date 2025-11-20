import threading
import json
import os
import time
import webview
from datetime import datetime
from pdd_scraper import run_scraper, DEFAULT_KEYWORD, DEFAULT_PRICE_THRESHOLD, DEFAULT_PINNED_THRESHOLD, DEFAULT_REVIEWS_THRESHOLD
from license_client import get_machine_hash, activate as lic_activate, validate as lic_validate, HeartbeatThread, end_session, load_license_state, save_license_state

class Bridge:
    def __init__(self, window):
        self.window = window
        self.mac = get_machine_hash()
        self.session = {"license_id": None, "token": None}
        self.hb_thread = None
        self.stop_event = threading.Event()
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
        }
        self._sum_price = 0.0
        self._sum_pinned = 0.0
        self._sum_count = 0

    def getMachineHash(self):
        return self.mac

    def pickDirectory(self):
        try:
            path = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if path and isinstance(path, list):
                path = path[0]
            if path:
                self.state["exportDir"] = path
                cfg = {"client": {"export_dir": path}}
                try:
                    with open(os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "PDDScraper", "app.ini"), "w", encoding="utf-8") as f:
                        f.write("[client]\nexport_dir=" + path)
                except Exception:
                    pass
            return {"status": "OK", "path": path or ""}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def activate(self, code):
        try:
            r = lic_activate(code, self.mac)
            if r.get("status") == "OK":
                save_license_state({"license_key": code, "license_id": r.get("license_id")})
            return r
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def validate(self):
        st = load_license_state()
        key = st.get("license_key")
        if not key:
            return {"status": "NO_KEY"}
        try:
            r = lic_validate(key, self.mac)
            if r.get("status") == "OK":
                self.session["license_id"] = r.get("license_id")
                self.session["token"] = r.get("session_token")
                if self.hb_thread:
                    try:
                        self.hb_thread.stop()
                    except Exception:
                        pass
                self.hb_thread = HeartbeatThread(r.get("license_id"), self.mac, r.get("session_token"), interval=30)
                self.hb_thread.start()
            return r
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def endSession(self):
        if not (self.session.get("license_id") and self.session.get("token")):
            return {"status": "NO_SESSION"}
        try:
            r = end_session(self.session["license_id"], self.mac, self.session["token"])
            if r.get("status") == "OK":
                if self.hb_thread:
                    try:
                        self.hb_thread.stop()
                    except Exception:
                        pass
                self.session["token"] = None
            return r
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def startScrape(self, params):
        try:
            self.state["keyword"] = (params.get("keyword") or DEFAULT_KEYWORD).strip()
            self.state["price"] = float(params.get("price") or DEFAULT_PRICE_THRESHOLD)
            self.state["pinned"] = float(params.get("pinned") or DEFAULT_PINNED_THRESHOLD)
            self.state["reviews"] = int(params.get("reviews") or DEFAULT_REVIEWS_THRESHOLD)
            self.state["exportDir"] = params.get("exportDir") or self.state.get("exportDir") or ""
        except Exception:
            return {"status": "ERROR", "message": "参数错误"}
        if not self.state["exportDir"]:
            return {"status": "NO_EXPORT_DIR"}
        st = load_license_state()
        if not st.get("license_key"):
            return {"status": "NO_KEY"}
        try:
            r = lic_validate(st["license_key"], self.mac)
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
        if r.get("status") != "OK":
            return r
        self.stop_event.clear()
        self.state["status"] = "running"
        self._sum_price = 0.0
        self._sum_pinned = 0.0
        self._sum_count = 0
        out_path = os.path.join(self.state["exportDir"], "pdd_results.xlsx")
        self.state["outfile"] = out_path
        def on_item(item):
            try:
                self._sum_price += float(item.get("price") or 0)
                self._sum_pinned += float(item.get("pinned") or 0)
                self._sum_count += 1
                self.state["avg_price"] = self._sum_price / max(1, self._sum_count)
                self.state["avg_pinned"] = self._sum_pinned / max(1, self._sum_count)
                self.window.evaluate_js("window.__onItem && window.__onItem(" + json.dumps(item) + ")")
            except Exception:
                pass
        def on_progress(info):
            try:
                self.state.update({
                    "visited": info.get("visited", 0),
                    "collected": info.get("collected", 0),
                    "filtered": info.get("filtered", 0),
                    "list_count": info.get("list_count", 0),
                    "batch_progress": info.get("batch_progress", "0/0"),
                })
                payload = dict(info)
                payload["avg_price"] = self.state["avg_price"]
                payload["avg_pinned"] = self.state["avg_pinned"]
                payload["outfile"] = self.state.get("outfile", "")
                self.window.evaluate_js("window.__onProgress && window.__onProgress(" + json.dumps(payload) + ")")
            except Exception:
                pass
        def worker():
            try:
                run_scraper(self.state["keyword"], self.state["price"], self.state["pinned"], self.state["reviews"], on_item=on_item, on_progress=on_progress, stop_event=self.stop_event, output_path=out_path)
            except Exception:
                pass
            finally:
                self.state["status"] = "idle"
                try:
                    self.window.evaluate_js("window.__onStatus && window.__onStatus('idle')")
                except Exception:
                    pass
        threading.Thread(target=worker, daemon=True).start()
        return {"status": "OK"}

    def stopScrape(self):
        self.stop_event.set()
        self.state["status"] = "stopped"
        try:
            self.window.evaluate_js("window.__onStatus && window.__onStatus('stopped')")
        except Exception:
            pass
        return {"status": "OK"}

    def getState(self):
        s = dict(self.state)
        s["now"] = datetime.now().isoformat()
        return s

    def openFolder(self, path):
        try:
            p = path or self.state.get("outfile") or self.state.get("exportDir")
            if not p:
                return {"status": "NO_PATH"}
            if os.path.isfile(p):
                os.startfile(os.path.dirname(p))
            else:
                os.startfile(p)
            return {"status": "OK"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def exitApp(self):
        """Exit the application"""
        try:
            # End any active session first
            if self.session.get("license_id") and self.session.get("token"):
                end_session(self.session["license_id"], self.session["token"])
            
            # Destroy the window
            self.window.destroy()
            return {"status": "OK"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

def main():
    html_path = os.path.join(os.path.dirname(__file__), "webui", "index.html")
    window = webview.create_window("拼多多采集（授权版）", html_path, width=1200, height=900)
    api = Bridge(window)
    try:
        window.expose(api.getMachineHash)
        window.expose(api.pickDirectory)
        window.expose(api.activate)
        window.expose(api.validate)
        window.expose(api.endSession)
        window.expose(api.startScrape)
        window.expose(api.stopScrape)
        window.expose(api.getState)
        window.expose(api.openFolder)
        window.expose(api.exitApp)
    except Exception:
        pass
    webview.start(http_server=True, gui="edgechromium", debug=False)

if __name__ == "__main__":
    main()

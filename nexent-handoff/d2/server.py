import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AREA = "AREA-D2-DEMO"
DEVICE = "DEVICE-D2-DEMO"
TYPE = "walkway_violation"
BOUNDARY = datetime.fromisoformat("2026-11-24T00:00:00+08:00")
EVENTS = {
    "D2-OLD-001": ("2026-11-23T10:00:00+08:00", "WO-D2-OLD"),
    "D2-NEW-001": ("2026-11-24T10:00:00+08:00", "WO-D2-NEW"),
    "D2-MISSING-001": ("2026-11-24T11:00:00+08:00", "WO-D2-MISSING"),
}
TOOLS = {
    "get_event_evidence": (("event_id",), "Get replay evidence for a simulated event ID."),
    "lookup_applicable_rule": (("event_type", "area_id", "occurred_at"), "Get the SOP version and required evidence at event time."),
    "get_work_order": (("device_id", "area_id", "occurred_at"), "Find the fixture work order for the device, area and event time."),
    "get_permit": (("work_order_id", "area_id", "occurred_at"), "Find the matching permit for the work order, area and event time."),
}
def found(facts, evidence):
    return {"status": "ok", "facts": facts, "evidence": [evidence]}

def missing():
    return {"status": "not_found", "facts": {}, "evidence": []}

def execute(name, args):
    if name == "get_event_evidence":
        event_id = args["event_id"]
        if event_id not in EVENTS:
            return missing()
        return found({
            "event_id": event_id, "event_type": TYPE, "area_id": AREA,
            "device_id": DEVICE, "occurred_at": EVENTS[event_id][0],
            "assessment": "通道越界候选，尚未核验区域边界",
            "observation": "绿背心人员沿黄色标线一侧的设备通道行走，右侧绿色通道为空",
            "association_is_simulated": True,
        }, {"asset_id": "VID-SAFE-0_te23",
            "source_uri": "saferaw://test/0_safe_walkway_violation/0_te23.mp4",
            "start_ms": 500, "end_ms": 7000, "time_base": "original_video"})
    occurred = datetime.fromisoformat(args["occurred_at"])
    if occurred.tzinfo is None:
        raise ValueError("occurred_at must include a timezone")
    if args["area_id"] != AREA:
        return missing()
    if name == "lookup_applicable_rule":
        if args["event_type"] != TYPE:
            return missing()
        new = occurred >= BOUNDARY
        version = "v2" if new else "v1"
        clause = "D2-SOP-02" if new else "D2-SOP-01"
        return found({"rule_version": version, "clause_id": clause,
                      "required_evidence": ["work_order", "permit"] if new else ["work_order"],
                      "simulated": True}, {"asset_id": "SOP-D2-DEMO", "position": clause, "version": version})
    for timestamp, order in EVENTS.values():
        if occurred != datetime.fromisoformat(timestamp):
            continue
        if name == "get_work_order" and args["device_id"] == DEVICE:
            return found({"work_order_id": order, "state": "valid", "area_id": AREA,
                          "device_id": DEVICE, "simulated": True},
                         {"asset_id": "WORK-ORDERS-D2-DEMO", "record_id": order})
        if name == "get_permit" and order == args["work_order_id"] == "WO-D2-NEW":
            return found({"permit_id": "PERMIT-D2-NEW", "work_order_id": order,
                          "area_id": AREA, "state": "valid", "simulated": True},
                         {"asset_id": "PERMITS-D2-DEMO", "record_id": "PERMIT-D2-NEW"})
    return missing()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_error(405)

    def reply(self, status, payload=None):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else b""
        self.send_response(status)
        if data:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def do_POST(self):
        if self.path != "/mcp":
            self.reply(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 65536:
                self.reply(400)
                return
            req = json.loads(self.rfile.read(length))
            method = req["method"]
            params = req.get("params", {})
        except (ValueError, KeyError, TypeError):
            self.reply(400)
            return
        if "id" not in req:
            self.reply(202)
            return
        response = {"jsonrpc": "2.0", "id": req["id"]}
        try:
            if method == "initialize":
                version = params.get("protocolVersion")
                supported = ("2025-03-26", "2025-06-18", "2025-11-25")
                result = {"protocolVersion": version if version in supported else supported[-1],
                          "capabilities": {"tools": {}},
                          "serverInfo": {"name": "workshop-safety-d2", "version": "1.0.0"}}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": [
                    {"name": name, "description": desc, "inputSchema": {
                        "type": "object", "properties": {key: {"type": "string"} for key in keys},
                        "required": list(keys), "additionalProperties": False}}
                    for name, (keys, desc) in TOOLS.items()]}
            elif method == "tools/call":
                name, args = params["name"], params["arguments"]
                keys, _ = TOOLS[name]
                if set(args) != set(keys) or any(not isinstance(args[k], str) for k in keys):
                    raise ValueError("invalid tool arguments")
                value = execute(name, args)
                result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}
            else:
                response["error"] = {"code": -32601, "message": "Method not found"}
                result = None
            if result is not None:
                response["result"] = result
        except (KeyError, ValueError, TypeError):
            response["error"] = {"code": -32602, "message": "Invalid params"}
        self.reply(200, response)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", default=18082, type=int)
    config = parser.parse_args()
    with ThreadingHTTPServer((config.bind, config.port), Handler) as server:
        print(f"MCP ready at http://{config.bind}:{config.port}/mcp", flush=True)
        server.serve_forever()

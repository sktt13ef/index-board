from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from stock_data import StockDataProvider

app = Flask(__name__)
app.config["SECRET_KEY"] = "stock-dashboard-secret"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化数据提供者
stock_provider = StockDataProvider(socketio)


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/stocks")
def get_stocks():
    """获取所有股票数据API"""
    from flask import request

    force_refresh = request.args.get("refresh") == "1"
    data = stock_provider.get_all_indices(force_refresh=force_refresh)
    return jsonify(data)


@app.route("/api/stock/<key>")
def get_stock(key):
    """获取单个股票数据API"""
    data = stock_provider.get_all_indices()
    if key in data:
        return jsonify(data[key])
    return jsonify({"error": "Stock not found"}), 404


@app.route("/api/history/<key>")
def get_history(key):
    """获取历史数据API"""
    from flask import request
    period = request.args.get("period", "1mo")

    data = stock_provider.get_historical_data(key, period)
    return jsonify(data)


@app.route("/api/valuation/<key>")
def get_valuation(key):
    """获取指数估值数据API"""
    data = stock_provider.get_valuation_data(key)
    if data:
        return jsonify(data)
    return jsonify({"error": "Valuation data not available"}), 404


@app.route("/api/valuations")
def get_all_valuations():
    """获取所有指数估值数据API"""
    return jsonify(stock_provider._valuation_cache)


@app.route("/api/admin/update-pe", methods=["POST"])
def admin_update_pe():
    """手动触发PE数据更新API（需要管理员权限）"""
    from flask import request
    
    # 简单的密钥验证（生产环境应该使用更安全的认证）
    secret_key = request.headers.get("X-Admin-Key")
    if secret_key != "stock-dashboard-admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        import subprocess
        import sys
        
        # 运行更新脚本
        result = subprocess.run(
            [sys.executable, "update_pe_data.py", "--force"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            # 重新加载估值缓存
            stock_provider.update_valuation_cache()
            return jsonify({
                "success": True,
                "message": "PE数据更新成功",
                "output": result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout
            })
        else:
            return jsonify({
                "success": False,
                "message": "PE数据更新失败",
                "error": result.stderr
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新异常: {str(e)}"
        }), 500


@app.route("/api/admin/pe-config")
def get_pe_config():
    """获取当前PE配置API"""
    try:
        import json
        import os
        
        config_file = "pe_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            return jsonify({"message": "配置文件不存在"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@socketio.on("connect")
def handle_connect():
    """客户端连接"""
    print("客户端已连接")
    # 发送当前数据
    data = stock_provider.get_all_indices()
    emit("stock_update", data)


@socketio.on("disconnect")
def handle_disconnect():
    """客户端断开"""
    print("客户端已断开")


@socketio.on("request_update")
def handle_request_update():
    """客户端请求更新"""
    data = stock_provider.get_all_indices(force_refresh=True)
    emit("stock_update", data)


if __name__ == "__main__":
    import threading
    # 先做快速的快照（价格行情，秒级）
    stock_provider.get_all_indices(force_refresh=True)
    # 估值缓存可能首次拉很久（10 年中债等），放后台慢慢跑
    threading.Thread(
        target=stock_provider.update_valuation_cache,
        daemon=True,
    ).start()
    stock_provider.start_auto_update(interval=30)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)

import os

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from stock_data import StockDataProvider
from market_cache import get_market_cache
from market_sources import get_source_registry


def downsample_history(rows, max_points):
    """Preserve first/last and local high/low points while limiting chart payload."""
    if not max_points or max_points <= 0 or len(rows) <= max_points:
        return rows
    if max_points < 8:
        return rows[:max_points]

    bucket_count = max(1, (max_points - 2) // 2)
    middle = list(enumerate(rows[1:-1], start=1))
    bucket_size = max(1, (len(middle) + bucket_count - 1) // bucket_count)
    selected = {0: rows[0], len(rows) - 1: rows[-1]}

    for start in range(0, len(middle), bucket_size):
        bucket = middle[start : start + bucket_size]
        if not bucket:
            continue
        min_index, min_row = min(bucket, key=lambda item: float(item[1].get("close") or 0))
        max_index, max_row = max(bucket, key=lambda item: float(item[1].get("close") or 0))
        selected[min_index] = min_row
        selected[max_index] = max_row

    return [selected[index] for index in sorted(selected)]


def _clean_history_rows(rows):
    cleaned = []
    for row in rows or []:
        try:
            date = row.get("date")
            close = float(row.get("close"))
        except (TypeError, ValueError, AttributeError):
            continue
        if not date or close <= 0:
            continue
        cleaned.append({"date": date, "raw": close})
    return sorted(cleaned, key=lambda item: item["date"])


def _normalize_history_rows(rows, base_raw, start_date=None, end_date=None):
    result = []
    for row in rows:
        if start_date and row["date"] < start_date:
            continue
        if end_date and row["date"] > end_date:
            continue
        value = row["raw"] / base_raw * 100
        result.append({
            "date": row["date"],
            "close": round(value, 4),
            "raw": row["raw"],
        })
    return result


def build_compare_history(price_rows, total_rows, max_points):
    """Normalize two series on their full overlapping range before downsampling."""
    price = _clean_history_rows(price_rows)
    total = _clean_history_rows(total_rows)
    if not price and not total:
        return {"price": [], "total": [], "note": ""}

    if price and total:
        start_date = max(price[0]["date"], total[0]["date"])
        end_date = min(price[-1]["date"], total[-1]["date"])
        if start_date > end_date:
            return {"price": [], "total": [], "note": "两条线没有共同日期，不能做收益对比。"}
        price_base = next((row for row in price if start_date <= row["date"] <= end_date), None)
        total_base = next((row for row in total if start_date <= row["date"] <= end_date), None)
        if not price_base or not total_base:
            return {"price": [], "total": [], "note": "两条线没有共同日期，不能做收益对比。"}
        return {
            "price": downsample_history(
                _normalize_history_rows(price, price_base["raw"], start_date, end_date),
                max_points,
            ),
            "total": downsample_history(
                _normalize_history_rows(total, total_base["raw"], start_date, end_date),
                max_points,
            ),
            "note": f"共同区间 {start_date} 起，首个可用点=100",
        }

    if price:
        return {
            "price": downsample_history(_normalize_history_rows(price, price[0]["raw"]), max_points),
            "total": [],
            "note": "仅有指数收益曲线可用，按首日=100展示。",
        }

    return {
        "price": [],
        "total": downsample_history(_normalize_history_rows(total, total[0]["raw"]), max_points),
        "note": "仅有第二条曲线可用，按首日=100展示。",
    }

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("STOCK_DASHBOARD_SECRET_KEY") or os.urandom(32)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化数据提供者
stock_provider = StockDataProvider(socketio)


@app.route("/")
def index():
    """主页"""
    return render_template("index.html", page_title="市场看板", brand_sub="")


@app.route("/design-preview")
def design_preview():
    """UI design preview."""
    return render_template("design_preview.html", page_title="市场看板 UI 设计稿", brand_sub="设计稿")


@app.after_request
def add_no_cache_headers(response):
    """Keep the dashboard from serving stale inline JavaScript after local edits."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
    series = request.args.get("series", "price")
    try:
        max_points = int(request.args.get("max_points", "0") or 0)
    except ValueError:
        max_points = 0

    data = stock_provider.get_historical_data(key, period, series=series)
    return jsonify(downsample_history(data, max_points))


@app.route("/api/history")
def get_history_query():
    """Query-string compatible history API: /api/history?symbol=CSI300&period=1y."""
    from flask import request

    key = request.args.get("symbol") or request.args.get("key")
    if not key:
        return jsonify({"error": "symbol is required"}), 400
    period = request.args.get("period", "1mo")
    series = request.args.get("series", "price")
    try:
        max_points = int(request.args.get("max_points", "0") or 0)
    except ValueError:
        max_points = 0

    data = stock_provider.get_historical_data(key, period, series=series)
    return jsonify(downsample_history(data, max_points))


@app.route("/api/history-compare/<key>")
def get_history_compare(key):
    """Return normalized compare curves, calculated before chart downsampling."""
    from flask import request

    period = request.args.get("period", "1mo")
    try:
        max_points = int(request.args.get("max_points", "0") or 0)
    except ValueError:
        max_points = 0

    price_rows = stock_provider.get_historical_data(key, period, series="price")
    total_rows = stock_provider.get_historical_data(key, period, series="total_return")
    return jsonify(build_compare_history(price_rows, total_rows, max_points))


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


@app.route("/api/cache/status")
def get_cache_status():
    """查看本地 SQLite 缓存状态。"""
    return jsonify(get_market_cache().status())


@app.route("/api/source-registry")
def get_source_registry_api():
    """Canonical source registry for audit/debug pages."""
    return jsonify(get_source_registry())


@app.route("/api/admin/update-pe", methods=["POST"])
def admin_update_pe():
    """手动触发PE数据更新API（需要管理员权限）"""
    from flask import request
    
    admin_key = os.environ.get("STOCK_DASHBOARD_ADMIN_KEY")
    if not admin_key:
        return jsonify({"error": "Admin endpoint disabled; set STOCK_DASHBOARD_ADMIN_KEY to enable it"}), 503

    secret_key = request.headers.get("X-Admin-Key")
    if secret_key != admin_key:
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
    # 启动时优先使用本地 SQLite 缓存；缺失或过期的标的才回源。
    stock_provider.get_all_indices(force_refresh=False)
    # 估值缓存可能首次拉很久（10 年中债等），放后台慢慢跑
    threading.Thread(
        target=stock_provider.update_valuation_cache,
        daemon=True,
    ).start()
    stock_provider.start_auto_update(interval=30)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)

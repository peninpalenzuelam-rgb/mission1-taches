from flask import Flask, render_template, request, redirect, url_for, abort
from pathlib import Path
from flask import jsonify
import json
import shutil
from datetime import datetime

app = Flask(__name__)
print("✅ LOADED:", __file__)
DATA_FILE = Path("tasks.json")

BACKUP_DIR = Path("backups")
CONFIG_FILE = Path("config.json")

TODAY_FILE = Path("today.json")


DEFAULT_CONFIG = {
    "keep_backups": 30,
    "port": 5001,
}


def load_tasks():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def load_config():
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        cfg = DEFAULT_CONFIG.copy()
        cfg.update({k: data[k] for k in DEFAULT_CONFIG.keys() if k in data})
        return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()
    

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def prune_backups(keep=30):
    if not BACKUP_DIR.exists():
        return
    files = sorted(BACKUP_DIR.glob("tasks-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[keep:]:
        f.unlink()


def backup_tasks_file():
    if DATA_FILE.exists():
        BACKUP_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(DATA_FILE, BACKUP_DIR / f"tasks-{stamp}.json")
        cfg = load_config()
        prune_backups(int(cfg.get("keep_backups", 30)))


def save_tasks(tasks):
    backup_tasks_file()
    DATA_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def ordered_items(tasks):
    return sorted(
        list(enumerate(tasks)),
        key=lambda it: (it[1].get("done", False), it[1].get("pos", 10**9)),
    )

@app.get("/")
def index():
    q = (request.args.get("q") or "").strip().lower()
    
    tasks = load_tasks()
    items = ordered_items(tasks)
    
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("done"))
    todo = total - done

    filtered_items = items
    if q:
       filtered_items = [(i, t) for (i, t) in items if q in (t.get("title", "").lower())] 
    
    filtered_total = len(filtered_items)
    filtered_done = sum(1 for _, t in filtered_items if t.get("done"))
    filtered_todo = filtered_total - filtered_done
    
    return render_template(
        "index.html",
        items=filtered_items, 
        q=q,
        total=total, done=done, todo=todo,
        filtered_total=filtered_total, filtered_done=filtered_done, filtered_todo=filtered_todo
)


@app.post("/add")
def add():
    title = request.form.get("title", "").strip()
    if title:
        tasks = load_tasks()
        max_pos = max((t.get("pos", 0) for t in tasks), default=0)
        tasks.append({"title": title, "done": False, "pos": max_pos + 10})
        save_tasks(tasks)
    return redirect(url_for("index"))

@app.post("/toggle/<int:display_id>")
def toggle(display_id):
    tasks = load_tasks()
    items = ordered_items(tasks)
    if 1 <= display_id <= len(items):
        real_i, _ = items[display_id - 1]
        tasks[real_i]["done"] = not bool(tasks[real_i].get("done"))
        save_tasks(tasks)
    return redirect(url_for("index"))


@app.post("/delete/<int:display_id>")
def delete(display_id):
    tasks = load_tasks()
    items = ordered_items(tasks)
    if 1 <= display_id <= len(items):
        real_i, _ = items[display_id - 1]
        tasks.pop(real_i)
        save_tasks(tasks)
    return redirect(url_for("index"))


@app.post("/edit/<int:display_id>")
def edit(display_id):
    new_title = request.form.get("title", "").strip()
    tasks = load_tasks()
    items = ordered_items(tasks)
    if new_title and 1 <= display_id <= len(items):
        real_i, _ = items[display_id - 1]
        tasks[real_i]["title"] = new_title
        save_tasks(tasks)
    return redirect(url_for("index"))

@app.post("/up/<int:display_id>")
def move_up(display_id):
    tasks = load_tasks()
    items = ordered_items(tasks)
    todo = [(real_i, t) for (real_i, t) in items if not t.get("done", False)]

    if 1 <= display_id <= len(items):
        real_i, t = items[display_id - 1]
        if t.get("done", False):
            return redirect(url_for("index"))

        pos_in_todo = next((k for k, (ri, _) in enumerate(todo) if ri == real_i), None)
        if pos_in_todo is None or pos_in_todo == 0:
            return redirect(url_for("index"))

        prev_real_i, _ = todo[pos_in_todo - 1]
        tasks[real_i]["pos"], tasks[prev_real_i]["pos"] = tasks[prev_real_i]["pos"], tasks[real_i]["pos"]
        save_tasks(tasks)

    return redirect(url_for("index"))


@app.post("/down/<int:display_id>")
def move_down(display_id):
    tasks = load_tasks()
    items = ordered_items(tasks)

    todo = [(real_i, t) for (real_i, t) in items if not t.get("done", False)]

    if 1 <= display_id <= len(items):
        real_i, t = items[display_id - 1]
        if t.get("done", False):
            return redirect(url_for("index"))

        pos_in_todo = next((k for k, (ri, _) in enumerate(todo) if ri == real_i), None)
        if pos_in_todo is None or pos_in_todo == len(todo) - 1:
            return redirect(url_for("index"))

        next_real_i, _ = todo[pos_in_todo + 1]
        tasks[real_i]["pos"], tasks[next_real_i]["pos"] = tasks[next_real_i]["pos"], tasks[real_i]["pos"]
        save_tasks(tasks)

    return redirect(url_for("index"))

from flask import Response
import csv
import io

@app.get("/export.csv")
def export_csv():
    tasks = load_tasks()
    items = ordered_items(tasks)

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["num", "title", "done", "pos"])

    for display_id, (real_i, t) in enumerate(items, start=1):
        writer.writerow([display_id, t.get("title", ""), t.get("done", False), t.get("pos", "")])

    return Response(
        out.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=tasks.csv"},
    )
@app.get("/backups")
def backups():
    BACKUP_DIR.mkdir(exist_ok=True)
    files = sorted(BACKUP_DIR.glob("tasks-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    items = []
    for p in files:
        st = p.stat()
        items.append({
            "name": p.name,
            "mtime": st.st_mtime,
            "size": st.st_size,
        })
    return render_template("backups.html", backups=items)


def safe_backup_path(name: str) -> Path:
    # Empêche les chemins du type ../../
    if "/" in name or "\\" in name:
        abort(400)
    if not (name.startswith("tasks-") and name.endswith(".json")):
        abort(400)

    p = (BACKUP_DIR / name).resolve()
    if p.parent != BACKUP_DIR.resolve():
        abort(400)
    if not p.exists():
        abort(404)
    return p


@app.post("/restore/<path:name>")
def restore_backup(name):
    src = safe_backup_path(name)

    # backup de l'état actuel avant d'écraser
    backup_tasks_file()

    # restaure
    shutil.copy2(src, DATA_FILE)

    return redirect(url_for("index"))

@app.get("/settings")
def settings():
    cfg = load_config()
    saved = request.args.get("saved") == "1"
    return render_template("settings.html", cfg=cfg, saved=saved)
    print("saved=", saved)

@app.post("/settings")
def settings_save():
    cfg = load_config()

    keep_raw = (request.form.get("keep_backups") or "").strip()
    port_raw = (request.form.get("port") or "").strip()

    if keep_raw.isdigit():
        keep = int(keep_raw)
        cfg["keep_backups"] = max(1, min(keep, 500))  # limite raisonnable
    if port_raw.isdigit():
        port = int(port_raw)
        cfg["port"] = max(1024, min(port, 65535))

    save_config(cfg)
    return redirect(url_for("settings", saved=1))




def load_today():
    if not TODAY_FILE.exists():
        return {"day_number": 1, "actions": [], "kpi_today": {"leads": 0, "sales": 0}}
    return json.loads(TODAY_FILE.read_text(encoding="utf-8"))


def save_today(data):
    TODAY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/today")
def today_page():
    data = load_today()
    # Top 3 actions (au cas où il y en a plus tard)
    actions = data.get("actions", [])[:3]
    kpi = data.get("kpi_today", {"leads": 0, "sales": 0})
    day_number = data.get("day_number", 1)
    return render_template("today.html", actions=actions, kpi=kpi, day_number=day_number)


@app.post("/today/action/<action_id>")
def today_toggle_action(action_id):
    data = load_today()
    for a in data.get("actions", []):
        if a.get("id") == action_id:
            a["done"] = not bool(a.get("done"))
            break
    save_today(data)
    return redirect(url_for("today_page"))


@app.post("/today/kpi")
def today_save_kpi():
    data = load_today()
    leads_raw = (request.form.get("leads") or "0").strip()
    sales_raw = (request.form.get("sales") or "0").strip()

    leads = int(leads_raw) if leads_raw.isdigit() else 0
    sales = int(sales_raw) if sales_raw.isdigit() else 0

    data["kpi_today"] = {"leads": leads, "sales": sales}
    save_today(data)
    return redirect(url_for("today_page"))


@app.post("/today/reset")
def today_reset():
    data = load_today()
    for a in data.get("actions", []):
        a["done"] = False
    data["kpi_today"] = {"leads": 0, "sales": 0}
    save_today(data)
    return redirect(url_for("today_page"))


if __name__ == "__main__":
    cfg = load_config()
    app.run(host="0.0.0.0", port=int(cfg.get("port", 5001)), debug=False)
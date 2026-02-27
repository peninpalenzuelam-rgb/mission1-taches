from flask import Flask, render_template, request, redirect, url_for, abort
from pathlib import Path
from flask import jsonify
import json
from flask import Response
import csv
import io
import shutil
from datetime import datetime

app = Flask(__name__)

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
    
    plan_progress = {"done": 0, "total": 0, "pct": 0}
    try:
        plan = load_plan()
        total_actions = 0
        done_actions = 0
        for d in plan.get("days", []):
            for it in d.get("items", []):
                total_actions += 1
                if it.get("done"):
                    done_actions += 1
        pct = int((done_actions / total_actions) * 100) if total_actions else 0
        plan_progress = {"done": done_actions, "total": total_actions, "pct": pct}
    except Exception:
        pass


    current_day = None
    try:
        plan = load_plan()
        for d in plan.get("days", []):
            items = d.get("items", [])
            if items and any(not it.get("done") for it in items):
                current_day = d.get("day")
                break
    except Exception:
        pass

    return render_template(
        "index.html",
        items=filtered_items, 
        q=q,
        total=total, done=done, todo=todo,
        filtered_total=filtered_total, filtered_done=filtered_done, filtered_todo=filtered_todo, plan_progress=plan_progress, current_day=current_day)


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

    backup_tasks_file()

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


PLAN_FILE = Path("plan.json")

def load_plan():
    if not PLAN_FILE.exists():
        return {"sector": "coiffeur", "week": 1, "days": []}
    return json.loads(PLAN_FILE.read_text(encoding="utf-8"))

def save_plan(plan):
    PLAN_FILE.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")



def get_current_day_from_plan(plan):
    for d in plan.get("days", []):
        items = d.get("items", [])
        if items and any(not it.get("done") for it in items):
            return d.get("day")
    return None


@app.get("/today")
def today_page():
    plan = load_plan()
    current_day = get_current_day_from_plan(plan)

    day_obj = None

    
    if current_day is None and plan.get("days"):
        day_obj = plan["days"][-1]
        current_day = day_obj.get("day")
    else:
        for d in plan.get("days", []):
            if d.get("day") == current_day:
                day_obj = d
                break

    actions = (day_obj.get("items", []) if day_obj else [])[:3]
    salon = load_salon()
    for a in actions:
        a["title"] = apply_salon(a.get("title",""), salon)
        a["script"] = apply_salon(a.get("script",""), salon)
    accroche = ""
    try:
        contenu = load_contenu()
        for dd in contenu.get("days", []):
            if dd.get("day") == (current_day or 1):
                accroche = dd.get("reel", {}).get("hook", "")
                break
        salon = load_salon()
        accroche = apply_salon(hook, salon)
    except Exception:
        accroche = ""
    return render_template("today.html", actions=actions, day_number=current_day or 1, current_day=current_day or 1, accroche=accroche)


@app.post("/today/action/<action_id>")
def today_toggle_action(action_id):
    plan = load_plan()

    for d in plan.get("days", []):
        for it in d.get("items", []):
            if it.get("id") == action_id:
                it["done"] = not bool(it.get("done"))
                save_plan(plan)
                return redirect(url_for("today_page"))

    return redirect(url_for("today_page"))


@app.post("/today/reset")
def today_reset():
    plan = load_plan()
    current_day = get_current_day_from_plan(plan)

    if current_day is None and plan.get("days"):
        current_day = plan["days"][-1].get("day")

    for d in plan.get("days", []):
        if d.get("day") == current_day:
            for it in d.get("items", []):
                it["done"] = False
            break

    save_plan(plan)
    return redirect(url_for("today_page"))


@app.get("/plan")
def plan_page():
    plan = load_plan()
    salon = load_salon()
    for d in plan.get("days", []):
        for it in d.get("items", []):
            it["title"] = apply_salon(it.get("title",""), salon)
            it["script"] = apply_salon(it.get("script",""), salon)
    return render_template("plan.html", plan=plan)

@app.post("/plan/toggle/<item_id>")
def plan_toggle(item_id):
    plan = load_plan()
    for d in plan.get("days", []):
        for it in d.get("items", []):
            if it.get("id") == item_id:
                it["done"] = not bool(it.get("done"))
                save_plan(plan)
                return redirect(url_for("plan_page"))
    return redirect(url_for("plan_page"))


SUIVI_FILE = Path("suivi.json")

def load_suivi():
    if not SUIVI_FILE.exists():
        return {"week": 1, "data": {"leads": 0, "bookings": 0, "noshow": 0, "revenue": 0, "reviews": 0}}
    return json.loads(SUIVI_FILE.read_text(encoding="utf-8"))

def save_suivi(suivi):
    SUIVI_FILE.write_text(json.dumps(suivi, ensure_ascii=False, indent=2), encoding="utf-8")

@app.get("/suivi")
def suivi_page():
    suivi = load_suivi()
    data = suivi.get("data", {})
    score = 0
    if data.get("bookings", 0) >= 5: score += 1
    if data.get("reviews", 0) >= 3: score += 1
    if data.get("noshow", 0) <= 2: score += 1
    return render_template("suivi.html", suivi=suivi, data=data, score=score)

@app.post("/suivi/save")
def suivi_save():
    suivi = load_suivi()
    d = suivi.get("data", {})

    def to_int(name):
        raw = (request.form.get(name) or "0").strip()
        return int(raw) if raw.lstrip("-").isdigit() else 0

    d["leads"] = max(0, to_int("leads"))
    d["bookings"] = max(0, to_int("bookings"))
    d["noshow"] = max(0, to_int("noshow"))
    d["revenue"] = max(0, to_int("revenue"))
    d["reviews"] = max(0, to_int("reviews"))

    suivi["data"] = d
    save_suivi(suivi)
    return redirect(url_for("suivi_page"))


CONTENU_FILE = Path("contenu.json")

def load_contenu():
    if not CONTENU_FILE.exists():
        return {"sector": "coiffeur", "week": 1, "days": []}
    return json.loads(CONTENU_FILE.read_text(encoding="utf-8"))

@app.get("/contenu")
def contenu_page():
    data = load_contenu()
    salon = load_salon()
    for d in data.get("days", []):
        d["reel"]["hook"] = apply_salon(d["reel"].get("hook",""), salon)
        d["reel"]["script"] = apply_salon(d["reel"].get("script",""), salon)
        d["post"]["title"] = apply_salon(d["post"].get("title",""), salon)
        d["post"]["caption"] = apply_salon(d["post"].get("caption",""), salon)
        d["post"]["visual"] = apply_salon(d["post"].get("visual",""), salon)
        d["story"]["slides"] = [apply_salon(s, salon) for s in d["story"].get("slides", [])]
        
    reseau = salon.get("reseau_1", "Instagram")
    return render_template("contenu.html", contenu=data, salon=salon, reseau=reseau)

SALON_FILE = Path("salon.json")

def load_salon():
    if not SALON_FILE.exists():
        return {"nom_salon": "Mon salon", "ville": "", "telephone": "", "lien_avis_google": "", "cta": "DM RDV", "reseau_1": "Instagram",
            "reseau_2": "Google",
            "reseau_3": "Facebook"}
    
    salon = json.loads(SALON_FILE.read_text(encoding="utf-8"))
    salon.setdefault("reseau_1", "Instagram")
    salon.setdefault("reseau_2", "Google")
    salon.setdefault("reseau_3", "Facebook")
    return salon


def save_salon(data):
    SALON_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def apply_salon(text, salon):
    if not isinstance(text, str):
        return text
    return (text
        .replace("[VILLE]", salon.get("ville","") or "[VILLE]")
        .replace("[LIEN]", salon.get("lien_avis_google","") or "[LIEN]")
        .replace("[téléphone/DM]", salon.get("telephone","") or (salon.get("cta","DM RDV")))
        .replace("[OFFRE]", "Offre du moment")  # optionnel, on pourra le rendre configurable
    )

@app.get("/salon")
def salon_page():
    salon = load_salon()
    saved = request.args.get("saved") == "1"
    return render_template("salon.html", salon=salon, saved=saved)

@app.post("/salon")
def salon_save():
    salon = load_salon()
    salon["nom_salon"] = (request.form.get("nom_salon") or "").strip() or "Mon salon"
    salon["ville"] = (request.form.get("ville") or "").strip()
    salon["telephone"] = (request.form.get("telephone") or "").strip()
    salon["lien_avis_google"] = (request.form.get("lien_avis_google") or "").strip()
    salon["cta"] = (request.form.get("cta") or "").strip() or "DM RDV"

    salon["reseau_1"] = (request.form.get("reseau_1") or "").strip() or "Instagram"
    salon["reseau_2"] = (request.form.get("reseau_2") or "").strip() or "Google"
    salon["reseau_3"] = (request.form.get("reseau_3") or "").strip() or "Facebook"

    save_salon(salon)
    return redirect(url_for("salon_page", saved=1))

if __name__ == "__main__":
    cfg = load_config()
    app.run(host="0.0.0.0", port=int(cfg.get("port", 5001)), debug=False)
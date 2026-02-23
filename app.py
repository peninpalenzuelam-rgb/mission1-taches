from flask import Flask, render_template, request, redirect, url_for
import json
from pathlib import Path

app = Flask(__name__)
DATA_FILE = Path("tasks.json")


def load_tasks():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_tasks(tasks):
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)

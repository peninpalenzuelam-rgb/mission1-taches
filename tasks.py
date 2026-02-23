import json
from pathlib import Path

DATA_FILE = Path("tasks.json")


def load_tasks():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_tasks(tasks):
    DATA_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_tasks(tasks):
    if not tasks:
        print("Aucune tâche.")
        return

    ordered = sorted(tasks, key=lambda t: (t.get("done", False), t.get("title", "")))
    for i, t in enumerate(ordered, start=1):
        mark = "✅" if t.get("done") else "⬜️"
        print(f"{i}. {mark} {t.get('title','')}")
        


def ask_index(tasks, prompt):
    if not tasks:
        print("Aucune tâche.")
        return None
    raw = input(prompt).strip()
    if not raw.isdigit():
        print("❌ Entrez un numéro.")
        return None
    idx = int(raw) - 1
    if idx < 0 or idx >= len(tasks):
        print("❌ Numéro invalide.")
        return None
    return idx


def add_task(tasks):
    title = input("Nouvelle tâche : ").strip()
    if not title:
        print("❌ Tâche vide, annulé.")
        return
    tasks.append({"title": title, "done": False})
    save_tasks(tasks)
    print("✅ Ajoutée.")


def toggle_done(tasks):
    items = ordered_items(tasks)
    if not items:
        print("Aucune tâche.")
        return

    list_tasks(tasks)
    raw = input("Numéro de la tâche à (dé)cocher : ").strip()
    if not raw.isdigit():
        print("❌ Entrez un numéro.")
        return

    display_idx = int(raw) - 1
    if display_idx < 0 or display_idx >= len(items):
        print("❌ Numéro invalide.")
        return

    real_i, _ = items[display_idx]
    tasks[real_i]["done"] = not bool(tasks[real_i].get("done"))
    save_tasks(tasks)
    print("✅ Mise à jour.")


def delete_task(tasks):
    items = ordered_items(tasks)
    if not items:
        print("Aucune tâche.")
        return

    list_tasks(tasks)
    raw = input("Numéro de la tâche à supprimer : ").strip()
    if not raw.isdigit():
        print("❌ Entrez un numéro.")
        return

    display_idx = int(raw) - 1
    if display_idx < 0 or display_idx >= len(items):
        print("❌ Numéro invalide.")
        return

    real_i, t = items[display_idx]   # <-- LE "MAPPING" est ici
    removed = tasks.pop(real_i)
    save_tasks(tasks)
    print(f"🗑️ Supprimée : {removed.get('title','')}")


def reset_all(tasks):
    for t in tasks:
        t["done"] = False
    save_tasks(tasks)
    print("🔄 Tout est repassé à ⬜️.")


def show_stats(task):
    total = len(task)
    done = sum(1 for t in task if t.get("done"))
    todo = total - done 
    print(f"Total: {total}")
    print(f"Faites: {done}")
    print(f"Á faire: {todo}")


def edit_task(tasks):
    items = ordered_items(tasks)
    if not items:
        print("Aucune tâche.")
        return

    list_tasks(tasks)
    raw = input("Numéro de la tâche à éditer : ").strip()
    if not raw.isdigit():
        print("❌ Entrez un numéro.")
        return

    display_idx = int(raw) - 1
    if display_idx < 0 or display_idx >= len(items):
        print("❌ Numéro invalide.")
        return

    real_i, _ = items[display_idx]   # <-- MAPPING affichage -> vrai index

    new_title = input("Nouveau titre : ").strip()
    if not new_title:
        print("❌ Titre vide, annulé.")
        return

    tasks[real_i]["title"] = new_title
    save_tasks(tasks)
    print("✅ Tâche modifiée.")
    
def main():
    tasks = load_tasks()

    while True:
        print("\n--- TASKS v1 ---")
        print("A) Ajouter")
        print("L) Lister")
        print("C) (Dé)cocher")
        print("D) Supprimer")
        print("R) Reset (tout décocher)")
        print("S) Stats")
        print("E) Éditer")
        print("Q) Quitter")

        choice = input("> ").strip().lower()

        if choice in ("a", "1"):
            add_task(tasks)
            tasks = load_tasks()
        elif choice in ("l", "2"):
            list_tasks(tasks)
        elif choice in ("c", "3"):
            toggle_done(tasks)
            tasks = load_tasks()
        elif choice in ("d",):
            delete_task(tasks)
            tasks = load_tasks()
        elif choice in ("r",):
            reset_all(tasks)
            tasks = load_tasks()
        elif choice in ("s",):
            show_stats(tasks)
            tasks = load_tasks()
        elif choice in ("e,"):
            edit_task(tasks)
            tasks = load_tasks()
        elif choice in ("q", "4"):
            print("Bye.")
            break
        else:
            print("❌ Choix invalide.")
def ordered_items(tasks):
    # retourne une liste de tuples: (index_original, task)
    return sorted(
        list(enumerate(tasks)),
        key=lambda it: (it[1].get("done", False), it[1].get("title", "")),
    )

def list_tasks(tasks):
    items = ordered_items(tasks)
    if not items:
        print("Aucune tâche.")
        return
    for display_i, (real_i, t) in enumerate(items, start=1):
        mark = "✅" if t.get("done") else "⬜️"
        print(f"{display_i}. {mark} {t.get('title','')}")


if __name__ == "__main__":
    main()
      
      

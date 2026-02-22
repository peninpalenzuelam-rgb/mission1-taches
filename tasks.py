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
    list_tasks(tasks)
    idx = ask_index(tasks, "Numéro de la tâche à (dé)cocher : ")
    if idx is None:
        return
    tasks[idx]["done"] = not bool(tasks[idx].get("done"))
    save_tasks(tasks)
    print("✅ Mise à jour.")


def delete_task(tasks):
    list_tasks(tasks)
    idx = ask_index(tasks, "Numéro de la tâche à supprimer : ")
    if idx is None:
        return
    removed = tasks.pop(idx)
    save_tasks(tasks)
    print(f"🗑️ Supprimée : {removed.get('title','')}")


def reset_all(tasks):
    for t in tasks:
        t["done"] = False
    save_tasks(tasks)
    print("🔄 Tout est repassé à ⬜️.")


def main():
    tasks = load_tasks()

    while True:
        print("\n--- TASKS ---")
        print("A) Ajouter")
        print("L) Lister")
        print("C) (Dé)cocher")
        print("D) Supprimer")
        print("R) Reset (tout décocher)")
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
        elif choice in ("q", "4"):
            print("Bye.")
            break
        else:
            print("❌ Choix invalide.")


if __name__ == "__main__":
    main()
    
    


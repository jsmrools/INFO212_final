from __future__ import annotations

# Small knowledge base
GOAL_BLOCKS = {
    "styrke": [
        ("Knebøy", "main"),
        ("Benkpress", "main"),
        ("Markløft", "main"),
        ("Skulderpress", "assist"),
        ("Roing med stang", "assist"),
    ],
    "hypertrofi": [
        ("Skrå benk m/manualer", "main"),
        ("Nedtrekk", "main"),
        ("Skulderpress", "assist"),
        ("Roing kabel", "assist"),
        ("Sidehev", "isolation"),
        ("Biceps curl", "isolation"),
        ("Triceps pushdown", "isolation"),
    ],
    "spenst": [
        ("Box jumps", "main"),
        ("Medisinball-kast", "main"),
        ("Hoppende utfall", "assist"),
        ("Kettlebell swing", "assist"),
        ("Kjerne – hollow hold", "isolation"),
    ],
    "utholdenhet": [
        ("Intervall (løp/sykkel/romaskin)", "main"),
        ("toes to bar", "main"),
        ("Goblet squat (lett)", "assist"),
        ("Pushups", "assist"),
        ("Planke", "isolation"),
    ],
}

LEVEL_TUNING = {
    "nybegynner": {"main": (3, "5–8"), "assist": (2, "8–12"), "isolation": (2, "12–15"), "rpe": "6–7"},
    "middels":    {"main": (4, "4–6"), "assist": (3, "8–10"), "isolation": (3, "12–15"), "rpe": "7–8"},
    "avansert":   {"main": (5, "3–5"), "assist": (4, "6–8"),  "isolation": (3, "10–12"), "rpe": "8–9"},
}

def _swap_for_gear(name: str, gear: str) -> str:
    lname = name.lower()
    if gear == "kroppsvekt":
        if "benk" in lname:      return "Pushups (variant)"
        if "mark" in lname:      return "Hip hinge (kroppsvekt)"
        if "skulderpress" in lname: return "Pike pushups"
        if "roing" in lname:     return "Invertert roing"
    if gear == "hjemme_enkle":
        if name == "Knebøy":     return "Goblet squat"
        if "nedtrekk" in lname:  return "Pull-aparts / ettarms roing m/manual"
    return name

def _time_cap(goal: str) -> int:
    # rough cap: more isolation for hypertrophy, fewer items for strength
    return {"hypertrofi": 7, "styrke": 5, "spenst": 6, "utholdenhet": 5}.get(goal, 6)

def generate_plan(goal: str, level: str, gear: str):
    goal = goal if goal in GOAL_BLOCKS else "hypertrofi"
    level = level if level in LEVEL_TUNING else "nybegynner"
    blocks = GOAL_BLOCKS[goal]
    tune = LEVEL_TUNING[level]
    cap = _time_cap(goal)

    out = []
    for name, kind in blocks[:cap]:
        name = _swap_for_gear(name, gear)
        sets, reps = tune[kind]
        out.append({"name": name, "sets": sets, "reps": reps, "weight": 0})
    # Quality-of-life: finisher suggestion for longer sessions (stays compatible)
    if goal in ("hypertrofi", "utholdenhet") and len(out) < cap:
        out.append({"name": "Finisher: core/mobilitet", "sets": 1, "reps": "8–10 min", "weight": 0})
    return out

def generate_weekly_plan(goal: str, level: str, gear: str, days_per_week: int = 3):
    # reuse your existing blocks/tuning; simple split based on days
    days_per_week = max(2, min(5, int(days_per_week or 3)))
    meta = {"goal": goal, "level": level, "gear": gear, "days_per_week": days_per_week}

    splits = {
        2: [("Dag 1 – Helkropp", "full"), ("Dag 2 – Helkropp", "full")],
        3: [("Dag 1 – Overkropp", "upper"), ("Dag 2 – Underkropp", "lower"), ("Dag 3 – Helkropp", "full")],
        4: [("Dag 1 – Overkropp", "upper"), ("Dag 2 – Underkropp", "lower"),
            ("Dag 3 – Overkropp", "upper"), ("Dag 4 – Underkropp", "lower")],
        5: [(f"Dag {i} – Helkropp" if i==3 else f"Dag {i} – Fokus {['push','pull','legs','core','mixed'][i-1]}", "full")
            for i in range(1,6)]
    }
    slots = splits.get(days_per_week)

    week = {"meta": meta, "days": []}
    for name, focus in slots:
        ex_list = generate_plan(goal, level, gear)  # start from your single-day set
        # light filter to match focus
        if focus == "upper":
            ex_list = [e for e in ex_list if any(k in e["name"].lower() for k in ["benk","press","ro","pull","skuld","push"])]
        elif focus == "lower":
            ex_list = [e for e in ex_list if any(k in e["name"].lower() for k in ["kneb","mark","utfall","squat","hinge","swing"])]
        # add a finisher for variety on full body
        if focus == "full":
            ex_list = ex_list[:6] + [{"name": "Finisher: core/mobilitet", "time_min": 8}]
        week["days"].append({"name": name, "exercises": ex_list})
    return week


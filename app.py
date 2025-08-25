import os
import sqlite3
from typing import List, Optional, Tuple
from datetime import datetime
import uuid
from PIL import Image
import streamlit as st

# Percorsi
DB_PATH = "recipes.db"
IMG_DIR = ".streamlit/images"   # cartella sicura anche sul cloud
PLACEHOLDER_IMG = "assets/placeholder.png"

os.makedirs(IMG_DIR, exist_ok=True)

# ------------------------- DB LAYER -------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              ingredients TEXT NOT NULL,
              steps TEXT NOT NULL,
              tags TEXT DEFAULT '',
              prep_minutes INTEGER,
              image_path TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
        """)

def to_tag_list(tags_csv: str) -> List[str]:
    if isinstance(tags_csv, list):
        return [t.strip() for t in tags_csv if t.strip()]
    return [t.strip() for t in tags_csv.split("|") if t.strip()] if tags_csv else []

def from_tag_list(tags: List[str]) -> str:
    seen = set()
    ordered = []
    for t in tags:
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            ordered.append(t)
    return "|".join(ordered)

def list_all_tags(conn) -> List[str]:
    rows = conn.execute("SELECT tags FROM recipes").fetchall()
    tags = []
    for r in rows:
        tags.extend(to_tag_list(r["tags"]))
    return sorted(set(tags), key=lambda s: s.lower())

def create_recipe(title: str, ingredients: str, steps: str, tags: List[str],
                  prep_minutes: Optional[int], image_path: Optional[str]) -> int:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO recipes(title, ingredients, steps, tags, prep_minutes, image_path, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (title, ingredients, steps, from_tag_list(tags), prep_minutes, image_path, now, now))
        return cur.lastrowid

def update_recipe(recipe_id: int, title: str, ingredients: str, steps: str, tags: List[str],
                  prep_minutes: Optional[int], image_path: Optional[str]):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            UPDATE recipes
            SET title=?, ingredients=?, steps=?, tags=?, prep_minutes=?, image_path=?, updated_at=?
            WHERE id=?
        """, (title, ingredients, steps, from_tag_list(tags), prep_minutes, image_path, now, recipe_id))

def delete_recipe(recipe_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT image_path FROM recipes WHERE id=?", (recipe_id,)).fetchone()
        if row and row["image_path"] and os.path.exists(row["image_path"]):
            try:
                os.remove(row["image_path"])
            except Exception:
                pass
        conn.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))

def fetch_recipe(recipe_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()

def search_recipes(query: str, with_tags: List[str]) -> List[sqlite3.Row]:
    q = f"%{query.lower()}%" if query else "%"
    sql = "SELECT * FROM recipes WHERE lower(title) LIKE ? OR lower(ingredients) LIKE ? OR lower(steps) LIKE ?"
    params: Tuple = (q, q, q)
    if with_tags:
        tag_like = [f"%{t.lower()}%" for t in with_tags]
        tag_pred = " AND " + " AND ".join(["lower(tags) LIKE ?" for _ in tag_like])
        sql += tag_pred
        params += tuple(tag_like)
    sql += " ORDER BY updated_at DESC"
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()

# ------------------------- UI HELPERS -------------------------

def save_uploaded_image(file) -> Optional[str]:
    if not file:
        return None
    try:
        ext = os.path.splitext(file.name)[1].lower() or ".png"
        name = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(IMG_DIR, name)
        img = Image.open(file).convert("RGB")
        img.save(path)
        return path
    except Exception as e:
        st.error(f"Errore salvataggio immagine: {e}")
        return None

TAG_EMOJIS = {
    "Vegano": "🌱",
    "Vegetariano": "🥦",
    "Senza glutine": "🚫🌾",
    "Senza lattosio": "🥛❌",
    "Proteico": "💪",
    "Light": "✨",
    "Comfort food": "🛋️",
    "Antipasto": "🥟",
    "Primo": "🍝",
    "Secondo": "🥘",
    "Contorno": "🥗",
    "Piatto unico": "🍲",
    "Zuppa": "🍜",
    "Insalata": "🥬",
    "Snack": "🍿",
    "Dolce": "🍰",
    "Dessert": "🧁",
    "Bevanda": "🍹",
    "Panificati": "🍞",
    "Pizza": "🍕",
    "Estivo": "🌞",
    "Autunnale": "🍂",
    "Invernale": "❄️",
    "Primaverile": "🌸",
    "Fresco": "🍉",
    "Caldo": "🔥",
}

TAG_OPTIONS = list(TAG_EMOJIS.keys())

def emoji_for_tags(tags: List[str]) -> str:
    for tag in tags:
        clean_tag = tag.strip()
        emoji = TAG_EMOJIS.get(clean_tag)
        if emoji:
            return emoji
    return "🍽️"

def recipe_card(row: sqlite3.Row):
    cols = st.columns([1, 3])
    with cols[0]:
        if row["image_path"] and os.path.exists(row["image_path"]):
            st.image(row["image_path"], use_container_width=True)
        else:
            st.image(PLACEHOLDER_IMG, use_container_width=True)

    with cols[1]:
        emoji = emoji_for_tags(to_tag_list(row["tags"]))
        st.subheader(f"{emoji} {row['title']}")

        tag_badges = " ".join([f"`{t}`" for t in to_tag_list(row["tags"])])
        if tag_badges:
            st.markdown(tag_badges)

        meta = []
        if row["prep_minutes"]:
            meta.append(f"⏱️ {row['prep_minutes']} min")
        if meta:
            st.caption(" • ".join(meta))

        with st.expander("Ingredienti"):
            st.write(row["ingredients"])
        with st.expander("Preparazione"):
            st.write(row["steps"])

        edit_col, del_col = st.columns([1, 1])
        with edit_col:
            if st.button("✏️ Modifica", key=f"edit-{row['id']}"):
                st.session_state["edit_id"] = row["id"]
                st.rerun()
        with del_col:
            if st.button("🗑️ Elimina", key=f"del-{row['id']}"):
                delete_recipe(row["id"])
                st.success("Ricetta eliminata")
                st.rerun()

# ------------------------- APP -------------------------

st.set_page_config(page_title="50 sfumature di sugo", page_icon="🍝", layout="wide")
init_db()

st.title("🍳 Spadellando con Ale - Ricettario online")
st.caption("Cerca, aggiungi, modifica e condividi ricette.")

# Sidebar
with st.sidebar:
    st.header("Azioni")
    mode = st.radio("Modalità", ["Ricettario", "Carica una nuova ricetta!"], horizontal=True)
    with get_conn() as conn:
        all_tags = list_all_tags(conn)
    st.divider()

if st.session_state.get("show_balloons"):
    st.balloons()
    st.session_state["show_balloons"] = False

# --- Modalità crea/modifica ---
if mode == "Carica una nuova ricetta!" or st.session_state.get("edit_id"):
    editing_id = st.session_state.get("edit_id")
    st.subheader("✏️ Modulo ricetta")
    if editing_id:
        data = fetch_recipe(editing_id)
        if not data:
            st.error("Ricetta non trovata!")
            st.session_state["edit_id"] = None
            st.stop()
    else:
        data = None

    with st.form(key="recipe_form", clear_on_submit=False):
        title = st.text_input("Titolo", value=(data["title"] if data else ""))
        prep = st.number_input("Minuti di preparazione", min_value=0, value=int(data["prep_minutes"]) if data and data["prep_minutes"] else 0)
        tags_input = st.multiselect("Categorie", options=TAG_OPTIONS, default=to_tag_list(data["tags"]) if data else [])
        ingredients = st.text_area("Ingredienti", height=150, value=(data["ingredients"] if data else ""))
        steps = st.text_area("Preparazione", height=200, value=(data["steps"] if data else ""))
        image_file = st.file_uploader("Immagine", type=["png", "jpg", "jpeg", "webp"])
        submitted = st.form_submit_button("Salva")

        if submitted:
            if not title.strip() or not ingredients.strip() or not steps.strip():
                st.error("Titolo, ingredienti e preparazione sono obbligatori!")
            else:
                with st.spinner("Salvando la ricetta... ⏳"):
                    import time; time.sleep(2)
                    img_path = data["image_path"] if data else None
                    if image_file is not None:
                        img_path = save_uploaded_image(image_file)

                    if editing_id:
                        update_recipe(
                            editing_id,
                            title.strip(),
                            ingredients.strip(),
                            steps.strip(),
                            tags_input,
                            int(prep) if prep else None,
                            img_path
                        )
                        st.success("Ricetta aggiornata ✅")
                        st.session_state["edit_id"] = None
                    else:
                        rid = create_recipe(
                            title.strip(),
                            ingredients.strip(),
                            steps.strip(),
                            tags_input,
                            int(prep) if prep else None,
                            img_path
                        )
                        st.success("Ricetta salvata ✅")
                
                st.session_state["show_balloons"] = True
                st.session_state["edit_id"] = None
                st.rerun()

# --- Modalità visualizza ---
else:
    st.subheader("🔎 Cerca ricette")
    qcol, tcol = st.columns([2,2])
    with qcol:
        query = st.text_input("Testo libero", placeholder="es. pesto, cioccolato, vegano…")
    with tcol:
        with get_conn() as conn:
            tags_pick = st.multiselect("Filtra per tag", options=list_all_tags(conn))

    results = search_recipes(query, tags_pick)
    st.caption(f"Trovate {len(results)} ricette")
    st.divider()

    if not results:
        st.info("Nessuna ricetta trovata. Aggiungine una dal menù laterale!")
    else:
        for row in results:
            recipe_card(row)

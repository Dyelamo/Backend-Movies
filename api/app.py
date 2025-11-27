from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from api.email_sender import enviar_email_recomendaciones

app = FastAPI(title="🎬 API Recomendador de Películas - MovieLens (Híbrido)")

# ===========================================================
# 🔐 Configuración CORS para permitir acceso desde React
# ===========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes limitar a ["http://localhost:5173"] si usas Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================
# 🧩 Cargar modelo y dataset al iniciar el servidor
# ===========================================================
with open("models/svd_model_conTODO.pkl", "rb") as f:
    model = pickle.load(f)

movies_df = pd.read_csv("data/movies.csv")

# ===========================================================
# 🔥 EXTRAER MATRIZ LATENTE DE PELÍCULAS DEL MODELO SVD
# ===========================================================
Q = model.qi  # matriz latente de películas

movieId_to_innerId = {}
for raw_id in model.trainset._raw2inner_id_items:
    try:
        movieId_to_innerId[int(raw_id)] = model.trainset.to_inner_iid(raw_id)
    except:
        pass


def similitud_latente(movie_id, favoritos_ids):
    """Similitud coseno entre factores latentes del modelo SVD."""
    if movie_id not in movieId_to_innerId:
        return 0

    vec_mov = Q[movieId_to_innerId[movie_id]].reshape(1, -1)

    sims = []
    for fid in favoritos_ids:
        if fid in movieId_to_innerId:
            vec_fav = Q[movieId_to_innerId[fid]].reshape(1, -1)
            sim = cosine_similarity(vec_mov, vec_fav)[0][0]
            sims.append(sim)

    return float(np.mean(sims)) if sims else 0





# ===========================================
# Generar matriz TF-IDF para contenido
# ===========================================
movies_df["genres_clean"] = movies_df["genres"].fillna("").apply(lambda g: g.replace("|", " "))

vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(movies_df["genres_clean"])

# Similaridad coseno entre todas las películas
def similitud_con_favoritos(favoritos_ids):
    """
    Calcula similitud TF-IDF solo entre las películas favoritas 
    y todas las películas. Optimizado para no consumir 60 GB.
    """
    indices_favoritos = [
        movies_df.index[movies_df["movieId"] == fid][0]
        for fid in favoritos_ids
    ]

    # TF-IDF solo de las favoritas
    tfidf_favs = tfidf_matrix[indices_favoritos]

    # Similaridad solo contra TODAS las películas
    sim_matrix = cosine_similarity(tfidf_favs, tfidf_matrix)

    return sim_matrix


def generar_vector_usuario(favoritos_ids, model):
    """
    Promedia los vectores latentes de las películas favoritas
    para construir un vector latente del usuario nuevo.
    """
    factores = model.qi  # matriz de películas (n_movies x n_factors)
    movie_to_index = {mid: idx for idx, mid in enumerate(model.trainset._raw2inner_id_items.keys())}

    vectors = []
    for mid in favoritos_ids:
        if mid in movie_to_index:
            idx = movie_to_index[mid]
            vectors.append(factores[idx])

    if not vectors:
        return None

    return np.mean(vectors, axis=0)



# ===========================================================
# Esquema de datos recibido desde React o Postman
# ===========================================================
class UserPreferences(BaseModel):
    email: str
    favoritos: list[str]
    categorias: list[str] | None = None
    top_n: int = 5

# ===========================================================
# Función auxiliar — Calcula afinidad de género
# ===========================================================
def calcular_afinidad_genero(genres_str, categorias_usuario):
    """
    Retorna 1 si al menos un género de la película coincide
    con los géneros seleccionados por el usuario, 0 si no.
    """
    if not categorias_usuario:
        return 0
    if not isinstance(genres_str, str):
        return 0
    generos_pelicula = genres_str.split("|")
    coincidencias = any(g in generos_pelicula for g in categorias_usuario)
    return 1 if coincidencias else 0



# ===========================================================
# Endpoint OMDb + SVD + Afinidad de géneros (VERSIÓN FINAL)
# ===========================================================

links_df = pd.read_csv("data/links.csv")

class PreferenciasOMDB(BaseModel):
    email: str
    imdb_ids: list[str]
    categorias: list[str] | None = None
    top_n: int = 10


def imdb_to_movieId(imdb_id: str):
    try:
        imdb_clean = imdb_id.replace("tt", "")
        imdb_num = int(imdb_clean.lstrip("0"))

        row = links_df[links_df["imdbId"] == imdb_num]

        if row.empty:
            row = links_df[links_df["imdbId"].astype(str) == imdb_clean]

        if row.empty:
            return None

        return int(row.iloc[0]["movieId"])
    except:
        return None


@app.post("/recomendar-omdb")
def recomendar_omdb(preferencias: PreferenciasOMDB):
    nuevo_user_id = 999998

    # 1️⃣ Convertir IMDb IDs a movieId
    favoritos_ids = []
    for imdb in preferencias.imdb_ids:
        mid = imdb_to_movieId(imdb)
        if mid is not None:
            favoritos_ids.append(mid)

    if len(favoritos_ids) == 0:
        return {"error": "Ninguno de los IMDb IDs existe en MovieLens."}

    # 2️⃣ Crear vector latente del usuario basado en favoritos
    user_vector = generar_vector_usuario(favoritos_ids, model)
    sim_matrix = similitud_con_favoritos(favoritos_ids)


    resultados = []

    for index, row in movies_df.iterrows():
        movie_id = row["movieId"]
        if movie_id in favoritos_ids:
            continue

        # ---------- Similitud latente ----------
        sim_lat = similitud_latente(movie_id, favoritos_ids)

        # ---------- SVD ----------
        pred_svd = model.predict(nuevo_user_id, movie_id).est

        # ---------- Afinidad por género ----------
        categorias = preferencias.categorias or []
        generos = str(row["genres"]).split("|")
        afinidad = 1 if any(g in generos for g in categorias) else 0

        # ---------- Similitud de contenido ----------
        sim_fav = max(sim_matrix[:, index])

        #  Score final profesional
        score = (
            0.55 * pred_svd +
            0.20 * sim_fav +
            0.15 * sim_lat +
            0.10 * afinidad
        )

        # Convertir a IMDb
        link_row = links_df[links_df["movieId"] == movie_id]
        imdb_num = str(link_row["imdbId"].values[0]).zfill(7)

        resultados.append({
            "titulo": row["title"],
            "movieId": movie_id,
            "imdb_id": imdb_num,
            "prediccion_svd": round(pred_svd, 3),
            "similitud_con_favoritos": round(sim_fav, 3),
            "afinidad_genero": afinidad,
            "similitud_latente": round(sim_lat, 3),
            "puntaje_final": round(score, 3)
        })

    recomendaciones = sorted(resultados, key=lambda x: x["puntaje_final"], reverse=True)[:preferencias.top_n]
    enviar_email_recomendaciones(preferencias.email, recomendaciones)

    return {
        "email": preferencias.email,
        "recomendaciones": recomendaciones
    }

# ===========================================================
# Ejecutar con: python -m uvicorn api.app:app --reload
# ===========================================================

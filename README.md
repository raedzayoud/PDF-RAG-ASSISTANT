# 📄 PDF-RAG-ASSISTANT

**Assistant conversationnel RAG full-stack** : posez n'importe quelle question — générale ou sur vos PDFs — et le chatbot décide lui-même si la réponse provient de ses connaissances ou de vos documents (avec citations `[fichier.pdf, page N]`).

> Angular 21 · FastAPI · PostgreSQL 16 · Groq (`openai/gpt-oss-20b`) · embeddings locaux (sentence-transformers)

---

## ✨ Fonctionnalités

| | |
|---|---|
| 🤖 **Chat hybride** | Question générale → connaissances du modèle ; question sur les documents → réponse fondée + citation de la page. CSV decision par le LLM lui-même (pas de routeur forcé). |
| 📎 **Upload PDF** | Chapman/Barre : drag & drop dans la barre latérale ou bouton 📎 → upload → réindexation automatique (chunking + embeddings + similarité cosinus). |
| 💬 **Sidebar ChatGPT** | Nouvelle discussion (*créée seulement au premier envoi*), liste de l'historique complet stocké en PostgreSQL, clic pour reprendre une conversation abandonnée — même après F5 ou plusieurs jours. |
| 🧠 **Mémoire conversationnelle** | Les 10 derniers tours de dialogue sont injectés dans le prompt (`HISTORY_MESSAGES`), les tours complets persistés en base. |
| 🕐 **Session persistée** | `sessionId` en `localStorage` → historique recharge automatiquement. |
| 🎨 **UI light épurée** | Bulles animées, indicateur « typing », toasts, dropzone visuelle, design 100 % CSS (aucune lib UI). |
| 🧪 **Unit testé** | Vitest (frontend), structure prête pour pytest (backend). |

---

## 🏗 Architecture

```
┌──────────────┐   HTTP/CORS    ┌───────────────────────────────┐
│   Angular 21 │◄──────────────►│   FastAPI (orchestrateur)     │
│  localhost:4200                │   app/main.py                 │
└──────────────┘                └──────────────┬────────────────┘
                                               │
         ┌─────────────────────────────────────┼──────────────────────────┐
         ▼                                     ▼                          ▼
┌─────────────────────┐            ┌──────────────────────┐   ┌──────────────────────┐
│ RAG pipeline        │            │ LLMService           │   │ ChatMemoryStore      │
│ rag_pipeline.py     │            │ llm_service.py       │   │ chat_memory.py       │
│                     │            │                      │   │                      │
│ PDFLoader +         │            │ Groq (OpenAI-compat) │   │ chat_sessions        │
│ TextChunker ─────►  │            │ openai/gpt-oss-20b   │   │ chat_messages        │
│ EmbeddingService    │            │ base_url api.groq.   │   │ (SQLAlchemy 2.0,     │
│ (MiniLM-L12 v2      │            │ com/openai/v1        │   │  PostgreSQL 16       │
│  LOCAL, ~500 Mo     │            │                      │   │  Docker :5433)       │
│  cache HF)          │            │ decide: doc vs       │   │                      │
│        ▼            │            │ general + citations  │   │                      │
│ InMemoryVectorStore │            └──────────────────────┘   └──────────────────────┘
│ (NumPy cosine)      │
└─────────────────────┘
```

### Qui fait quoi (mapping fichier ⇄ rôle)

| Fichier backend | Rôle |
|---|---|
| `app/main.py` | **Orchestrateur REST** : lifespan (init tables + index), les 7 endpoints, CORS, contrôles upload |
| `app/rag_pipeline.py` | **Orchestrateur RAG** : coordonne loader → chunker → embeddings → retriever → LLM |
| `app/pdf_loader.py` | Lecture des PDFs de `documents/` (pypdf) |
| `app/text_chunker.py` | Découpage en passages chevauchants (`CHUNK_SIZE=1000`, `CHUNK_OVERLAP=150`) |
| `app/embedding_service.py` | Encodeur local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (texte → vecteur 384-d, gratuit, tourne sur votre machine) |
| `app/vector_store.py` | **Index vectoriel IN MEMORY** (NumPy + similarité cosinus, re-sync au démarrage) |
| `app/retriever.py` | Top-K passages les plus proches de la question (`TOP_K=4`) |
| `app/llm_service.py` | **LLM** : client OpenAI SDK pointé sur Groq ; prompt hybride « réponds à tout, cite si tu utilises le contexte » |
| `app/chat_memory.py` | Historique : sessions + messages + titres (1er message utilisateur) |
| `app/database.py` / `app/db_models.py` | Engine SQLAlchemy + tables `chat_sessions` / `chat_messages` |
| `app/config.py` | Toutes les variables `.env` |

### Frontend

| Fichier | Rôle |
|---|---|
| `components/chat-page/` | Écran : sidebar (sessions, dropzone) + chat + composer 📎 |
| `components/message-bubble/` | Bulle user / assistant (sans affichage de sources — design volontairement épuré) |
| `services/pdf-chat-api.service.ts` | Client HTTP + messages d'erreur FR (422/404/502/503) |
| `models/chat.models.ts` | Contrat TypeScript ⇄ FastAPI |

---

## 🚀 Démarrage rapide

### Prérequis
- Python **3.13+**, Node **20+** (npm), Docker Desktop
- Compte [Groq](https://console.groq.com/) gratuit → créer une **API key** (`gsk_...`)

### 1) PostgreSQL en Docker

```bash
cd pdf_rag_api
docker compose up -d          # postgres:16 sur le port hôte 5433
```

### 2) Backend FastAPI

```bash
cd pdf_rag_api
python -m venv .venv && .venv\Scripts\activate    # (Windows)
pip install -r requirements.txt

copy .env.example .env          # puis coller VOTRE GROQ_API_KEY dans .env
uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
```

Le 1er démarrage télécharge le modèle d'embeddings (~500 Mo, une seule fois, cache `~/.cache/huggingface`).

### 3) Frontend Angular

```bash
cd client
npm install
ng serve                         # http://localhost:4200
```

### 4) Déposer des PDFs
Clic 📎 ou drag & drop dans la sidebar → indexation automatique (`20+ passages` s'affichent). **Posez ensuite n'importe quelle question.**

---

## ⚙️ Variables d'environnement (`.env` — jamais commité)

Voir [`.env.example`](pdf_rag_api/.env.example) : clés Groq, modèle LLM, modèle d'embeddings, paramètres de chunking, PostgreSQL, CORS.

> 🔒 **Sécurité** : la clé Groq (et toute clé API) vit **strictement dans `.env`**, exclu du dépôt par `.gitignore`. Ne la collez jamais dans le code, les logs ou un commit.

---

## 🔌 API REST (base : `http://127.0.0.1:8000`)

| Méthode | Route | Rôle |
|---|---|---|
| `GET` | `/api/health` | Statut |
| `GET`/`POST` | `/api/sessions` | Lister les conversations / créer une session |
| `GET` | `/api/sessions/{id}/messages` | Historique d'une session |
| `POST` | `/api/chat` | `{session_id, question}` → `{answer, sources}` |
| `POST` | `/api/documents/upload` | multipart `file` (.pdf, ≤ 20 Mo) |
| `POST` | `/api/documents/sync` | Rebuild de l'index vectoriel |
| `GET` | `/api/documents/status` | `{ready, indexed_chunks}` |

Exemple :
```json
POST /api/chat
{ "session_id": "5d80a468-…", "question": "Quel est l'objectif du cahier des charges ?" }
```
→
```json
{ "answer": "L'objectif est de définir …", "sources": [{ "filename": "…", "page": 5, "similarity": 0.49, "snippet": "…" }] }
```
*(Le frontend n'affiche pas `sources` : choix design ; les données restent dispo pour les appels directs.)*

---

## 🧭 Limites connues & roadmap

- L'index vectoriel est **en mémoire** → reconstruit à chaque démarrage (rapide, documents locaux persistés sur disque). Roadmap : persistance **pgvector** dans le PostgreSQL existant
- Pas d'authentification projet (usage local). Roadmap : JWT + multi-utilisateurs
- Suppression / renommage des conversations, mode sombre : à venir
- Port hôte `5433` (le compose redirige 5433→5432 pour cohabiter avec un PostgreSQL local éventuel)

---

## 👤 Auteur

**Raed Zayoud** — [raedzayoud](https://github.com/raedzayoud)

Projet d'apprentissage du RAG full-stack : si ce dépôt vous a aidé, une ⭐ fait toujours plaisir !

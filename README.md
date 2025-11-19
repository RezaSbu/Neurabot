````markdown
# 🤖 Neurabot - AI-Powered RAG Chatbot


> **Retrieval-Augmented Generation (RAG) Full-Stack Chatbot**
> A sophisticated AI chatbot that leverages your custom documents and institutional reports to provide intelligent, context-aware responses about technology trends and industry insights.

---

## 🌟 Live Demo

| Platform | Link |
| :--- | :--- |
| **🚀 Vercel** | [**View Live Demo**](https://neurabot-sepia.vercel.app) |
| **🚀 CodeAwake** | [**Alternative Demo**](https://tech-trends-chatbot.codeawake.com) |

---

## 🎯 Overview

Neurabot is a **full-stack application** combining **Large Language Models (LLMs)** with **custom document retrieval** (Vector Search). It is designed to ingest authoritative sources (PDFs, Reports) and answer complex queries with high factual accuracy.

### 🏢 Data Sources Integration
The current model is trained/indexed on reports from:
* **World Bank** (Economic Data)
* **World Economic Forum** (Global Trends)
* **McKinsey & Deloitte** (Business Intelligence)
* **OECD** (Social Data)

---

## ✨ Key Features

### 🧠 Advanced AI Capabilities
* **RAG Architecture:** Combines LLM reasoning with semantic document retrieval.
* **Context-Aware:** Remembers previous turns in the conversation.
* **Multi-Source:** Seamlessly integrates diverse institutional reports.

### 📊 Data Management
* **Vector Search:** Powered by **Redis Stack** for millisecond-latency retrieval.
* **Document Support:** PDF, TXT, and DOCX ingestion.
* **Export:** Download chat history as JSON.

### 🎨 User Experience
* **Modern UI:** Built with React & Vite (Dark/Light mode).
* **Responsive:** Optimized for mobile and desktop.

---

## 🏗️ Architecture

```text
Neurabot/
├── 📂 backend/                 # FastAPI Application (Python)
│   ├── app/
│   │   ├── api/            # REST Endpoints
│   │   ├── assistants/     # RAG & LLM Logic
│   │   ├── loader.py       # Document Ingestion Script
│   │   └── prompts/        # System Instructions
│   ├── data/               # Local Document Storage
│   └── pyproject.toml      # Poetry Dependencies
│
├── 📂 frontend/                # React Application (TypeScript)
│   ├── src/
│   │   ├── components/     # UI Components
│   │   └── services/       # API Integration
│   └── vite.config.ts      # Build Config
│
└── 🐳 docker-compose.yml       # Container Orchestration
````

-----

## 🚀 Quick Start

### Prerequisites

  * **Python 3.11+** (Managed by Poetry)
  * **Node.js 18+**
  * **Redis Stack** (Must support `RedisJSON` & `RediSearch`)
  * **OpenAI API Key**

### 📦 Installation

#### 1\. Clone Repository

```bash
git clone [https://github.com/RezaSbu/Neurabot.git](https://github.com/RezaSbu/Neurabot.git)
cd Neurabot
```

#### 2\. Backend Setup

```bash
cd backend

# Install dependencies with Poetry
poetry install

# Configure Environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Load/Index Documents into Redis
poetry run load

# Start Backend Server
poetry run dev
```

#### 3\. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure Environment
cp .env.example .env.development

# Start Frontend Server
npm run dev
```

#### 4\. Access Application

  * **Frontend:** `http://localhost:3000`
  * **Backend Docs:** `http://localhost:8000/docs`

-----

## ⚙️ Configuration

### Backend Variables (`backend/.env`)

```env
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Frontend Variables (`frontend/.env.development`)

```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Neurabot
```

-----

## 🔧 Advanced Usage & Customization

### 1\. Adding Custom Data

To train the bot on your own data:

1.  Place your `PDF` or `TXT` files in `backend/data/docs/`.
2.  Run the ingestion script:
    ```bash
    poetry run load
    ```

### 2\. Modifying AI Behavior

Edit `backend/app/assistants/prompts.py` to change the system persona:

```python
SYSTEM_PROMPT = """
You are an expert Technical Consultant.
Answer strictly based on the provided context.
"""
```

### 3\. Model Tuning

Adjust parameters in `backend/app/config.py`:

```python
MODEL_CONFIG = {
    "model": "gpt-4",
    "temperature": 0.1,  # Lower for more factual answers
    "max_tokens": 2000
}
```

-----

## 🐳 Deployment (Docker)

For production deployment using Docker Compose:

```bash
# Build and start services
docker-compose up -d --build

# Scale backend (optional)
docker-compose up -d --scale backend=3
```

**Production Configuration (`docker-compose.prod.yml`):**
Ensure `REDIS_URL` points to the container name (`redis:6379`) and `ENVIRONMENT` is set to `production`.

-----

## 🧪 Testing

| Component | Command |
| :--- | :--- |
| **Backend** | `cd backend && poetry run pytest` |
| **Frontend** | `cd frontend && npm test` |
| **API (Curl)** | `curl -X POST http://localhost:8000/chat ...` |

-----

## 🤝 Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes.
4.  Run tests (`poetry run pytest`).
5.  Open a Pull Request.

-----

## 📈 Roadmap

  * [ ] **Multi-Language Support:** Internationalization (i18n).
  * [ ] **Voice Integration:** Speech-to-text and TTS.
  * [ ] **Plugins:** Third-party tool integration.
  * [ ] **Mobile App:** Native iOS/Android wrapper.

-----

## 📞 Support & Community

  * **Issues:** [GitHub Issues](https://www.google.com/search?q=https://github.com/RezaSbu/Neurabot/issues)

-----

## 📄 License

This project is licensed under the MIT License.

-----

*Built with ❤️ by [Reza Ahmadi](https://www.google.com/search?q=https://github.com/RezaSbu)*


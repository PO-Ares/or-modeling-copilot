# Deployment Guide

## Fast demo deployment

This is suitable for portfolio or interview demonstration.

```bash
unzip operations-research-assistant-main.zip
cd operations-research-assistant-main
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

In another terminal:

```bash
cd operations-research-assistant-main
source venv/bin/activate
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

Open:

```text
http://YOUR_SERVER_IP:8501
```

Cloud security group: open port `8501` for quick demo. Open port `8000` only when you need direct API docs access.

## Ollama on server

```bash
ollama pull qwen2.5:1.5b
ollama serve
```

`.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b
API_BASE_URL=http://127.0.0.1:8000/api
```

## Switch to Qwen later

```env
LLM_PROVIDER=qwen
QWEN_API_KEY=your_real_key
QWEN_MODEL=qwen-plus
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

No code change is required.

## GitHub security

Commit:

```text
.env.example
```

Do not commit:

```text
.env
app.db
venv/
__pycache__/
```


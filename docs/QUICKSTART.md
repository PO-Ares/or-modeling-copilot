# Quickstart

## 1. Install Ollama

Pull the default local model:

```bash
ollama pull qwen2.5:1.5b
ollama serve
```

If Ollama is not running, the app still uses rule fallback for classification.

## 2. Create environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure `.env`

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Default:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b
API_BASE_URL=http://localhost:8000/api
```

## 5. Start backend

```bash
python main.py
```

Visit:

```text
http://localhost:8000/docs
```

## 6. Start frontend

Open another terminal:

```bash
streamlit run streamlit_app.py
```

Visit:

```text
http://localhost:8501
```

## 7. Server demo command

```bash
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

Open port `8501` in the cloud security group for a quick demo.


# 🚀 Quick Start Guide - 5 Minutes to Running

## Prerequisites
- Python 3.9+
- OpenAI API Key

## Installation (3 Steps)

### 1️⃣ Setup Environment
```bash
cd retail-insights-assistant
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2️⃣ Configure API Key
```bash
cp .env.example .env
# Edit .env and add your key:
# OPENAI_API_KEY=sk-your-key-here
```

### 3️⃣ Run the App
```bash
streamlit run app.py
```

**That's it!** Open http://localhost:8501 in your browser.

## First Use

1. **Upload Data** - Use the sample file: `data/sample_retail_data.csv`
2. **Click "Load Data"** - Wait for processing
3. **Ask Questions** - Try: "What were the total sales in 2023?"

## Example Questions to Try

✓ "Which category had the highest profit?"
✓ "Show me the top 5 regions by revenue"
✓ "Compare Q3 vs Q4 performance"
✓ "What's the profit margin by product?"
✓ "Which products are underperforming?"

## Modes

**Q&A Mode** (default)
- Type questions in natural language
- Get instant answers with data

**Summary Mode**
- Click "Generate Comprehensive Summary"
- Get automated business intelligence report

## Testing

Verify everything works:
```bash
python test_system.py
```

## Need Help?

- 📖 Full docs: `README.md`
- 🔧 Setup help: `SETUP.md`
- 📊 Architecture: `Architecture_Presentation.pptx`
- 📋 Overview: `DELIVERABLES.md`

## Docker (Alternative)

```bash
docker-compose up -d
```

That's it! Open http://localhost:8501

---

**Built for enterprise retail analytics | AI-powered insights in seconds**

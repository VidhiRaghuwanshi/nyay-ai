# 🚀 Backend Setup Guide - FastAPI

## Indian Judiciary AI System - Backend Implementation

### 📁 Backend Directory Structure

```
backend/
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore
├── run.py                        # Main entry point (we'll create this)
│
└── app/
    ├── __init__.py
    ├── main.py                   # FastAPI app setup
    │
    ├── api/                      # API Routes
    │   ├── __init__.py
    │   ├── precedent_routes.py   # Feature 3 routes
    │   ├── risk_detector_routes.py # Feature 4 routes
    │   ├── procedural_routes.py  # Feature 5 routes
    │   ├── chatbot_routes.py     # Feature 6 routes
    │   ├── outcome_routes.py     # Feature 7 routes
    │   └── drafting_routes.py    # Feature 8 routes
    │
    ├── services/                 # Business Logic
    │   ├── __init__.py
    │   ├── google_api_service.py # Google API integration
    │   ├── precedent_service.py
    │   ├── risk_detector_service.py
    │   ├── procedural_service.py
    │   ├── outcome_service.py
    │   └── drafting_service.py
    │
    ├── models/                   # Data Models
    │   ├── __init__.py
    │   └── schemas.py            # Pydantic models
    │
    ├── config/                   # Configuration
    │   ├── __init__.py
    │   └── settings.py           # App settings
    │
    └── utils/                    # Utilities (ready for extensions)
        └── __init__.py
```

---

## 🏗️ Installation & Setup

### **Step 1: Install Python Dependencies**

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt
```

### **Step 2: Set Up Environment Variables**

```bash
# Copy environment template
copy .env.example .env

# Edit .env file with your configurations
# Especially add your Google API key
```

**⚠️ Getting Google API Key:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Generative AI API (Gemini)
4. Create API key in Credentials section
5. Copy key to `.env` file as `GOOGLE_API_KEY`

Keep the key only in `backend/.env` or your deployment provider's secret store.
Do not put it in `frontend/LegalAi/.env*`, React source files, browser requests,
Git commits, screenshots, or issue reports. If a key has already been exposed,
revoke it in Google Cloud Console and create a replacement.

### **Step 3: Create Main Entry Point**

Create file: `backend/run.py`

```python
"""Main entry point for the backend server"""
import logging
import uvicorn
from app.main import app
from app.config.settings import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║     Indian Judiciary AI System - Backend Server      ║
    ║                   FastAPI v0.104.1                   ║
    ╚══════════════════════════════════════════════════════╝
    
    🚀 Starting server on {settings.HOST}:{settings.PORT}
    📚 API Documentation: http://localhost:8000/docs
    🔄 Health Check: http://localhost:8000/health
    """)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
```

---

## ▶️ Run the Backend

### **Option 1: Using Python**
```bash
python run.py
```

### **Option 2: Using Uvicorn Directly**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### **Option 3: Using Windows PowerShell**
```powershell
python run.py
```

---

## 🔗 API Endpoints

### **Base URL: `http://localhost:8000`**

### **Precedent Graph Engine** (Feature 3)
```
POST   /api/precedent/search          # Search cases
POST   /api/precedent/analyze         # Analyze graph
GET    /api/precedent/cases/{case_id} # Get case details
```

### **Risk Detector** (Feature 4)
```
POST   /api/detector/analyze          # Analyze risks
POST   /api/detector/contradictions   # Detect issues
```

### **Procedural Flow** (Feature 5)
```
POST   /api/procedural/predict        # Predict timeline
GET    /api/procedural/factors        # Get delay factors
```

### **Chatbot** (Feature 6)
```
POST   /api/chatbot/ask               # Ask question
POST   /api/chatbot/classify          # Classify issue
POST   /api/chatbot/extract-entities  # Extract entities
GET    /api/chatbot/suggestions       # Get suggestions
```

### **Outcome Calibration** (Feature 7)
```
POST   /api/outcome/predict           # Predict outcome
GET    /api/outcome/calibration       # Get metrics
```

### **Auto Drafting** (Feature 8)
```
POST   /api/drafting/generate         # Generate document
POST   /api/drafting/citations        # Get citations
GET    /api/drafting/templates        # Get templates
```

### **Health & Utility**
```
GET    /                              # Root endpoint
GET    /health                        # Health check
GET    /docs                          # API documentation (Swagger)
GET    /redoc                         # ReDoc documentation
```

---

## 📊 Testing Endpoints

### **Using Python Requests**

```python
import requests

BASE_URL = "http://localhost:8000"

# Test health
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Test chatbot
response = requests.post(
    f"{BASE_URL}/api/chatbot/ask",
    json={"message": "Can I get bail under IPC 420?"}
)
print(response.json())

# Test risk detection
response = requests.post(
    f"{BASE_URL}/api/detector/analyze",
    json={"case_text": "The accused was charged with fraud", "case_type": "criminal"}
)
print(response.json())
```

### **Using cURL**

```bash
# Health check
curl http://localhost:8000/health

# Chatbot request
curl -X POST http://localhost:8000/api/chatbot/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "Can I get bail under IPC 420?"}'

# Risk analysis
curl -X POST http://localhost:8000/api/detector/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "case_text": "The accused was charged with fraud",
    "case_type": "criminal"
  }'
```

### **Using Swagger UI**

Open your browser: **http://localhost:8000/docs**

You can test all endpoints directly from the Swagger interface!

---

## 🔐 Google API Configuration

### **For Google Generative AI (Recommended)**

1. Set `GOOGLE_API_KEY` in `.env`
2. Chatbot will use Google Gemini Pro model
3. For Entity extraction and Classification, uses same API

### **Fallback Mode (Without API Key)**

If `GOOGLE_API_KEY` is not set:
- Chatbot returns mock legal knowledge base responses
- All features work with predefined data
- Good for development/testing

---

## 🐛 Troubleshooting

### **Issue: Port 8000 already in use**
```bash
# Use different port
uvicorn app.main:app --port 8001 --reload
```

### **Issue: Google API Key error**
```bash
# Check .env file has correct key format
# Verify key is enabled in Google Cloud Console
# Check API quotas in Google Cloud
```

### **Issue: Import errors**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version (3.9+ required)
python --version
```

### **Issue: CORS errors from frontend**
```
# Update ALLOWED_ORIGINS in .env or settings.py
# Frontend URL must be in the list
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## 📦 Database Setup (Optional)

### **SQLite (Default)**
- Automatically created on first run
- File: `./legal_ai.db`
- No additional setup needed

### **MongoDB (Optional)**
```bash
# Install MongoDB
# Update .env with MongoDB URL
MONGODB_URL=mongodb://localhost:27017
```

### **PostgreSQL (Optional)**
```bash
# Install PostgreSQL
# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@localhost/legal_ai
```

---

## 🚀 Deployment

### **Docker (Recommended)**

Create file: `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]
```

Build and run:
```bash
docker build -t legal-ai-backend .
docker run -p 8000:8000 --env-file .env legal-ai-backend
```

### **Heroku**

```bash
heroku login
heroku create your-app-name
heroku config:set GOOGLE_API_KEY=your_key
git push heroku main
```

### **AWS EC2**

```bash
pip install -r requirements.txt
python run.py &
```

---

## 📝 Logging

Logs are configured in `app/config/settings.py`

View logs:
```bash
tail -f logs/legal_ai.log
```

---

## 🔌 Connecting Frontend to Backend

In frontend `.env`:
```
VITE_API_URL=http://localhost:8000/api
```

Request example (React):
```javascript
const response = await axios.post(
  `${import.meta.env.VITE_API_URL}/chatbot/ask`,
  { message: "Can I get bail?" }
);
```

---

## ✅ Checklist

- ✅ Python 3.9+ installed
- ✅ `requirements.txt` dependencies installed
- ✅ `.env` file created with configurations
- ✅ Google API key added (optional but recommended)
- ✅ Backend running on port 8000
- ✅ Swagger docs accessible at /docs
- ✅ Frontend configured to use backend URL

---

## 🎯 Next Steps

1. **Test Backend**: Try endpoints on Swagger UI
2. **Connect Frontend**: Update API URL in frontend
3. **Add Database**: Set up SQLite/MongoDB as needed
4. **Add Authentication**: Implement JWT tokens
5. **Deploy**: Use Docker/Heroku for production

---

## 📞 Support

- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

**Backend is ready to use!** 🎉

Start the server and test the endpoints in the Swagger UI.

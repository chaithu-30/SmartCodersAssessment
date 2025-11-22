# Local Testing Guide

## ✅ Test Results

All backend tests passed successfully!

### Backend Status:
- ✓ Python 3.13.7 installed
- ✓ Django 4.2.7 installed
- ✓ Pinecone package installed
- ✓ All imports working
- ✓ HTML cleaning working
- ✓ Text chunking working
- ✓ Pinecone API key configured
- ✓ Django system check passed

## Quick Start Commands

### Backend (Terminal 1):
```bash
cd backend
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Mac/Linux
python manage.py runserver
```

The backend will run on `http://localhost:8000`

### Frontend (Terminal 2):
```bash
cd frontend
npm install  # If not already done
npm start
```

The frontend will open at `http://localhost:3000`

## Testing the API

### Test Fetch Endpoint:
```bash
curl -X POST http://localhost:8000/api/fetch/ ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://en.wikipedia.org/wiki/Python_(programming_language)\"}"
```

### Test Search Endpoint:
```bash
curl -X POST http://localhost:8000/api/search/ ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"Python programming\",\"url\":\"https://en.wikipedia.org/wiki/Python_(programming_language)\"}"
```

## Troubleshooting

1. **If Pinecone errors occur**: Make sure your `.env` file in `backend/` has:
   ```
   PINECONE_API_KEY=your-api-key-here
   PINECONE_INDEX_NAME=html-chunks
   PINECONE_ENVIRONMENT=us-east-1
   ```

2. **If frontend can't connect**: Make sure backend is running on port 8000

3. **If import errors**: Activate virtual environment and run:
   ```bash
   pip install -r requirements.txt
   ```


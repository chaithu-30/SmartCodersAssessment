# HTML Chunk Search Application

A web application that allows users to search HTML content from websites using semantic search.

## Features

- Clean, modern UI with responsive design
- URL fetching and HTML content extraction
- Intelligent HTML parsing
- Tokenization and chunking (max 500 tokens per chunk)
- Semantic search using vector embeddings
- Top 10 relevance-ranked results
- In-memory storage (no external database required)

## Tech Stack

- **Frontend**: React 18
- **Backend**: Django 4.2 with Django REST Framework
- **HTML Parsing**: BeautifulSoup4
- **Tokenization**: Transformers (Hugging Face)
- **Semantic Search**: Sentence Transformers

## Prerequisites

- Python 3.9 or higher
- Node.js 16 or higher and npm

## Local Development Setup

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
   - **Windows**: `venv\Scripts\activate`
   - **Linux/Mac**: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Run database migrations:
```bash
python manage.py migrate
```

6. Start the Django server:
```bash
python manage.py runserver
```

The backend API will be available at `http://localhost:8000`.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`.

## Production Deployment

### Frontend Deployment on Vercel

1. **Install Vercel CLI** (if not already installed):
```bash
npm i -g vercel
```

2. **Navigate to frontend directory**:
```bash
cd frontend
```

3. **Set environment variable**:
   - Go to your Vercel project settings
   - Add environment variable: `REACT_APP_API_URL` = `https://your-backend-url.onrender.com`

4. **Deploy**:
```bash
vercel
```
Or connect your GitHub repository to Vercel for automatic deployments.

5. **Build Settings** (if using Vercel dashboard):
   - Framework Preset: Create React App
   - Build Command: `npm run build`
   - Output Directory: `build`
   - Install Command: `npm install`

### Backend Deployment on Render

1. **Create a new Web Service** on Render:
   - Connect your GitHub repository
   - Select the `backend` directory as the root directory

2. **Configure Build Settings**:
   - Build Command: `pip install -r requirements.txt && python manage.py migrate`
   - Start Command: `gunicorn project_settings.wsgi:application`

3. **Set Environment Variables**:
   ```
   DEBUG=False
   SECRET_KEY=your-secret-key-here
   ALLOWED_HOSTS=your-app-name.onrender.com
   CORS_ALLOWED_ORIGINS=https://your-frontend-app.vercel.app
   ```

4. **Add Gunicorn to requirements.txt** (if not already present):
   ```
   gunicorn>=21.2.0
   ```

5. **Deploy**: Render will automatically deploy when you push to your repository.

### Important Notes

- **No Pinecone Required**: This application uses in-memory storage, so no external vector database setup is needed.
- **CORS Configuration**: Make sure to set `CORS_ALLOWED_ORIGINS` in your backend environment variables to match your frontend URL.
- **API URL**: Update `REACT_APP_API_URL` in Vercel to point to your Render backend URL.

## Usage

1. Open the application
2. Enter a website URL
3. Enter your search query
4. Click "Search"
5. View the top 10 most relevant content chunks

## API Endpoints

### POST `/api/fetch/`
Fetches and indexes HTML content from a URL.

**Request:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "url": "https://example.com",
  "chunks_count": 15,
  "indexed": true,
  "message": "Processed 15 chunks"
}
```

### POST `/api/search/`
Searches for relevant chunks based on a query.

**Request:**
```json
{
  "query": "contact information",
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "query": "contact information",
  "results": [...],
  "count": 10
}
```

## License

This project is created for assessment purposes.

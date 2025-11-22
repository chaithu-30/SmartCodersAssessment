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

## Setup

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

## Usage

1. Open the application at `http://localhost:3000`
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

## Production Deployment

### Backend
- Set `DEBUG = False` in settings
- Set a secure `SECRET_KEY` in environment variables
- Configure `ALLOWED_HOSTS`
- Use a production WSGI server (e.g., Gunicorn)

### Frontend
- Build the production bundle: `npm run build`
- Serve the `build` directory using a web server

## License

This project is created for assessment purposes.

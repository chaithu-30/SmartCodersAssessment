# HTML Chunk Search Application

A web application that searches through website content using semantic search. Enter a URL and a search query to find the most relevant content chunks.

## Prerequisites

Before you begin, make sure you have:

- **Python 3.9+** installed
- **Node.js 16+** and **npm** installed

## Local Setup

### Backend Setup

1. Navigate to the backend folder:
```bash
cd backend
```

2. Create and activate a virtual environment:

   **Windows:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

   **Mac/Linux:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Run database migrations:
```bash
python manage.py migrate
```

5. Start the backend server:
```bash
python manage.py runserver
```

The backend will run on `http://localhost:8000`

### Frontend Setup

1. Open a new terminal and navigate to the frontend folder:
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

The frontend will open at `http://localhost:3000`

## Vector Database Configuration

**No setup required!** This application uses in-memory storage, so you don't need to configure any external vector database. The embeddings are stored in memory when you index a URL.

## Usage

1. Open `http://localhost:3000` in your browser
2. Enter a website URL (e.g., `https://en.wikipedia.org/wiki/Python`)
3. Enter your search query
4. Click "Search" to see the top 10 most relevant results

That's it! The application will fetch the webpage, extract content, and search through it using semantic similarity.

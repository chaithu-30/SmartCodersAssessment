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

This application uses **Pinecone** as the vector database for storing and searching embeddings.

### Pinecone Setup

1. Create a free account at [pinecone.io](https://www.pinecone.io)

2. Create a new index:
   - Dimension: `384`
   - Metric: `cosine`
   - Cloud: `aws`
   - Region: `us-east-1` (or your preferred region)

3. Get your API key from the Pinecone dashboard

4. Create a `.env` file in the `backend` directory:
```bash
PINECONE_API_KEY=your-api-key-here
PINECONE_INDEX_NAME=html-chunks
PINECONE_ENVIRONMENT=us-east-1
```

The application will automatically create the index if it doesn't exist when you first run it.

## Usage

1. Open `http://localhost:3000` in your browser
2. Enter a website URL (e.g., `https://en.wikipedia.org/wiki/Python`)
3. Enter your search query
4. Click "Search" to see the top 10 most relevant results

That's it! The application will fetch the webpage, extract content, and search through it using semantic similarity.

## Deployment

### Backend Deployment Options (Free Tier)

#### Option 1: Render (Recommended - Free Tier)

1. **Create a Render account** at [render.com](https://render.com)

2. **Create a new Web Service**:
   - Connect your GitHub repository
   - Select the `backend` folder as the root directory
   - **Environment**: Python 3
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt && pip uninstall -y torch && pip install torch --index-url https://download.pytorch.org/whl/cpu && python manage.py migrate`
   - **Start Command**: `gunicorn project_settings.wsgi:application --bind 0.0.0.0:$PORT --timeout 180 --workers 1 --threads 1`

3. **Set Environment Variables**:
   - `DEBUG=False`
   - `SECRET_KEY=your-secret-key-here` (generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
   - `ALLOWED_HOSTS=your-app-name.onrender.com`
   - `PINECONE_API_KEY=your-pinecone-api-key`
   - `PINECONE_INDEX_NAME=html-chunks`
   - `PINECONE_ENVIRONMENT=us-east-1`
   - `CORS_ALLOWED_ORIGINS=https://your-frontend-url.vercel.app`

4. **Deploy** - Render will automatically build and deploy

**Note**: Render free tier may spin down after inactivity. First build may take 10-15 minutes due to PyTorch installation.

#### Option 2: Fly.io (Free Tier - 3 Apps)

1. **Install Fly CLI**: `curl -L https://fly.io/install.sh | sh`

2. **Login**: `fly auth login`

3. **Initialize**: In the `backend` folder, run `fly launch` and follow prompts

4. **Set Environment Variables** using `fly secrets set`:
   ```bash
   fly secrets set DEBUG=False
   fly secrets set SECRET_KEY=your-secret-key
   fly secrets set ALLOWED_HOSTS=your-app-name.fly.dev
   fly secrets set PINECONE_API_KEY=your-key
   fly secrets set PINECONE_INDEX_NAME=html-chunks
   fly secrets set PINECONE_ENVIRONMENT=us-east-1
   fly secrets set CORS_ALLOWED_ORIGINS=https://your-frontend-url.vercel.app
   ```

5. **Deploy**: `fly deploy`

#### Option 3: Koyeb (Free Tier)

1. **Create a Koyeb account** at [koyeb.com](https://www.koyeb.com)

2. **Create a new App**:
   - Connect GitHub repository
   - Set root directory to `backend`
   - **Build Command**: `pip install -r requirements.txt && pip uninstall -y torch && pip install torch --index-url https://download.pytorch.org/whl/cpu && python manage.py migrate`
   - **Run Command**: `gunicorn project_settings.wsgi:application --bind 0.0.0.0:$PORT --timeout 180`

3. **Set Environment Variables** in Koyeb dashboard (same as Render)

4. **Deploy** - Koyeb will automatically build and deploy

### Frontend Deployment (Vercel - Free)

1. **Connect your GitHub repository** to Vercel
2. **Set Root Directory** to `frontend`
3. **Add Environment Variable**:
   - `REACT_APP_API_URL=https://your-backend-url.onrender.com` (or your chosen backend URL)
4. **Deploy** - Vercel will automatically build and deploy

**Note**: All platforms above offer free tiers. Render is recommended for ease of use, but Fly.io and Koyeb are also good alternatives.

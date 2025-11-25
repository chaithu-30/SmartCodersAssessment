HTML Chunk Search

A simple web application that lets you search through website content using keyword-based search. Just provide a URL and a search query, and it will find the most relevant content chunks for you.

Prerequisites

Before you get started, make sure you have these installed on your machine:

- Python 3.9 or higher - You can download it from python.org
- Node.js 16 or higher - Get it from nodejs.org
- Pinecone account - It's free! Sign up at pinecone.io

Project Structure

Here's how the project is organized:

Smart Coders assessment/
├── backend/                    # Django backend API
│   ├── search_api/            # Main API app
│   │   ├── views.py           # API endpoints and search logic
│   │   ├── urls.py            # URL routing
│   │   └── models.py          # Database models
│   ├── project_settings/      # Django project settings
│   │   ├── settings.py        # Configuration
│   │   └── urls.py            # Main URL config
│   ├── requirements.txt       # Python dependencies
│   └── manage.py             # Django management script
│
└── frontend/                  # React frontend
    ├── src/
    │   ├── App.js             # Main app component
    │   ├── components/        # React components
    │   │   ├── SearchForm.js  # Search input form
    │   │   └── ResultsDisplay.js  # Results display
    │   └── index.js           # Entry point
    └── package.json           # Node dependencies

Dependencies

The project uses a few key libraries:

Backend:
- Django and Django REST Framework for the API
- BeautifulSoup4 for parsing HTML content
- Pinecone client for vector database operations
- Gunicorn for production server (optional for local development)

Frontend:
- React for the user interface
- Axios for making API calls

All dependencies are listed in requirements.txt (backend) and package.json (frontend), so you don't need to install them manually.

Local Setup

Setting Up the Backend

First, let's get the Django backend running:

1. Navigate to the backend folder:
   cd backend

2. Create a virtual environment (this keeps your project dependencies separate):
   python -m venv venv

3. Activate the virtual environment:
   
   On Windows:
   venv\Scripts\activate
   
   On Mac or Linux:
   source venv/bin/activate

4. Install the required packages:
If you are using MAC:- pip install mac_requirements.txt
If you are using WINDOWS :- pip install -r windows_requirements.txt
   
   This might take a minute or two as it downloads all the dependencies.

5. Set up the database:
   python manage.py migrate

6. Start the development server:
   python manage.py runserver

   You should see a message saying the server is running at http://localhost:8000. Keep this terminal window open!

Setting Up the Frontend

Now let's get the React frontend running. Open a new terminal window (keep the backend server running):

1. Navigate to the frontend folder:
   cd frontend

2. Install the dependencies:
   npm install
   
   This will download all the Node.js packages needed for the frontend.

3. Start the development server:
   npm start

   This should automatically open your browser to http://localhost:3000. If it doesn't, just open that URL manually.

That's it! You should now have both servers running and the application ready to use.

Vector Database Configuration

This application uses Pinecone to store and search through the content. Think of it as a smart database that helps find relevant content quickly.

Getting Started with Pinecone

1. Create an account:
   - Go to pinecone.io and sign up for a free account
   - The free tier is plenty for development and testing

2. Create an index:
   - Once you're logged in, go to your Pinecone dashboard
   - Click "Create Index" and use these settings:
     - Dimension: 384
     - Metric: cosine
     - Cloud: aws
     - Region: us-east-1 (or pick a region closer to you)
   - Give it a name like html-chunks

3. Get your API key:
   - In the Pinecone dashboard, find your API key (usually in the "API Keys" section)
   - Copy it - you'll need it in the next step

4. Configure the backend:
   - In the backend folder, create a new file called .env
   - Add these lines to it:
     PINECONE_API_KEY=your-actual-api-key-here
     PINECONE_INDEX_NAME=html-chunks
     PINECONE_ENVIRONMENT=us-east-1
   - Replace your-actual-api-key-here with the API key you copied from Pinecone
   - Make sure the index name matches what you created in Pinecone

5. That's it! When you start the backend server, it will automatically connect to Pinecone. If the index doesn't exist yet, the application will create it for you automatically.

Troubleshooting

If you run into any issues:

- Backend won't start? Make sure your virtual environment is activated and all dependencies are installed.
- Frontend won't connect? Check that the backend server is running on port 8000.
- Pinecone connection errors? Double-check your API key in the .env file and make sure there are no extra spaces.

Good luck, and happy searching!

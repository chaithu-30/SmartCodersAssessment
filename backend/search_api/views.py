from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests
from bs4 import BeautifulSoup
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer, util
import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Global state
_indexed_pages = {}
_tokenizer = None
_model = None

STOP_WORDS = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'in', 'to', 'of', 'for', 'on', 'with', 'at', 'by', 'from'}

# === MODEL LOADING ===
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _model

def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
    return _tokenizer

# === HTML PROCESSING ===
def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove unwanted tags
    for tag in soup(['script', 'style', 'noscript', 'iframe', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    # Get main content if Wikipedia
    main = soup.find('div', id='mw-content-text') or soup.find('main') or soup
    
    # Extract and clean text
    text = main.get_text(separator=' ', strip=True)
    text = re.sub(r'\[edit\]|\[\d+\]', '', text)  # Remove [edit] and citations
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    
    return ' '.join(w for w in text.split() if len(w) >= 2)

# === CHUNKING ===
def chunk_text(text, max_tokens=500):
    if not text:
        return []
    
    tokenizer = get_tokenizer()
    tokens = tokenizer.encode(text, add_special_tokens=False)
    
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True).strip()
        if chunk_text:
            chunks.append(chunk_text)
    
    return chunks

# === INDEXING ===
def index_url(url, chunks):
    if not chunks:
        return False
    
    try:
        model = get_model()
        embeddings = model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
        
        _indexed_pages[url] = {
            'chunks': chunks,
            'embeddings': embeddings
        }
        return True
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        return False

# === SCORING ===
def score_result(chunk_text, query, semantic_score, chunk_idx):
    chunk_lower = chunk_text.lower()
    query_lower = query.lower()
    query_words = [w for w in query_lower.split() if len(w) >= 3 and w not in STOP_WORDS]
    
    # Exact phrase match = 99% score
    if query_lower in chunk_lower:
        return 0.99, f"Exact phrase '{query}' found"
    
    # Count keyword matches
    matched = sum(1 for w in query_words if w in chunk_lower)
    
    if matched == 0:
        # Pure semantic scoring
        score = semantic_score * 0.6
        return min(0.99, score), f"Semantic similarity only ({semantic_score:.0%})"
    
    # Hybrid scoring: semantic + keyword
    keyword_ratio = matched / max(len(query_words), 1)
    keyword_score = keyword_ratio * 0.7
    
    # Combine scores
    final_score = semantic_score * 0.3 + keyword_score * 0.7
    
    # Bonus for first chunks
    if chunk_idx < 2:
        final_score += 0.1
    
    final_score = min(0.99, final_score * 1.1)
    
    reason = f"Found {matched}/{len(query_words)} keywords"
    if chunk_idx == 0:
        reason += " | Document intro"
    
    return final_score, reason

# === SEARCH ===
def search(query, url=None, top_k=10):
    if not _indexed_pages or not query:
        return []
    
    model = get_model()
    query_embedding = model.encode(query, normalize_embeddings=True, show_progress_bar=False)
    
    results = []
    pages = [url] if url and url in _indexed_pages else _indexed_pages.keys()
    
    for page_url in pages:
        data = _indexed_pages[page_url]
        similarities = util.cos_sim(query_embedding, data['embeddings'])[0]
        
        for idx, (chunk, sim) in enumerate(zip(data['chunks'], similarities)):
            score, reason = score_result(chunk, query, float(sim), idx)
            
            results.append({
                'chunk_text': chunk,
                'chunk_index': idx,
                'url': page_url,
                'relevance_score': score,
                'score_reason': reason,
                'semantic_score': float(sim)
            })
    
    # Sort and deduplicate
    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    seen = set()
    unique = []
    
    for r in results:
        uid = f"{r['url']}_{r['chunk_index']}"
        if uid not in seen:
            seen.add(uid)
            unique.append(r)
    
    return unique[:top_k]

# === API ENDPOINTS ===
@api_view(['POST'])
def fetch_url_view(request):
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL required'}, status=400)
    
    try:
        # Fetch HTML
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Process
        text = clean_html(response.text)
        chunks = chunk_text(text, max_tokens=500)
        
        if not chunks:
            return Response({'error': 'No content extracted'}, status=400)
        
        # Index
        success = index_url(url, chunks)
        
        return Response({
            'url': url,
            'chunks_count': len(chunks),
            'indexed': success
        })
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def search_view(request):
    query = request.data.get('query', '').strip()
    url = request.data.get('url')
    
    if not query:
        return Response({'error': 'Query required'}, status=400)
    
    try:
        results = search(query, url=url, top_k=10)
        return Response({
            'query': query,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        return Response({'error': str(e)}, status=500)

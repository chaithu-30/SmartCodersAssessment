from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

# Global state - lazy loaded
_tokenizer = None
_model = None
_indexed_pages = {}

STOP_WORDS = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'in', 'to', 'of', 'for', 'on', 'with', 'at', 'by'}

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _model

def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        try:
            model = get_model()
            if hasattr(model, 'tokenizer') and model.tokenizer is not None:
                _tokenizer = model.tokenizer
            elif hasattr(model, '_modules') and 'tokenizer' in model._modules:
                _tokenizer = model._modules['tokenizer']
            else:
                from transformers import AutoTokenizer
                _tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Could not load tokenizer: {e}, using word-based chunking")
            _tokenizer = None
    return _tokenizer

def get_pinecone_index():
    global _pinecone_index, _pinecone_client
    
    if _pinecone_index is not None:
        return _pinecone_index if _pinecone_index is not False else None
    
    try:
        api_key = settings.PINECONE_API_KEY
        environment = settings.PINECONE_ENVIRONMENT
        index_name = settings.PINECONE_INDEX_NAME
        
        _pinecone_client = Pinecone(api_key=api_key)
        
        # Create index if doesn't exist
        existing = [idx.name for idx in _pinecone_client.list_indexes()]
        if index_name not in existing:
            _pinecone_client.create_index(
                name=index_name,
                dimension=384,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region=environment)
            )
        
        _pinecone_index = _pinecone_client.Index(index_name)
        return _pinecone_index
        
    except Exception as e:
        logger.error(f"Pinecone init failed: {e}")
        _pinecone_index = False
        return None
    
def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove unwanted tags
    for tag in soup(['script', 'style', 'noscript', 'iframe', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    # Get main content
    main = soup.find('div', id='mw-content-text') or soup.find('main') or soup
    
    # Clean text
    text = main.get_text(separator=' ', strip=True)
    text = re.sub(r'\[edit\]|\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    return ' '.join(w for w in text.split() if len(w) >= 2)

def chunk_text(text, max_tokens=500):
    if not text:
        return []
    
    tokenizer = get_tokenizer()
    if tokenizer is None:
        words = text.split()
        words_per_chunk = max_tokens
        chunks = []
        for i in range(0, len(words), words_per_chunk):
            chunk = ' '.join(words[i:i + words_per_chunk])
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks
    
    try:
        tokens = tokenizer.encode(text, add_special_tokens=False)
        chunks = []
        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True).strip()
            if chunk_text:
                chunks.append(chunk_text)
        return chunks
    except Exception as e:
        logger.warning(f"Tokenizer error: {e}, using word-based chunking")
        words = text.split()
        words_per_chunk = max_tokens
        chunks = []
        for i in range(0, len(words), words_per_chunk):
            chunk = ' '.join(words[i:i + words_per_chunk])
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

# === INDEXING WITH PINECONE ===
def index_url(url, chunks):
    if not chunks:
        return False
    
    index = get_pinecone_index()
    if not index:
        return False
    
    try:
        model = get_model()
        url_hash = abs(hash(url)) % (10 ** 8)
        
        # Delete old chunks for this URL
        try:
            index.delete(filter={"url": {"$eq": url}})
        except:
            pass
        
        # Generate embeddings
        embeddings = model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
        
        # Prepare vectors for Pinecone
        vectors = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vectors.append({
                "id": f"{url_hash}_{idx}",
                "values": embedding.tolist(),
                "metadata": {
                    "chunk_text": chunk[:5000],  # Pinecone metadata limit
                    "url": url,
                    "chunk_index": idx
                }
            })
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
        
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
        # Pure semantic scoring from Pinecone
        score = semantic_score * 0.6
        return min(0.99, score), f"Semantic similarity ({semantic_score:.0%})"
    
    # Hybrid: Pinecone semantic + keyword matching
    keyword_ratio = matched / max(len(query_words), 1)
    keyword_score = keyword_ratio * 0.7
    
    # Combine scores
    final_score = semantic_score * 0.3 + keyword_score * 0.7
    
    # Bonus for first chunks
    if chunk_idx < 2:
        final_score += 0.1
    
    final_score = min(0.99, final_score * 1.1)
    
    reason = f"Found {matched}/{len(query_words)} keywords"
    if semantic_score > 0.5:
        reason += f" | High semantic match ({semantic_score:.0%})"
    if chunk_idx == 0:
        reason += " | Document intro"
    
    return final_score, reason

# === SEARCH WITH PINECONE ===
def search(query, url=None, top_k=10):
    if not query:
        return []
    
    index = get_pinecone_index()
    if not index:
        return []
    
    try:
        model = get_model()
        
        # Generate query embedding
        query_embedding = model.encode(query, normalize_embeddings=True, show_progress_bar=False)
        
        # Search Pinecone (semantic search)
        filter_dict = {"url": {"$eq": url}} if url else None
        fetch_k = min(top_k * 3, 30)  # Fetch more for reranking
        
        response = index.query(
            vector=query_embedding.tolist(),
            top_k=fetch_k,
            filter=filter_dict,
            include_metadata=True
        )
        
        # Rerank with keyword matching
        results = []
        for match in response.matches:
            metadata = match.metadata
            chunk_text = metadata.get('chunk_text', '')
            
            if not chunk_text:
                continue
            
            # match.score is the cosine similarity from Pinecone
            final_score, reason = score_result(
                chunk_text,
                query,
                match.score,
                int(metadata.get('chunk_index', 0))
            )
            
            results.append({
                'chunk_text': chunk_text,
                'chunk_index': metadata.get('chunk_index', 0),
                'url': metadata.get('url', ''),
                'relevance_score': final_score,
                'score_reason': reason,
                'semantic_score': match.score  # Pinecone's semantic score
            })
        
        # Sort by final score and deduplicate
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        seen = set()
        unique = []
        for r in results:
            uid = f"{r['url']}_{r['chunk_index']}"
            if uid not in seen:
                seen.add(uid)
                unique.append(r)
        
        return unique[:top_k]
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

# === API ENDPOINTS ===
@api_view(['POST'])
def fetch_url_view(request):
    """Fetch URL, extract content, and index in Pinecone."""
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL required'}, status=400)
    
    try:
        # Fetch HTML
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Process and chunk
        text = clean_html(response.text)
        chunks = chunk_text(text, max_tokens=500)
        
        if not chunks:
            return Response({'error': 'No content extracted'}, status=400)
        
        # Index in Pinecone
        success = index_url(url, chunks)
        
        return Response({
            'url': url,
            'chunks_count': len(chunks),
            'indexed': success,
            'message': f'Indexed {len(chunks)} chunks in Pinecone'
        })
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def search_view(request):
    """
    Search indexed content using Pinecone semantic search + keyword matching.
    Returns top 10 most relevant chunks.
    """
    query = request.data.get('query', '').strip()
    url = request.data.get('url')
    
    if not query:
        return Response({'error': 'Query required'}, status=400)
    
    try:
        # Search using Pinecone vector database
        results = search(query, url=url, top_k=10)
        
        return Response({
            'query': query,
            'results': results,
            'count': len(results),
            'search_method': 'Pinecone semantic search + keyword reranking'
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return Response({'error': str(e)}, status=500)

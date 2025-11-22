from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from pinecone import Pinecone, ServerlessSpec
import logging
import re

logger = logging.getLogger(__name__)

_model = None
_tokenizer = None
_pinecone_index = None
_pinecone_client = None

STOP_WORDS = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'in', 'to', 'of', 'for', 'on', 'with', 'at', 'by', 'from'}

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        logger.info("Model loaded")
    return _model

def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        try:
            model = get_model()
            _tokenizer = getattr(model, 'tokenizer', None)
            if _tokenizer is None:
                from transformers import AutoTokenizer
                _tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Tokenizer load failed: {e}")
            _tokenizer = False
    return _tokenizer if _tokenizer is not False else None

def get_pinecone_index():
    global _pinecone_index, _pinecone_client
    
    if _pinecone_index is not None:
        return _pinecone_index if _pinecone_index is not False else None
    
    try:
        api_key = settings.PINECONE_API_KEY
        index_name = getattr(settings, 'PINECONE_INDEX_NAME', 'html-chunks')
        environment = getattr(settings, 'PINECONE_ENVIRONMENT', 'us-east-1')
        
        _pinecone_client = Pinecone(api_key=api_key)
        
        existing = [idx.name for idx in _pinecone_client.list_indexes()]
        if index_name not in existing:
            _pinecone_client.create_index(
                name=index_name,
                dimension=384,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region=environment)
            )
            logger.info(f"Created Pinecone index: {index_name}")
        
        _pinecone_index = _pinecone_client.Index(index_name)
        logger.info(f"Connected to Pinecone: {index_name}")
        return _pinecone_index
        
    except Exception as e:
        logger.error(f"Pinecone init failed: {e}")
        _pinecone_index = False
        return None

def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    for tag in soup(['script', 'style', 'noscript', 'iframe', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    main = soup.find('div', id='mw-content-text') or soup.find('main') or soup
    
    text = main.get_text(separator=' ', strip=True)
    text = re.sub(r'\[edit\]|\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    return ' '.join(w for w in text.split() if len(w) >= 2)

def chunk_text(text, max_tokens=500):
    if not text:
        return []
    
    tokenizer = get_tokenizer()
    
    if tokenizer:
        try:
            tokens = tokenizer.encode(text, add_special_tokens=False)
            chunks = []
            for i in range(0, len(tokens), max_tokens):
                chunk_tokens = tokens[i:i + max_tokens]
                chunk = tokenizer.decode(chunk_tokens, skip_special_tokens=True).strip()
                if chunk:
                    chunks.append(chunk)
            return chunks
        except Exception as e:
            logger.warning(f"Tokenization failed: {e}")
    
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_tokens):
        chunk = ' '.join(words[i:i + max_tokens]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks

def index_url(url, chunks):
    if not chunks:
        return False
    
    index = get_pinecone_index()
    if not index:
        logger.error("Pinecone not available")
        return False
    
    try:
        model = get_model()
        url_hash = abs(hash(url)) % (10 ** 8)
        
        try:
            index.delete(filter={"url": {"$eq": url}})
        except Exception as e:
            logger.warning(f"Could not delete old chunks: {e}")
        
        embeddings = model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
        
        vectors = [{
            "id": f"{url_hash}_{idx}",
            "values": emb.tolist(),
            "metadata": {
                "chunk_text": chunk[:5000],
                "url": url,
                "chunk_index": idx
            }
        } for idx, (chunk, emb) in enumerate(zip(chunks, embeddings))]
        
        for i in range(0, len(vectors), 100):
            index.upsert(vectors=vectors[i:i + 100])
        
        logger.info(f"Indexed {len(chunks)} chunks for {url}")
        return True
        
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        return False

def score_result(chunk_text, query, semantic_score, chunk_idx):
    chunk_lower = chunk_text.lower()
    query_lower = query.lower().strip()
    
    query_words = [w for w in query_lower.split() if len(w) >= 3 and w not in STOP_WORDS]
    if not query_words:
        query_words = query_lower.split()
    
    if query_lower in chunk_lower:
        return 0.99, f"Exact phrase '{query}'"
    
    matched = sum(1 for w in query_words if w in chunk_lower)
    
    if matched == 0:
        score = semantic_score * 0.6
        return min(0.99, score), f"Semantic only ({semantic_score:.0%})"
    
    keyword_ratio = matched / len(query_words)
    final_score = semantic_score * 0.3 + keyword_ratio * 0.7
    
    if chunk_idx < 2:
        final_score += 0.1
    
    final_score = min(0.99, final_score * 1.1)
    
    reason = f"{matched}/{len(query_words)} keywords"
    if semantic_score > 0.5:
        reason += f" | High semantic ({semantic_score:.0%})"
    if chunk_idx == 0:
        reason += " | Intro"
    
    return final_score, reason

def search(query, url=None, top_k=10):
    if not query:
        return []
    
    index = get_pinecone_index()
    if not index:
        return []
    
    try:
        model = get_model()
        
        query_embedding = model.encode(query, normalize_embeddings=True, show_progress_bar=False)
        
        filter_dict = {"url": {"$eq": url}} if url else None
        response = index.query(
            vector=query_embedding.tolist(),
            top_k=min(top_k * 3, 30),
            filter=filter_dict,
            include_metadata=True
        )
        
        results = []
        for match in response.matches:
            metadata = match.metadata
            chunk_text = metadata.get('chunk_text', '')
            
            if not chunk_text:
                continue
            
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
                'semantic_score': round(match.score, 4)
            })
        
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        unique = []
        seen = set()
        for r in results:
            uid = f"{r['url']}_{r['chunk_index']}"
            if uid not in seen:
                seen.add(uid)
                unique.append(r)
        
        return unique[:top_k]
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

@api_view(['POST'])
def fetch_url_view(request):
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        text = clean_html(response.text)
        chunks = chunk_text(text, max_tokens=500)
        
        if not chunks:
            return Response({'error': 'No content extracted'}, status=status.HTTP_400_BAD_REQUEST)
        
        success = index_url(url, chunks)
        
        return Response({
            'url': url,
            'chunks_count': len(chunks),
            'indexed': success,
            'message': f'Indexed {len(chunks)} chunks'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def search_view(request):
    query = request.data.get('query', '').strip()
    url = request.data.get('url')
    
    if not query:
        return Response({'error': 'Query required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        results = search(query, url=url, top_k=10)
        
        return Response({
            'query': query,
            'results': results,
            'count': len(results)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

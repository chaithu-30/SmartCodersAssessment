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

_pinecone_index = None
_pinecone_client = None

STOP_WORDS = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'in', 'to', 'of', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'it', 'this', 'that', 'but', 'not', 'or', 'and', 'if', 'can', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'shall'}

def extract_keywords(text, max_keywords=50):
    """Extract important keywords from text for metadata storage"""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    word_freq = {}
    for word in words:
        if word not in STOP_WORDS:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, freq in sorted_words[:max_keywords]]
    return keywords

def get_pinecone_index():
    global _pinecone_index, _pinecone_client
    
    if _pinecone_index is not None:
        return _pinecone_index if _pinecone_index is not False else None
    
    try:
        api_key = settings.PINECONE_API_KEY
        index_name = getattr(settings, 'PINECONE_INDEX_NAME', 'html-chunks')
        environment = getattr(settings, 'PINECONE_ENVIRONMENT', 'us-east-1')
        
        logger.info(f"Pinecone config - Index: {index_name}, Environment: {environment}")
        
        if not api_key:
            logger.error("PINECONE_API_KEY not configured")
            _pinecone_index = False
            return None
            
        logger.info("Initializing Pinecone client...")
        _pinecone_client = Pinecone(api_key=api_key)
        
        existing = [idx.name for idx in _pinecone_client.list_indexes()]
        logger.info(f"Found {len(existing)} existing indexes")
            
        if index_name not in existing:
            logger.info(f"Creating Pinecone index: {index_name}")
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
        logger.error(f"Pinecone init failed: {e}", exc_info=True)
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
    
    logger.info(f"Indexing {len(chunks)} chunks for {url}")
    
    index = get_pinecone_index()
    if not index:
        logger.error("Pinecone not available")
        return False
    
    try:
        url_hash = abs(hash(url)) % (10 ** 8)
        
        try:
            index.delete(filter={"url": {"$eq": url}})
        except Exception as e:
            logger.warning(f"Could not delete old chunks: {e}")
        
        logger.info(f"Indexing {len(chunks)} chunks with keywords...")
        
        import gc
        
        upload_batch_size = 10
        vectors_batch = []
        
        for idx, chunk in enumerate(chunks):
            keywords = extract_keywords(chunk, max_keywords=30)
            keywords_str = ' '.join(keywords[:20])
            
            dummy_vector = [1.0] + [0.0] * 383
            
            vector = {
                "id": f"{url_hash}_{idx}",
                "values": dummy_vector,
                "metadata": {
                    "chunk_text": chunk[:2000],
                    "url": url,
                    "chunk_index": str(idx),
                    "keywords": keywords_str
                }
            }
            vectors_batch.append(vector)
            
            if len(vectors_batch) >= upload_batch_size:
                index.upsert(vectors=vectors_batch)
                vectors_batch = []
                gc.collect()
        
        if vectors_batch:
            index.upsert(vectors=vectors_batch)
            vectors_batch = []
        
        logger.info(f"All {len(chunks)} chunks indexed")
        
        gc.collect()
        
        logger.info(f"Indexed {len(chunks)} chunks for {url}")
        return True
        
    except Exception as e:
        logger.error(f"Indexing error: {e}", exc_info=True)
        return False

def score_chunk(chunk_text, query, chunk_idx=0):
    """Keyword-based scoring strategy with term frequency boost"""
    chunk_lower = chunk_text.lower()
    query_lower = query.lower().strip()
    
    query_words = [w for w in query_lower.split() if w not in STOP_WORDS and len(w) >= 2]
    
    if not query_words:
        query_words = [w for w in query_lower.split() if len(w) >= 2]
    
    if not query_words:
        return 0.0, "No valid keywords"
    
    matched = sum(1 for word in query_words if re.search(r'\b' + re.escape(word) + r'\b', chunk_lower))
    match_ratio = matched / len(query_words) if query_words else 0.0
    
    total_occurrences = sum(len(re.findall(r'\b' + re.escape(word) + r'\b', chunk_lower)) for word in query_words)
    frequency_boost = min(1.0, total_occurrences / max(len(query_words), 3))
    
    exact_match = 1.0 if query_lower in chunk_lower else 0.0
    
    positions = []
    for w in query_words:
        match = re.search(r'\b' + re.escape(w) + r'\b', chunk_lower)
        if match:
            positions.append(match.start())
    first_position = min(positions) if positions else 999
    
    if first_position < 100:
        position_bonus = 1.0
    elif first_position < 450:
        position_bonus = 0.7
    else:
        position_bonus = 0.0
    
    final_score = (match_ratio * 0.5) + (frequency_boost * 0.3) + (exact_match * 0.2) + (position_bonus * 0.1)
    
    final_score = min(1.0, max(0.0, final_score))
    
    reason_parts = []
    if exact_match > 0:
        reason_parts.append("Exact phrase")
    reason_parts.append(f"{matched}/{len(query_words)} keywords")
    if total_occurrences > len(query_words):
        reason_parts.append(f"{total_occurrences} total occurrences")
    if position_bonus > 0:
        reason_parts.append(f"Early position ({first_position} chars)")
    if chunk_idx == 0:
        reason_parts.append("Intro")
    
    reason = " | ".join(reason_parts) if reason_parts else "Low relevance"
    
    return final_score, reason

def search(query, url=None, top_k=10):
    if not query:
        return []
    
    index = get_pinecone_index()
    if not index:
        logger.error("Pinecone not available for search")
        return []
    
    try:
        filter_dict = {"url": {"$eq": url}} if url else None
        
        dummy_query_vector = [1.0] + [0.0] * 383
        fetch_k = min(top_k * 5, 100)
        
        logger.info(f"Querying Pinecone with fetch_k={fetch_k}")
        
        response = index.query(
            vector=dummy_query_vector,
            top_k=fetch_k,
            filter=filter_dict,
            include_metadata=True
        )
        
        logger.info(f"Pinecone returned {len(response.matches)} matches")
        
        results = []
        for idx, match in enumerate(response.matches):
            metadata = match.metadata
            chunk_text = metadata.get('chunk_text', '')
            
            if not chunk_text:
                continue
            
            chunk_idx = int(metadata.get('chunk_index', idx))
            
            final_score, reason = score_chunk(chunk_text, query, chunk_idx)
            
            results.append({
                'chunk_text': chunk_text,
                'url': metadata.get('url', ''),
                'chunk_index': metadata.get('chunk_index', ''),
                'relevance_score': round(final_score, 4),
                'score_reason': reason
            })
        
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        unique = []
        seen = set()
        for r in results:
            uid = f"{r['url']}_{r['chunk_index']}"
            if uid not in seen:
                seen.add(uid)
                unique.append(r)
        
        final_results = unique[:top_k]
        return final_results
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return []

@api_view(['GET'])
def health_check(request):
    logger.info("Health check requested")
    return Response({
        'status': 'healthy',
        'service': 'HTML Chunk Search API'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
def fetch_url_view(request):
    logger.info(f"Fetch request received: {request.data}")
    
    url = request.data.get('url')
    if not url:
        logger.warning("Fetch request missing URL")
        return Response({'error': 'URL required'}, status=status.HTTP_400_BAD_REQUEST)
    
    logger.info(f"Processing URL: {url}")
    
    try:
        logger.info("Fetching HTML from URL...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info(f"HTML fetched successfully, length: {len(response.text)} bytes")
        
        logger.info("Cleaning HTML...")
        text = clean_html(response.text)
        logger.info(f"Cleaned text length: {len(text)}")
        
        logger.info("Chunking text...")
        chunks = chunk_text(text, max_tokens=500)
        logger.info(f"Created {len(chunks)} chunks")
        
        if not chunks:
            logger.warning("No chunks created from text")
            return Response({'error': 'No content extracted'}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info("Starting indexing to Pinecone...")
        success = index_url(url, chunks)
        logger.info(f"Indexing result: {success}")
        
        result = {
            'url': url,
            'chunks_count': len(chunks),
            'indexed': success,
            'message': f'Indexed {len(chunks)} chunks'
        }
        
        return Response(result, status=status.HTTP_200_OK)
        
    except requests.exceptions.Timeout:
        error_msg = "Request timeout: URL took too long to respond"
        logger.error(error_msg)
        return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching URL: {e}")
        return Response({'error': f'Failed to fetch URL: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Fetch error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def search_view(request):
    logger.info(f"Search request received: {request.data}")
    
    query = request.data.get('query', '').strip()
    url = request.data.get('url')
    
    if not query:
        logger.warning("Search request missing query")
        return Response({'error': 'Query required'}, status=status.HTTP_400_BAD_REQUEST)
    
    logger.info(f"Searching for: '{query}' in {url if url else 'all URLs'}")
    
    try:
        results = search(query, url=url, top_k=10)
        logger.info(f"Search completed, found {len(results)} results")
        
        response_data = {
            'query': query,
            'results': results,
            'count': len(results)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

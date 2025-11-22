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

# Model loaded lazily on first request to save memory
_model = None

_tokenizer = None
_pinecone_index = None
_pinecone_client = None

STOP_WORDS = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'in', 'to', 'of', 'for', 'on', 'with', 'at', 'by', 'from'}

def get_model():
    global _model
    if _model is None:
        print("\n" + "=" * 60)
        print("MODEL LOADING: Starting sentence-transformers model load...")
        print("=" * 60)
        logger.info("Starting model loading...")
        try:
            # Set PyTorch memory optimizations
            import os
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
            
            print("Importing SentenceTransformer...")
            from sentence_transformers import SentenceTransformer
            import torch
            # Clear any cached memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            print("Initializing model (smallest model for memory efficiency)...")
            # Using smallest model: paraphrase-MiniLM-L3-v2 (22MB, 384 dimensions)
            _model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L3-v2')
            
            # Set model to evaluation mode and disable gradients
            _model.eval()
            for param in _model.parameters():
                param.requires_grad = False
            
            print("=" * 60)
            print("MODEL LOADED SUCCESSFULLY!")
            print("=" * 60 + "\n")
            logger.info("Model loaded successfully")
        except Exception as e:
            print("=" * 60)
            print(f"MODEL LOADING ERROR: {type(e).__name__}: {e}")
            import traceback
            print(traceback.format_exc())
            print("=" * 60 + "\n")
            logger.error(f"Model loading failed: {e}", exc_info=True)
            raise
    else:
        print("Model already loaded, reusing existing instance")
    return _model

def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        try:
            model = get_model()
            _tokenizer = getattr(model, 'tokenizer', None)
            if _tokenizer is None:
                from transformers import AutoTokenizer
                _tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/paraphrase-MiniLM-L3-v2')
        except Exception as e:
            logger.warning(f"Tokenizer load failed: {e}")
            _tokenizer = False
    return _tokenizer if _tokenizer is not False else None

def get_pinecone_index():
    global _pinecone_index, _pinecone_client
    
    print("\n" + "=" * 60)
    print("PINECONE: Checking connection...")
    print("=" * 60)
    
    if _pinecone_index is not None:
        print("Pinecone already connected, reusing existing connection")
        return _pinecone_index if _pinecone_index is not False else None
    
    try:
        print("PINECONE: Getting configuration from settings...")
        api_key = settings.PINECONE_API_KEY
        index_name = getattr(settings, 'PINECONE_INDEX_NAME', 'html-chunks')
        environment = getattr(settings, 'PINECONE_ENVIRONMENT', 'us-east-1')
        
        print(f"PINECONE: API Key present: {bool(api_key)}")
        print(f"PINECONE: Index name: {index_name}")
        print(f"PINECONE: Environment: {environment}")
        logger.info(f"Pinecone config - Index: {index_name}, Environment: {environment}")
        
        if not api_key:
            print("=" * 60)
            print("ERROR: PINECONE_API_KEY not set in environment variables!")
            print("=" * 60 + "\n")
            logger.error("PINECONE_API_KEY not configured")
            _pinecone_index = False
            return None
            
        print("PINECONE: Initializing Pinecone client...")
        logger.info("Initializing Pinecone client...")
        _pinecone_client = Pinecone(api_key=api_key)
        print("PINECONE: Client initialized successfully")
        
        print("PINECONE: Listing existing indexes...")
        existing = [idx.name for idx in _pinecone_client.list_indexes()]
        print(f"PINECONE: Found {len(existing)} existing indexes: {existing}")
        logger.info(f"Found {len(existing)} existing indexes")
            
        if index_name not in existing:
            print(f"PINECONE: Index '{index_name}' not found, creating...")
            logger.info(f"Creating Pinecone index: {index_name}")
            _pinecone_client.create_index(
                name=index_name,
                    dimension=384,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region=environment)
            )
            print(f"PINECONE: Index '{index_name}' created successfully")
            logger.info(f"Created Pinecone index: {index_name}")
        else:
            print(f"PINECONE: Index '{index_name}' already exists")
        
        print("PINECONE: Connecting to index...")
        _pinecone_index = _pinecone_client.Index(index_name)
        print("=" * 60)
        print("PINECONE: CONNECTED SUCCESSFULLY!")
        print("=" * 60 + "\n")
        logger.info(f"Connected to Pinecone: {index_name}")
        return _pinecone_index
        
    except Exception as e:
        print("=" * 60)
        print(f"PINECONE ERROR: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        print("=" * 60 + "\n")
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
        print("WARNING: Empty text provided for chunking")
        return []

    print(f"Chunking text (length: {len(text)}, max_tokens: {max_tokens})...")
    tokenizer = get_tokenizer()
    
    if tokenizer:
        try:
            print("Using tokenizer for chunking...")
            tokens = tokenizer.encode(text, add_special_tokens=False)
            print(f"Text tokenized into {len(tokens)} tokens")
            chunks = []
            for i in range(0, len(tokens), max_tokens):
                chunk_tokens = tokens[i:i + max_tokens]
                chunk = tokenizer.decode(chunk_tokens, skip_special_tokens=True).strip()
                if chunk:
                    chunks.append(chunk)
            print(f"Created {len(chunks)} chunks using tokenizer")
            return chunks
        except Exception as e:
            print(f"WARNING: Tokenization failed: {e}, falling back to word-based chunking")
            logger.warning(f"Tokenization failed: {e}")
    
    print("Using word-based chunking (fallback)...")
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_tokens):
        chunk = ' '.join(words[i:i + max_tokens]).strip()
        if chunk:
            chunks.append(chunk)
    print(f"Created {len(chunks)} chunks using word-based method")
    return chunks

def index_url(url, chunks):
    print("\n" + "=" * 60)
    print("INDEX_URL FUNCTION CALLED")
    print("=" * 60)
    
    if not chunks:
        print("ERROR: No chunks provided")
        return False
    
    print(f"Indexing {len(chunks)} chunks for URL: {url}")
    logger.info(f"Indexing {len(chunks)} chunks for {url}")
    
    print("Getting Pinecone index...")
    index = get_pinecone_index()
    if not index:
        print("ERROR: Pinecone index not available")
        logger.error("Pinecone not available")
        return False
    
    try:
        print("Getting model for embeddings...")
        model = get_model()
        print("Model retrieved, generating embeddings...")
        url_hash = abs(hash(url)) % (10 ** 8)
        print(f"URL hash: {url_hash}")
        
        print("Deleting old chunks for this URL...")
        try:
            index.delete(filter={"url": {"$eq": url}})
            print("Old chunks deleted")
        except Exception as e:
            print(f"Warning: Could not delete old chunks: {e}")
            logger.warning(f"Could not delete old chunks: {e}")
        
        print(f"Generating embeddings for {len(chunks)} chunks in small batches (memory efficient)...")
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        
        # Process in small batches to reduce memory usage
        batch_size = 10  # Small batch size for memory efficiency
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_embeddings = model.encode(
                batch_chunks, 
                normalize_embeddings=True, 
                show_progress_bar=False,
                batch_size=8,  # Internal batch size
                convert_to_numpy=True
            )
            all_embeddings.append(batch_embeddings)
            print(f"Processed {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")
        
        import numpy as np
        embeddings = np.vstack(all_embeddings)
        print(f"Embeddings generated: shape {embeddings.shape}")
        logger.info(f"Embeddings generated: {embeddings.shape}")
        
        # Clear memory
        del all_embeddings
        import gc
        gc.collect()
        
        print("Preparing vectors for Pinecone...")
        vectors = [{
            "id": f"{url_hash}_{idx}",
            "values": emb.tolist() if hasattr(emb, 'tolist') else list(emb),
                "metadata": {
                "chunk_text": chunk[:5000],
                    "url": url,
                    "chunk_index": idx
                }
        } for idx, (chunk, emb) in enumerate(zip(chunks, embeddings))]
        print(f"Prepared {len(vectors)} vectors")
        
        # Clear embeddings from memory after conversion
        del embeddings
        gc.collect()
        
        # Use smaller batches for Pinecone upload to reduce memory
        upload_batch_size = 50  # Reduced from 100
        print(f"Uploading vectors to Pinecone in batches of {upload_batch_size}...")
        batch_count = (len(vectors) + upload_batch_size - 1) // upload_batch_size
        for i in range(0, len(vectors), upload_batch_size):
            batch_num = (i // upload_batch_size) + 1
            batch = vectors[i:i + upload_batch_size]
            print(f"Uploading batch {batch_num}/{batch_count} ({len(batch)} vectors)...")
            index.upsert(vectors=batch)
            print(f"Batch {batch_num} uploaded successfully")
            # Clear batch from memory
            del batch
            if i % (upload_batch_size * 5) == 0:  # GC every 5 batches
                import gc
                gc.collect()
        
        print("=" * 60)
        print(f"INDEXING SUCCESS: {len(chunks)} chunks indexed for {url}")
        print("=" * 60 + "\n")
        logger.info(f"Indexed {len(chunks)} chunks for {url}")
        return True
        
    except Exception as e:
        print("=" * 60)
        print(f"INDEXING ERROR: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        print("=" * 60 + "\n")
        logger.error(f"Indexing error: {e}", exc_info=True)
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
    print("\n" + "=" * 60)
    print("SEARCH FUNCTION CALLED")
    print("=" * 60)
    
    if not query:
        print("ERROR: Empty query")
        return []
    
    print(f"Query: '{query}'")
    print(f"URL filter: {url}")
    print(f"Top K: {top_k}")
    
    print("Getting Pinecone index...")
    index = get_pinecone_index()
    if not index:
        print("ERROR: Pinecone index not available")
        logger.error("Pinecone not available for search")
        return []
    
    try:
        print("Getting model for query embedding...")
        model = get_model()
        print("Generating query embedding...")
        logger.info(f"Generating embedding for query: '{query}'")
        query_embedding = model.encode(
            query, 
            normalize_embeddings=True, 
            show_progress_bar=False,
            convert_to_numpy=True
        )
        print(f"Query embedding generated: shape {query_embedding.shape}")
        
        # Convert to list immediately and clear numpy array
        query_embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
        del query_embedding
        import gc
        gc.collect()
        
        filter_dict = {"url": {"$eq": url}} if url else None
        fetch_k = min(top_k * 3, 30)
        print(f"Querying Pinecone (fetch_k={fetch_k}, filter={filter_dict})...")
        logger.info(f"Querying Pinecone with fetch_k={fetch_k}")
        
        response = index.query(
            vector=query_embedding_list,
            top_k=fetch_k,
            filter=filter_dict,
            include_metadata=True
        )
        
        # Clear query embedding from memory
        del query_embedding_list
        gc.collect()
        
        print(f"Pinecone returned {len(response.matches)} matches")
        logger.info(f"Pinecone returned {len(response.matches)} matches")
        
        print("Processing and scoring results...")
        results = []
        for idx, match in enumerate(response.matches):
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
        
        print(f"Scored {len(results)} results")
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        print("Results sorted by relevance")
        
        unique = []
        seen = set()
        for r in results:
            uid = f"{r['url']}_{r['chunk_index']}"
            if uid not in seen:
                seen.add(uid)
                unique.append(r)
        
        final_results = unique[:top_k]
        print(f"Returning top {len(final_results)} unique results")
        print("=" * 60 + "\n")
        return final_results
        
    except Exception as e:
        print("=" * 60)
        print(f"SEARCH FUNCTION ERROR: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        print("=" * 60 + "\n")
        logger.error(f"Search error: {e}", exc_info=True)
        return []

@api_view(['GET'])
def health_check(request):
    print("=" * 60)
    print("HEALTH CHECK ENDPOINT CALLED")
    print("=" * 60)
    logger.info("Health check requested")
    return Response({
        'status': 'healthy',
        'service': 'HTML Chunk Search API'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
def fetch_url_view(request):
    print("\n" + "=" * 60)
    print("FETCH API ENDPOINT CALLED")
    print("=" * 60)
    print(f"Request method: {request.method}")
    print(f"Request data: {request.data}")
    print(f"Content-Type: {request.content_type}")
    print("=" * 60 + "\n")
    logger.info(f"Fetch request received: {request.data}")
    
    url = request.data.get('url')
    if not url:
        print("ERROR: URL not provided in request")
        logger.warning("Fetch request missing URL")
        return Response({'error': 'URL required'}, status=status.HTTP_400_BAD_REQUEST)
    
    print(f"STEP 1: Processing URL: {url}")
    logger.info(f"Processing URL: {url}")
    
    try:
        print("STEP 2: Fetching HTML from URL...")
        logger.info("Fetching HTML from URL...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        print(f"STEP 2: HTML fetched successfully (status: {response.status_code}, length: {len(response.text)} bytes)")
        logger.info(f"HTML fetched successfully, length: {len(response.text)} bytes")
        
        print("STEP 3: Cleaning HTML...")
        logger.info("Cleaning HTML...")
        text = clean_html(response.text)
        print(f"STEP 3: HTML cleaned, text length: {len(text)} characters")
        logger.info(f"Cleaned text length: {len(text)}")
        
        print("STEP 4: Chunking text...")
        logger.info("Chunking text...")
        chunks = chunk_text(text, max_tokens=500)
        print(f"STEP 4: Created {len(chunks)} chunks")
        logger.info(f"Created {len(chunks)} chunks")
        
        if not chunks:
            print("ERROR: No chunks created from text")
            logger.warning("No chunks created from text")
            return Response({'error': 'No content extracted'}, status=status.HTTP_400_BAD_REQUEST)
        
        print("STEP 5: Starting indexing to Pinecone...")
        logger.info("Starting indexing to Pinecone...")
        success = index_url(url, chunks)
        print(f"STEP 5: Indexing completed, success: {success}")
        logger.info(f"Indexing result: {success}")
        
        result = {
            'url': url,
            'chunks_count': len(chunks),
            'indexed': success,
            'message': f'Indexed {len(chunks)} chunks'
        }
        print("=" * 60)
        print("FETCH API SUCCESS")
        print(f"Response: {result}")
        print("=" * 60 + "\n")
        return Response(result, status=status.HTTP_200_OK)
        
    except requests.exceptions.Timeout:
        error_msg = "Request timeout: URL took too long to respond"
        print("=" * 60)
        print(f"NETWORK ERROR: {error_msg}")
        print("=" * 60 + "\n")
        logger.error(error_msg)
        return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except requests.exceptions.RequestException as e:
        print("=" * 60)
        print(f"NETWORK ERROR: {type(e).__name__}: {e}")
        print("=" * 60 + "\n")
        logger.error(f"Network error fetching URL: {e}")
        return Response({'error': f'Failed to fetch URL: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        print("=" * 60)
        print(f"FETCH ERROR: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        print("=" * 60 + "\n")
        logger.error(f"Fetch error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def search_view(request):
    print("\n" + "=" * 60)
    print("SEARCH API ENDPOINT CALLED")
    print("=" * 60)
    print(f"Request data: {request.data}")
    logger.info(f"Search request received: {request.data}")
    
    query = request.data.get('query', '').strip()
    url = request.data.get('url')
    
    if not query:
        print("ERROR: Query not provided")
        logger.warning("Search request missing query")
        return Response({'error': 'Query required'}, status=status.HTTP_400_BAD_REQUEST)
    
    print(f"Search query: '{query}'")
    print(f"URL filter: {url if url else 'None (search all)'}")
    logger.info(f"Searching for: '{query}' in {url if url else 'all URLs'}")
    
    try:
        print("Calling search function...")
        results = search(query, url=url, top_k=10)
        print(f"Search completed, found {len(results)} results")
        logger.info(f"Search completed, found {len(results)} results")
        
        response_data = {
            'query': query,
            'results': results,
            'count': len(results)
        }
        print("=" * 60)
        print("SEARCH API SUCCESS")
        print(f"Returning {len(results)} results")
        print("=" * 60 + "\n")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print("=" * 60)
        print(f"SEARCH ERROR: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        print("=" * 60 + "\n")
        logger.error(f"Search error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

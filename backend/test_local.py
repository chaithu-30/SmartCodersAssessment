#!/usr/bin/env python
"""
Quick test script to verify local setup
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_settings.settings')
django.setup()

from search_api.views import get_model, get_tokenizer, clean_html, chunk_text

def test_imports():
    """Test if all imports work"""
    print("✓ Testing imports...")
    try:
        from sentence_transformers import SentenceTransformer
        from transformers import AutoTokenizer
        from pinecone import Pinecone
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_html_cleaning():
    """Test HTML cleaning"""
    print("\n✓ Testing HTML cleaning...")
    html = "<html><body><script>alert('test')</script><p>Hello World</p></body></html>"
    cleaned = clean_html(html)
    if "Hello World" in cleaned and "alert" not in cleaned:
        print("✓ HTML cleaning works")
        return True
    else:
        print("✗ HTML cleaning failed")
        return False

def test_chunking():
    """Test text chunking"""
    print("\n✓ Testing text chunking...")
    text = " ".join(["word"] * 1000)  # Create a long text
    chunks = chunk_text(text, max_tokens=100)
    if chunks and len(chunks) > 0:
        print(f"✓ Text chunking works (created {len(chunks)} chunks)")
        return True
    else:
        print("✗ Text chunking failed")
        return False

def test_pinecone_config():
    """Test Pinecone configuration"""
    print("\n✓ Testing Pinecone configuration...")
    from django.conf import settings
    api_key = getattr(settings, 'PINECONE_API_KEY', '')
    if api_key:
        print("✓ Pinecone API key found in settings")
        return True
    else:
        print("⚠ Pinecone API key not set (will need .env file for full functionality)")
        return False

def main():
    print("=" * 50)
    print("Local Setup Test")
    print("=" * 50)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("HTML Cleaning", test_html_cleaning()))
    results.append(("Text Chunking", test_chunking()))
    results.append(("Pinecone Config", test_pinecone_config()))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n✓ All tests passed! Your local setup is ready.")
    else:
        print("\n⚠ Some tests failed. Check the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())


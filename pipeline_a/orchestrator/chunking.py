# pipeline_a/orchestrator/chunking.py
import uuid
from typing import List, Dict, Any

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_text(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Chunks extracted pages using RecursiveCharacterTextSplitter.
    `pages` is a list of dicts: {"page_no": int, "text": str}
    Returns a list of chunk dicts:
      {"chunk_id": str, "page_start": int, "page_end": int, "chunk_text": str}
    """
    combined_text = ""
    page_offsets = []
    
    for p in pages:
        text = p["text"].strip()
        if not text:
            continue
        page_no = p["page_no"]
        
        start_idx = len(combined_text)
        chunk_header = f"\n--- PAGE {page_no} ---\n"
        combined_text += chunk_header + text + "\n"
        end_idx = len(combined_text)
        
        page_offsets.append({
            "page_no": page_no,
            "start": start_idx,
            "end": end_idx
        })
        
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
    )
    
    raw_chunks = splitter.split_text(combined_text)
    
    results = []
    
    # Keep track of search start index to handle duplicate chunk texts
    search_start = 0
    for chunk in raw_chunks:
        start_idx = combined_text.find(chunk, search_start)
        if start_idx == -1:
            # Fallback if somehow not found (shouldn't happen)
            start_idx = search_start
        end_idx = start_idx + len(chunk)
        search_start = start_idx + len(chunk) - 200 # advance search index, accounting for overlap
        
        overlapping_pages = [
            p["page_no"] for p in page_offsets
            if not (end_idx <= p["start"] or start_idx >= p["end"])
        ]
        
        page_start = min(overlapping_pages) if overlapping_pages else 1
        page_end = max(overlapping_pages) if overlapping_pages else 1
        
        results.append({
            "chunk_id": str(uuid.uuid4()),
            "page_start": page_start,
            "page_end": page_end,
            "chunk_text": chunk
        })
        
    return results

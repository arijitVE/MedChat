from pipeline_b.vector_db.qdrant_client import ensure_collections_exist, get_client, COLLECTIONS

ensure_collections_exist()
client = get_client()

for key, name in COLLECTIONS.items():
    exists = client.collection_exists(name)
    if exists:
        info = client.get_collection(name)
        count = client.count(name).count
        vectors_config = info.config.params.vectors
        size = getattr(vectors_config, 'size', None)
        print(f'✅ Collection [{name}]: exists=True, vectors={count}, size={size}')
    else:
        print(f'❌ Collection [{name}]: does not exist')
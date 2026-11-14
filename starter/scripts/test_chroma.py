"""Smoke test: Chroma (persistent, cosine, metadata filter) + a real local embedding model."""
import chromadb
from sentence_transformers import SentenceTransformer

MODEL = "intfloat/multilingual-e5-small"
model = SentenceTransformer(MODEL)  # first run downloads the model (~470 MB)
print("Model:", MODEL, "| dims:", model.get_sentence_embedding_dimension())

docs = ["Hạn nộp hồ sơ là ngày 30 tháng 6.",
        "Thư viện mở cửa từ 7 giờ sáng đến 9 giờ tối."]
vecs = model.encode(["passage: " + d for d in docs], normalize_embeddings=True).tolist()

client = chromadb.PersistentClient(path="chroma_test")
col = client.get_or_create_collection("test", metadata={"hnsw:space": "cosine"})
col.upsert(ids=["d1", "d2"], embeddings=vecs, documents=docs,
           metadatas=[{"page": 1, "chapter": "tuyen_sinh"}, {"page": 2, "chapter": "thu_vien"}])

q = model.encode("query: Khi nào hết hạn nộp hồ sơ?", normalize_embeddings=True).tolist()
r = col.query(query_embeddings=[q], n_results=1)
print("Top-1:", r["documents"][0][0], "| distance:", round(r["distances"][0][0], 3))

r2 = col.query(query_embeddings=[q], n_results=1, where={"chapter": "thu_vien"})
print("Có filter chapter=thu_vien:", r2["documents"][0][0])
print("Số bản ghi:", col.count(), "(chạy lại lần 2 vẫn phải là 2)")

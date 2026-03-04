
#from src.agents.triage import TriageAgent, save_profile
#if __name__ == "__main__":
    #agent = TriageAgent()
   # profile = agent.classify("Annual_Report_JUNE-2017.pdf")
  #  save_profile(profile)
 #   print(profile)

#from src.strategies.fast_text import FastTextExtractor

#extractor = FastTextExtractor()
#result = extractor.extract("Annual_Report_JUNE-2017.pdf")

#print("Confidence:", result.confidence)
#print("Text blocks:", len(result.document.text_blocks))

from src.agents.triage import TriageAgent, save_profile
from src.agents.extractor import ExtractionRouter

if __name__ == "__main__":
    #pdf_path = r"Data\samples\2013-E.C-Assigned-regular-budget-and-expense.pdf"
    #pdf_path = r"Data\samples\Annual_Report_JUNE-2017.pdf"
    
    #pdf_path = r"Data\samples\CBE Annual Report 2006-7 .pdf"
    pdf_path = "Data\samples\Consumer Price Index August 2025.pdf"

    triage = TriageAgent()
    profile = triage.classify(pdf_path)
    save_profile(profile)

    router = ExtractionRouter(confidence_threshold=0.65)
    result = router.extract(pdf_path, profile)

    print("Extraction confidence:", result.confidence)
    print("Text blocks:", len(result.document.text_blocks))


from src.chunking.layout_chunker import LayoutAwareChunker

# after extraction
chunker = LayoutAwareChunker(max_chars=800)
chunks = chunker.chunk(result.document)

print("Chunks produced:", len(chunks))
for c in chunks:
    print(f"- Page {c.page} | Confidence {round(c.confidence, 2)}")


from src.embeddings.embedder import DummyEmbedder
from src.embeddings.vector_store import InMemoryVectorStore

# after chunking
embedder = DummyEmbedder()
embedded_chunks = embedder.embed(chunks)

store = InMemoryVectorStore()
store.add(embedded_chunks)

print("Vectors stored:", len(store))
print("Sample metadata:", store.vectors[0].metadata.keys())

from src.answering.answer_generator import GroundedAnswerGenerator

generator = GroundedAnswerGenerator(min_confidence=0.5)

# Query the vector store instead of passing result directly
retrieved = store.retrieve(
    query="What is the total amount?",
    embedder=embedder,
    top_k=3,
)

answer = generator.generate(
    query="What is the total amount?",
    retrieved=retrieved,
)

print("\nANSWER:")
print(answer.text)
print("Confidence:", round(answer.answer_confidence, 2))

print("Citations:")
for c in answer.citations:
    print(f"- Chunk {c.chunk_id} | Page {c.page} | Conf {c.confidence}")
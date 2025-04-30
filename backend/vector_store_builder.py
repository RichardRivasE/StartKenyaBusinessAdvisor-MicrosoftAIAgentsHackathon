import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.vector_store import build_faiss_index, add_new_documents, load_faiss_index


#base_pdf_path = r"base\path\to\your\pdfs"
#pdf_paths = [os.path.join(base_pdf_path, pdf) for pdf in os.listdir(base_pdf_path)]
#csv = r"path\to\your\csv_file.csv"

#vs = build_faiss_index(pdf_paths, csv)

#adding new documents to the index
new_pdf_path = [r"path\to\your\new_pdf_file.pdf"]

vs = load_faiss_index()
add_new_documents(vs, new_pdf_paths=new_pdf_path)
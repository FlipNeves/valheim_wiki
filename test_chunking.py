from core import text_utils

def test_split_text():
    short = "Short text."
    chunks = text_utils.split_text_into_chunks(short, max_chars=50)
    assert len(chunks) == 1
    assert chunks[0] == short
    print("Teste de texto curto: OK")

    para = "Para 1.\n\nPara 2."
    chunks = text_utils.split_text_into_chunks(para, max_chars=10) 
    print(f"Chunks (Para): {chunks}")
    assert len(chunks) >= 2
    print("Teste de quebra de parágrafo: OK")

    long_no_spaces = "a" * 100
    chunks = text_utils.split_text_into_chunks(long_no_spaces, max_chars=50, overlap=0)
    assert len(chunks) == 2
    assert len(chunks[0]) == 50
    assert len(chunks[1]) == 50
    print("Teste de limite rígido: OK")

if __name__ == "__main__":
    test_split_text()

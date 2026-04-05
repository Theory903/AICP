import pytest
import os
from aicp.code_intelligence.ast_indexer import ASTIndexer
from aicp.code_intelligence.models import SymbolKind

def test_ast_indexer_python(tmp_path):
    # Given: A sample Python file
    py_file = tmp_path / "sample.py"
    py_file.write_text("""
class MyClass:
    def my_method(self):
        x = 10
        return x

def global_func():
    pass
""")

    # When: Indexing the file
    indexer = ASTIndexer()
    nodes = indexer.index_file(str(py_file))

    # Then: Verify the extracted symbols
    kinds = [n.kind for n in nodes]
    names = [n.name for n in nodes]

    assert SymbolKind.CLASS in kinds
    assert "MyClass" in names
    assert SymbolKind.FUNCTION in kinds
    assert "my_method" in names
    assert "global_func" in names
    assert "x" in names

def test_ast_indexer_invalid_file():
    # Given: A non-existent file
    indexer = ASTIndexer()
    
    # When: Indexing
    nodes = indexer.index_file("non_existent.py")
    
    # Then: Should return empty list
    assert nodes == []

def test_ast_indexer_non_python_file(tmp_path):
    # Given: A text file
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("Hello World")
    
    # When: Indexing
    indexer = ASTIndexer()
    nodes = indexer.index_file(str(txt_file))
    
    # Then: Should return empty list
    assert nodes == []

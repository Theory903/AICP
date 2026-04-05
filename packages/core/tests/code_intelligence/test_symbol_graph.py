import pytest
from aicp.code_intelligence.symbol_graph import SymbolGraph
from aicp.code_intelligence.models import ASTNode, SymbolLocation, SymbolKind, CallEdge

def test_symbol_graph_add_and_get():
    # Given: A SymbolGraph and some symbols
    graph = SymbolGraph()
    sym1 = ASTNode(kind=SymbolKind.CLASS, name="MyClass", location=SymbolLocation(uri="file1.py", line=1, character=0))
    sym2 = ASTNode(kind=SymbolKind.FUNCTION, name="my_func", location=SymbolLocation(uri="file2.py", line=5, character=4))

    # When: Adding symbols to the graph
    graph.add_symbol(sym1)
    graph.add_symbol(sym2)

    # Then: Verify symbols can be retrieved by name
    defs = graph.get_definitions("MyClass")
    assert len(defs) == 1
    assert defs[0].id == sym1.id
    assert defs[0].location.uri == "file1.py"

    defs_func = graph.get_definitions("my_func")
    assert len(defs_func) == 1
    assert defs_func[0].id == sym2.id

def test_symbol_graph_call_edges():
    # Given: A SymbolGraph and call relationships
    graph = SymbolGraph()
    caller = ASTNode(kind=SymbolKind.FUNCTION, name="caller", location=SymbolLocation(uri="f1.py", line=1, character=0))
    callee = ASTNode(kind=SymbolKind.FUNCTION, name="callee", location=SymbolLocation(uri="f2.py", line=1, character=0))
    graph.add_symbol(caller)
    graph.add_symbol(callee)

    edge = CallEdge(
        caller_id=caller.id,
        callee_id=callee.id,
        call_site=SymbolLocation(uri="f1.py", line=2, character=8)
    )

    # When: Adding a call edge
    graph.add_call_edge(edge)

    # Then: Verify caller and callee relationships
    assert graph.get_callers(callee.id) == [caller.id]
    assert graph.get_callees(caller.id) == [callee.id]
    
    # Check references (which use call edges currently)
    refs = graph.get_references(callee.id)
    assert len(refs) == 1
    assert refs[0].line == 2
    assert refs[0].character == 8

def test_symbol_graph_clear():
    # Given: A non-empty graph
    graph = SymbolGraph()
    graph.add_symbol(ASTNode(kind=SymbolKind.VARIABLE, name="x", location=SymbolLocation(uri="a.py", line=1, character=0)))
    
    # When: Clearing
    graph.clear()
    
    # Then: Should be empty
    assert graph.get_definitions("x") == []

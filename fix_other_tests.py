from pathlib import Path

# Fix integration test
p = Path('tests/integration/test_l4_workflow_lifecycle.py')
text = p.read_text(encoding='utf-8')
text = text.replace('from services.layer4_agents.src.', 'from layer4_agents.')
text = text.replace(
    'f"[LAYER3_IMPORT_PATH] Layer 3 relative-import chain breaks when loaded via sys.path: {_exc}"',
    'f"Layer 4 workflow import failed: {_exc}"'
)
p.write_text(text, encoding='utf-8')
print('Fixed test_l4_workflow_lifecycle.py')

# Fix performance test
p2 = Path('tests/performance/test_performance_optimizations.py')
text2 = p2.read_text(encoding='utf-8')
# Change path from src to parent directory
text2 = text2.replace(
    '_l3_canonical = _repo_root / "services" / "layer3-knowledge" / "src"',
    '_l3_canonical = _repo_root / "services" / "layer3-knowledge"'
)
# Change imports to use src. prefix
text2 = text2.replace(
    'from retrieval.hybrid_search import HybridSearch\n    from retrieval.graph_rag import GraphRAGEngine',
    'from src.retrieval.hybrid_search import HybridSearch\n    from src.retrieval.graph_rag import GraphRAGEngine'
)
# Change skip reason
text2 = text2.replace(
    'f"[LAYER3_IMPORT_PATH] Layer 3 canonical import failed: {_exc}"',
    'f"Layer 3 retrieval import failed: {_exc}"'
)
p2.write_text(text2, encoding='utf-8')
print('Fixed test_performance_optimizations.py')

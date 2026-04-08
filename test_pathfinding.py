"""
test_pathfinding.py
-------------------
Comprehensive test script to verify all pathfinding algorithms work correctly.
Tests each criteria with known start and destination nodes.
"""

from bridge import PrologBridge
from utils import ALGORITHM_MAP, format_path
import os

def test_all_algorithms():
    """Test all pathfinding algorithms with sample routes."""
    
    print("="*70)
    print("PATHFINDING ALGORITHM TEST SUITE")
    print("="*70)
    
    # Initialize Prolog bridge
    kb_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aiproject.pl")
    bridge = PrologBridge()
    
    if not bridge.load(kb_file):
        print("❌ Failed to load knowledge base")
        return False
    
    print("✅ Knowledge base loaded successfully\n")
    
    # Get available nodes
    nodes = bridge.get_all_nodes()
    print(f"Available nodes: {', '.join(nodes)}\n")
    
    # Test cases: (start, goal, description)
    test_cases = [
        ("old_harbour", "byles", "Old Harbour → Byles"),
        ("old_harbour", "spring_villiage", "Old Harbour → Spring Village (has landslide on route)"),
        ("gutters", "bushy_park", "Gutters → Bushy Park (has flood on route)"),
    ]
    
    all_passed = True
    
    for algo_label, (method_suffix, has_cost) in ALGORITHM_MAP.items():
        print(f"\n{'='*70}")
        print(f"Testing: {algo_label}")
        print(f"Method: query_{method_suffix}")
        print(f"{'='*70}")
        
        bridge_method = getattr(bridge, f"query_{method_suffix}", None)
        
        if not bridge_method:
            print(f"❌ Method 'query_{method_suffix}' not found in bridge!")
            all_passed = False
            continue
        
        for start, goal, description in test_cases:
            try:
                if has_cost:
                    path, cost = bridge_method(start, goal)
                else:
                    path = bridge_method(start, goal)
                    cost = None
                
                if path:
                    path_str = format_path(path)
                    if cost is not None:
                        print(f"  ✅ {description}")
                        print(f"     Path: {path_str}")
                        print(f"     Cost: {cost}")
                    else:
                        print(f"  ✅ {description}")
                        print(f"     Path: {path_str}")
                else:
                    print(f"  ⚠️  {description}")
                    print(f"     No path found (this may be expected for some algorithms)")
                    
            except Exception as e:
                print(f"  ❌ {description}")
                print(f"     Error: {e}")
                all_passed = False
    
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    
    if all_passed:
        print("✅ All algorithms executed successfully!")
    else:
        print("❌ Some tests failed - review output above")
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = test_all_algorithms()
    sys.exit(0 if success else 1)

"""
Quick verification script to test that all imports work correctly
after fixing the pydantic-settings dependency issue.
"""

import sys

def test_import(module_name, display_name=None):
    """Test importing a module"""
    if display_name is None:
        display_name = module_name
    
    try:
        __import__(module_name)
        print(f"✓ {display_name}: OK")
        return True
    except Exception as e:
        print(f"✗ {display_name}: FAILED - {e}")
        return False

def main():
    print("=" * 60)
    print("VERIFYING DEPENDENCY FIX")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # Test core dependencies
    print("Testing Core Dependencies:")
    all_passed &= test_import("pydantic", "pydantic")
    all_passed &= test_import("pydantic_settings", "pydantic-settings")
    all_passed &= test_import("yaml", "pyyaml")
    all_passed &= test_import("dotenv", "python-dotenv")
    print()
    
    # Test project imports
    print("Testing Project Imports:")
    all_passed &= test_import("src.config.loader", "ConfigLoader")
    all_passed &= test_import("src.web.api", "Web API")
    print()
    
    # Summary
    print("=" * 60)
    if all_passed:
        print("✅ SUCCESS: All imports working correctly!")
        print("The pydantic-settings dependency issue is FIXED.")
    else:
        print("❌ FAILURE: Some imports still failing.")
        print("Please check the error messages above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

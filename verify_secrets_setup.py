#!/usr/bin/env python3
"""
AgroSight Security Fix #1 Verification Script
Validates that secrets management is properly configured
"""

import os
import sys
from pathlib import Path


def check_env_file():
    """Check if .env file exists and is properly configured."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    print("📋 Checking .env files...")
    
    if not env_example.exists():
        print("  ❌ .env.example not found")
        return False
    print(f"  ✓ .env.example exists ({env_example.stat().st_size} bytes)")
    
    if not env_file.exists():
        print("  ⚠️  .env not found (this is expected for CI/CD)")
        return True
    
    # Check if .env has real keys (not placeholders)
    with open(env_file) as f:
        content = f.read()
        has_placeholder = "your_" in content or "YOUR_" in content or "xxxxx" in content
    
    if has_placeholder:
        print("  ⚠️  .env contains placeholder values - fill in real keys for local testing")
        return True
    
    print(f"  ✓ .env exists ({env_file.stat().st_size} bytes) with real values")
    return True


def check_gitignore():
    """Verify .env is in .gitignore."""
    print("\n🔒 Checking .gitignore...")
    
    gitignore = Path(".gitignore")
    if not gitignore.exists():
        print("  ❌ .gitignore not found")
        return False
    
    with open(gitignore) as f:
        content = f.read()
    
    if ".env" not in content:
        print("  ❌ .env not in .gitignore - THIS IS A SECURITY RISK!")
        return False
    
    if "!.env.example" in content:
        print("  ✓ .env in .gitignore with exception for .env.example")
        return True
    
    print("  ✓ .env in .gitignore")
    return True


def check_secrets_module():
    """Check if secrets manager module exists."""
    print("\n🔐 Checking secrets manager...")
    
    secrets_file = Path("app/utils/secrets.py")
    if not secrets_file.exists():
        print("  ❌ app/utils/secrets.py not found")
        return False
    
    print(f"  ✓ Secrets manager exists ({secrets_file.stat().st_size} bytes)")
    
    # Check for key features
    with open(secrets_file) as f:
        content = f.read()
    
    checks = [
        ("SecretManager class", "class SecretManager"),
        ("AWS backend", "_get_from_aws"),
        ("Vault backend", "_get_from_vault"),
        ("Azure backend", "_get_from_azure"),
        ("Validation method", "validate_required"),
    ]
    
    for name, pattern in checks:
        if pattern in content:
            print(f"    ✓ {name}")
        else:
            print(f"    ❌ {name} missing")
            return False
    
    return True


def check_config_validation():
    """Check if config.py has validation."""
    print("\n⚙️  Checking config validation...")
    
    config_file = Path("app/utils/config.py")
    if not config_file.exists():
        print("  ❌ app/utils/config.py not found")
        return False
    
    with open(config_file) as f:
        content = f.read()
    
    checks = [
        ("validate_secrets method", "def validate_secrets"),
        ("Secrets backend var", "secrets_backend"),
        ("Qdrant collection v8", "agricultural_knowledge_v8"),
    ]
    
    for name, pattern in checks:
        if pattern in content:
            print(f"  ✓ {name}")
        else:
            print(f"  ❌ {name} missing")
            return False
    
    return True


def check_startup_validation():
    """Check if main.py validates secrets."""
    print("\n🚀 Checking startup validation...")
    
    main_file = Path("app/main.py")
    if not main_file.exists():
        print("  ❌ app/main.py not found")
        return False
    
    with open(main_file) as f:
        content = f.read()
    
    if "_validate_secrets_on_startup" in content:
        print("  ✓ Startup validation hook present")
        return True
    else:
        print("  ❌ Startup validation hook missing")
        return False


def check_documentation():
    """Check if documentation exists."""
    print("\n📚 Checking documentation...")
    
    docs = [
        ("SECRETS_MANAGEMENT.md", "Comprehensive secrets guide"),
        ("SECURITY_FIX_1_SECRETS.md", "Security fix summary"),
    ]
    
    for doc_file, description in docs:
        path = Path(doc_file)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✓ {doc_file} ({size} bytes) - {description}")
        else:
            print(f"  ❌ {doc_file} not found")
            return False
    
    return True


def main():
    """Run all checks."""
    print("=" * 70)
    print("🔐 AgroSight Security Fix #1 - Secrets Management Verification")
    print("=" * 70)
    
    checks = [
        check_env_file,
        check_gitignore,
        check_secrets_module,
        check_config_validation,
        check_startup_validation,
        check_documentation,
    ]
    
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"  ❌ Error during check: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\nNext steps:")
        print("  1. Review SECRETS_MANAGEMENT.md for setup instructions")
        print("  2. Copy .env.example to .env")
        print("  3. Fill in your API keys in .env")
        print("  4. Run: python -m uvicorn app.main:app")
        return 0
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total})")
        print("\nPlease fix the issues above and re-run this verification.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Refined analysis to categorize unused functions with better context.
"""

import ast
import os
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def read_file_content(filepath: str) -> str:
    """Read file content safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


def categorize_unused_functions():
    """Categorize the unused functions from our previous analysis."""
    
    unused_functions = {
        # HIGH CONFIDENCE - Likely truly unused
        "show_admin_sidebar": {
            "file": "components/ui_utils.py",
            "line": 62,
            "category": "LIKELY_UNUSED",
            "reason": "Function defined but never called. Could be a legacy function."
        },
        
        # Database utility functions
        "delete_company_admins_from_db": {
            "file": "core/database.py", 
            "line": 291,
            "category": "ADMIN_UTILITY",
            "reason": "Database admin function, may be used for maintenance or future features"
        },
        "vacuum_database": {
            "file": "core/database.py",
            "line": 589, 
            "category": "ADMIN_UTILITY",
            "reason": "Database maintenance function"
        },
        "check_database_integrity": {
            "file": "core/database.py",
            "line": 611,
            "category": "ADMIN_UTILITY", 
            "reason": "Database maintenance function"
        },
        "get_table_info": {
            "file": "core/database.py",
            "line": 567,
            "category": "DEBUG_UTILITY",
            "reason": "Debugging/introspection function"
        },
        "get_all_tables": {
            "file": "core/database.py",
            "line": 579,
            "category": "DEBUG_UTILITY",
            "reason": "Debugging/introspection function"
        },
        "get_database_size": {
            "file": "core/database.py",
            "line": 600,
            "category": "DEBUG_UTILITY",
            "reason": "Debugging/introspection function"
        },
        "close_connection": {
            "file": "core/database.py",
            "line": 540,
            "category": "RESOURCE_MANAGEMENT",
            "reason": "Connection cleanup, may be needed for proper resource management"
        },
        
        # API utility functions
        "check_api_key": {
            "file": "utils/api_loader.py",
            "line": 50,
            "category": "API_UTILITY",
            "reason": "API validation function, may be used conditionally"
        },
        "get_api_key": {
            "file": "utils/api_loader.py", 
            "line": 58,
            "category": "API_UTILITY",
            "reason": "API retrieval function, may be used conditionally"
        },
        
        # Email service functions
        "send_verification_email": {
            "file": "services/email_service.py",
            "line": 9,
            "category": "DUPLICATE_WRAPPER",
            "reason": "Wrapper function, actual implementation in AuthService"
        },
        "send_verification_email": {
            "file": "utils/db_utils.py",
            "line": 40,
            "category": "DUPLICATE_WRAPPER", 
            "reason": "Another wrapper function for AuthService"
        },
        
        # Login functions
        "login_user": {
            "file": "services/auth_service.py",
            "line": 373,
            "category": "DUPLICATE_WRAPPER",
            "reason": "Legacy wrapper function, actual implementation in AuthService class"
        },
        "login_user": {
            "file": "services/login_service.py",
            "line": 17,
            "category": "DUPLICATE_WRAPPER",
            "reason": "Legacy wrapper function, actual implementation in AuthService class"
        },
        
        # FAQ management
        "save_faq_data": {
            "file": "pages/admin_faq_management.py",
            "line": 45,
            "category": "POSSIBLY_UNUSED",
            "reason": "May be legacy code replaced by newer implementation"
        },
        
        # Config validation functions  
        "validate_company_id": {
            "file": "utils/constants.py",
            "line": 217,
            "category": "VALIDATION_UTILITY",
            "reason": "Validation utility, may be used in data validation contexts"
        },
        "validate_email": {
            "file": "utils/constants.py", 
            "line": 233,
            "category": "VALIDATION_UTILITY",
            "reason": "Validation utility, may be used in data validation contexts"
        },
        
        # File path utilities
        "get_upload_folder_path": {
            "file": "utils/constants.py",
            "line": 172,
            "category": "PATH_UTILITY",
            "reason": "Path utility, may be used for file operations"
        },
        "get_backup_folder_path": {
            "file": "utils/constants.py",
            "line": 182,
            "category": "PATH_UTILITY", 
            "reason": "Path utility, may be used for backup operations"
        },
        "get_logs_folder_path": {
            "file": "utils/constants.py",
            "line": 192,
            "category": "PATH_UTILITY",
            "reason": "Path utility, may be used for logging"
        },
        
        # URL generators
        "generate_verification_url": {
            "file": "utils/constants.py",
            "line": 282,
            "category": "URL_GENERATOR",
            "reason": "URL utility, may be used in email templates or frontend"
        },
        "generate_admin_url": {
            "file": "utils/constants.py",
            "line": 286,
            "category": "URL_GENERATOR", 
            "reason": "URL utility, may be used in notifications or redirects"
        },
        "generate_user_url": {
            "file": "utils/constants.py",
            "line": 290,
            "category": "URL_GENERATOR",
            "reason": "URL utility, may be used in notifications or redirects"
        },
        
        # Company management
        "get_company_folder_info": {
            "file": "core/company_manager.py",
            "line": 302,
            "category": "COMPANY_UTILITY",
            "reason": "Company management utility, may be used for admin features"
        },
        "validate_company_id": {
            "file": "core/company_manager.py",
            "line": 337,
            "category": "VALIDATION_UTILITY",
            "reason": "Company validation, may be used in validation contexts"
        },
        
        # Config methods
        "has_anthropic_key": {
            "file": "config/unified_config.py",
            "line": 116,
            "category": "CONFIG_UTILITY",
            "reason": "Configuration check, may be used for conditional features"
        },
        "has_voyage_key": {
            "file": "config/unified_config.py",
            "line": 121,
            "category": "CONFIG_UTILITY",
            "reason": "Configuration check, may be used for conditional features"
        },
        "has_email_config": {
            "file": "config/unified_config.py",
            "line": 126,
            "category": "CONFIG_UTILITY",
            "reason": "Configuration check, may be used for conditional features"
        }
    }
    
    # Categorize by safety of removal
    categories = {
        "SAFE_TO_REMOVE": [],
        "REVIEW_BEFORE_REMOVING": [],
        "KEEP_FOR_FUTURE": [],
        "WRAPPER_FUNCTIONS": []
    }
    
    for func_name, details in unused_functions.items():
        category = details["category"]
        
        if category == "LIKELY_UNUSED":
            categories["SAFE_TO_REMOVE"].append((func_name, details))
        elif category in ["DUPLICATE_WRAPPER"]:
            categories["WRAPPER_FUNCTIONS"].append((func_name, details))
        elif category in ["DEBUG_UTILITY", "ADMIN_UTILITY", "API_UTILITY", "RESOURCE_MANAGEMENT"]:
            categories["KEEP_FOR_FUTURE"].append((func_name, details))
        else:
            categories["REVIEW_BEFORE_REMOVING"].append((func_name, details))
    
    return categories


def main():
    """Generate refined analysis report."""
    categories = categorize_unused_functions()
    
    print("=" * 80)
    print("REFINED UNUSED FUNCTION ANALYSIS")
    print("=" * 80)
    
    print("\n🟢 SAFE TO REMOVE (High confidence)")
    print("-" * 50)
    for func_name, details in categories["SAFE_TO_REMOVE"]:
        print(f"  {details['file']}:{details['line']} - {func_name}()")
        print(f"    Reason: {details['reason']}")
    
    print(f"\nTotal: {len(categories['SAFE_TO_REMOVE'])} functions")
    
    print("\n🟡 WRAPPER FUNCTIONS (Consider consolidating)")
    print("-" * 50)
    for func_name, details in categories["WRAPPER_FUNCTIONS"]:
        print(f"  {details['file']}:{details['line']} - {func_name}()")
        print(f"    Reason: {details['reason']}")
    
    print(f"\nTotal: {len(categories['WRAPPER_FUNCTIONS'])} functions")
    
    print("\n🟠 REVIEW BEFORE REMOVING (Medium confidence)")
    print("-" * 50)
    for func_name, details in categories["REVIEW_BEFORE_REMOVING"]:
        print(f"  {details['file']}:{details['line']} - {func_name}()")
        print(f"    Reason: {details['reason']}")
        
    print(f"\nTotal: {len(categories['REVIEW_BEFORE_REMOVING'])} functions")
    
    print("\n🔵 KEEP FOR FUTURE (Utility/maintenance functions)")
    print("-" * 50)
    for func_name, details in categories["KEEP_FOR_FUTURE"]:
        print(f"  {details['file']}:{details['line']} - {func_name}()")
        print(f"    Reason: {details['reason']}")
        
    print(f"\nTotal: {len(categories['KEEP_FOR_FUTURE'])} functions")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n1. IMMEDIATE ACTIONS:")
    print("   - Remove functions marked as 'SAFE_TO_REMOVE'")
    print("   - Consolidate wrapper functions to reduce duplication")
    
    print("\n2. REVIEW ACTIONS:")
    print("   - Examine 'REVIEW_BEFORE_REMOVING' functions for actual usage")
    print("   - Check if URL generators and path utilities are used in templates")
    print("   - Verify if validation functions are used in data processing")
    
    print("\n3. KEEP FOR MAINTENANCE:")
    print("   - Database utilities are useful for admin/maintenance tasks")
    print("   - Debug utilities help with troubleshooting")
    print("   - API utilities may be needed for conditional features")
    
    print("\n4. CODE QUALITY IMPROVEMENTS:")
    print("   - Consider moving utility functions to appropriate modules")
    print("   - Add unit tests for functions you decide to keep")
    print("   - Document public APIs clearly")


if __name__ == "__main__":
    main()
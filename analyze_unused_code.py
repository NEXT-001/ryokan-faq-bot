#!/usr/bin/env python3
"""
Comprehensive analysis script to identify unused functions and methods
in the Ryokan FAQ bot codebase.
"""

import ast
import os
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Union


class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor to extract function definitions and calls."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.functions_defined = []  # List of (name, line_number, type, class_name_if_method)
        self.functions_called = set()  # Set of function names called
        self.imports = set()  # Set of imported names
        self.class_names = []
        self.current_class = None
        
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        func_type = "method" if self.current_class else "function"
        self.functions_defined.append((
            node.name, 
            node.lineno, 
            func_type, 
            self.current_class
        ))
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        func_type = "async_method" if self.current_class else "async_function"
        self.functions_defined.append((
            node.name, 
            node.lineno, 
            func_type, 
            self.current_class
        ))
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        self.class_names.append(node.name)
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_Call(self, node):
        """Visit function calls."""
        # Handle direct function calls
        if isinstance(node.func, ast.Name):
            self.functions_called.add(node.func.id)
        # Handle method calls (obj.method())
        elif isinstance(node.func, ast.Attribute):
            self.functions_called.add(node.func.attr)
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Visit attribute access (for method calls not in Call context)."""
        if isinstance(node.attr, str):
            self.functions_called.add(node.attr)
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
            if alias.asname:
                self.imports.add(alias.asname)
    
    def visit_ImportFrom(self, node):
        """Visit from X import Y statements."""
        for alias in node.names:
            self.imports.add(alias.name)
            if alias.asname:
                self.imports.add(alias.asname)


def analyze_file(filepath: str) -> Tuple[List, Set, Set, List]:
    """Analyze a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content, filename=filepath)
        analyzer = CodeAnalyzer(filepath)
        analyzer.visit(tree)
        
        return (
            analyzer.functions_defined,
            analyzer.functions_called,
            analyzer.imports,
            analyzer.class_names
        )
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return [], set(), set(), []


def find_streamlit_callbacks(content: str) -> Set[str]:
    """Find potential Streamlit callback functions."""
    callbacks = set()
    
    # Common Streamlit callback patterns
    patterns = [
        r'st\.button\([^,)]+,\s*on_click=([^,)]+)',
        r'st\.form_submit_button\([^,)]+,\s*on_click=([^,)]+)',
        r'st\.selectbox\([^,)]+,\s*on_change=([^,)]+)',
        r'st\.slider\([^,)]+,\s*on_change=([^,)]+)',
        r'st\.text_input\([^,)]+,\s*on_change=([^,)]+)',
        r'st\.file_uploader\([^,)]+,\s*on_change=([^,)]+)',
        r'@st\.cache_data',
        r'@st\.cache_resource',
        r'@st\.fragment',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, str):
                callbacks.add(match.strip("'\""))
    
    return callbacks


def find_dynamic_calls(content: str) -> Set[str]:
    """Find potential dynamic function calls."""
    dynamic_calls = set()
    
    # Patterns for dynamic calls
    patterns = [
        r'getattr\([^,]+,\s*["\']([^"\']+)["\']',
        r'hasattr\([^,]+,\s*["\']([^"\']+)["\']',
        r'setattr\([^,]+,\s*["\']([^"\']+)["\']',
        r'exec\(',
        r'eval\(',
        r'__getattribute__',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, str):
                dynamic_calls.add(match)
    
    return dynamic_calls


def main():
    """Main analysis function."""
    project_root = "/mnt/c/Users/kangj/Documents/GitHub/ryokan-faq-bot"
    
    # Get all Python files
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip virtual environments and cache directories
        dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git']]
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files to analyze.")
    
    all_functions_defined = {}  # filepath -> [(name, line, type, class)]
    all_functions_called = set()
    all_imports = set()
    all_streamlit_callbacks = set()
    all_dynamic_calls = set()
    all_classes = {}  # filepath -> [class_names]
    
    # Analyze each file
    for filepath in python_files:
        print(f"Analyzing: {filepath}")
        
        functions_def, functions_called, imports, classes = analyze_file(filepath)
        
        all_functions_defined[filepath] = functions_def
        all_functions_called.update(functions_called)
        all_imports.update(imports)
        all_classes[filepath] = classes
        
        # Read file content for additional analysis
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            streamlit_callbacks = find_streamlit_callbacks(content)
            dynamic_calls = find_dynamic_calls(content)
            
            all_streamlit_callbacks.update(streamlit_callbacks)
            all_dynamic_calls.update(dynamic_calls)
            
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    # Analyze unused functions
    print("\n" + "="*80)
    print("UNUSED FUNCTION ANALYSIS")
    print("="*80)
    
    # Create sets for quick lookup
    called_functions = all_functions_called.copy()
    called_functions.update(all_streamlit_callbacks)
    called_functions.update(all_dynamic_calls)
    called_functions.update(all_imports)
    
    # Special functions that are typically entry points or have special meaning
    special_functions = {
        '__init__', '__str__', '__repr__', '__call__', '__enter__', '__exit__',
        '__len__', '__getitem__', '__setitem__', '__delitem__', '__iter__',
        '__next__', '__contains__', '__eq__', '__lt__', '__gt__', '__le__',
        '__ge__', '__ne__', '__hash__', '__bool__', '__add__', '__sub__',
        '__mul__', '__div__', '__mod__', '__pow__', '__and__', '__or__',
        '__xor__', '__lshift__', '__rshift__', '__invert__', '__pos__',
        '__neg__', '__abs__', '__complex__', '__int__', '__float__',
        'main', 'run', 'execute', 'handle', 'callback', 'test_'
    }
    
    unused_by_file = {}
    potentially_unused = {}
    
    for filepath, functions in all_functions_defined.items():
        unused_functions = []
        potentially_unused_functions = []
        
        for func_name, line_no, func_type, class_name in functions:
            # Skip special functions
            if any(special in func_name.lower() for special in special_functions):
                continue
            
            # Skip if function is called
            if func_name in called_functions:
                continue
            
            # Check for test functions
            if func_name.startswith('test_') or 'test' in filepath.lower():
                continue
            
            # High confidence unused
            if func_name not in called_functions:
                confidence = "HIGH"
                
                # Lower confidence for certain patterns
                if (func_name.startswith('_') or  # Private functions
                    'page' in func_name.lower() or  # Page functions
                    'service' in func_name.lower() or  # Service functions
                    'handle' in func_name.lower() or  # Handler functions
                    'callback' in func_name.lower() or  # Callback functions
                    func_type in ['method', 'async_method']):  # Methods might be called dynamically
                    confidence = "MEDIUM"
                
                unused_functions.append({
                    'name': func_name,
                    'line': line_no,
                    'type': func_type,
                    'class': class_name,
                    'confidence': confidence
                })
        
        if unused_functions:
            unused_by_file[filepath] = unused_functions
    
    # Generate report
    print(f"\nFound {sum(len(funcs) for funcs in unused_by_file.values())} potentially unused functions/methods")
    print(f"Across {len(unused_by_file)} files\n")
    
    for filepath, unused_functions in unused_by_file.items():
        rel_path = os.path.relpath(filepath, project_root)
        print(f"\n📁 {rel_path}")
        print("-" * len(rel_path))
        
        for func in sorted(unused_functions, key=lambda x: x['line']):
            class_info = f" (in class {func['class']})" if func['class'] else ""
            print(f"  Line {func['line']:3d}: {func['name']}(){class_info}")
            print(f"           Type: {func['type']}, Confidence: {func['confidence']}")
    
    # Summary statistics
    print(f"\n\n{'='*80}")
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"Total Python files analyzed: {len(python_files)}")
    print(f"Total functions/methods defined: {sum(len(funcs) for funcs in all_functions_defined.values())}")
    print(f"Total unique function names called: {len(all_functions_called)}")
    print(f"Total Streamlit callbacks found: {len(all_streamlit_callbacks)}")
    print(f"Total dynamic calls found: {len(all_dynamic_calls)}")
    print(f"Potentially unused functions: {sum(len(funcs) for funcs in unused_by_file.values())}")
    
    high_confidence = sum(1 for funcs in unused_by_file.values() 
                         for func in funcs if func['confidence'] == 'HIGH')
    medium_confidence = sum(1 for funcs in unused_by_file.values() 
                           for func in funcs if func['confidence'] == 'MEDIUM')
    
    print(f"  - High confidence unused: {high_confidence}")
    print(f"  - Medium confidence unused: {medium_confidence}")
    
    # Additional insights
    print(f"\n\n{'='*80}")
    print("ADDITIONAL INSIGHTS")
    print("="*80)
    
    if all_streamlit_callbacks:
        print(f"\nStreamlit callbacks detected: {', '.join(sorted(all_streamlit_callbacks))}")
    
    if all_dynamic_calls:
        print(f"\nDynamic calls detected: {', '.join(sorted(all_dynamic_calls))}")
    
    print(f"\nNote: This analysis may have false positives for:")
    print("- Functions called through Streamlit's callback system")
    print("- Functions called dynamically (getattr, exec, eval)")
    print("- Functions used as entry points from external systems")
    print("- Methods that implement interfaces or are overridden")
    print("- Functions that are imported and used in other codebases")


if __name__ == "__main__":
    main()
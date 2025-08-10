#!/usr/bin/env python3
"""
Code Quality Monitor for Manufacturing ERP System
Continuously monitors and reports on code quality issues
"""

import ast
import re
import sys
from pathlib import Path
from datetime import datetime
import json

class CodeQualityMonitor:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.issues = {
            'critical': [],
            'major': [],
            'minor': [],
            'info': []
        }
        self.metrics = {}
        
    def analyze(self):
        """Perform comprehensive code quality analysis"""
        with open(self.file_path, 'r') as f:
            self.content = f.read()
            self.lines = self.content.split('\n')
        
        self.calculate_metrics()
        self.check_structure()
        self.check_error_handling()
        self.check_performance()
        self.check_security()
        self.check_maintainability()
        self.generate_report()
        
    def calculate_metrics(self):
        """Calculate basic code metrics"""
        self.metrics = {
            'total_lines': len(self.lines),
            'blank_lines': sum(1 for line in self.lines if not line.strip()),
            'comment_lines': sum(1 for line in self.lines if line.strip().startswith('#')),
            'functions': 0,
            'classes': 0,
            'complexity': 0
        }
        
        try:
            tree = ast.parse(self.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.metrics['functions'] += 1
                    # Check function length
                    if hasattr(node, 'end_lineno'):
                        func_lines = node.end_lineno - node.lineno + 1
                        if func_lines > 100:
                            self.issues['major'].append(f"Function '{node.name}' is too long ({func_lines} lines)")
                        if func_lines > 200:
                            self.issues['critical'].append(f"Function '{node.name}' is extremely long ({func_lines} lines)")
                elif isinstance(node, ast.ClassDef):
                    self.metrics['classes'] += 1
        except SyntaxError as e:
            self.issues['critical'].append(f"Syntax error: {e}")
            
    def check_structure(self):
        """Check code structure and organization"""
        # Check for duplicate functions
        function_names = re.findall(r'def\s+(\w+)\s*\(', self.content)
        duplicates = [name for name in function_names if function_names.count(name) > 1]
        if duplicates:
            self.issues['major'].append(f"Duplicate function definitions: {set(duplicates)}")
        
        # Check for global variables (excluding constants)
        globals_pattern = r'^(?!(?:def|class|import|from|#))[a-z_][a-z0-9_]*\s*='
        globals_found = re.findall(globals_pattern, self.content, re.MULTILINE)
        if len(globals_found) > 10:
            self.issues['major'].append(f"Too many global variables ({len(globals_found)})")
            
    def check_error_handling(self):
        """Check error handling practices"""
        # Bare except clauses
        bare_excepts = re.findall(r'except\s*:', self.content)
        if bare_excepts:
            self.issues['major'].append(f"Found {len(bare_excepts)} bare except clauses")
        
        # Except pass anti-pattern
        except_pass = re.findall(r'except.*:\s*\n\s*pass', self.content)
        if except_pass:
            self.issues['major'].append(f"Found {len(except_pass)} except:pass anti-patterns")
        
        # Missing error messages
        except_without_log = re.findall(r'except\s+\w+.*:\s*\n(?!\s*(?:print|logger|raise))', self.content)
        if len(except_without_log) > 5:
            self.issues['minor'].append(f"Many exceptions without logging ({len(except_without_log)})")
            
    def check_performance(self):
        """Check for performance issues"""
        # Nested loops
        nested_loops = re.findall(r'for\s+.*:\s*\n.*for\s+.*:', self.content)
        if len(nested_loops) > 10:
            self.issues['minor'].append(f"Many nested loops found ({len(nested_loops)})")
        
        # DataFrame operations in loops
        df_in_loops = re.findall(r'for.*:\s*\n.*(?:iloc|loc|at|iat)', self.content)
        if df_in_loops:
            self.issues['major'].append(f"DataFrame operations in loops detected ({len(df_in_loops)})")
        
        # Missing caching
        no_cache = not re.search(r'@lru_cache|@cache|cache\s*=', self.content)
        if no_cache and self.metrics['functions'] > 20:
            self.issues['minor'].append("Consider adding caching for frequently called functions")
            
    def check_security(self):
        """Check for security issues"""
        # SQL injection risks
        sql_concat = re.findall(r'(?:SELECT|INSERT|UPDATE|DELETE).*\+.*(?:request|input|param)', self.content, re.IGNORECASE)
        if sql_concat:
            self.issues['critical'].append(f"Potential SQL injection risk ({len(sql_concat)} instances)")
        
        # Hardcoded secrets
        secrets_patterns = [
            r'(?:password|passwd|pwd|secret|token|api_key)\s*=\s*["\'][^"\']+["\']',
            r'(?:AWS|AZURE|GCP)_[A-Z_]*KEY\s*=',
        ]
        for pattern in secrets_patterns:
            if re.search(pattern, self.content, re.IGNORECASE):
                self.issues['critical'].append("Potential hardcoded secrets detected")
                break
                
    def check_maintainability(self):
        """Check code maintainability"""
        # Missing docstrings
        functions_without_docs = re.findall(r'def\s+\w+\([^)]*\):\s*\n(?!\s*(?:"""|\'\'\'))', self.content)
        if len(functions_without_docs) > self.metrics['functions'] * 0.3:
            self.issues['minor'].append(f"Many functions without docstrings ({len(functions_without_docs)})")
        
        # Magic numbers
        magic_numbers = re.findall(r'(?<!["\'])\b(?:3\.14159|2\.71828|86400|3600|1024|60)\b(?!["\'])', self.content)
        if len(magic_numbers) > 10:
            self.issues['minor'].append(f"Many magic numbers ({len(magic_numbers)}), consider using constants")
        
        # Long lines
        long_lines = [i for i, line in enumerate(self.lines, 1) if len(line) > 120]
        if len(long_lines) > 50:
            self.issues['minor'].append(f"Many long lines ({len(long_lines)} > 120 chars)")
            
    def generate_report(self):
        """Generate quality report"""
        print("\n" + "="*60)
        print(f"🔍 CODE QUALITY REPORT - {self.file_path.name}")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Metrics
        print("\n📊 METRICS:")
        print(f"  Total Lines: {self.metrics['total_lines']}")
        print(f"  Code Lines: {self.metrics['total_lines'] - self.metrics['blank_lines'] - self.metrics['comment_lines']}")
        print(f"  Functions: {self.metrics['functions']}")
        print(f"  Classes: {self.metrics['classes']}")
        
        # Quality Score
        total_issues = sum(len(issues) for issues in self.issues.values())
        if total_issues == 0:
            score = 100
        else:
            score = max(0, 100 - (len(self.issues['critical']) * 20 + 
                                  len(self.issues['major']) * 10 + 
                                  len(self.issues['minor']) * 3))
        
        print(f"\n🎯 QUALITY SCORE: {score}/100")
        
        # Issues
        if self.issues['critical']:
            print("\n🔴 CRITICAL ISSUES:")
            for issue in self.issues['critical']:
                print(f"  ❌ {issue}")
                
        if self.issues['major']:
            print("\n🟠 MAJOR ISSUES:")
            for issue in self.issues['major']:
                print(f"  ⚠️  {issue}")
                
        if self.issues['minor']:
            print("\n🟡 MINOR ISSUES:")
            for issue in self.issues['minor'][:5]:  # Show first 5
                print(f"  ℹ️  {issue}")
                
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if score < 60:
            print("  1. Address critical issues immediately")
            print("  2. Refactor long functions into smaller units")
            print("  3. Improve error handling")
        elif score < 80:
            print("  1. Fix major issues")
            print("  2. Add more documentation")
            print("  3. Consider performance optimizations")
        else:
            print("  1. Continue maintaining code quality")
            print("  2. Add unit tests for new functions")
            print("  3. Consider code review process")
            
        print("\n" + "="*60)
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'file': str(self.file_path),
            'metrics': self.metrics,
            'issues': self.issues,
            'score': score
        }
        
        report_file = self.file_path.parent / f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {report_file}")

if __name__ == "__main__":
    monitor = CodeQualityMonitor("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/beverly_comprehensive_erp.py")
    monitor.analyze()
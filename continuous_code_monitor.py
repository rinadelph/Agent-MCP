#\!/usr/bin/env python3
"""
Continuous Code Quality Monitor for Beverly Comprehensive ERP
Checks code quality, structure, and agent modifications every 30 seconds
"""

import time
import ast
import os
from pathlib import Path
from datetime import datetime
import json
import subprocess

class CodeQualityMonitor:
    def __init__(self, main_file='beverly_comprehensive_erp.py'):
        self.main_file = Path(main_file)
        self.last_check = None
        self.last_modified = None
        self.quality_scores = []
        
    def analyze_code_structure(self):
        """Analyze code structure and quality metrics"""
        if not self.main_file.exists():
            return {"error": "File not found"}
        
        with open(self.main_file, 'r') as f:
            content = f.read()
            lines = content.split('\n')
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"error": f"Syntax Error: {e}", "line": e.lineno}
        
        # Analyze functions
        functions = []
        classes = []
        imports = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                start = node.lineno
                end = node.end_lineno or start
                size = end - start
                functions.append({
                    'name': node.name,
                    'size': size,
                    'start_line': start,
                    'status': 'CRITICAL' if size > 200 else 'WARNING' if size > 100 else 'OK'
                })
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                imports += 1
        
        # Sort functions by size
        functions.sort(key=lambda x: x['size'], reverse=True)
        
        # Check for quality issues
        issues = []
        
        # Line length violations
        long_lines = sum(1 for line in lines if len(line) > 120)
        if long_lines > 0:
            issues.append(f"{long_lines} lines exceed 120 characters")
        
        # Bare except clauses
        bare_excepts = content.count('except:')
        if bare_excepts > 0:
            issues.append(f"{bare_excepts} bare except clauses found")
        
        # Check for critical yarn IDs (agent work verification)
        critical_yarns = ['19004', '18868', '18851', '18892', '14270']
        yarn_implementations = sum(1 for yarn in critical_yarns if yarn in content)
        
        # Check for specific implementations
        has_emergency_dashboard = 'emergency_shortage_dashboard' in content
        has_ml_training = 'SalesForecastingEngine' in content
        has_yarn_calculator = 'YarnRequirementCalculator' in content
        
        return {
            'timestamp': datetime.now().isoformat(),
            'file_stats': {
                'total_lines': len(lines),
                'total_functions': len(functions),
                'total_classes': len(classes),
                'imports': imports
            },
            'large_functions': functions[:5],  # Top 5 largest
            'quality_issues': issues,
            'implementation_status': {
                'critical_yarns_added': f"{yarn_implementations}/{len(critical_yarns)}",
                'emergency_dashboard': has_emergency_dashboard,
                'ml_training': has_ml_training,
                'yarn_calculator': has_yarn_calculator
            },
            'quality_score': self.calculate_quality_score(functions, issues)
        }
    
    def calculate_quality_score(self, functions, issues):
        """Calculate overall quality score (0-100)"""
        score = 100
        
        # Deduct for oversized functions
        for func in functions:
            if func['size'] > 200:
                score -= 10
            elif func['size'] > 100:
                score -= 3
        
        # Deduct for issues
        score -= len(issues) * 5
        
        return max(0, score)
    
    def check_recent_changes(self):
        """Check if file was recently modified"""
        if self.main_file.exists():
            mod_time = os.path.getmtime(self.main_file)
            if self.last_modified and mod_time != self.last_modified:
                return True, datetime.fromtimestamp(mod_time)
            self.last_modified = mod_time
        return False, None
    
    def monitor_agents(self):
        """Check what agents are doing"""
        agent_activity = {}
        
        # Check for running Python processes that might be tests
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            processes = result.stdout
            
            # Look for test scripts
            test_indicators = ['test_', 'train_', 'analyze_', 'critical_']
            for indicator in test_indicators:
                if indicator in processes:
                    agent_activity[indicator] = True
        except:
            pass
        
        return agent_activity
    
    def generate_report(self):
        """Generate comprehensive quality report"""
        analysis = self.analyze_code_structure()
        changed, mod_time = self.check_recent_changes()
        agent_activity = self.monitor_agents()
        
        report = {
            'analysis': analysis,
            'file_modified': changed,
            'last_modified': mod_time.isoformat() if mod_time else None,
            'agent_activity': agent_activity
        }
        
        # Color-coded output
        print("\n" + "="*80)
        print(f"📊 CODE QUALITY MONITOR - {datetime.now().strftime('%H:%M:%S')}")
        print("="*80)
        
        if 'error' in analysis:
            print(f"❌ ERROR: {analysis['error']}")
            return report
        
        # File stats
        stats = analysis['file_stats']
        print(f"\n📁 FILE STATISTICS:")
        print(f"  Lines: {stats['total_lines']}")
        print(f"  Functions: {stats['total_functions']}")
        print(f"  Classes: {stats['total_classes']}")
        print(f"  Quality Score: {analysis['quality_score']}/100")
        
        # Large functions
        if analysis['large_functions']:
            print(f"\n⚠️  LARGE FUNCTIONS:")
            for func in analysis['large_functions'][:3]:
                status_icon = "🔴" if func['status'] == 'CRITICAL' else "🟡" if func['status'] == 'WARNING' else "🟢"
                print(f"  {status_icon} {func['name']}: {func['size']} lines (line {func['start_line']})")
        
        # Quality issues
        if analysis['quality_issues']:
            print(f"\n❗ QUALITY ISSUES:")
            for issue in analysis['quality_issues']:
                print(f"  • {issue}")
        
        # Implementation status
        impl = analysis['implementation_status']
        print(f"\n🎯 IMPLEMENTATION STATUS:")
        print(f"  Critical Yarns: {impl['critical_yarns_added']}")
        print(f"  Emergency Dashboard: {'✅' if impl['emergency_dashboard'] else '❌'}")
        print(f"  ML Training: {'✅' if impl['ml_training'] else '❌'}")
        print(f"  Yarn Calculator: {'✅' if impl['yarn_calculator'] else '❌'}")
        
        # Recent changes
        if changed:
            print(f"\n🔄 FILE MODIFIED: {mod_time.strftime('%H:%M:%S')}")
        
        # Agent activity
        if agent_activity:
            print(f"\n👥 AGENT ACTIVITY DETECTED:")
            for activity in agent_activity:
                print(f"  • {activity}")
        
        return report
    
    def run_continuous(self, interval=30):
        """Run continuous monitoring"""
        print("🚀 Starting Continuous Code Quality Monitor")
        print(f"   Monitoring: {self.main_file}")
        print(f"   Interval: {interval} seconds")
        print("   Press Ctrl+C to stop\n")
        
        try:
            while True:
                report = self.generate_report()
                
                # Save report to file
                with open('quality_report.json', 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                
                # Check for critical issues
                if report['analysis'].get('quality_score', 100) < 50:
                    print("\n🚨 CRITICAL: Quality score below 50! Immediate action needed!")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n📊 Monitoring stopped")
            return

if __name__ == "__main__":
    monitor = CodeQualityMonitor()
    monitor.run_continuous(30)

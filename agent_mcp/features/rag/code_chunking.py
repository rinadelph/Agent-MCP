# Agent-MCP Code-Aware Chunking Module
# Ported from swarm_mcp with enhancements for agent_mcp architecture

import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import ast

from ...core.config import logger

# Language-specific file extensions mapping
LANGUAGE_FAMILIES = {
    'python': {'.py', '.pyw', '.pyx', '.pyi'},
    'javascript': {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'},
    'c_family': {'.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', '.c++', '.hh', '.hxx', '.h++'},
    'rust': {'.rs'},
    'go': {'.go'},
    'java': {'.java'},
    'ruby': {'.rb', '.rake'},
    'php': {'.php', '.php3', '.php4', '.php5', '.phtml'},
    'sql': {'.sql'},
    'shell': {'.sh', '.bash', '.zsh', '.fish'},
    'yaml': {'.yaml', '.yml'},
    'json': {'.json', '.jsonl'},
    'xml': {'.xml', '.xsd', '.xsl'},
    'html': {'.html', '.htm', '.xhtml'},
    'css': {'.css', '.scss', '.sass', '.less'},
}

# All code file extensions
CODE_EXTENSIONS = set()
for extensions in LANGUAGE_FAMILIES.values():
    CODE_EXTENSIONS.update(extensions)

# Additional document extensions that might contain code
DOCUMENT_EXTENSIONS = {'.md', '.rst', '.txt', '.adoc', '.tex'}


def detect_language_family(file_path: Path) -> str:
    """
    Detect the language family based on file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Language family name or 'generic' if unknown
    """
    extension = file_path.suffix.lower()
    
    for family, extensions in LANGUAGE_FAMILIES.items():
        if extension in extensions:
            return family
    
    return 'generic'


def extract_code_entities(content: str, file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract code entities (functions, classes, methods) with line numbers.
    
    Args:
        content: File content
        file_path: Path to the file
        
    Returns:
        List of entities with metadata
    """
    language_family = detect_language_family(file_path)
    entities = []
    
    if language_family == 'python':
        entities = _extract_python_entities(content)
    elif language_family == 'javascript':
        entities = _extract_javascript_entities(content)
    elif language_family in ['c_family', 'rust', 'go', 'java']:
        entities = _extract_generic_code_entities(content, language_family)
    
    return entities


def _extract_python_entities(content: str) -> List[Dict[str, Any]]:
    """Extract Python functions, classes, and methods."""
    entities = []
    lines = content.split('\n')
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                entity = {
                    'type': 'function',
                    'name': node.name,
                    'start_line': node.lineno,
                    'end_line': node.end_lineno or node.lineno,
                    'decorators': [d.id for d in node.decorator_list if hasattr(d, 'id')]
                }
                entities.append(entity)
                
            elif isinstance(node, ast.ClassDef):
                entity = {
                    'type': 'class',
                    'name': node.name,
                    'start_line': node.lineno,
                    'end_line': node.end_lineno or node.lineno,
                    'methods': []
                }
                
                # Extract methods within the class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method = {
                            'type': 'method',
                            'name': item.name,
                            'parent_class': node.name,
                            'start_line': item.lineno,
                            'end_line': item.end_lineno or item.lineno
                        }
                        entity['methods'].append(method)
                        entities.append(method)
                
                entities.append(entity)
                
    except SyntaxError as e:
        logger.warning(f"Failed to parse Python file: {e}")
        # Fallback to regex-based extraction
        entities = _extract_python_entities_regex(content)
    
    return entities


def _extract_python_entities_regex(content: str) -> List[Dict[str, Any]]:
    """Fallback regex-based Python entity extraction."""
    entities = []
    lines = content.split('\n')
    
    # Function pattern
    func_pattern = re.compile(r'^(async\s+)?def\s+(\w+)\s*\(', re.MULTILINE)
    # Class pattern  
    class_pattern = re.compile(r'^class\s+(\w+)[\s\(:]', re.MULTILINE)
    
    for match in func_pattern.finditer(content):
        line_no = content[:match.start()].count('\n') + 1
        entities.append({
            'type': 'function',
            'name': match.group(2),
            'start_line': line_no,
            'end_line': line_no  # Will be updated by chunk boundaries
        })
    
    for match in class_pattern.finditer(content):
        line_no = content[:match.start()].count('\n') + 1
        entities.append({
            'type': 'class',
            'name': match.group(1),
            'start_line': line_no,
            'end_line': line_no
        })
    
    return entities


def _extract_javascript_entities(content: str) -> List[Dict[str, Any]]:
    """Extract JavaScript/TypeScript functions, classes, and components."""
    entities = []
    
    # Function patterns (various forms)
    patterns = [
        # Named functions
        (r'function\s+(\w+)\s*\(', 'function'),
        # Const/let/var arrow functions
        (r'(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=]+)\s*=>', 'function'),
        # Class declarations
        (r'class\s+(\w+)(?:\s+extends\s+\w+)?\s*{', 'class'),
        # React components (function form)
        (r'(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)\s*\(', 'component'),
        # React components (const form)
        (r'(?:export\s+)?(?:const|let)\s+([A-Z]\w+)\s*=\s*(?:\([^)]*\)|[^=]+)\s*=>', 'component'),
    ]
    
    for pattern, entity_type in patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            line_no = content[:match.start()].count('\n') + 1
            entities.append({
                'type': entity_type,
                'name': match.group(1),
                'start_line': line_no,
                'end_line': line_no
            })
    
    return entities


def _extract_generic_code_entities(content: str, language: str) -> List[Dict[str, Any]]:
    """Extract entities for C-family, Rust, Go, Java languages."""
    entities = []
    
    # Language-specific patterns
    if language == 'c_family':
        # C/C++ function pattern
        func_pattern = r'(?:static\s+)?(?:inline\s+)?(?:\w+\s+)*?(\w+)\s*\([^)]*\)\s*{'
    elif language == 'rust':
        # Rust function pattern
        func_pattern = r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[<(]'
    elif language == 'go':
        # Go function pattern
        func_pattern = r'func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\('
    elif language == 'java':
        # Java method pattern
        func_pattern = r'(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*{'
    else:
        return entities
    
    for match in re.finditer(func_pattern, content, re.MULTILINE):
        line_no = content[:match.start()].count('\n') + 1
        entities.append({
            'type': 'function',
            'name': match.group(1),
            'start_line': line_no,
            'end_line': line_no
        })
    
    return entities


def chunk_code_aware(
    content: str,
    file_path: Path,
    target_size: int = 1500,
    max_size: int = 3000,
    min_size: int = 300
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Perform code-aware chunking that preserves code structure.
    
    Args:
        content: File content to chunk
        file_path: Path to the file for language detection
        target_size: Target chunk size in characters
        max_size: Maximum chunk size before forcing split
        min_size: Minimum chunk size to avoid tiny chunks
        
    Returns:
        List of (chunk_text, metadata) tuples
    """
    language_family = detect_language_family(file_path)
    
    if language_family == 'python':
        return _chunk_python_code(content, target_size, max_size, min_size)
    elif language_family == 'javascript':
        return _chunk_javascript_code(content, target_size, max_size, min_size)
    elif language_family in ['c_family', 'rust', 'go', 'java']:
        return _chunk_generic_code(content, target_size, max_size, min_size, language_family)
    else:
        # Fallback to generic code chunking
        return _chunk_generic_code(content, target_size, max_size, min_size, 'generic')


def _chunk_python_code(
    content: str, 
    target_size: int,
    max_size: int,
    min_size: int
) -> List[Tuple[str, Dict[str, Any]]]:
    """Chunk Python code preserving class and function boundaries."""
    chunks = []
    lines = content.split('\n')
    
    # Extract entities first
    entities = _extract_python_entities(content)
    
    # Sort entities by start line
    entities.sort(key=lambda x: x['start_line'])
    
    # Track current chunk
    current_chunk_lines = []
    current_chunk_size = 0
    chunk_metadata = {
        'language': 'python',
        'section_type': 'module_header',
        'entities': []
    }
    
    # Process line by line
    line_num = 0
    entity_idx = 0
    
    while line_num < len(lines):
        line = lines[line_num]
        line_size = len(line) + 1  # +1 for newline
        
        # Check if we're at the start of an entity
        at_entity_start = False
        current_entity = None
        
        if entity_idx < len(entities):
            current_entity = entities[entity_idx]
            if line_num + 1 == current_entity['start_line']:
                at_entity_start = True
        
        # Decide whether to start a new chunk
        should_split = False
        
        if at_entity_start and current_chunk_size > min_size:
            # We're at the start of a new entity and have enough content
            should_split = True
        elif current_chunk_size + line_size > max_size:
            # Force split at max size
            should_split = True
        elif current_chunk_size > target_size and not at_entity_start:
            # Look ahead for a good split point
            lookahead = min(10, len(lines) - line_num)
            for i in range(1, lookahead):
                if line_num + i < len(lines):
                    future_line = lines[line_num + i].strip()
                    # Good split points: empty lines, class/function definitions
                    if (not future_line or 
                        future_line.startswith('def ') or 
                        future_line.startswith('class ') or
                        future_line.startswith('async def ')):
                        should_split = True
                        break
        
        if should_split and current_chunk_lines:
            # Create chunk
            chunk_text = '\n'.join(current_chunk_lines)
            chunks.append((chunk_text, chunk_metadata.copy()))
            
            # Reset for next chunk
            current_chunk_lines = []
            current_chunk_size = 0
            chunk_metadata = {
                'language': 'python',
                'section_type': 'code',
                'entities': []
            }
        
        # Add line to current chunk
        current_chunk_lines.append(line)
        current_chunk_size += line_size
        
        # Update metadata if we're in an entity
        if current_entity and line_num + 1 >= current_entity['start_line']:
            if current_entity not in chunk_metadata['entities']:
                chunk_metadata['entities'].append(current_entity)
                chunk_metadata['section_type'] = current_entity['type']
            
            # Move to next entity if we've passed this one
            if line_num + 1 >= current_entity.get('end_line', current_entity['start_line']):
                entity_idx += 1
        
        line_num += 1
    
    # Don't forget the last chunk
    if current_chunk_lines:
        chunk_text = '\n'.join(current_chunk_lines)
        chunks.append((chunk_text, chunk_metadata))
    
    return chunks


def _chunk_javascript_code(
    content: str,
    target_size: int,
    max_size: int, 
    min_size: int
) -> List[Tuple[str, Dict[str, Any]]]:
    """Chunk JavaScript/TypeScript code preserving function and component boundaries."""
    chunks = []
    lines = content.split('\n')
    
    # Extract entities
    entities = _extract_javascript_entities(content)
    entities.sort(key=lambda x: x['start_line'])
    
    current_chunk_lines = []
    current_chunk_size = 0
    chunk_metadata = {
        'language': 'javascript',
        'section_type': 'module',
        'entities': []
    }
    
    # Track brace depth for better splitting
    brace_depth = 0
    line_num = 0
    entity_idx = 0
    
    while line_num < len(lines):
        line = lines[line_num]
        line_size = len(line) + 1
        
        # Update brace depth
        brace_depth += line.count('{') - line.count('}')
        
        # Check for entity boundaries
        at_entity_start = False
        if entity_idx < len(entities) and line_num + 1 == entities[entity_idx]['start_line']:
            at_entity_start = True
        
        # Splitting logic
        should_split = False
        
        if at_entity_start and current_chunk_size > min_size:
            should_split = True
        elif current_chunk_size + line_size > max_size:
            should_split = True
        elif current_chunk_size > target_size and brace_depth == 0:
            # Good place to split when not inside a block
            should_split = True
        
        if should_split and current_chunk_lines:
            chunk_text = '\n'.join(current_chunk_lines)
            chunks.append((chunk_text, chunk_metadata.copy()))
            
            current_chunk_lines = []
            current_chunk_size = 0
            chunk_metadata = {
                'language': 'javascript',
                'section_type': 'code',
                'entities': []
            }
        
        current_chunk_lines.append(line)
        current_chunk_size += line_size
        
        # Update entity tracking
        if entity_idx < len(entities):
            entity = entities[entity_idx]
            if line_num + 1 >= entity['start_line']:
                if entity not in chunk_metadata['entities']:
                    chunk_metadata['entities'].append(entity)
                    chunk_metadata['section_type'] = entity['type']
                # Simple heuristic for entity end
                if brace_depth == 0 and line_num > entity['start_line']:
                    entity_idx += 1
        
        line_num += 1
    
    if current_chunk_lines:
        chunk_text = '\n'.join(current_chunk_lines)
        chunks.append((chunk_text, chunk_metadata))
    
    return chunks


def _chunk_generic_code(
    content: str,
    target_size: int,
    max_size: int,
    min_size: int,
    language: str
) -> List[Tuple[str, Dict[str, Any]]]:
    """Generic code chunking for various languages."""
    chunks = []
    lines = content.split('\n')
    
    current_chunk_lines = []
    current_chunk_size = 0
    chunk_metadata = {
        'language': language,
        'section_type': 'code',
        'line_range': None
    }
    
    # Track various depth indicators
    brace_depth = 0
    paren_depth = 0
    in_multiline_comment = False
    
    start_line = 1
    
    for line_num, line in enumerate(lines):
        line_size = len(line) + 1
        
        # Update depth tracking
        if not in_multiline_comment:
            brace_depth += line.count('{') - line.count('}')
            paren_depth += line.count('(') - line.count(')')
            
            if '/*' in line:
                in_multiline_comment = True
        
        if in_multiline_comment and '*/' in line:
            in_multiline_comment = False
        
        # Check if we should split
        should_split = False
        
        if current_chunk_size + line_size > max_size:
            should_split = True
        elif current_chunk_size > target_size:
            # Look for good split points
            if (brace_depth == 0 and 
                paren_depth == 0 and 
                not in_multiline_comment and
                (not line.strip() or line.strip().startswith('//'))):
                should_split = True
        
        if should_split and current_chunk_lines:
            chunk_text = '\n'.join(current_chunk_lines)
            chunk_metadata['line_range'] = (start_line, line_num)
            chunks.append((chunk_text, chunk_metadata.copy()))
            
            current_chunk_lines = []
            current_chunk_size = 0
            start_line = line_num + 1
            chunk_metadata = {
                'language': language,
                'section_type': 'code',
                'line_range': None
            }
        
        current_chunk_lines.append(line)
        current_chunk_size += line_size
    
    if current_chunk_lines:
        chunk_text = '\n'.join(current_chunk_lines)
        chunk_metadata['line_range'] = (start_line, len(lines))
        chunks.append((chunk_text, chunk_metadata))
    
    return chunks


def create_file_summary(content: str, file_path: Path, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a summary of a code file for hierarchical indexing.
    
    Args:
        content: File content
        file_path: Path to file
        entities: Extracted code entities
        
    Returns:
        File summary metadata
    """
    language = detect_language_family(file_path)
    lines = content.split('\n')
    
    # Extract imports/dependencies
    imports = []
    if language == 'python':
        import_pattern = re.compile(r'^(?:from\s+(\S+)\s+)?import\s+(.+)$', re.MULTILINE)
        for match in import_pattern.finditer(content):
            if match.group(1):
                imports.append(match.group(1))
            else:
                # Handle comma-separated imports
                for imp in match.group(2).split(','):
                    imports.append(imp.strip().split()[0])
    
    elif language == 'javascript':
        # ES6 imports
        import_pattern = re.compile(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', re.MULTILINE)
        imports.extend(match.group(1) for match in import_pattern.finditer(content))
        # CommonJS requires
        require_pattern = re.compile(r'require\s*\([\'"]([^\'"]+)[\'"]\)', re.MULTILINE)
        imports.extend(match.group(1) for match in require_pattern.finditer(content))
    
    # Group entities by type
    functions = [e for e in entities if e['type'] == 'function']
    classes = [e for e in entities if e['type'] == 'class']
    methods = [e for e in entities if e['type'] == 'method']
    components = [e for e in entities if e['type'] == 'component']
    
    return {
        'document_type': 'file_summary',
        'file_path': str(file_path),
        'language': language,
        'total_lines': len(lines),
        'imports': list(set(imports)),  # Remove duplicates
        'entities': entities,
        'entity_count': {
            'functions': len(functions),
            'classes': len(classes),
            'methods': len(methods),
            'components': len(components)
        },
        'entity_names': {
            'functions': [f['name'] for f in functions],
            'classes': [c['name'] for c in classes],
            'components': [c['name'] for c in components]
        }
    }
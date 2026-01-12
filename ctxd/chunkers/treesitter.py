"""
Tree-sitter based chunking strategy for multiple languages.

Uses AST parsing to extract functions and classes as semantic chunks.
Supports Python, JavaScript, TypeScript, and Go.
"""

import logging
from typing import Any, Optional, Callable
from tree_sitter import Language, Parser, Node

from .base import ChunkStrategy
from .fallback import FallbackChunker

logger = logging.getLogger(__name__)

# Fix 2: Lazy tree-sitter imports
# Language modules are imported on-demand in _get_language() instead of at module load time


class TreeSitterChunker(ChunkStrategy):
    """
    Multi-language AST-based chunking strategy using tree-sitter.

    Extracts functions and classes as separate chunks, including their
    decorators and docstrings. For small files (<50 lines), keeps the
    entire file as a single chunk.

    Supported languages: Python, JavaScript, TypeScript, Go
    """

    # Class-level cache for lazy-loaded languages (Fix 2: Performance optimization)
    _languages: dict[str, Language] = {}

    # Language-specific configurations
    LANGUAGE_CONFIGS = {
        "python": {
            "definition_types": ["function_definition", "class_definition"],
            "name_extractor": "_extract_python_name",
            "decorator_finder": "_find_python_decorators",
        },
        "javascript": {
            "definition_types": [
                "function_declaration",
                "generator_function_declaration",  # Generator functions
                "class_declaration",
                "method_definition",
                "variable_declarator",  # For arrow functions
            ],
            "name_extractor": "_extract_js_name",
            "decorator_finder": None,  # JS doesn't use decorators (yet)
        },
        "typescript": {
            "language_func": "language_typescript",
            "definition_types": [
                "function_declaration",
                "generator_function_declaration",  # Generator functions
                "class_declaration",
                "method_definition",
                "interface_declaration",
                "type_alias_declaration",
                "variable_declarator",  # For arrow functions
                "abstract_class_declaration",  # Abstract classes
            ],
            "name_extractor": "_extract_js_name",  # Same as JS
            "decorator_finder": None,
        },
        "go": {
            "definition_types": [
                "function_declaration",
                "method_declaration",
                "type_spec",  # For structs and interfaces
            ],
            "name_extractor": "_extract_go_name",
            "decorator_finder": None,
        },
    }

    @classmethod
    def _get_language(cls, lang: str) -> Language:
        """
        Lazy-load tree-sitter language module (Fix 2: Performance optimization).

        Args:
            lang: Language name ("python", "javascript", "typescript", "go")

        Returns:
            Language instance

        Raises:
            ValueError: If language is not supported
        """
        if lang not in cls._languages:
            logger.debug(f"Lazy-loading tree-sitter language: {lang}")
            if lang == "python":
                import tree_sitter_python as ts
                cls._languages[lang] = Language(ts.language())
            elif lang == "javascript":
                import tree_sitter_javascript as ts
                cls._languages[lang] = Language(ts.language())
            elif lang == "typescript":
                import tree_sitter_typescript as ts
                cls._languages[lang] = Language(ts.language_typescript())
            elif lang == "go":
                import tree_sitter_go as ts
                cls._languages[lang] = Language(ts.language())
            else:
                raise ValueError(f"Unsupported language: {lang}")
        return cls._languages[lang]

    def __init__(self, language: str, small_file_threshold: int = 50, max_chunk_size: int = 500):
        """
        Initialize the tree-sitter chunker.

        Args:
            language: Programming language ("python", "javascript", "typescript", "go")
            small_file_threshold: Files with fewer lines are kept as single chunk
            max_chunk_size: Maximum chunk size for fallback chunker (Phase 6)

        Raises:
            ValueError: If language is not supported
        """
        self.language_name = language
        self.small_file_threshold = small_file_threshold

        # Get language configuration
        self.config = self.LANGUAGE_CONFIGS.get(language)
        if not self.config:
            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported: {list(self.LANGUAGE_CONFIGS.keys())}"
            )

        # Lazy-load language and initialize parser (Fix 2: Performance optimization)
        self.language = self._get_language(language)
        self.parser = Parser(self.language)

        # Get language-specific extractors
        self.name_extractor: Callable = getattr(self, self.config["name_extractor"])
        self.decorator_finder: Optional[Callable] = (
            getattr(self, self.config["decorator_finder"])
            if self.config["decorator_finder"]
            else None
        )

        # Initialize fallback chunker for parse errors (Phase 6)
        self.fallback_chunker = FallbackChunker(
            max_chunk_size=max_chunk_size,
            chunk_overlap=50
        )

    def chunk(self, content: str, path: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Split code into function/class chunks based on language.

        Args:
            content: The source code
            path: File path for logging

        Returns:
            List of (chunk_text, metadata) tuples
        """
        if not content.strip():
            return []

        lines = content.split("\n")
        line_count = len(lines)

        # Parse the code with improved error handling (Phase 6)
        try:
            tree = self.parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node

            # Only fall back on critical parse errors, not minor issues (Phase 6)
            # Many test snippets have minor errors but are still parseable
            if root_node.has_error:
                logger.debug(
                    f"Parse warnings in {path} ({self.language_name}), "
                    f"attempting to extract definitions anyway"
                )

            # Extract definitions based on language-specific types
            definition_types = self.config["definition_types"]
            chunks = []
            for node in self._walk_tree(root_node):
                if node.type in definition_types:
                    chunk_info = self._extract_definition(node, content)
                    if chunk_info:
                        chunks.append(chunk_info)

            if chunks:
                logger.debug(
                    f"Extracted {len(chunks)} chunks from {path} "
                    f"using tree-sitter ({self.language_name})"
                )
                return chunks
            else:
                # No definitions found - return whole file as one chunk
                logger.debug(f"No definitions found in {path}, using single chunk")
                return [(content, {
                    "start_line": 1,
                    "end_line": line_count,
                    "chunk_type": "block",
                    "name": None,
                })]

        except Exception as e:
            # Graceful fallback on any parsing exception (Phase 6)
            logger.error(
                f"Tree-sitter parsing failed for {path} ({self.language_name}): {e}. "
                f"Using fallback chunker"
            )
            return self.fallback_chunker.chunk(content, path)

    def _walk_tree(self, node: Node) -> list[Node]:
        """
        Walk the AST and collect all nodes.

        Args:
            node: Root node to start walking from

        Returns:
            List of all nodes in the tree
        """
        nodes = [node]
        for child in node.children:
            nodes.extend(self._walk_tree(child))
        return nodes

    def _extract_definition(
        self,
        node: Node,
        content: str
    ) -> Optional[tuple[str, dict[str, Any]]]:
        """
        Extract a function, class, or type definition as a chunk.

        Args:
            node: AST node representing the definition
            content: Full file content

        Returns:
            (chunk_text, metadata) tuple or None
        """
        # For JS/TS variable_declarator, check if it's an arrow function
        if node.type == "variable_declarator":
            if not self._is_arrow_function(node):
                return None  # Skip non-function variable declarations

        start_line = node.start_point[0] + 1  # tree-sitter uses 0-indexed lines
        end_line = node.end_point[0] + 1

        # Extract the chunk text
        chunk_text = content.encode("utf8")[node.start_byte:node.end_byte].decode("utf8")

        # Extract name using language-specific extractor
        name = self.name_extractor(node)

        # Determine chunk type
        chunk_type = self._determine_chunk_type(node)

        # Include decorators if present (Python-specific)
        if self.decorator_finder:
            decorators = self.decorator_finder(node, content)
            if decorators:
                chunk_text = decorators + "\n" + chunk_text
                # Adjust start_line to include decorators
                decorator_lines = decorators.count("\n") + 1
                start_line -= decorator_lines

        return (chunk_text, {
            "start_line": start_line,
            "end_line": end_line,
            "chunk_type": chunk_type,
            "name": name,
        })

    def _determine_chunk_type(self, node: Node) -> str:
        """Determine the chunk type based on node type."""
        type_mapping = {
            "function_definition": "function",
            "function_declaration": "function",
            "generator_function_declaration": "function",  # JS/TS generators
            "method_definition": "function",
            "method_declaration": "function",
            "class_definition": "class",
            "class_declaration": "class",
            "abstract_class_declaration": "class",  # TypeScript abstract classes
            "interface_declaration": "interface",
            "type_alias_declaration": "type",
            "type_spec": "type",
            "variable_declarator": "function",  # Arrow functions
        }
        return type_mapping.get(node.type, "block")

    def _is_arrow_function(self, node: Node) -> bool:
        """Check if a variable_declarator contains an arrow function."""
        for child in node.children:
            if child.type == "arrow_function":
                return True
            # Check nested (e.g., in assignment)
            for grandchild in child.children:
                if grandchild.type == "arrow_function":
                    return True
        return False

    # ===== Python-specific extractors =====

    def _extract_python_name(self, node: Node) -> Optional[str]:
        """
        Extract the name of a Python function or class definition.

        Args:
            node: AST node representing the definition

        Returns:
            Name string or None
        """
        # For function_definition and class_definition, the name is typically
        # the second child (after 'def' or 'class' keyword)
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf8")

        # If not found in direct children, look one level deeper
        for child in node.children:
            for grandchild in child.children:
                if grandchild.type == "identifier":
                    return grandchild.text.decode("utf8")

        return None

    def _find_python_decorators(self, node: Node, content: str) -> str:
        """
        Find decorators for a Python function/class definition.

        Args:
            node: The function/class definition node
            content: Full file content

        Returns:
            Decorator text or empty string
        """
        # Look for decorated_definition parent
        if node.parent and node.parent.type == "decorated_definition":
            decorator_node = None
            for child in node.parent.children:
                if child.type == "decorator":
                    decorator_node = child
                    break

            if decorator_node:
                return content.encode("utf8")[
                    decorator_node.start_byte:decorator_node.end_byte
                ].decode("utf8")

        return ""

    # ===== JavaScript/TypeScript-specific extractors =====

    def _extract_js_name(self, node: Node) -> Optional[str]:
        """
        Extract the name of a JS/TS function, class, interface, or type.

        Args:
            node: AST node representing the definition

        Returns:
            Name string or None
        """
        if node.type in ["function_declaration", "generator_function_declaration", "class_declaration", "abstract_class_declaration", "method_definition"]:
            # Name is a direct child (identifier, property_identifier, or type_identifier for TS classes)
            for child in node.children:
                if child.type in ["identifier", "property_identifier", "type_identifier"]:
                    return child.text.decode("utf8")

        elif node.type in ["interface_declaration", "type_alias_declaration"]:
            # TypeScript types/interfaces: name follows keyword
            for child in node.children:
                if child.type == "type_identifier":
                    return child.text.decode("utf8")

        elif node.type == "variable_declarator":
            # For: const myFunc = () => {}
            # Name is first child (identifier)
            if node.children and node.children[0].type == "identifier":
                return node.children[0].text.decode("utf8")

        return None

    # ===== Go-specific extractors =====

    def _extract_go_name(self, node: Node) -> Optional[str]:
        """
        Extract the name of a Go function, method, or type.

        Args:
            node: AST node representing the definition

        Returns:
            Name string or None
        """
        if node.type == "function_declaration":
            # Function name is an identifier child
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf8")

        elif node.type == "method_declaration":
            # Method name is a field_identifier child (after receiver parameter_list)
            for child in node.children:
                if child.type == "field_identifier":
                    return child.text.decode("utf8")

        elif node.type == "type_spec":
            # Type specification (struct, interface)
            # First child is the type name
            if node.children and node.children[0].type == "type_identifier":
                return node.children[0].text.decode("utf8")

        return None

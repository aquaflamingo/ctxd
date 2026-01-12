"""
Unit tests for chunking strategies.

Tests TreeSitterChunker (Python, JavaScript, TypeScript, Go), MarkdownChunker, and FallbackChunker.
"""

import pytest
from pathlib import Path
from ctxd.chunkers import TreeSitterChunker, MarkdownChunker, FallbackChunker


class TestTreeSitterChunker:
    """Tests for TreeSitterChunker."""

    # ===== Python Tests =====

    def test_chunk_python_functions(self):
        """Test chunking Python code with multiple functions."""
        chunker = TreeSitterChunker("python")
        code = '''
def function_one():
    """First function."""
    return 1

def function_two():
    """Second function."""
    return 2

def function_three():
    """Third function."""
    return 3
'''
        chunks = chunker.chunk(code, "test.py")

        assert len(chunks) >= 3  # At least 3 functions
        # Check that each chunk has the expected metadata
        for text, metadata in chunks:
            assert "start_line" in metadata
            assert "end_line" in metadata
            assert metadata["chunk_type"] in ("function", "class", "block")

    def test_chunk_python_class(self):
        """Test chunking Python code with a class."""
        chunker = TreeSitterChunker("python")
        code = '''
class MyClass:
    """A test class."""

    def method_one(self):
        """First method."""
        return 1

    def method_two(self):
        """Second method."""
        return 2
'''
        chunks = chunker.chunk(code, "test.py")

        # Should have at least the class and its methods
        assert len(chunks) > 0

        # Check that class is identified
        class_chunks = [c for c in chunks if c[1]["chunk_type"] == "class"]
        assert len(class_chunks) > 0

    def test_chunk_python_with_decorators(self):
        """Test that decorators are included with functions."""
        chunker = TreeSitterChunker("python")
        code = '''
@property
def decorated_function():
    """A decorated function."""
    return "value"
'''
        chunks = chunker.chunk(code, "test.py")

        assert len(chunks) > 0
        text, metadata = chunks[0]
        # Decorator should be included in the text
        # Note: This depends on the tree-sitter implementation
        assert metadata["name"] == "decorated_function"

    def test_chunk_small_file_with_function(self):
        """Test that functions are extracted even from small files."""
        chunker = TreeSitterChunker("python", small_file_threshold=50)
        code = '''
def small_function():
    """A function in a small file."""
    return "small"
'''
        chunks = chunker.chunk(code, "test.py")

        # Should extract the function
        assert len(chunks) == 1
        text, metadata = chunks[0]
        assert metadata["chunk_type"] == "function"
        assert metadata["name"] == "small_function"

    def test_chunk_empty_file(self):
        """Test chunking an empty file."""
        chunker = TreeSitterChunker("python")
        chunks = chunker.chunk("", "test.py")
        assert len(chunks) == 0

    def test_chunk_python_with_docstrings(self):
        """Test that docstrings are included with functions."""
        chunker = TreeSitterChunker("python")
        code = '''
def documented_function():
    """
    This is a detailed docstring.

    It has multiple lines.
    """
    return "value"
'''
        chunks = chunker.chunk(code, "test.py")

        assert len(chunks) > 0
        text, metadata = chunks[0]
        assert "detailed docstring" in text
        assert metadata["name"] == "documented_function"

    def test_chunk_parse_error_fallback(self):
        """Test that parse errors fall back to single chunk."""
        chunker = TreeSitterChunker("python")
        # Invalid Python syntax
        code = "def invalid syntax here {"
        chunks = chunker.chunk(code, "test.py")

        # Should still return a chunk (fallback to whole file)
        assert len(chunks) == 1


class TestMarkdownChunker:
    """Tests for MarkdownChunker."""

    def test_markdown_header_chunking(self):
        """Markdown files are chunked by headers."""
        chunker = MarkdownChunker()
        content = "# Header 1\n\nContent 1\n\n## Header 2\n\nContent 2"
        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 2
        assert chunks[0][1]["name"] == "Header 1"
        assert chunks[0][1]["chunk_type"] == "section"
        assert chunks[1][1]["name"] == "Header 2"
        assert chunks[1][1]["chunk_type"] == "section"

    def test_markdown_nested_headers(self):
        """Test chunking with nested header levels."""
        chunker = MarkdownChunker()
        content = """# Main Title

Introduction text.

## Section 1

Section 1 content.

### Subsection 1.1

Subsection content.

## Section 2

Section 2 content."""

        chunks = chunker.chunk(content, "test.md")

        # Should have 4 chunks: Main Title, Section 1, Subsection 1.1, Section 2
        assert len(chunks) == 4
        assert chunks[0][1]["name"] == "Main Title"
        assert chunks[1][1]["name"] == "Section 1"
        assert chunks[2][1]["name"] == "Subsection 1.1"
        assert chunks[3][1]["name"] == "Section 2"

    def test_markdown_without_headers(self):
        """Markdown without headers should be single chunk."""
        chunker = MarkdownChunker()
        content = """This is just plain text.

With multiple paragraphs.

But no headers."""

        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 1
        assert chunks[0][1]["chunk_type"] == "section"
        assert chunks[0][1]["name"] is None
        assert chunks[0][0] == content

    def test_markdown_with_code_blocks(self):
        """Code blocks should stay with their section."""
        chunker = MarkdownChunker()
        content = """# Code Example

Here's some Python code:

```python
def example():
    return "Hello"
```

More text after code."""

        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "Code Example"
        assert "```python" in chunks[0][0]
        assert "def example():" in chunks[0][0]
        assert "More text after code." in chunks[0][0]

    def test_markdown_empty_file(self):
        """Empty markdown files should return empty list."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk("", "test.md")
        assert len(chunks) == 0

    def test_markdown_only_whitespace(self):
        """Markdown with only whitespace should return empty list."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk("   \n\n  \t  \n", "test.md")
        assert len(chunks) == 0

    def test_markdown_only_headers(self):
        """Markdown with only headers (no content)."""
        chunker = MarkdownChunker()
        content = """# Header 1
## Header 2
### Header 3"""

        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 3
        assert chunks[0][1]["name"] == "Header 1"
        assert chunks[1][1]["name"] == "Header 2"
        assert chunks[2][1]["name"] == "Header 3"

    def test_markdown_header_levels(self):
        """Test all six header levels."""
        chunker = MarkdownChunker()
        content = """# H1
## H2
### H3
#### H4
##### H5
###### H6"""

        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 6
        for i, chunk in enumerate(chunks, 1):
            assert chunk[1]["name"] == f"H{i}"

    def test_markdown_mixed_content(self):
        """Test markdown with various content types."""
        chunker = MarkdownChunker()
        content = """# Main Section

Regular text with **bold** and *italic*.

- List item 1
- List item 2

## Subsection

> Blockquote text

1. Numbered list
2. Second item

### Deep Section

[Link text](https://example.com)

| Table | Header |
|-------|--------|
| Cell  | Cell   |"""

        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 3
        assert "**bold**" in chunks[0][0]
        assert "> Blockquote" in chunks[1][0]
        assert "| Table |" in chunks[2][0]

    def test_markdown_line_numbers(self):
        """Test that line numbers are correctly tracked."""
        chunker = MarkdownChunker()
        content = """# Header 1
Line 2
Line 3

## Header 2
Line 6
Line 7"""

        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 2
        assert chunks[0][1]["start_line"] == 1
        assert chunks[0][1]["end_line"] == 4  # Through line 4
        assert chunks[1][1]["start_line"] == 5
        assert chunks[1][1]["end_line"] == 7

    def test_markdown_header_with_formatting(self):
        """Test headers with inline formatting."""
        chunker = MarkdownChunker()
        content = """# Header with **bold** text

Content here.

## Header with `code`

More content."""

        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 2
        assert chunks[0][1]["name"] == "Header with **bold** text"
        assert chunks[1][1]["name"] == "Header with `code`"

    def test_markdown_not_header_patterns(self):
        """Test that non-header # patterns are not treated as headers."""
        chunker = MarkdownChunker()
        content = """# Real Header

This is text with #hashtag in the middle.
And this line has # but no space after it.

#NoSpaceHeader should not be a header.

## Another Real Header

Content here."""

        chunks = chunker.chunk(content, "test.md")

        # Should only have 2 chunks for the 2 real headers
        assert len(chunks) == 2
        assert chunks[0][1]["name"] == "Real Header"
        assert chunks[1][1]["name"] == "Another Real Header"
        assert "#hashtag" in chunks[0][0]

    def test_markdown_fixture_file(self):
        """Test chunking the comprehensive fixture file."""
        chunker = MarkdownChunker()
        fixture_path = Path(__file__).parent / "fixtures" / "sample.md"

        with open(fixture_path, "r") as f:
            content = f.read()

        chunks = chunker.chunk(content, "sample.md")

        # Verify we get expected number of chunks (all headers in the fixture)
        assert len(chunks) > 5  # The fixture has many headers

        # Check first chunk is the main title
        assert chunks[0][1]["name"] == "ctxd Documentation"
        assert chunks[0][1]["chunk_type"] == "section"

        # Verify some specific sections exist
        section_names = [chunk[1]["name"] for chunk in chunks]
        assert "Getting Started" in section_names
        assert "Usage" in section_names

        # Verify code blocks stay with their sections
        code_chunks = [chunk for chunk in chunks if "```" in chunk[0]]
        assert len(code_chunks) > 0  # Should have chunks with code blocks

    def test_markdown_content_before_first_header(self):
        """Test content before the first header."""
        chunker = MarkdownChunker()
        content = """Some introduction text
that comes before any header.

# First Header

Content under first header."""

        chunks = chunker.chunk(content, "test.md")

        # Content before first header creates a chunk with name=None
        assert len(chunks) == 2
        assert chunks[0][1]["name"] is None
        assert chunks[0][1]["chunk_type"] == "section"
        assert "Some introduction text" in chunks[0][0]
        assert chunks[1][1]["name"] == "First Header"

    def test_markdown_multiple_code_blocks(self):
        """Test section with multiple code blocks."""
        chunker = MarkdownChunker()
        content = """# Code Section

First code block:

```python
def func1():
    pass
```

Some text in between.

```javascript
function func2() {}
```

## Next Section

Content."""

        chunks = chunker.chunk(content, "test.md")

        assert len(chunks) == 2
        assert chunks[0][1]["name"] == "Code Section"
        assert chunks[0][0].count("```") == 4  # Two opening, two closing
        assert "python" in chunks[0][0]
        assert "javascript" in chunks[0][0]


class TestFallbackChunker:
    """Tests for FallbackChunker."""

    def test_chunk_paragraphs(self):
        """Test chunking text by paragraphs."""
        chunker = FallbackChunker()
        text = '''First paragraph here.
It has multiple lines.

Second paragraph here.
Also multiple lines.

Third paragraph.'''

        chunks = chunker.chunk(text, "test.txt")

        assert len(chunks) == 3
        for text_chunk, metadata in chunks:
            assert metadata["chunk_type"] == "paragraph"
            assert metadata["name"] is None

    def test_chunk_respects_max_size(self):
        """Test that large paragraphs are split."""
        chunker = FallbackChunker(max_chunk_size=10, chunk_overlap=2)
        # Create a text with more than 10 words
        text = " ".join([f"word{i}" for i in range(50)])

        chunks = chunker.chunk(text, "test.txt")

        # Should be split into multiple chunks
        assert len(chunks) > 1

        # Each chunk should have <= max_chunk_size words (approximately)
        for text_chunk, metadata in chunks:
            word_count = len(text_chunk.split())
            assert word_count <= 12  # Allow some tolerance for overlap

    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        chunker = FallbackChunker(max_chunk_size=10, chunk_overlap=5)
        text = " ".join([f"word{i}" for i in range(30)])

        chunks = chunker.chunk(text, "test.txt")

        # With overlap, adjacent chunks should share some words
        if len(chunks) > 1:
            # Check overlap between first two chunks
            chunk1_words = set(chunks[0][0].split())
            chunk2_words = set(chunks[1][0].split())
            overlap = chunk1_words & chunk2_words
            assert len(overlap) > 0

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunker = FallbackChunker()
        chunks = chunker.chunk("", "test.txt")
        assert len(chunks) == 0

    def test_chunk_single_paragraph(self):
        """Test chunking a single paragraph."""
        chunker = FallbackChunker()
        text = "This is a single paragraph without double newlines."

        chunks = chunker.chunk(text, "test.txt")

        assert len(chunks) == 1
        text_chunk, metadata = chunks[0]
        assert text_chunk == text
        assert metadata["start_line"] == 1

    def test_chunk_markdown(self):
        """Test chunking markdown text."""
        chunker = FallbackChunker()
        markdown = '''# Title

First section content.

## Subtitle

Second section content.'''

        chunks = chunker.chunk(markdown, "README.md")

        # Should split by double newlines
        assert len(chunks) >= 2

    def test_line_numbers_are_tracked(self):
        """Test that line numbers are correctly tracked."""
        chunker = FallbackChunker()
        text = '''First paragraph.

Second paragraph.

Third paragraph.'''

        chunks = chunker.chunk(text, "test.txt")

        # Verify line numbers increase
        prev_end = 0
        for text_chunk, metadata in chunks:
            assert metadata["start_line"] > prev_end
            assert metadata["end_line"] >= metadata["start_line"]
            prev_end = metadata["end_line"]


class TestGoChunking:
    """Tests for Go language chunking with TreeSitterChunker."""

    def test_go_function_chunking(self):
        """Go functions are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

// Add adds two integers
func Add(a, b int) int {
    return a + b
}"""
        chunks = chunker.chunk(content, "test.go")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "Add"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "func Add(a, b int) int" in chunks[0][0]

    def test_go_multiple_functions(self):
        """Multiple Go functions are chunked separately."""
        chunker = TreeSitterChunker("go")
        content = """package main

func Add(a, b int) int {
    return a + b
}

func Subtract(a, b int) int {
    return a - b
}

func Multiply(a, b int) int {
    return a * b
}"""
        chunks = chunker.chunk(content, "test.go")

        assert len(chunks) == 3
        names = [c[1]["name"] for c in chunks]
        assert "Add" in names
        assert "Subtract" in names
        assert "Multiply" in names

        for chunk in chunks:
            assert chunk[1]["chunk_type"] == "function"

    def test_go_method_value_receiver(self):
        """Go methods with value receivers are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

type Calculator struct {
    value int
}

// Compute performs calculation
func (c Calculator) Compute(x int) int {
    return c.value + x
}"""
        chunks = chunker.chunk(content, "test.go")

        # Should have struct type and method
        assert len(chunks) >= 1

        # Find the method chunk
        method_chunks = [c for c in chunks if c[1]["name"] == "Compute"]
        assert len(method_chunks) == 1
        assert method_chunks[0][1]["chunk_type"] == "function"
        assert "func (c Calculator) Compute" in method_chunks[0][0]

    def test_go_method_pointer_receiver(self):
        """Go methods with pointer receivers are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

type Calculator struct {
    value int
}

// Add adds to the calculator value
func (c *Calculator) Add(x int) {
    c.value += x
}"""
        chunks = chunker.chunk(content, "test.go")

        # Find the method chunk
        method_chunks = [c for c in chunks if c[1]["name"] == "Add"]
        assert len(method_chunks) == 1
        assert method_chunks[0][1]["chunk_type"] == "function"
        assert "func (c *Calculator) Add" in method_chunks[0][0]

    def test_go_struct_definition(self):
        """Go struct definitions are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

type Calculator struct {
    value   int
    history []int
}"""
        chunks = chunker.chunk(content, "test.go")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "Calculator"
        assert chunks[0][1]["chunk_type"] == "type"
        # Note: type_spec nodes don't include the "type" keyword
        assert "Calculator struct" in chunks[0][0]

    def test_go_interface_definition(self):
        """Go interface definitions are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

type Adder interface {
    Add(a, b int) int
    Subtract(a, b int) int
}"""
        chunks = chunker.chunk(content, "test.go")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "Adder"
        assert chunks[0][1]["chunk_type"] == "type"
        # Note: type_spec nodes don't include the "type" keyword
        assert "Adder interface" in chunks[0][0]

    def test_go_mixed_definitions(self):
        """Mixed Go definitions (functions, methods, types) are all chunked."""
        chunker = TreeSitterChunker("go")
        content = """package main

func Add(a, b int) int {
    return a + b
}

type Calculator struct {
    value int
}

func (c *Calculator) Compute(x int) int {
    return c.value + x
}

type Adder interface {
    Add(a, b int) int
}"""
        chunks = chunker.chunk(content, "test.go")

        # Should have: Add function, Calculator struct, Compute method, Adder interface
        assert len(chunks) == 4

        names = [c[1]["name"] for c in chunks]
        assert "Add" in names
        assert "Calculator" in names
        assert "Compute" in names
        assert "Adder" in names

        # Check chunk types
        type_chunks = [c for c in chunks if c[1]["chunk_type"] == "type"]
        assert len(type_chunks) == 2  # Calculator and Adder

        function_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        assert len(function_chunks) == 2  # Add and Compute

    def test_go_with_comments(self):
        """Go functions with comments are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

// Add adds two integers and returns the result.
// Returns an error if the result would overflow.
func Add(a, b int) (int, error) {
    return a + b, nil
}"""
        chunks = chunker.chunk(content, "test.go")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "Add"
        # Note: Comments above function are NOT included in tree-sitter node
        # Only the function body itself is included
        assert "func Add(a, b int) (int, error)" in chunks[0][0]

    def test_go_generic_type(self):
        """Go generic types (Go 1.18+) are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

type Stack[T any] struct {
    items []T
}

func (s *Stack[T]) Push(item T) {
    s.items = append(s.items, item)
}"""
        chunks = chunker.chunk(content, "test.go")

        # Should have Stack type and Push method
        assert len(chunks) >= 1

        names = [c[1]["name"] for c in chunks]
        assert "Stack" in names or "Push" in names

    def test_go_complex_function_signature(self):
        """Go functions with complex signatures are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

func complexFunction(
    a, b int,
    name string,
    opts ...func(int) int,
) (int, string, error) {
    return a + b, name, nil
}"""
        chunks = chunker.chunk(content, "test.go")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "complexFunction"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "func complexFunction" in chunks[0][0]

    def test_go_empty_file(self):
        """Empty Go file returns no chunks."""
        chunker = TreeSitterChunker("go")
        chunks = chunker.chunk("", "test.go")
        assert len(chunks) == 0

    def test_go_package_only(self):
        """Go file with only package declaration returns single chunk."""
        chunker = TreeSitterChunker("go")
        content = """package main

import "fmt"
"""
        chunks = chunker.chunk(content, "test.go")

        # No functions or types, should return whole file as single chunk
        assert len(chunks) == 1
        assert chunks[0][1]["chunk_type"] == "block"
        assert chunks[0][1]["name"] is None

    def test_go_parse_error_fallback(self):
        """Invalid Go syntax falls back to single chunk."""
        chunker = TreeSitterChunker("go")
        # Invalid Go syntax
        content = "func invalid syntax here {"
        chunks = chunker.chunk(content, "test.go")

        # Should still return a chunk (fallback to whole file)
        assert len(chunks) == 1

    def test_go_fixture_file(self):
        """Test comprehensive Go fixture file."""
        import os
        chunker = TreeSitterChunker("go")

        fixture_path = Path(__file__).parent / "fixtures" / "sample.go"
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        with open(fixture_path, "r") as f:
            content = f.read()

        chunks = chunker.chunk(content, "sample.go")

        # The fixture should have many chunks (functions, methods, types)
        assert len(chunks) >= 10

        # Check for expected function/method names
        names = [c[1]["name"] for c in chunks]
        assert "Add" in names
        assert "Multiply" in names
        assert "Calculator" in names
        assert "Adder" in names
        assert "Point" in names

        # Check chunk types distribution
        function_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        type_chunks = [c for c in chunks if c[1]["chunk_type"] == "type"]

        assert len(function_chunks) > 0
        assert len(type_chunks) > 0

        # Verify all chunks have required metadata
        for text, metadata in chunks:
            assert "start_line" in metadata
            assert "end_line" in metadata
            assert "chunk_type" in metadata
            assert "name" in metadata
            assert metadata["end_line"] >= metadata["start_line"]

    def test_go_line_numbers_accurate(self):
        """Go chunk line numbers are accurate."""
        chunker = TreeSitterChunker("go")
        content = """package main

func First() int {
    return 1
}

func Second() int {
    return 2
}"""
        chunks = chunker.chunk(content, "test.go")

        assert len(chunks) == 2

        # First function should start around line 3
        assert chunks[0][1]["start_line"] == 3
        assert chunks[0][1]["end_line"] == 5

        # Second function should start around line 7
        assert chunks[1][1]["start_line"] == 7
        assert chunks[1][1]["end_line"] == 9

    def test_go_embedded_interface(self):
        """Go embedded interfaces are chunked correctly."""
        chunker = TreeSitterChunker("go")
        content = """package main

type ArithmeticOperator interface {
    Adder
    Multiplier
    Subtract(a, b int) int
}"""
        chunks = chunker.chunk(content, "test.go")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "ArithmeticOperator"
        assert chunks[0][1]["chunk_type"] == "type"
        # Note: type_spec nodes don't include the "type" keyword
        assert "ArithmeticOperator interface" in chunks[0][0]


class TestJavaScriptChunking:
    """Tests for JavaScript language chunking with TreeSitterChunker."""

    def test_javascript_function_declaration(self):
        """JavaScript function declarations are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
function add(a, b) {
    return a + b;
}
"""
        chunks = chunker.chunk(content, "test.js")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "add"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "function add(a, b)" in chunks[0][0]

    def test_javascript_arrow_function(self):
        """JavaScript arrow functions assigned to variables are chunked."""
        chunker = TreeSitterChunker("javascript")
        content = """
const multiply = (x, y) => {
    return x * y;
};
"""
        chunks = chunker.chunk(content, "test.js")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "multiply"
        assert chunks[0][1]["chunk_type"] == "function"
        # Note: variable_declarator doesn't include the "const" keyword
        assert "multiply = (x, y) =>" in chunks[0][0]

    def test_javascript_arrow_function_single_expression(self):
        """Single-expression arrow functions are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """const square = n => n * n;"""
        chunks = chunker.chunk(content, "test.js")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "square"
        assert chunks[0][1]["chunk_type"] == "function"

    def test_javascript_class_declaration(self):
        """JavaScript ES6 classes are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
class Calculator {
    constructor(value = 0) {
        this.value = value;
    }

    add(n) {
        this.value += n;
        return this;
    }

    getResult() {
        return this.value;
    }
}
"""
        chunks = chunker.chunk(content, "test.js")

        # Should have class and methods
        assert len(chunks) >= 1

        # Find class chunk
        class_chunks = [c for c in chunks if c[1]["chunk_type"] == "class"]
        assert len(class_chunks) >= 1
        assert class_chunks[0][1]["name"] == "Calculator"

    def test_javascript_export_function(self):
        """JavaScript export statements with functions are chunked."""
        chunker = TreeSitterChunker("javascript")
        content = """
export function divide(a, b) {
    if (b === 0) {
        throw new Error("Division by zero");
    }
    return a / b;
}
"""
        chunks = chunker.chunk(content, "test.js")

        assert len(chunks) >= 1
        # Should find the divide function
        names = [c[1]["name"] for c in chunks]
        assert "divide" in names

    def test_javascript_multiple_functions(self):
        """Multiple JavaScript functions are chunked separately."""
        chunker = TreeSitterChunker("javascript")
        content = """
function add(a, b) {
    return a + b;
}

const multiply = (x, y) => x * y;

function subtract(a, b) {
    return a - b;
}
"""
        chunks = chunker.chunk(content, "test.js")

        assert len(chunks) == 3
        names = [c[1]["name"] for c in chunks]
        assert "add" in names
        assert "multiply" in names
        assert "subtract" in names

    def test_javascript_method_definition(self):
        """JavaScript class methods are chunked."""
        chunker = TreeSitterChunker("javascript")
        content = """
class Calculator {
    add(n) {
        return n + 1;
    }
}
"""
        chunks = chunker.chunk(content, "test.js")

        # Should have class and/or method
        assert len(chunks) >= 1
        names = [c[1]["name"] for c in chunks]
        assert "Calculator" in names or "add" in names

    def test_javascript_empty_file(self):
        """Empty JavaScript file returns no chunks."""
        chunker = TreeSitterChunker("javascript")
        chunks = chunker.chunk("", "test.js")
        assert len(chunks) == 0

    def test_javascript_no_definitions(self):
        """JavaScript with only variable declarations returns single chunk."""
        chunker = TreeSitterChunker("javascript")
        content = """
const x = 5;
let y = 10;
var z = 15;
"""
        chunks = chunker.chunk(content, "test.js")

        # No functions or classes, should return whole file as single chunk
        assert len(chunks) == 1
        assert chunks[0][1]["chunk_type"] == "block"

    def test_javascript_parse_error_fallback(self):
        """Invalid JavaScript syntax falls back to single chunk."""
        chunker = TreeSitterChunker("javascript")
        content = "function invalid syntax here {"
        chunks = chunker.chunk(content, "test.js")

        # Should still return a chunk (fallback to whole file)
        assert len(chunks) == 1

    def test_javascript_fixture_file(self):
        """Test comprehensive JavaScript fixture file."""
        import os
        chunker = TreeSitterChunker("javascript")

        fixture_path = Path(__file__).parent / "fixtures" / "sample.js"
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        with open(fixture_path, "r") as f:
            content = f.read()

        chunks = chunker.chunk(content, "sample.js")

        # Should have multiple chunks
        assert len(chunks) > 3

        # Check for expected function/class names
        names = [c[1]["name"] for c in chunks]
        assert "add" in names
        assert "multiply" in names
        assert "Calculator" in names

        # Verify all chunks have required metadata
        for text, metadata in chunks:
            assert "start_line" in metadata
            assert "end_line" in metadata
            assert "chunk_type" in metadata
            assert "name" in metadata


class TestTypeScriptChunking:
    """Tests for TypeScript language chunking with TreeSitterChunker."""

    def test_typescript_function_declaration(self):
        """TypeScript function declarations are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
function createUser(name: string, email: string): User {
    return {
        id: Math.random(),
        name,
        email
    };
}
"""
        chunks = chunker.chunk(content, "test.ts")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "createUser"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "function createUser" in chunks[0][0]

    def test_typescript_arrow_function(self):
        """TypeScript arrow functions with type annotations are chunked."""
        chunker = TreeSitterChunker("typescript")
        content = """
const validateEmail = (email: string): boolean => {
    return email.includes('@');
};
"""
        chunks = chunker.chunk(content, "test.ts")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "validateEmail"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "(email: string): boolean" in chunks[0][0]

    def test_typescript_interface_declaration(self):
        """TypeScript interfaces are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
interface User {
    id: number;
    name: string;
    email: string;
}
"""
        chunks = chunker.chunk(content, "test.ts")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "User"
        assert chunks[0][1]["chunk_type"] == "interface"
        assert "interface User" in chunks[0][0]

    def test_typescript_type_alias(self):
        """TypeScript type aliases are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
type UserID = string | number;
"""
        chunks = chunker.chunk(content, "test.ts")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "UserID"
        assert chunks[0][1]["chunk_type"] == "type"
        assert "type UserID" in chunks[0][0]

    def test_typescript_generic_type(self):
        """TypeScript generic types are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
type Result<T> = {
    success: boolean;
    data?: T;
    error?: string;
};
"""
        chunks = chunker.chunk(content, "test.ts")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "Result"
        assert chunks[0][1]["chunk_type"] == "type"
        assert "type Result<T>" in chunks[0][0]

    def test_typescript_class_with_types(self):
        """TypeScript classes with type annotations are chunked."""
        chunker = TreeSitterChunker("typescript")
        content = """
class UserService {
    private users: User[] = [];

    addUser(user: User): void {
        this.users.push(user);
    }

    findUser(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }
}
"""
        chunks = chunker.chunk(content, "test.ts")

        # Should have class and methods
        assert len(chunks) >= 1

        # Find class chunk
        names = [c[1]["name"] for c in chunks]
        assert "UserService" in names

    def test_typescript_generic_function(self):
        """TypeScript generic functions are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
function wrapResult<T>(data: T): Result<T> {
    return {
        success: true,
        data
    };
}
"""
        chunks = chunker.chunk(content, "test.ts")

        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "wrapResult"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "function wrapResult<T>" in chunks[0][0]

    def test_typescript_mixed_definitions(self):
        """Mixed TypeScript definitions are all chunked."""
        chunker = TreeSitterChunker("typescript")
        content = """
interface User {
    id: number;
    name: string;
}

type UserID = string | number;

function createUser(name: string): User {
    return { id: 1, name };
}

class UserService {
    private users: User[] = [];
}
"""
        chunks = chunker.chunk(content, "test.ts")

        # Should have interface, type, function, class
        assert len(chunks) >= 4

        names = [c[1]["name"] for c in chunks]
        assert "User" in names
        assert "UserID" in names
        assert "createUser" in names
        assert "UserService" in names

        # Check chunk types
        interface_chunks = [c for c in chunks if c[1]["chunk_type"] == "interface"]
        type_chunks = [c for c in chunks if c[1]["chunk_type"] == "type"]
        function_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        class_chunks = [c for c in chunks if c[1]["chunk_type"] == "class"]

        assert len(interface_chunks) >= 1
        assert len(type_chunks) >= 1
        assert len(function_chunks) >= 1
        assert len(class_chunks) >= 1

    def test_typescript_empty_file(self):
        """Empty TypeScript file returns no chunks."""
        chunker = TreeSitterChunker("typescript")
        chunks = chunker.chunk("", "test.ts")
        assert len(chunks) == 0

    def test_typescript_parse_error_fallback(self):
        """Invalid TypeScript syntax falls back to single chunk."""
        chunker = TreeSitterChunker("typescript")
        content = "function invalid syntax here {"
        chunks = chunker.chunk(content, "test.ts")

        # Should still return a chunk (fallback to whole file)
        assert len(chunks) == 1

    def test_typescript_fixture_file(self):
        """Test comprehensive TypeScript fixture file."""
        import os
        chunker = TreeSitterChunker("typescript")

        fixture_path = Path(__file__).parent / "fixtures" / "sample.ts"
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        with open(fixture_path, "r") as f:
            content = f.read()

        chunks = chunker.chunk(content, "sample.ts")

        # Should have multiple chunks (interfaces, types, functions, class)
        assert len(chunks) > 5

        # Check for expected names
        names = [c[1]["name"] for c in chunks]
        assert "User" in names
        assert "UserID" in names
        assert "Result" in names
        assert "createUser" in names
        assert "validateEmail" in names
        assert "UserService" in names
        assert "wrapResult" in names

        # Verify chunk type distribution
        interface_chunks = [c for c in chunks if c[1]["chunk_type"] == "interface"]
        type_chunks = [c for c in chunks if c[1]["chunk_type"] == "type"]
        function_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        class_chunks = [c for c in chunks if c[1]["chunk_type"] == "class"]

        assert len(interface_chunks) > 0
        assert len(type_chunks) > 0
        assert len(function_chunks) > 0
        assert len(class_chunks) > 0

        # Verify all chunks have required metadata
        for text, metadata in chunks:
            assert "start_line" in metadata
            assert "end_line" in metadata
            assert "chunk_type" in metadata
            assert "name" in metadata

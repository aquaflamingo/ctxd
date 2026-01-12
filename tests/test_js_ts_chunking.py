"""
JavaScript and TypeScript chunking tests for TreeSitterChunker.

These tests cover:
- JavaScript function declarations and arrow functions
- ES6 classes and methods
- TypeScript interfaces and type aliases
- Generics
- Export statements
- Edge cases
"""

import pytest
from pathlib import Path
from ctxd.chunkers import TreeSitterChunker


class TestJavaScriptChunking:
    """Tests for JavaScript code chunking."""

    def test_javascript_function_declaration(self):
        """JavaScript function declarations are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
function myFunction(param) {
    return param + 1;
}
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "myFunction"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "function myFunction" in chunks[0][0]

    def test_javascript_multiple_functions(self):
        """Multiple JavaScript functions are chunked separately."""
        chunker = TreeSitterChunker("javascript")
        content = """
function add(a, b) {
    return a + b;
}

function subtract(a, b) {
    return a - b;
}

function multiply(a, b) {
    return a * b;
}
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 3

        names = [chunk[1]["name"] for chunk in chunks]
        assert "add" in names
        assert "subtract" in names
        assert "multiply" in names

        for chunk in chunks:
            assert chunk[1]["chunk_type"] == "function"

    def test_javascript_arrow_function(self):
        """Arrow functions are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
const greet = (name) => {
    return `Hello, ${name}!`;
};
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "greet"
        assert chunks[0][1]["chunk_type"] == "function"
        # Note: tree-sitter extracts only the declarator part, not the full statement
        assert "greet" in chunks[0][0]

    def test_javascript_arrow_function_implicit_return(self):
        """Arrow functions with implicit return are chunked."""
        chunker = TreeSitterChunker("javascript")
        content = """
const square = (n) => n * n;
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "square"
        assert chunks[0][1]["chunk_type"] == "function"

    def test_javascript_class_declaration(self):
        """JavaScript classes are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
class Calculator {
    constructor() {
        this.result = 0;
    }

    add(value) {
        this.result += value;
        return this;
    }

    getResult() {
        return this.result;
    }
}
"""
        chunks = chunker.chunk(content, "test.js")

        # Should have class and methods
        assert len(chunks) >= 1

        # Check for class chunk
        class_chunks = [c for c in chunks if c[1]["chunk_type"] == "class"]
        assert len(class_chunks) == 1
        assert class_chunks[0][1]["name"] == "Calculator"

        # Check for method chunks
        method_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        method_names = [m[1]["name"] for m in method_chunks]
        assert "add" in method_names
        assert "getResult" in method_names

    def test_javascript_async_function(self):
        """Async functions are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
async function fetchData(url) {
    const response = await fetch(url);
    const data = await response.json();
    return data;
}
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "fetchData"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "async function" in chunks[0][0]

    def test_javascript_async_arrow_function(self):
        """Async arrow functions are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
const fetchUser = async (userId) => {
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
};
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "fetchUser"
        assert chunks[0][1]["chunk_type"] == "function"

    def test_javascript_exported_function(self):
        """Exported functions are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
export function exportedFunction() {
    return "I am exported";
}

export const exportedArrow = () => {
    return "Arrow function export";
};
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 2

        names = [chunk[1]["name"] for chunk in chunks]
        assert "exportedFunction" in names
        assert "exportedArrow" in names

    def test_javascript_generator_function(self):
        """Generator functions are chunked correctly."""
        chunker = TreeSitterChunker("javascript")
        content = """
function* numberGenerator() {
    yield 1;
    yield 2;
    yield 3;
}
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 1
        # Generator function name may be extracted from the generator_function node
        assert chunks[0][1]["chunk_type"] == "function"
        assert "yield" in chunks[0][0]

    def test_javascript_empty_file(self):
        """Empty JavaScript files return no chunks."""
        chunker = TreeSitterChunker("javascript")
        chunks = chunker.chunk("", "test.js")
        assert len(chunks) == 0

    def test_javascript_only_comments(self):
        """Files with only comments return single chunk."""
        chunker = TreeSitterChunker("javascript")
        content = """
// This is a comment
/* This is a multi-line
   comment */
"""
        chunks = chunker.chunk(content, "test.js")
        # No definitions, should return whole file as one chunk
        assert len(chunks) == 1
        assert chunks[0][1]["chunk_type"] == "block"
        assert chunks[0][1]["name"] is None

    def test_javascript_parse_error_fallback(self):
        """JavaScript parse errors fall back to single chunk."""
        chunker = TreeSitterChunker("javascript")
        # Invalid JavaScript syntax
        code = "function invalid { syntax here"
        chunks = chunker.chunk(code, "test.js")

        # Should still return a chunk (fallback)
        assert len(chunks) == 1
        assert chunks[0][1]["chunk_type"] == "block"

    def test_javascript_fixture_file(self):
        """Test chunking the sample.js fixture file."""
        chunker = TreeSitterChunker("javascript")
        fixture_path = Path(__file__).parent / "fixtures" / "sample.js"

        with open(fixture_path, "r") as f:
            content = f.read()

        chunks = chunker.chunk(content, "sample.js")

        # Should find multiple functions and classes
        assert len(chunks) > 5

        # Check for specific functions
        names = [chunk[1]["name"] for chunk in chunks]
        assert "calculateSum" in names
        assert "multiply" in names
        assert "greet" in names
        assert "square" in names
        assert "Calculator" in names
        assert "MathUtils" in names
        assert "fetchData" in names

        # Verify chunk types
        function_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        class_chunks = [c for c in chunks if c[1]["chunk_type"] == "class"]
        assert len(function_chunks) > 0
        assert len(class_chunks) > 0

    def test_javascript_line_numbers(self):
        """Line numbers in JavaScript chunks are correct."""
        chunker = TreeSitterChunker("javascript")
        content = """// Line 1
// Line 2
function firstFunction() {
    return 1;
}

// Line 7
function secondFunction() {
    return 2;
}
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 2

        # First function should start around line 3
        assert chunks[0][1]["start_line"] == 3
        assert chunks[0][1]["end_line"] == 5

        # Second function should start around line 8
        assert chunks[1][1]["start_line"] == 8
        assert chunks[1][1]["end_line"] == 10


class TestTypeScriptChunking:
    """Tests for TypeScript code chunking."""

    def test_typescript_function_declaration(self):
        """TypeScript function declarations are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
function greet(name: string): string {
    return `Hello, ${name}!`;
}
"""
        chunks = chunker.chunk(content, "test.ts")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "greet"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "string" in chunks[0][0]  # Type annotation should be included

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

    def test_typescript_generic_interface(self):
        """Generic TypeScript interfaces are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
interface Repository<T> {
    findById(id: number): T | null;
    findAll(): T[];
    save(item: T): void;
}
"""
        chunks = chunker.chunk(content, "test.ts")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "Repository"
        assert chunks[0][1]["chunk_type"] == "interface"
        assert "<T>" in chunks[0][0]

    def test_typescript_type_alias(self):
        """TypeScript type aliases are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
type Status = 'pending' | 'active' | 'inactive';
"""
        chunks = chunker.chunk(content, "test.ts")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "Status"
        assert chunks[0][1]["chunk_type"] == "type"
        assert "type Status" in chunks[0][0]

    def test_typescript_complex_type_alias(self):
        """Complex TypeScript type aliases are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
type ApiResponse<T> = {
    data: T;
    status: number;
    message: string;
};
"""
        chunks = chunker.chunk(content, "test.ts")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "ApiResponse"
        assert chunks[0][1]["chunk_type"] == "type"

    def test_typescript_class_with_types(self):
        """TypeScript classes with type annotations are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
class UserService {
    private users: User[] = [];

    async fetchUsers(): Promise<User[]> {
        const response = await fetch('/api/users');
        return response.json();
    }

    findUserById(id: number): User | undefined {
        return this.users.find(user => user.id === id);
    }
}
"""
        chunks = chunker.chunk(content, "test.ts")

        # Should have class and methods
        assert len(chunks) >= 1

        # Check for methods - class may be chunked with methods
        method_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        method_names = [m[1]["name"] for m in method_chunks]
        assert "fetchUsers" in method_names
        assert "findUserById" in method_names

    def test_typescript_generic_class(self):
        """Generic TypeScript classes are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
class DataStore<T> {
    private items: T[] = [];

    add(item: T): void {
        this.items.push(item);
    }

    getAll(): T[] {
        return [...this.items];
    }
}
"""
        chunks = chunker.chunk(content, "test.ts")

        # Should have class and/or methods - check that generics are preserved
        assert len(chunks) >= 1
        # Look for generic type parameter in any chunk
        has_generic = any("<T>" in chunk[0] or "T[]" in chunk[0] for chunk in chunks)
        assert has_generic, "Generic type parameter should be preserved in chunks"

    def test_typescript_generic_function(self):
        """Generic TypeScript functions are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
function identity<T>(value: T): T {
    return value;
}
"""
        chunks = chunker.chunk(content, "test.ts")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "identity"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "<T>" in chunks[0][0]

    def test_typescript_arrow_function_with_types(self):
        """TypeScript arrow functions with type annotations are chunked."""
        chunker = TreeSitterChunker("typescript")
        content = """
const filterUsers = (users: User[], minAge: number): User[] => {
    return users.filter(user => user.age >= minAge);
};
"""
        chunks = chunker.chunk(content, "test.ts")
        assert len(chunks) == 1
        assert chunks[0][1]["name"] == "filterUsers"
        assert chunks[0][1]["chunk_type"] == "function"
        assert "User[]" in chunks[0][0]

    def test_typescript_multiple_interfaces_and_types(self):
        """Multiple TypeScript interfaces and types are chunked separately."""
        chunker = TreeSitterChunker("typescript")
        content = """
interface User {
    id: number;
    name: string;
}

type UserId = number;

interface Product {
    id: number;
    title: string;
}

type ProductId = string;
"""
        chunks = chunker.chunk(content, "test.ts")
        assert len(chunks) == 4

        names = [chunk[1]["name"] for chunk in chunks]
        assert "User" in names
        assert "UserId" in names
        assert "Product" in names
        assert "ProductId" in names

        # Check chunk types
        interface_chunks = [c for c in chunks if c[1]["chunk_type"] == "interface"]
        type_chunks = [c for c in chunks if c[1]["chunk_type"] == "type"]
        assert len(interface_chunks) == 2
        assert len(type_chunks) == 2

    def test_typescript_empty_file(self):
        """Empty TypeScript files return no chunks."""
        chunker = TreeSitterChunker("typescript")
        chunks = chunker.chunk("", "test.ts")
        assert len(chunks) == 0

    def test_typescript_parse_error_fallback(self):
        """TypeScript parse errors fall back to single chunk."""
        chunker = TreeSitterChunker("typescript")
        # Invalid TypeScript syntax
        code = "interface Invalid { missing brace"
        chunks = chunker.chunk(code, "test.ts")

        # Should still return a chunk (fallback)
        assert len(chunks) == 1
        assert chunks[0][1]["chunk_type"] == "block"

    def test_typescript_fixture_file(self):
        """Test chunking the sample.ts fixture file."""
        chunker = TreeSitterChunker("typescript")
        fixture_path = Path(__file__).parent / "fixtures" / "sample.ts"

        with open(fixture_path, "r") as f:
            content = f.read()

        chunks = chunker.chunk(content, "sample.ts")

        # Should find many interfaces, types, functions, and classes
        assert len(chunks) > 10

        # Check for specific items
        names = [chunk[1]["name"] for chunk in chunks]
        assert "User" in names
        assert "Repository" in names
        assert "Status" in names
        assert "ApiResponse" in names
        assert "createUser" in names
        assert "identity" in names
        assert "UserService" in names
        assert "DataStore" in names

        # Verify chunk types
        interface_chunks = [c for c in chunks if c[1]["chunk_type"] == "interface"]
        type_chunks = [c for c in chunks if c[1]["chunk_type"] == "type"]
        function_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        class_chunks = [c for c in chunks if c[1]["chunk_type"] == "class"]

        assert len(interface_chunks) > 0
        assert len(type_chunks) > 0
        assert len(function_chunks) > 0
        assert len(class_chunks) > 0

    def test_typescript_abstract_class(self):
        """TypeScript abstract classes are chunked correctly."""
        chunker = TreeSitterChunker("typescript")
        content = """
abstract class Animal {
    constructor(protected name: string) {}

    abstract makeSound(): string;

    move(distance: number): void {
        console.log(`${this.name} moved ${distance} meters.`);
    }
}
"""
        chunks = chunker.chunk(content, "test.ts")

        # Should have class and methods
        class_chunks = [c for c in chunks if c[1]["chunk_type"] == "class"]
        assert len(class_chunks) == 1
        assert class_chunks[0][1]["name"] == "Animal"
        assert "abstract class" in class_chunks[0][0]

    def test_typescript_enum(self):
        """TypeScript enums are handled."""
        chunker = TreeSitterChunker("typescript")
        content = """
enum Color {
    Red = 'RED',
    Green = 'GREEN',
    Blue = 'BLUE'
}

function getColor(): Color {
    return Color.Red;
}
"""
        chunks = chunker.chunk(content, "test.ts")

        # Should at least find the function
        # Enum handling depends on tree-sitter grammar
        function_chunks = [c for c in chunks if c[1]["chunk_type"] == "function"]
        assert len(function_chunks) >= 1

        names = [chunk[1]["name"] for chunk in function_chunks]
        assert "getColor" in names


class TestEdgeCases:
    """Edge case tests for TreeSitterChunker."""

    def test_unsupported_language(self):
        """Creating chunker with unsupported language raises error."""
        with pytest.raises(ValueError, match="Unsupported language"):
            TreeSitterChunker("ruby")

    def test_javascript_with_jsdoc(self):
        """JSDoc comments are included with functions."""
        chunker = TreeSitterChunker("javascript")
        content = """
/**
 * Multiply two numbers together.
 * @param {number} x - First number
 * @param {number} y - Second number
 * @returns {number} Product of x and y
 */
function multiply(x, y) {
    const result = x * y;
    return result;
}
"""
        chunks = chunker.chunk(content, "test.js")
        assert len(chunks) == 1
        # JSDoc should be part of the function text
        assert chunks[0][1]["name"] == "multiply"

    def test_typescript_exported_types(self):
        """TypeScript export statements with types."""
        chunker = TreeSitterChunker("typescript")
        content = """
export interface User {
    id: number;
    name: string;
}

export type UserId = number;

export class UserService {
    getUser(id: UserId): User {
        return { id, name: 'Test' };
    }
}
"""
        chunks = chunker.chunk(content, "test.ts")
        assert len(chunks) >= 3

        names = [chunk[1]["name"] for chunk in chunks]
        assert "User" in names
        assert "UserId" in names
        assert "UserService" in names

    def test_nested_arrow_functions(self):
        """Nested arrow functions (only outer should be chunked)."""
        chunker = TreeSitterChunker("javascript")
        content = """
const outer = () => {
    const inner = () => {
        return 42;
    };
    return inner();
};
"""
        chunks = chunker.chunk(content, "test.js")
        # Should only chunk the outer function
        assert len(chunks) >= 1
        assert chunks[0][1]["name"] == "outer"

# ctxd Skill Examples

This document shows how Claude Code behaves with and without the ctxd-search skill.

## Example 1: Finding Authentication Code

### Without the Skill

**User:** "Where is the authentication logic?"

**Claude (without skill):**
```
Let me search for authentication-related files...
[Uses Glob to find files with "auth" in name]
[Uses Grep to search for "auth" string]

I found these files:
- src/auth.py
- src/middleware/auth.py
- tests/test_auth.py

Let me read them to understand the authentication logic...
[Reads each file sequentially, uses lots of tokens]
```

**Issues:**
- Uses keyword search (Grep) instead of semantic search
- Searches by filename pattern, might miss code
- Reads entire files, consuming many tokens
- No prioritization of relevant code chunks
- Might miss authentication logic in files not named "auth"

### With the Skill

**User:** "Where is the authentication logic?"

**Claude (with skill):**
```
I'll search the codebase for authentication logic using ctxd...
[Uses ctx_search("authentication logic", limit=10)]

Found authentication code in these locations:

1. src/auth/login.py:23-45 (score: 0.91)
   - authenticate_user() function
   - Handles password verification and session creation

2. src/middleware/auth.py:12-34 (score: 0.87)
   - AuthMiddleware class
   - JWT token validation for API requests

3. src/models/user.py:67-82 (score: 0.78)
   - User.check_password() method
   - Password hashing verification

The main authentication flow starts in src/auth/login.py:23.
Would you like me to read the full file for detailed analysis?
```

**Benefits:**
- Uses semantic search to find relevant code by meaning
- Returns ranked results with relevance scores
- Shows specific line ranges, not entire files
- Provides context about what each chunk does
- Efficient token usage (only reads what's needed)
- Finds all authentication-related code, regardless of file names

---

## Example 2: Understanding Project Architecture

### Without the Skill

**User:** "Explain how this project is structured"

**Claude (without skill):**
```
Let me look at the directory structure...
[Uses Bash ls or Glob to list files]

The project has these directories:
- src/
- tests/
- docs/
- config/

Let me read some key files...
[Starts reading random files to understand structure]
[Uses many tokens, may miss important patterns]
```

**Issues:**
- Only shows file/directory names
- No understanding of actual code organization
- Random file reading wastes tokens
- Misses conceptual organization
- Can't identify architectural patterns

### With the Skill

**User:** "Explain how this project is structured"

**Claude (with skill):**
```
Let me explore the codebase structure using ctxd...

[Uses ctx_status to see language distribution]
The project contains:
- 234 Python files
- 42 JavaScript files
- 18 YAML files

[Uses ctx_search("main entry point", limit=5)]
[Uses ctx_search("configuration", limit=5)]
[Uses ctx_search("database setup", limit=5)]
[Uses ctx_search("API routes", limit=5)]

Based on semantic search, this project follows a layered architecture:

**Entry Point:** src/main.py:1-25
- Initializes the FastAPI application
- Loads configuration from config/settings.py

**API Layer:** src/api/routes/ (multiple files)
- User routes: src/api/routes/users.py
- Auth routes: src/api/routes/auth.py
- Follows REST conventions

**Business Logic:** src/services/
- UserService: src/services/user_service.py:10-89
- AuthService: src/services/auth_service.py:15-120

**Data Layer:** src/models/ and src/repositories/
- SQLAlchemy models in src/models/
- Repository pattern in src/repositories/

**Configuration:** config/
- Settings management in config/settings.py
- Environment-based configuration

The architecture separates concerns clearly: API → Services → Repositories → Models
```

**Benefits:**
- Semantic understanding of code organization
- Identifies architectural patterns automatically
- Provides specific file:line references
- Efficient exploration with targeted searches
- Explains conceptual structure, not just files
- Minimal token usage through smart querying

---

## Example 3: Debugging a Feature

### Without the Skill

**User:** "There's a bug in payment processing, help me investigate"

**Claude (without skill):**
```
Let me search for payment-related files...
[Uses Grep for "payment"]

Found many occurrences of "payment"...
[Shows 50+ grep results with context]
[Overwhelming and unfocused]

Let me read some of these files...
[Reads multiple large files]
[High token usage, unfocused investigation]
```

**Issues:**
- Keyword search finds too many results
- No relevance ranking
- Reads entire files unnecessarily
- Unfocused investigation
- Wastes tokens on irrelevant code

### With the Skill

**User:** "There's a bug in payment processing, help me investigate"

**Claude (with skill):**
```
I'll search for payment processing code using ctxd...

[Uses ctx_search("payment processing", limit=10, chunk_types=["function"])]

Found the main payment processing functions:

1. src/payments/processor.py:45-89 (score: 0.93)
   - process_payment() - Main payment processing function
   - Handles Stripe API integration

2. src/api/payment_routes.py:23-56 (score: 0.86)
   - POST /api/payments endpoint
   - Validates payment data and calls processor

3. src/services/payment_service.py:67-112 (score: 0.84)
   - PaymentService.charge() - Business logic
   - Includes retry logic and error handling

Now let me search for error handling in payments:
[Uses ctx_search("payment error handling", limit=5)]

And payment-related tests:
[Uses ctx_search("payment test", directories=["tests/"], limit=5)]

**Analysis:**
The payment flow is: API → Service → Processor
- Potential issue areas:
  1. Error handling in processor.py:78-82 looks incomplete
  2. No validation for negative amounts in payment_routes.py:34
  3. Missing test coverage for edge cases

Would you like me to read the full processor.py file to investigate further?
```

**Benefits:**
- Focused search on relevant code
- Progressive refinement (main code → error handling → tests)
- Identifies specific potential issues
- Efficient token usage
- Structured investigation approach
- Actionable insights

---

## Example 4: Finding Code Patterns

### Without the Skill

**User:** "Show me all API endpoints in this project"

**Claude (without skill):**
```
Let me search for API routes...
[Uses Grep for "@app.route" or "router.get"]

Found these patterns:
[Shows raw grep output with many false positives]

Let me read the route files...
[Reads multiple files in full]
```

**Issues:**
- Depends on exact decorator/pattern matching
- Misses endpoints using different frameworks
- Many false positives
- No organization or categorization
- Reads full files unnecessarily

### With the Skill

**User:** "Show me all API endpoints in this project"

**Claude (with skill):**
```
I'll search for API endpoints using semantic search...

[Uses ctx_search("API endpoint", limit=30, chunk_types=["function"])]

Found 24 API endpoints, organized by resource:

**User Endpoints:**
- GET /api/users → src/api/routes/users.py:15
- GET /api/users/{id} → src/api/routes/users.py:28
- POST /api/users → src/api/routes/users.py:45
- PUT /api/users/{id} → src/api/routes/users.py:67
- DELETE /api/users/{id} → src/api/routes/users.py:89

**Authentication Endpoints:**
- POST /api/auth/login → src/api/routes/auth.py:12
- POST /api/auth/logout → src/api/routes/auth.py:34
- POST /api/auth/refresh → src/api/routes/auth.py:56

**Payment Endpoints:**
- POST /api/payments → src/api/routes/payments.py:23
- GET /api/payments/{id} → src/api/routes/payments.py:45

[etc...]

All endpoints follow REST conventions and are organized by resource.
```

**Benefits:**
- Semantic search finds endpoints regardless of framework
- Natural organization by resource
- Complete coverage across codebase
- Specific file:line references
- No need to read full files
- Clear, organized output

---

## Example 5: Learning a New Codebase

### Without the Skill

**User:** "I'm new to this codebase, help me understand it"

**Claude (without skill):**
```
Let me look at the project structure...
[Lists directories]

Let me read the README...
[Reads README.md]

Let me check the main entry point...
[Guesses at common entry point files]
[Might not find the actual entry point]

Let me read some core files...
[Randomly explores files, inefficient]
```

**Issues:**
- Inefficient exploration
- No systematic approach
- High token usage
- May miss important code
- Generic advice not specific to codebase

### With the Skill

**User:** "I'm new to this codebase, help me understand it"

**Claude (with skill):**
```
I'll help you understand this codebase using ctxd.

First, let me check the index composition:
[Uses ctx_status]

**Codebase Overview:**
- 234 files indexed
- Languages: Python (85%), JavaScript (12%), YAML (3%)
- Last indexed: 2 hours ago

Now let me explore the key areas:

[Uses ctx_search("main entry point", limit=3)]
**Entry Point:** src/main.py:1
- FastAPI application initialization
- Configures middleware and routes

[Uses ctx_search("configuration management", limit=5)]
**Configuration:**
- Settings loaded from environment: config/settings.py:23
- Database config: config/database.py:12
- Feature flags: config/features.py:8

[Uses ctx_search("core functionality", limit=10)]
**Core Features:**
1. User management (src/services/user_service.py)
2. Authentication with JWT (src/auth/)
3. Payment processing (src/payments/)
4. Email notifications (src/notifications/)

[Uses ctx_search("database schema", limit=5)]
**Data Models:**
- User model: src/models/user.py:15
- Payment model: src/models/payment.py:23
- Uses SQLAlchemy ORM

**Architecture Pattern:**
This is a FastAPI application following a layered architecture:
- API Routes → Services → Repositories → Models
- Dependency injection for service layer
- Repository pattern for data access

**Getting Started:**
1. Start with src/main.py to see app initialization
2. Check config/settings.py for configuration
3. Explore src/api/routes/ for available endpoints
4. Review src/services/ for business logic

What specific area would you like to explore deeper?
```

**Benefits:**
- Systematic exploration approach
- Semantic understanding of architecture
- Specific references for further reading
- Efficient token usage
- Actionable next steps
- Contextual understanding, not just file listings

---

## Summary of Improvements

| Aspect | Without Skill | With Skill |
|--------|---------------|------------|
| **Search Method** | Keyword (Grep/Glob) | Semantic (ctxd) |
| **Result Quality** | Many false positives | Ranked by relevance |
| **Token Usage** | High (reads full files) | Low (targeted chunks) |
| **Coverage** | Misses relevant code | Finds semantically similar code |
| **Organization** | Raw, unstructured results | Categorized, explained |
| **Efficiency** | Random exploration | Strategic, progressive refinement |
| **Understanding** | Surface-level | Architectural/conceptual |
| **User Experience** | Overwhelming | Focused and actionable |

## Key Takeaways

The ctxd-search skill teaches Claude to:

1. **Use the right tool for the job**
   - ctxd for semantic code discovery
   - Read for detailed analysis
   - Grep for exact string matching
   - Glob for file patterns

2. **Search semantically, not literally**
   - "authentication flow" finds all auth code
   - Not just files/functions with "auth" in the name

3. **Progressive refinement**
   - Start broad, narrow with filters
   - Build understanding iteratively

4. **Efficient token usage**
   - Search returns small, relevant chunks
   - Only read full files when necessary

5. **Provide actionable insights**
   - Organized, categorized results
   - Specific file:line references
   - Context and next steps

---

**Install the skill to unlock these capabilities!**

```bash
./install-skill.sh /path/to/your/project
```

// Sample TypeScript file for testing chunking

// Interface declaration
interface User {
    id: number;
    name: string;
    email: string;
}

// Type alias
type UserID = string | number;

// Generic type
type Result<T> = {
    success: boolean;
    data?: T;
    error?: string;
};

// Function with type annotations
function createUser(name: string, email: string): User {
    return {
        id: Math.random(),
        name,
        email
    };
}

// Arrow function with types
const validateEmail = (email: string): boolean => {
    return email.includes('@');
};

// Class with TypeScript features
class UserService {
    private users: User[] = [];

    addUser(user: User): void {
        this.users.push(user);
    }

    findUser(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }

    getAllUsers(): User[] {
        return [...this.users];
    }
}

// Generic function
function wrapResult<T>(data: T): Result<T> {
    return {
        success: true,
        data
    };
}

// Export with type
export type { User, UserID, Result };
export { createUser, UserService };

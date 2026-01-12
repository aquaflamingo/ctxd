// Sample JavaScript file for testing chunking

// Standard function declaration
function add(a, b) {
    return a + b;
}

// Arrow function assigned to const
const multiply = (x, y) => {
    return x * y;
};

// Arrow function (single expression)
const square = n => n * n;

// ES6 Class
class Calculator {
    constructor(initialValue = 0) {
        this.value = initialValue;
    }

    // Method definition
    add(n) {
        this.value += n;
        return this;
    }

    subtract(n) {
        this.value -= n;
        return this;
    }

    getResult() {
        return this.value;
    }
}

// Export statement with function
export function divide(a, b) {
    if (b === 0) {
        throw new Error("Division by zero");
    }
    return a / b;
}

// Default export
export default Calculator;

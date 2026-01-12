package calculator

import "fmt"

// Add adds two integers and returns the result
func Add(a, b int) int {
	return a + b
}

// Multiply multiplies two integers
func Multiply(x, y int) int {
	return x * y
}

// Calculator represents a simple calculator
type Calculator struct {
	value int
	name  string
}

// NewCalculator creates a new Calculator instance
func NewCalculator(initialValue int) *Calculator {
	return &Calculator{
		value: initialValue,
		name:  "default",
	}
}

// Add adds a number to the calculator's value (method with pointer receiver)
func (c *Calculator) Add(n int) {
	c.value += n
}

// Subtract subtracts a number from the calculator's value
func (c *Calculator) Subtract(n int) {
	c.value -= n
}

// GetValue returns the current value (method with value receiver)
func (c Calculator) GetValue() int {
	return c.value
}

// Display prints the current value
func (c *Calculator) Display() {
	fmt.Printf("%s: %d\n", c.name, c.value)
}

// Adder interface defines addition behavior
type Adder interface {
	Add(a, b int) int
}

// Multiplier interface for multiplication
type Multiplier interface {
	Multiply(x, y int) int
}

// MathOperator combines multiple interfaces
type MathOperator interface {
	Adder
	Multiplier
}

// Point represents a 2D point
type Point struct {
	X float64
	Y float64
}

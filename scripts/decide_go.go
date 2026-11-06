// decide_go.go: the decision tables of atlas.yaml, answered in Go.
//
// No table is declared here. A caller sends the tables and its questions as one JSON record on stdin,
// and gets the answers as one JSON record on stdout, so Go and decide.py can only differ in how they
// evaluate. A pattern Go's regexp engine cannot compile exits 1 rather than being dropped.
//
// To run: go run decide_go.go < request.json
// To test: go test -v decide_go_test.go decide_go.go

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"regexp"
)

// CommandCategory represents a compiled command pattern with its risk level.
type CommandCategory struct {
	Name    string
	Pattern *regexp.Regexp
	Risk    int
}

// GateCategory maps gate ids to their evaluation cost category.
type GateCategory struct {
	Name  string   `json:"name"`
	Gates []string `json:"gates"`
}

// CommandResult represents the result of command classification.
type CommandResult struct {
	Category string `json:"category"`
	Risk     int    `json:"risk"`
}

// DecisionEngine holds the compiled decision tables. Patterns and gate categories keep their declared
// order, because the first match answers.
type DecisionEngine struct {
	CommandPatterns []CommandCategory
	GateCategories  []GateCategory
	Transitions     map[string]map[string]string
}

// NewDecisionEngine creates an empty decision engine.
func NewDecisionEngine() *DecisionEngine {
	return &DecisionEngine{Transitions: make(map[string]map[string]string)}
}

// AddCommandPattern adds a compiled command pattern to the engine.
func (e *DecisionEngine) AddCommandPattern(name, pattern string, risk int) error {
	compiled, err := regexp.Compile(pattern)
	if err != nil {
		return fmt.Errorf("invalid pattern %q: %w", pattern, err)
	}
	e.CommandPatterns = append(e.CommandPatterns, CommandCategory{Name: name, Pattern: compiled, Risk: risk})
	return nil
}

// AddGateCategory adds a gate category mapping.
func (e *DecisionEngine) AddGateCategory(category string, gates []string) {
	e.GateCategories = append(e.GateCategories, GateCategory{Name: category, Gates: gates})
}

// AddTransition adds a state transition.
func (e *DecisionEngine) AddTransition(state, verdict, nextState string) {
	if e.Transitions[state] == nil {
		e.Transitions[state] = make(map[string]string)
	}
	e.Transitions[state][verdict] = nextState
}

// ClassifyCommand classifies a command against compiled patterns.
// Returns the category and risk level, or ("unknown", -1) if no match.
func (e *DecisionEngine) ClassifyCommand(command string) CommandResult {
	for _, cat := range e.CommandPatterns {
		if cat.Pattern.MatchString(command) {
			return CommandResult{Category: cat.Name, Risk: cat.Risk}
		}
	}
	return CommandResult{Category: "unknown", Risk: -1}
}

// GateCategoryFor returns the category for a gate id, or "unknown" if not found.
func (e *DecisionEngine) GateCategoryFor(gateID string) string {
	for _, category := range e.GateCategories {
		for _, g := range category.Gates {
			if g == gateID {
				return category.Name
			}
		}
	}
	return "unknown"
}

// Transition returns the next state for a given state and verdict, or "" if none is declared.
func (e *DecisionEngine) Transition(state, verdict string) string {
	return e.Transitions[state][verdict]
}

// Request is the record read from stdin: the tables, then the questions.
type Request struct {
	CommandCategories []struct {
		Name    string `json:"name"`
		Pattern string `json:"pattern"`
		Risk    int    `json:"risk"`
	} `json:"command_categories"`
	GateCategories []GateCategory               `json:"gate_categories"`
	Transitions    map[string]map[string]string `json:"transitions"`
	Commands       []string                     `json:"commands"`
	Gates          []string                     `json:"gates"`
	Moves          [][2]string                  `json:"moves"`
}

// Response is the record written to stdout, one answer per question, in order.
type Response struct {
	Commands []CommandResult `json:"commands"`
	Gates    []string        `json:"gates"`
	Moves    []string        `json:"moves"`
}

// Answer builds the engine from the request's tables and answers its questions.
func Answer(req Request) (Response, error) {
	engine := NewDecisionEngine()
	for _, cat := range req.CommandCategories {
		if err := engine.AddCommandPattern(cat.Name, cat.Pattern, cat.Risk); err != nil {
			return Response{}, err
		}
	}
	engine.GateCategories = req.GateCategories
	engine.Transitions = req.Transitions
	resp := Response{Commands: []CommandResult{}, Gates: []string{}, Moves: []string{}}
	for _, command := range req.Commands {
		resp.Commands = append(resp.Commands, engine.ClassifyCommand(command))
	}
	for _, gate := range req.Gates {
		resp.Gates = append(resp.Gates, engine.GateCategoryFor(gate))
	}
	for _, move := range req.Moves {
		resp.Moves = append(resp.Moves, engine.Transition(move[0], move[1]))
	}
	return resp, nil
}

func main() {
	var req Request
	if err := json.NewDecoder(os.Stdin).Decode(&req); err != nil {
		fmt.Fprintln(os.Stderr, "decide_go: unreadable request:", err)
		os.Exit(1)
	}
	resp, err := Answer(req)
	if err != nil {
		fmt.Fprintln(os.Stderr, "decide_go:", err)
		os.Exit(1)
	}
	if err := json.NewEncoder(os.Stdout).Encode(resp); err != nil {
		fmt.Fprintln(os.Stderr, "decide_go:", err)
		os.Exit(1)
	}
}

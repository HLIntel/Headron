// decide_go.go — Compiled decision table evaluation in Go.
//
// This module provides high-speed decision table operations for the Headron decision engine.
// It compiles regex patterns at startup and classifies commands in sub-millisecond time.
//
// To build: go build -o decide_go decide_go.go
// To test: go test -v decide_go_test.go decide_go.go

package main

import (
	"fmt"
	"regexp"
	"strings"
)

// CommandCategory represents a compiled command pattern with its risk level.
type CommandCategory struct {
	Name   string
	Pattern *regexp.Regexp
	Risk   int
}

// GateCategory maps gate ids to their evaluation cost category.
type GateCategory struct {
	Category string
	Gates    []string
}

// Verdict represents a typed categorical verdict.
type Verdict string

const (
	VerdictPass      Verdict = "pass"
	VerdictFail      Verdict = "fail"
	VerdictIsolate   Verdict = "isolate"
	VerdictFastTrack Verdict = "fast_track"
)

// CommandResult represents the result of command classification.
type CommandResult struct {
	Category string
	Risk     int
}

// DecisionEngine holds the compiled decision tables.
type DecisionEngine struct {
	CommandPatterns []CommandCategory
	GateCategories  map[string][]string
	Transitions     map[string]map[string]string
}

// NewDecisionEngine creates a new compiled decision engine.
func NewDecisionEngine() *DecisionEngine {
	return &DecisionEngine{
		GateCategories: make(map[string][]string),
		Transitions:    make(map[string]map[string]string),
	}
}

// AddCommandPattern adds a compiled command pattern to the engine.
func (e *DecisionEngine) AddCommandPattern(name, pattern string, risk int) error {
	compiled, err := regexp.Compile(pattern)
	if err != nil {
		return fmt.Errorf("invalid pattern %q: %w", pattern, err)
	}
	e.CommandPatterns = append(e.CommandPatterns, CommandCategory{
		Name:    name,
		Pattern: compiled,
		Risk:    risk,
	})
	return nil
}

// AddGateCategory adds a gate category mapping.
func (e *DecisionEngine) AddGateCategory(category string, gates []string) {
	e.GateCategories[category] = gates
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
	for category, gates := range e.GateCategories {
		for _, g := range gates {
			if g == gateID {
				return category
			}
		}
	}
	return "unknown"
}

// Transition returns the next state for a given state and verdict.
func (e *DecisionEngine) Transition(state, verdict string) string {
	if transitions, ok := e.Transitions[state]; ok {
		if next, ok := transitions[verdict]; ok {
			return next
		}
	}
	return ""
}

// ClassifyDiff classifies a diff's metadata against all constraints.
// Returns a map of gate names to verdict types.
func (e *DecisionEngine) ClassifyDiff(files []string, astDelta int, depScope string) map[string]string {
	verdicts := make(map[string]string)

	// Check dependency scope
	if depScope == "external" {
		verdicts["dependency_graph"] = string(VerdictFail)
	} else if depScope == "local" {
		verdicts["dependency_graph"] = string(VerdictPass)
	}

	// Check AST delta
	if astDelta > 10 {
		verdicts["code_shape"] = string(VerdictIsolate)
	} else if astDelta > 5 {
		verdicts["code_shape"] = string(VerdictPass)
	}

	// Default pass for classified gates
	for _, gates := range e.GateCategories {
		for _, gate := range gates {
			if _, exists := verdicts[gate]; !exists {
				verdicts[gate] = string(VerdictPass)
			}
		}
	}

	return verdicts
}

// ForbiddenPathTouched checks if a file path matches any forbidden pattern.
func (e *DecisionEngine) ForbiddenPathTouched(filePath string, forbiddenPaths []string) bool {
	for _, fp := range forbiddenPaths {
		if strings.HasPrefix(filePath, fp) {
			return true
		}
	}
	return false
}

// GraphNode represents a node in the knowledge graph.
type GraphNode struct {
	ID     string
	Type   string
	Tags   []string
	Meta   map[string]string
}

// GraphEdge represents a directed edge between nodes.
type GraphEdge struct {
	Source string
	Target string
	Type   string
	Weight float64
}

// KnowledgeGraph represents an in-memory knowledge graph.
type KnowledgeGraph struct {
	Nodes      map[string]GraphNode
	Edges      []GraphEdge
	Adjacency  map[string][]string
	Tags       map[string][]string
}

// NewKnowledgeGraph creates a new empty knowledge graph.
func NewKnowledgeGraph() *KnowledgeGraph {
	return &KnowledgeGraph{
		Nodes:     make(map[string]GraphNode),
		Adjacency: make(map[string][]string),
		Tags:      make(map[string][]string),
	}
}

// AddNode adds a node to the graph.
func (g *KnowledgeGraph) AddNode(node GraphNode) {
	g.Nodes[node.ID] = node
	for _, tag := range node.Tags {
		g.Tags[tag] = append(g.Tags[tag], node.ID)
	}
}

// AddEdge adds a directed edge to the graph.
func (g *KnowledgeGraph) AddEdge(edge GraphEdge) {
	g.Edges = append(g.Edges, edge)
	g.Adjacency[edge.Source] = append(g.Adjacency[edge.Source], edge.Target)
}

// Query returns all adjacent nodes for a given node id.
func (g *KnowledgeGraph) Query(nodeID string) []string {
	return g.Adjacency[nodeID]
}

// GetByTag returns all node ids with a given tag.
func (g *KnowledgeGraph) GetByTag(tag string) []string {
	return g.Tags[tag]
}

// Traverse performs a DFS traversal from the start node.
func (g *KnowledgeGraph) Traverse(start string, maxDepth int) [][]string {
	var paths [][]string
	visited := make(map[string]bool)

	var dfs func(current string, path []string, depth int)
	dfs = func(current string, path []string, depth int) {
		path = append(path, current)
		visited[current] = true

		if depth >= maxDepth {
			paths = append(paths, path)
			return
		}

		adjacent := g.Adjacency[current]
		if len(adjacent) == 0 {
			paths = append(paths, path)
			return
		}

		for _, next := range adjacent {
			if !visited[next] {
				dfs(next, path, depth+1)
			}
		}
	}

	dfs(start, nil, 0)
	return paths
}

func main() {
	engine := NewDecisionEngine()

	// Add command patterns
	engine.AddCommandPattern("safe", `^(git (status|diff|log)|ls|cat|grep)`, 0)
	engine.AddCommandPattern("guarded", `^(git (commit|push|reset)|rm |sed -i)`, 1)
	engine.AddCommandPattern("refused", `^(sudo |curl .*\|)`, 2)

	// Add gate categories
	engine.AddGateCategory("instant", []string{"contract", "context_cost", "code_shape"})
	engine.AddGateCategory("cheap", []string{"format", "lint", "typecheck"})

	// Add transitions
	engine.AddTransition("ingest", "pass", "classify")
	engine.AddTransition("ingest", "fail", "halt")
	engine.AddTransition("classify", "pass", "verify")
	engine.AddTransition("verify", "pass", "exit")

	// Classify commands
	result := engine.ClassifyCommand("git status")
	fmt.Printf("git status: %s (risk %d)\n", result.Category, result.Risk)

	result = engine.ClassifyCommand("git push origin main")
	fmt.Printf("git push: %s (risk %d)\n", result.Category, result.Risk)

	// Gate category lookup
	category := engine.GateCategoryFor("contract")
	fmt.Printf("contract gate: %s\n", category)

	// Transition lookup
	next := engine.Transition("ingest", "pass")
	fmt.Printf("ingest/pass -> %s\n", next)

	// Build knowledge graph
	graph := NewKnowledgeGraph()
	graph.AddNode(GraphNode{ID: "contract", Type: "gate", Tags: []string{"instant", "gate"}})
	graph.AddNode(GraphNode{ID: "format", Type: "gate", Tags: []string{"cheap", "gate"}})
	graph.AddNode(GraphNode{ID: "pass", Type: "verdict", Tags: []string{"verdict"}})
	graph.AddEdge(GraphEdge{Source: "pass", Target: "contract", Type: "enables"})

	// Query graph
	adjacent := graph.Query("pass")
	fmt.Printf("adjacent to pass: %v\n", adjacent)

	// Get by tag
	gates := graph.GetByTag("gate")
	fmt.Printf("gates: %v\n", gates)
}

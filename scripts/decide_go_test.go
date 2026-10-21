// decide_go_test.go — Tests for the Go decision engine.
//
// To run: go test -v decide_go_test.go decide_go.go

package main

import (
	"testing"
)

func TestNewDecisionEngine(t *testing.T) {
	engine := NewDecisionEngine()
	if engine == nil {
		t.Fatal("expected non-nil engine")
	}
	if len(engine.CommandPatterns) != 0 {
		t.Fatal("expected empty command patterns")
	}
}

func TestAddCommandPattern(t *testing.T) {
	engine := NewDecisionEngine()

	err := engine.AddCommandPattern("safe", `^(git (status|diff|log))`, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(engine.CommandPatterns) != 1 {
		t.Fatalf("expected 1 pattern, got %d", len(engine.CommandPatterns))
	}
}

func TestAddCommandPatternInvalid(t *testing.T) {
	engine := NewDecisionEngine()

	err := engine.AddCommandPattern("broken", `([`, 0)
	if err == nil {
		t.Fatal("expected error for invalid pattern")
	}
}

func TestClassifyCommand(t *testing.T) {
	engine := NewDecisionEngine()
	engine.AddCommandPattern("safe", `^(git (status|diff|log))`, 0)
	engine.AddCommandPattern("guarded", `^(git (commit|push))`, 1)

	tests := []struct {
		cmd      string
		category string
		risk     int
	}{
		{"git status", "safe", 0},
		{"git diff", "safe", 0},
		{"git push origin main", "guarded", 1},
		{"unknown command", "unknown", -1},
	}

	for _, tt := range tests {
		result := engine.ClassifyCommand(tt.cmd)
		if result.Category != tt.category {
			t.Errorf("ClassifyCommand(%q) = %s, want %s", tt.cmd, result.Category, tt.category)
		}
		if result.Risk != tt.risk {
			t.Errorf("ClassifyCommand(%q) risk = %d, want %d", tt.cmd, result.Risk, tt.risk)
		}
	}
}

func TestGateCategoryFor(t *testing.T) {
	engine := NewDecisionEngine()
	engine.AddGateCategory("instant", []string{"contract", "context_cost"})
	engine.AddGateCategory("cheap", []string{"format", "lint"})

	tests := []struct {
		gate     string
		category string
	}{
		{"contract", "instant"},
		{"format", "cheap"},
		{"nonexistent", "unknown"},
	}

	for _, tt := range tests {
		got := engine.GateCategoryFor(tt.gate)
		if got != tt.category {
			t.Errorf("GateCategoryFor(%q) = %s, want %s", tt.gate, got, tt.category)
		}
	}
}

func TestTransition(t *testing.T) {
	engine := NewDecisionEngine()
	engine.AddTransition("ingest", "pass", "classify")
	engine.AddTransition("ingest", "fail", "halt")

	tests := []struct {
		state   string
		verdict string
		next    string
	}{
		{"ingest", "pass", "classify"},
		{"ingest", "fail", "halt"},
		{"ingest", "unknown", ""},
		{"unknown", "pass", ""},
	}

	for _, tt := range tests {
		got := engine.Transition(tt.state, tt.verdict)
		if got != tt.next {
			t.Errorf("Transition(%q, %q) = %s, want %s", tt.state, tt.verdict, got, tt.next)
		}
	}
}

func TestClassifyDiff(t *testing.T) {
	engine := NewDecisionEngine()
	engine.AddGateCategory("instant", []string{"contract", "code_shape"})

	// External dependency
	verdicts := engine.ClassifyDiff([]string{"README.md"}, 0, "external")
	if verdicts["dependency_graph"] != "fail" {
		t.Errorf("expected fail for external dep, got %s", verdicts["dependency_graph"])
	}

	// Large AST delta
	verdicts = engine.ClassifyDiff([]string{"README.md"}, 15, "none")
	if verdicts["code_shape"] != "isolate" {
		t.Errorf("expected isolate for large AST, got %s", verdicts["code_shape"])
	}

	// Clean diff
	verdicts = engine.ClassifyDiff([]string{"README.md"}, 3, "none")
	if verdicts["contract"] != "pass" {
		t.Errorf("expected pass for clean diff, got %s", verdicts["contract"])
	}
}

func TestForbiddenPathTouched(t *testing.T) {
	engine := NewDecisionEngine()
	forbidden := []string{"scripts/atlas.py", "config/"}

	tests := []struct {
		path     string
		expected bool
	}{
		{"scripts/atlas.py", true},
		{"scripts/atlas.py.backup", true},
		{"config/settings.yaml", true},
		{"README.md", false},
	}

	for _, tt := range tests {
		got := engine.ForbiddenPathTouched(tt.path, forbidden)
		if got != tt.expected {
			t.Errorf("ForbiddenPathTouched(%q) = %v, want %v", tt.path, got, tt.expected)
		}
	}
}

func TestKnowledgeGraph(t *testing.T) {
	graph := NewKnowledgeGraph()

	// Add nodes
	graph.AddNode(GraphNode{
		ID:   "contract",
		Type: "gate",
		Tags: []string{"instant", "gate"},
	})
	graph.AddNode(GraphNode{
		ID:   "format",
		Type: "gate",
		Tags: []string{"cheap", "gate"},
	})

	// Add edge
	graph.AddEdge(GraphEdge{
		Source: "contract",
		Target: "format",
		Type:   "enables",
	})

	// Query
	adjacent := graph.Query("contract")
	if len(adjacent) != 1 || adjacent[0] != "format" {
		t.Errorf("Query(contract) = %v, want [format]", adjacent)
	}

	// Get by tag
	gates := graph.GetByTag("gate")
	if len(gates) != 2 {
		t.Errorf("GetByTag(gate) = %v, want 2 gates", gates)
	}
}

func TestKnowledgeGraphTraverse(t *testing.T) {
	graph := NewKnowledgeGraph()
	graph.AddNode(GraphNode{ID: "a", Type: "node", Tags: nil})
	graph.AddNode(GraphNode{ID: "b", Type: "node", Tags: nil})
	graph.AddNode(GraphNode{ID: "c", Type: "node", Tags: nil})

	graph.AddEdge(GraphEdge{Source: "a", Target: "b", Type: "enables"})
	graph.AddEdge(GraphEdge{Source: "b", Target: "c", Type: "enables"})

	paths := graph.Traverse("a", 10)
	if len(paths) == 0 {
		t.Error("expected at least one path")
	}

	// First path should contain a, b, c
	path := paths[0]
	if len(path) < 3 {
		t.Errorf("path too short: %v", path)
	}
}

func TestKnowledgeGraphEmpty(t *testing.T) {
	graph := NewKnowledgeGraph()

	adjacent := graph.Query("nonexistent")
	if adjacent != nil {
		t.Errorf("Query(nonexistent) = %v, want nil", adjacent)
	}

	gates := graph.GetByTag("nonexistent")
	if gates != nil {
		t.Errorf("GetByTag(nonexistent) = %v, want nil", gates)
	}
}

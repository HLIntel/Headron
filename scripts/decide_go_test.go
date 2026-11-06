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

func TestAnswerFollowsDeclaredOrder(t *testing.T) {
	req := Request{
		GateCategories: []GateCategory{{Name: "first", Gates: []string{"g"}}, {Name: "second", Gates: []string{"g"}}},
		Gates:          []string{"g"},
		Commands:       []string{"anything"},
		Moves:          [][2]string{{"ingest", "pass"}},
	}
	resp, err := Answer(req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.Gates[0] != "first" {
		t.Errorf("a gate in two categories answered %q, want the first declared", resp.Gates[0])
	}
	if resp.Commands[0].Risk != -1 || resp.Moves[0] != "" {
		t.Errorf("an empty table answered %v and %q", resp.Commands[0], resp.Moves[0])
	}
}

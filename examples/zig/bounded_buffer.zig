//! A fixed-capacity buffer: memory is decided at compile time, and a write past it is an error.
//!
//! The defect this kills: an append that reallocates without limit. A fixed array plus an explicit
//! error.Full means the bound cannot be forgotten by a caller — the compiler makes them handle it.
//!
//! Verify: zig test examples/zig/bounded_buffer.zig

const std = @import("std");

fn Bounded(comptime T: type, comptime capacity: usize) type {
    return struct {
        items: [capacity]T = undefined,
        len: usize = 0,

        const Self = @This();

        fn push(self: *Self, item: T) error{Full}!void {
            if (self.len == capacity) return error.Full;
            self.items[self.len] = item;
            self.len += 1;
        }

        fn slice(self: *const Self) []const T {
            return self.items[0..self.len];
        }
    };
}

test "refuses past capacity, keeps what fit" {
    var buf = Bounded(u8, 2){};
    try buf.push('a');
    try buf.push('b');
    try std.testing.expectError(error.Full, buf.push('c'));
    try std.testing.expectEqualSlices(u8, "ab", buf.slice());
}

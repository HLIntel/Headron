# A queue with a CAPACITY that refuses when full, rather than growing until the node dies.
#
# The defect this kills: an unbounded mailbox or buffer. A producer faster than its consumer
# grows memory without limit, and the failure arrives far from its cause. Refusing at the
# boundary turns an out-of-memory crash into a value the producer must handle.
#
# Verify: elixir examples/elixir/bounded_queue.exs

defmodule BoundedQueue do
  def new(capacity) when capacity > 0, do: %{items: :queue.new(), size: 0, capacity: capacity}

  def push(%{size: size, capacity: capacity}, _item) when size >= capacity, do: {:error, :full}
  def push(q, item), do: {:ok, %{q | items: :queue.in(item, q.items), size: q.size + 1}}

  def pop(%{size: 0}), do: {:error, :empty}

  def pop(q) do
    {{:value, item}, rest} = :queue.out(q.items)
    {:ok, item, %{q | items: rest, size: q.size - 1}}
  end
end

q = BoundedQueue.new(2)
{:ok, q} = BoundedQueue.push(q, :a)
{:ok, q} = BoundedQueue.push(q, :b)
{:error, :full} = BoundedQueue.push(q, :c)
{:ok, :a, q} = BoundedQueue.pop(q)
{:ok, q} = BoundedQueue.push(q, :c)
{:ok, :b, q} = BoundedQueue.pop(q)
{:ok, :c, q} = BoundedQueue.pop(q)
{:error, :empty} = BoundedQueue.pop(q)
IO.puts("bounded_queue: ok")

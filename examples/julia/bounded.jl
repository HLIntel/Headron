# Bounded chunks: 100 items in groups of at most 8, every task joined by @sync.
# Run: julia bounded.jl
function run_bounded(items::Vector{Int}, limit::Int)
    @assert limit >= 1
    done = Vector{Int}(undef, length(items))
    @sync begin
        for (n, chunk) in enumerate(Iterators.partition(items, limit))
            @async begin
                for (k, x) in enumerate(chunk)
                    done[(n - 1) * limit + k] = x * 2
                end
            end
        end
    end
    return done
end

got = run_bounded(collect(1:100), 8)
@assert got == collect(2:2:200)
println("bounded: 1 assertion held — 100 items in chunks of at most 8, every task joined")

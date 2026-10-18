# Bounded chunks: 100 items in groups of at most 8, every item doubled and none lost.
# Run: uiua run --no-format bounded.ua
Items ← +1⇡100
Groups ← ⌊÷8⇡⧻Items
Sizes ← ⊕⧻ Groups Items
⍤"no group holds more than 8" ≤8 /↥ Sizes
⍤"every item is kept" =⧻Items /+ Sizes
⍤"every item is doubled" ≍ ×2 Items ×2+1⇡100
&p "bounded: 3 assertions held — 100 items in groups of at most 8, every item doubled"

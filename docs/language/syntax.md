# Canonical syntax through Milestone 2

```ebnf
program       = { declaration } EOF ;
declaration   = binding | function | record | union ;
binding       = "let" identifier "=" expression ";" ;
function      = "fn" identifier "(" [ parameters ] ")" "->" type block ;
parameters    = parameter { "," parameter } ;
parameter     = identifier ":" type ;
record        = "record" identifier "{" { field "," } "}" ;
field         = identifier ":" type ;
union         = "union" identifier "{" { variant "," } "}" ;
variant       = identifier [ "(" type ")" ] ;
type          = identifier | "Option" "[" type "]"
              | "Result" "[" type "," type "]" ;
block         = "{" { binding } expression "}" ;
expression    = if | match | record-value | precedence-expression ;
if            = "if" expression block "else" block ;
match         = "match" expression "{" { arm "," } "}" ;
arm           = identifier [ "(" identifier ")" ] "=>" expression ;
record-value  = "new" identifier "{" [ field-value { "," field-value } ] "}" ;
field-value   = identifier ":" expression ;
primary       = integer | string | "true" | "false" | "()" | identifier
              | "(" expression ")" ;
suffix        = primary { "(" [ expression { "," expression } ] ")"
              | "." identifier } ;
unary         = ("!" | "-") unary | suffix ;
```

Binary precedence from lowest to highest is `||`, `&&`, `== !=`, `< <= > >=`, `+ -`, and `* /`. Binary operators associate left. Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. Integers are decimal non-negative `i64` source tokens; negative values use unary `-`.

Strings use double quotes and only `\\`, `\"`, `\n`, `\r`, and `\t` escapes. Multiline strings are invalid. The keywords `let`, `fn`, `record`, `union`, `if`, `else`, `match`, `new`, `true`, and `false` cannot be identifiers.

`//` starts a non-semantic line comment. Comments are discarded by canonical formatting and do not affect semantic IDs or semantic content hashes.

Canonical formatting uses two-space indentation, spaces around binary operators and delimiters, no parameter/argument/record-value trailing comma, and required trailing commas for record members, union variants, and match arms. Top-level declarations are separated by one blank line. Redundant grouping is removed while required grouping is emitted.

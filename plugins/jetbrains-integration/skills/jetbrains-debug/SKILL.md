---
name: jetbrains-debug
description: "Use when debugging PHP code with PhpStorm - set breakpoints, step through code, inspect variables, evaluate expressions. Triggers: debug this, set breakpoint, step through, inspect variable, why is this null"
---

# JetBrains Debugger Skill

Debug PHP code using PhpStorm's integrated debugger via CLI.

## Prerequisites

- PhpStorm running with MCP server enabled
- Xdebug configured in PHP environment
- Debug configuration created in PhpStorm

## Quick Reference

| Task | Command |
|------|---------|
| Set breakpoint | `jetbrains-debug bp set <file> <line>` |
| List breakpoints | `jetbrains-debug bp list` |
| Remove breakpoint | `jetbrains-debug bp remove <id>` |
| List configs | `jetbrains-debug configs` |
| Start debugging | `jetbrains-debug start <config>` |
| Stop debugging | `jetbrains-debug stop` |
| Step over | `jetbrains-debug step over` |
| Step into | `jetbrains-debug step into` |
| Step out | `jetbrains-debug step out` |
| Continue | `jetbrains-debug continue` |
| Get variables | `jetbrains-debug vars` |
| Evaluate expression | `jetbrains-debug eval <expr>` |
| Set variable | `jetbrains-debug set <var> <value>` |
| Get stack trace | `jetbrains-debug stack` |
| Get status | `jetbrains-debug status` |

## Standard Debugging Workflow

### 1. Set Breakpoint(s)

```bash
# Set breakpoint at specific line
jetbrains-debug bp set src/Service/PaymentService.php 35

# Conditional breakpoint (only stops when condition is true)
jetbrains-debug bp set src/Service/PaymentService.php 50 --condition "\$amount > 100"

# Logpoint (logs without stopping)
jetbrains-debug bp set src/Service/PaymentService.php 50 --log "Amount is {\$amount}"

# Temporary breakpoint (auto-removes after hit)
jetbrains-debug bp set src/Service/PaymentService.php 30 --temp
```

### 2. List Available Debug Configurations

```bash
jetbrains-debug configs
```

Common configurations:
- `PHP Debug` - Listen for Xdebug connections
- `PHPUnit` - Debug unit tests
- `Main` - Project-specific config

### 3. Start Debug Session

```bash
jetbrains-debug start "PHP Debug"
```

### 4. Trigger the Code

Now trigger the code path you want to debug:
- Make HTTP request to the endpoint
- Run console command
- Execute test

### 5. When Breakpoint Hits

Check current state:
```bash
# Get full debug status (location, variables, stack)
jetbrains-debug status

# Get just variables
jetbrains-debug vars

# Get stack trace
jetbrains-debug stack
```

### 6. Step Through Code

```bash
# Step over - execute current line, stop at next
jetbrains-debug step over

# Step into - enter the function call
jetbrains-debug step into

# Step out - finish current function, stop at caller
jetbrains-debug step out

# Continue - run until next breakpoint
jetbrains-debug continue

# Run to specific line
jetbrains-debug run-to src/Service/PaymentService.php 75
```

### 7. Inspect and Evaluate

```bash
# Evaluate any expression
jetbrains-debug eval "\$this->paymentMethod->getIdentifier()"

# Check specific variable
jetbrains-debug eval "\$paymentTransaction"

# Call methods
jetbrains-debug eval "\$entity->toArray()"

# Modify variable value
jetbrains-debug set amount "150.00"
```

### 8. Stop Session

```bash
jetbrains-debug stop
```

## Common Debugging Scenarios

### Scenario 1: Debug Why Value is Null

```bash
# 1. Find where the value is set (use Serena)
serena refs "ClassName/setProperty" src/Entity/ClassName.php

# 2. Set breakpoint at setter
jetbrains-debug bp set src/Entity/ClassName.php 45

# 3. Start debug and trigger
jetbrains-debug start "PHP Debug"

# 4. When stopped, check call stack
jetbrains-debug stack

# 5. Evaluate the incoming value
jetbrains-debug eval "\$value"
```

### Scenario 2: Debug Failed Payment

```bash
# 1. Set breakpoint in payment method
jetbrains-debug bp set src/Meyer/MollieFixBundle/Decorator/PaymentMethod/MolliePaymentDecorator.php 30

# 2. Start listening
jetbrains-debug start "PHP Debug"

# 3. Make payment attempt in browser

# 4. When stopped, inspect transaction
jetbrains-debug eval "\$paymentTransaction->getResponse()"
jetbrains-debug eval "\$paymentTransaction->isSuccessful()"
```

### Scenario 3: Debug Event Listener

```bash
# 1. Find the listener (use Serena)
serena find CustomerEntityListener --kind class

# 2. Set breakpoint in event method
jetbrains-debug bp set src/Meyer/CustomerBundle/EventListener/CustomerEntityListener.php 50

# 3. Debug
jetbrains-debug start "PHP Debug"

# 4. Trigger entity save that fires the event
```

## Breakpoint Management

```bash
# List all breakpoints
jetbrains-debug bp list

# Remove specific breakpoint
jetbrains-debug bp remove 123456789

# Clear all breakpoints
jetbrains-debug bp clear
```

## Thread Management (for async/queue workers)

```bash
# List all threads
jetbrains-debug threads
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Breakpoint not hit | Xdebug not configured | Check `php.ini` for xdebug settings |
| No debug configs | PhpStorm not configured | Create Run Configuration in PhpStorm |
| Session timeout | Long-running code | Increase Xdebug timeout |
| Can't evaluate | Out of scope | Select correct stack frame first |

### Check Xdebug Status

```bash
# In container
docker exec hmkg-phpfpm php -v | grep -i xdebug
docker exec hmkg-phpfpm php -i | grep xdebug
```

## Integration with Serena

Use Serena for **finding** code, JetBrains Debug for **debugging** it:

```bash
# 1. Find the problematic method (Serena)
serena find processPayment --kind method

# 2. Find all callers (Serena)
serena refs "PaymentService/processPayment" src/Service/PaymentService.php

# 3. Set breakpoint and debug (JetBrains Debug)
jetbrains-debug bp set src/Service/PaymentService.php 45
jetbrains-debug start "PHP Debug"
```

## Integration with JetBrains IDE Tools

Use `jetbrains` CLI for IDE features alongside debugging:

```bash
# Get symbol info
jetbrains symbol src/Service/PaymentService.php 45 20

# Check file for errors
jetbrains problems src/Service/PaymentService.php

# Open file in editor
jetbrains open src/Service/PaymentService.php
```

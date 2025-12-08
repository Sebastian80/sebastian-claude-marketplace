---
name: jetbrains-debug
description: "Use when debugging PHP code with PhpStorm - set breakpoints, step through code, inspect variables, evaluate expressions. Triggers: debug this, set breakpoint, step through, inspect variable, why is this null"
---

# JetBrains Debugger Skill

Debug PHP code using PhpStorm's integrated debugger via MCP.

## Prerequisites

- PhpStorm running with MCP server enabled
- Xdebug configured in PHP environment
- Debug configuration created in PhpStorm

## Quick Reference

| Task | Tool |
|------|------|
| Set breakpoint | `mcp__jetbrains-debugger__set_breakpoint` |
| Start debugging | `mcp__jetbrains-debugger__start_debug_session` |
| Step over (next line) | `mcp__jetbrains-debugger__step_over` |
| Step into (enter function) | `mcp__jetbrains-debugger__step_into` |
| Step out (exit function) | `mcp__jetbrains-debugger__step_out` |
| Continue to next breakpoint | `mcp__jetbrains-debugger__resume_execution` |
| Get all variables | `mcp__jetbrains-debugger__get_variables` |
| Evaluate expression | `mcp__jetbrains-debugger__evaluate_expression` |
| Get stack trace | `mcp__jetbrains-debugger__get_stack_trace` |
| Stop debugging | `mcp__jetbrains-debugger__stop_debug_session` |

## Standard Debugging Workflow

### 1. Set Breakpoint(s)

```bash
# Set breakpoint at specific line
mcp__jetbrains-debugger__set_breakpoint(
    file_path="/home/sebastian/workspace/hmkg/src/Meyer/MollieFixBundle/Decorator/PaymentMethod/MolliePaymentDecorator.php",
    line=35
)

# Conditional breakpoint (only stops when condition is true)
mcp__jetbrains-debugger__set_breakpoint(
    file_path="src/Service/PaymentService.php",
    line=50,
    condition="$amount > 100"
)

# Logpoint (logs without stopping)
mcp__jetbrains-debugger__set_breakpoint(
    file_path="src/Service/PaymentService.php",
    line=50,
    log_message="Amount is {$amount}",
    suspend_policy="none"
)
```

### 2. List Available Debug Configurations

```bash
mcp__jetbrains-debugger__list_run_configurations()
```

Common configurations:
- `PHP Debug` - Listen for Xdebug connections
- `PHPUnit` - Debug unit tests
- `Symfony Console` - Debug console commands

### 3. Start Debug Session

```bash
mcp__jetbrains-debugger__start_debug_session(configuration_name="PHP Debug")
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
mcp__jetbrains-debugger__get_debug_session_status()

# Get just variables
mcp__jetbrains-debugger__get_variables()

# Get stack trace
mcp__jetbrains-debugger__get_stack_trace()
```

### 6. Step Through Code

```bash
# Step over - execute current line, stop at next
mcp__jetbrains-debugger__step_over()

# Step into - enter the function call
mcp__jetbrains-debugger__step_into()

# Step out - finish current function, stop at caller
mcp__jetbrains-debugger__step_out()

# Continue - run until next breakpoint
mcp__jetbrains-debugger__resume_execution()

# Run to specific line (temporary breakpoint)
mcp__jetbrains-debugger__run_to_line(
    file_path="src/Service/PaymentService.php",
    line=75
)
```

### 7. Inspect and Evaluate

```bash
# Evaluate any expression
mcp__jetbrains-debugger__evaluate_expression(expression="$this->paymentMethod->getIdentifier()")

# Check specific variable
mcp__jetbrains-debugger__evaluate_expression(expression="$paymentTransaction")

# Call methods
mcp__jetbrains-debugger__evaluate_expression(expression="$entity->toArray()")

# Modify variable value
mcp__jetbrains-debugger__set_variable(variable_name="amount", new_value="150.00")
```

### 8. Stop Session

```bash
mcp__jetbrains-debugger__stop_debug_session()
```

## Common Debugging Scenarios

### Scenario 1: Debug Why Value is Null

```bash
# 1. Find where the value is set (use Serena)
$SERENA refs "ClassName/setProperty" src/Entity/ClassName.php --all

# 2. Set breakpoint at setter
mcp__jetbrains-debugger__set_breakpoint(file_path="src/Entity/ClassName.php", line=45)

# 3. Start debug and trigger
mcp__jetbrains-debugger__start_debug_session(configuration_name="PHP Debug")

# 4. When stopped, check call stack
mcp__jetbrains-debugger__get_stack_trace()

# 5. Evaluate the incoming value
mcp__jetbrains-debugger__evaluate_expression(expression="$value")
```

### Scenario 2: Debug Failed Payment

```bash
# 1. Set breakpoint in payment method
mcp__jetbrains-debugger__set_breakpoint(
    file_path="src/Meyer/MollieFixBundle/Decorator/PaymentMethod/MolliePaymentDecorator.php",
    line=30
)

# 2. Start listening
mcp__jetbrains-debugger__start_debug_session(configuration_name="PHP Debug")

# 3. Make payment attempt in browser

# 4. When stopped, inspect transaction
mcp__jetbrains-debugger__evaluate_expression(expression="$paymentTransaction->getResponse()")
mcp__jetbrains-debugger__evaluate_expression(expression="$paymentTransaction->isSuccessful()")
```

### Scenario 3: Debug Event Listener

```bash
# 1. Find the listener (use Serena)
$SERENA find CustomerEntityListener --kind class --body --path src/

# 2. Set breakpoint in event method
mcp__jetbrains-debugger__set_breakpoint(
    file_path="src/Meyer/CustomerBundle/EventListener/CustomerEntityListener.php",
    line=50
)

# 3. Debug
mcp__jetbrains-debugger__start_debug_session(configuration_name="PHP Debug")

# 4. Trigger entity save that fires the event
```

## Breakpoint Management

```bash
# List all breakpoints
mcp__jetbrains-debugger__list_breakpoints()

# Remove specific breakpoint
mcp__jetbrains-debugger__remove_breakpoint(breakpoint_id="bp_123")

# Temporary breakpoint (auto-removes after hit)
mcp__jetbrains-debugger__set_breakpoint(
    file_path="src/Service/MyService.php",
    line=30,
    temporary=true
)
```

## Thread Management (for async/queue workers)

```bash
# List all threads
mcp__jetbrains-debugger__list_threads()

# Suspend only current thread (others continue)
mcp__jetbrains-debugger__set_breakpoint(
    file_path="src/Async/MessageHandler.php",
    line=25,
    suspend_policy="thread"
)
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
php -v | grep -i xdebug

# Check config
php -i | grep xdebug
```

## Integration with Serena

Use Serena for **finding** code, JetBrains for **debugging** it:

```bash
# 1. Find the problematic method (Serena)
$SERENA find processPayment --kind method --path src/

# 2. Get its documentation (JetBrains)
mcp__jetbrains__get_symbol_info(filePath="src/Service/PaymentService.php", line=45, column=20)

# 3. Find all callers (Serena)
$SERENA refs "PaymentService/processPayment" src/Service/PaymentService.php

# 4. Set breakpoint and debug (JetBrains)
mcp__jetbrains-debugger__set_breakpoint(file_path="src/Service/PaymentService.php", line=45)
mcp__jetbrains-debugger__start_debug_session(configuration_name="PHP Debug")
```

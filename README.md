# klaimera

Automatic claimer and roller for Mudae, version `0.0.0`.

**WARNING: The current version is primitive and is very volatile stability wise.**
**Do not use it unless you _know_ what you are doing.**

## Requirements

- Poetry
- Python >=3.7

## Commands

### dispatch

**Syntax**: `kmra dispatch`

- `kmra dispatch`  
Lists down all dispatched events

### notify

**Syntax**: `kmra notify (push|alert)`

- `kmra notify push`  
Sends a push notification using notify-run. Silently fails if not registered.
- `kmra notify alert`  
Sounds a notification using the playsound package. Silently fails if `alert.wav` is non
existent.
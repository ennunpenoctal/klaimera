# klaimera

Automatic claimer and roller for Mudae, version `0.0.1`.

> **WARNING: The current version is primitive and is very volatile in terms of stability.**
> **Do not use it unless you _know_ what you are doing. Self-bots are against Discord's**
> **Terms of Service and I am in no way liable for what may be taken upon your account.**
> **_Use this at your own precaution._**

These are neccesary before Klaimera can be bumped to `0.1.0`.

- [ ] Automatic Rolling
  - [ ] Reset Tracking (`SYNC_TIME`)

- [ ] Basic Commands
  - [ ] `dispatch`
    - [x] Listing
    - [ ] Manipulation
  - [ ] `config`
    - [ ] Listing
    - [ ] Manipulation

- [x] Notifications
  - [x] Push
  - [x] Alert

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
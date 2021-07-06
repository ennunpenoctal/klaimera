# klaimera

Automatic claimer and roller for Mudae.

## Requirements

- **Poetry**, alongside basic knowledge of the package.

- **Python 3.7**

## Usage 

- Duplicate `config.toml-TEMPLATE` as `config.toml`
  - Configure as needed

- Prepare the environment
  - Use `poetry shell` to create a virtualenv
  - Use `poetry install` to install needed dependencies

- Run `klaimera.py`

## Command Usage

##### USE THESE IN AN ISOLATED CHANNEL!

### `kmra status`

Replies with a general overview of klaimera, including _uptime_, _dispatched events_,
_last married_.

### `kmra config [ID [set VALUE|add VALUE|rem VALUE]]`

Reads and writes to the config.toml.

**Examples**

- `kmra config`  
Lists most of the configuration file, with the exception of `user.token`.

- `kmra config target.character`  
Replied with `["Yuki Nagato"]`. (Template config.toml)

- `kmra config target.character add "Kiryu Coco"`  
Add `"Kiryu Coco"` to an array.

- `kmra config user.sound set False`  
Set `user.sound` to `False`. 

- `kmra config target.character rem "Kiryu Coco"`  
Reacts with `commands.emojiSuccess` if operation is successful.

### `kmra dispatch [EVENT SECONDS]`

Lists and reschedule dispatches.

Events: `roll`, `reload`, `reset_claim`, `reset_kakera`, `reset_daily`, `sync`, `bench`

**Examples**

- `kmra dispatch`  
Lists all dispatches, alongside their timestamps and datetimes.

- `kmra dispatch roll`  
Similar to the command above, but for the certain event.

- `kmra dispatch roll 0`  
Schedules next roll dispatch in `0` seconds. (Rolls now)

### `kmra notify [push|sound]`

Tests out the push notification/sound alert feature.

**Examples**

- `kmra notify push`  
Sends a push notification using _notify.run_.

- `kmra notify sound`  
Plays an audio alert using _playsound2_.


### `kmra log MESSAGE`

Add a message to the log.

**Example**

- `kmra log Doing something~`  
Logs with level `INFO` `"Doing something~"`.
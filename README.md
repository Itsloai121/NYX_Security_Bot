# Nyx Security Bot

A Discord security bot that watches your server and stops attacks before they destroy it.

---

## Words you should know

| Word | Meaning |
|---|---|
| Nuke | Someone deletes most of the server: channels, roles, or bans everyone. |
| Raid | Many fake or attacker accounts join at once and spam. |
| Webhook | A link that lets outside scripts post into a channel, bypassing normal rules. |
| Token | A hidden key that keeps a Discord account logged in. If stolen, the account is stolen. |
| Modlog | A private staff channel where the bot writes down everything that happens. |

---

## What does the bot do?

### 1. Anti-Nuke — stops server destruction
The bot watches dangerous actions:
- deleting channels
- creating many channels
- deleting roles
- changing role permissions
- creating webhooks
- mass bans
- mass kicks

If one account does these actions too fast, the bot instantly punishes it: remove all roles, kick, or ban (you choose the mode).

### 2. Anti-Raid — stops mass-join attacks
The bot counts how many members join in a few seconds. If joins spike, it locks public channels so raiders cannot post. It unlocks automatically after the time you set.

### 3. Mention-spam blocking
If a message mentions too many people at once (the classic "@everyone scam ping"), the bot deletes the message and times out the sender.

### 4. Modlog — keeps records
Discord's own audit log is limited and expires. This bot sends every important event to a staff-only channel:
- message deletes and edits
- joins, leaves, kicks, bans
- channel and role changes
- webhook creation
- role changes on members

You always know who did what, and when.

### 5. Backup and restore — recovery after an attack
The bot saves a snapshot of your server structure: categories, channels, roles, and permissions. If the server gets nuked, one command rebuilds it.

### 6. Moderation tools
Simple commands for staff: ban, kick, timeout, purge messages, lock and unlock channels.

### 7. Whitelist
Trusted people and roles can be added to a whitelist. The bot will never punish them by mistake.

---

## How does it detect an attack?

The bot counts actions inside a short time window. Example: 2 channel deletes in 10 seconds.

- Normal staff work does not trigger it.
- Fast mass destruction triggers it.

When triggered, the bot:
1. Reads the audit log to find who did it.
2. Skips bots, whitelisted users, and itself.
3. Punishes the account (strip roles / kick / ban).
4. Writes the full event into the modlog as evidence.

The server owner is never auto-punished. Owner actions only raise an alert, because a bot cannot outrank the owner.

---

## Benefits

- Stops a nuke in seconds, not hours.
- Limits raid damage with automatic lockdown.
- Keeps evidence of who did what, even after Discord's audit log expires.
- Rebuilds channels and roles from backup after an attack.
- Catches webhook abuse, one of the most used attack tricks.
- Reduces human error with clear logs and simple commands.
- Works 24/7, with no tired moments.

---

## Commands

| Command | Who can use | What it does |
|---|---|---|
| `!setup #channel` | Admin | Sets the staff-only modlog channel |
| `!antinuke enable` / `!antinuke disable` | Admin | Turns anti-nuke on or off |
| `!antinuke status` | Admin | Shows anti-nuke settings |
| `!antinuke whitelist add @user or @role` | Admin | Exempts a user or role from punishment |
| `!antinuke whitelist remove @user or @role` | Admin | Removes the exemption |
| `!punishment strip\|kick\|ban` | Admin | Chooses the anti-nuke punishment |
| `!antiraid on\|off` | Admin | Turns anti-raid on or off |
| `!joins 10 10` | Admin | Raid trigger: 10 joins in 10 seconds |
| `!mentions 15` | Admin | Mention-spam threshold |
| `!lockdown 10` | Admin | Locks public channels for 10 minutes |
| `!release` | Admin | Unlocks channels now |
| `!ban @user reason` | Staff with Ban | Bans a member |
| `!kick @user reason` | Staff with Kick | Kicks a member |
| `!timeout @user 10 reason` | Staff with Timeout | Times out a member |
| `!purge 50` | Staff with Manage Messages | Deletes last 50 messages |
| `!lock #channel` / `!unlock #channel` | Staff with Manage Channels | Locks or unlocks one channel |
| `!backup create` | Admin | Saves a snapshot of channels and roles |
| `!backup list` | Admin | Shows saved snapshots |
| `!backup restore 3` | Admin | Rebuilds snapshot #3 |
| `!showsettings` | Admin | Shows all current settings |

---

## Setup (short version)

1. Install: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and put in your bot token and owner ID.
3. In the Discord Developer Portal, enable these Privileged Gateway Intents:
   - Server Members Intent
   - Message Content Intent
   - Moderation (Bans) Intent
4. Invite the bot with these permissions: Manage Roles, Manage Channels, Ban Members, Kick Members, Timeout Members, Manage Messages, View Audit Log, Read/Send Messages in the modlog channel.
5. Move the bot's role to the top of the role list.
6. In your server run: `!setup #staff-logs` then `!antinuke enable`.
7. Create a backup now: `!backup create`.

---

## What this bot does NOT do (important)

- It does not protect accounts. Staff still need 2FA, safe passwords, and safe habits. A phished owner account can still destroy the server.
- It does not scan malware files. Discord's Explicit Media Filter only checks explicit images, not viruses or token loggers.
- It does not bring members back after a full server deletion. Member recovery needs a tool like RestoreCord. This bot restores channels and roles only.
- It cannot restore a backup that was never made. Create backups before an attack, not after.

---

## One golden rule

Keep the security bot's role above every other role in the server. If any role sits above it, the bot cannot stop that role.

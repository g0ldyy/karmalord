<h1 align="center" id="title">👑 KarmaLord</h1>
<p align="center"><img src="https://socialify.git.ci/g0ldyy/karmalord/image?description=1&font=Inter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Dark" /></p>
<p align="center">
  <a href="https://ko-fi.com/E1E7ZVMAD">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg">
  </a>
</p>

# 🚀 Features

- ✨ **Multi-Account Management** - Rotate between multiple Reddit accounts
- 🎯 **Target-Based Actions** - Configure specific actions for different users
- 🤖 **Intelligent Automation** - Smart delays and detection avoidance
- 📊 **Real-time Monitoring** - Track actions and success rates
- 🔄 **Session Persistence** - Resume where you left off
- 🚨 **Discord Notifications** - Get updates on actions and errors
- ⚡ **High Performance** - Optimized for speed and reliability
- 🌐 **Proxy Support** - Full proxy rotation with automatic failover
- 🕵️ **Advanced Stealth** - curl_cffi integration with browser impersonation
- 🔒 **TLS Fingerprint Rotation** - Automatic rotation for enhanced anonymity
- ⏱️ **Intelligent Rate Limiting** - Configurable limits with human-like delays

# 🔧 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/g0ldyy/karmalord.git
cd karmalord
```

2. **Install dependencies:**
```bash
pip install uv
uv sync
```

3. **Create configuration files:**
```bash
python main.py --create-config
python main.py --create-samples
```

# 📖 Configuration

## 1. Main Configuration (config.json)

Create the configuration file:
```bash
python main.py --create-config
```

**Example config.json:**
```json
{
  "min_delay_between_actions": 8.0,
  "max_delay_between_actions": 25.0,
  "min_delay_between_accounts": 45.0,
  "max_delay_between_accounts": 180.0,
  "min_delay_between_targets": 30.0,
  "max_delay_between_targets": 90.0,
  "max_actions_per_hour": 8,
  "max_actions_per_day": 35,
  "request_timeout": 45,
  "max_retries": 3,
  "backoff_factor": 2.5,
  "rotate_tls_profiles": true,
  "browser_rotation_hours": 2,
  "check_interval": 300,
  "max_post_age_hours": 48,
  "use_proxy_rotation": true,
  "proxy_list": [
    "http://proxy1.example.com:8080",
    "http://username:password@proxy2.example.com:8080",
    "socks5://127.0.0.1:9050"
  ],
  "log_level": "INFO",
  "log_file": "karmalord.log",
  "save_session_data": true,
  "accounts_file": "accounts.json",
  "targets_file": "targets.json",
  "session_data_file": "session_data.json",
  "discord_webhook_enabled": true,
  "discord_webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
  "discord_notify_on_action": true,
  "discord_notify_on_cycle_complete": true,
  "discord_notify_on_errors": true
}
```

## 2. Reddit App Setup

For each Reddit account:
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill out:
   - **Name**: Your app name
   - **Type**: Select "script"
   - **Redirect URI**: http://localhost:8080
4. Note the `client_id` (under app name) and `client_secret`

## 3. Accounts Configuration (accounts.json)

```json
[
  {
    "username": "your_username_1",
    "password": "your_password_1", 
    "client_id": "your_client_id_1",
    "client_secret": "your_client_secret_1"
  }
]
```

## 4. Targets Configuration (targets.json)

```json
{
  "target_username_1": {
    "action": 1,
    "enabled": true,
    "max_posts": 10,
    "description": "Upvote this user's posts"
  },
  "target_username_2": {
    "action": -1,
    "enabled": true,
    "max_posts": 5,
    "description": "Downvote this user's posts"
  }
}
```

**Action Values:** `1` = Upvote, `-1` = Downvote, `0` = Clear vote

## 5. Discord Webhooks

Get real-time notifications via Discord:

1. **Create a Discord Webhook:**
   - Right-click on channel → "Edit Channel" → "Integrations" → "Webhooks"
   - Click "New Webhook" and copy the URL

2. **Configure notifications:**
   - **🗳️ Vote Actions**: Each upvote/downvote with details
   - **✅ Cycle Complete**: Summary after each check cycle
   - **🚨 Errors**: Immediate alerts for exceptions

## 6. Proxy Configuration

Advanced proxy rotation with automatic failover:

**Supported formats:**
- HTTP: `http://proxy.example.com:8080`
- HTTPS: `https://proxy.example.com:3128`
- SOCKS5: `socks5://proxy.example.com:1080`
- With Auth: `http://username:password@proxy.example.com:8080`

**Features:**
- 🔄 Automatic rotation for each request
- 🛡️ Failover protection with smart retry
- 📊 Real-time monitoring and logging
- 🌐 Multiple protocol support

# 🚀 Usage

## Interactive Mode (Recommended)
```bash
python main.py
```

## Command Line Mode
```bash
# Single check cycle
python main.py -a accounts.json -t targets.json -m single

# Continuous auto-tracking
python main.py -a accounts.json -t targets.json -m auto -i 300

# With custom config
python main.py -c my_config.json -a accounts.json -t targets.json -m single
```

## Creating Files
```bash
python main.py --create-samples  # Create all sample files
python main.py --create-config   # Create configuration file only
```

# 🛡️ Security & Stealth

## Browser Impersonation
- **curl_cffi** for perfect browser mimicking
- Chrome, Firefox, Safari, Edge fingerprints
- Automatic TLS fingerprint rotation
- Real browser headers and behavior

## Rate Limiting & Detection Avoidance
- Conservative action limits (8/hour, 35/day)
- Human-like random delays (8-25 seconds)
- Account rotation with extended delays
- Post age filtering (recent posts only)
- Automatic backoff on rate limits
- Session persistence to avoid duplicates

### Delay Types
- **Between Actions**: Individual vote delays (8-25s) for natural behavior
- **Between Accounts**: Account rotation delays (45-180s) for stealth
- **Between Targets**: User switching delays (30-90s) when processing multiple targets
- Smart delay optimization: no delay if no actions were performed

# ⚙️ Configuration Reference

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `min_delay_between_actions` | 8.0 | 3.0-60.0 | Min delay between actions (seconds) |
| `max_delay_between_actions` | 25.0 | 5.0-120.0 | Max delay between actions (seconds) |
| `min_delay_between_accounts` | 45.0 | 10.0-300.0 | Min delay between account switches (seconds) |
| `max_delay_between_accounts` | 180.0 | 30.0-600.0 | Max delay between account switches (seconds) |
| `min_delay_between_targets` | 30.0 | 5.0-300.0 | Min delay between target users (seconds) |
| `max_delay_between_targets` | 90.0 | 10.0-600.0 | Max delay between target users (seconds) |
| `max_actions_per_hour` | 8 | 1-20 | Max actions per hour per account |
| `max_actions_per_day` | 35 | 5-100 | Max actions per day per account |
| `check_interval` | 300 | 60-3600 | Check interval for new posts (seconds) |
| `rotate_tls_profiles` | true | - | Rotate TLS fingerprints |
| `browser_rotation_hours` | 2 | - | Hours between browser changes |

# 📊 Monitoring & Logs

- **Log file**: `karmalord.log` (configurable)
- **Session data**: `session_data.json` for persistence
- **Real-time console output** with detailed status
- **Configuration validation** via Pydantic

# 🔧 Troubleshooting

## Common Issues

1. **Configuration validation failed**
   - Check JSON syntax and value ranges
   - Use `--create-config` to regenerate

2. **OAuth failed**
   - Verify client_id/client_secret
   - Ensure Reddit app type is "script"

3. **No accounts available**
   - All accounts hit rate limits
   - Wait for reset or increase limits

## Debug Mode
```json
{ "log_level": "DEBUG" }
```

# 🤝 Contributing

Contributions welcome for enhanced stealth features, detection avoidance, and performance optimizations.

# 📄 License

MIT License - See LICENSE file for details.

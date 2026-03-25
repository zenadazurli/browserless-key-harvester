# Browserless Key Harvester

Automated tool to create Browserless.io accounts and harvest API keys during off-peak hours (23:00 - 00:00).

## Deploy on Render

1. Create a new **Cron Job**
2. Connect this repository
3. Set schedule: `0 23 * * *`
4. Add environment variables
5. Deploy!

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_ACCOUNTS_PER_DAY` | `5` | Maximum accounts per day |
| `START_HOUR` | `23` | Start hour (23 = 11 PM) |
| `END_HOUR` | `0` | End hour (0 = midnight) |

## Output

Keys saved in `/tmp/browserless_keys/`:
- `all_keys.txt` - Simple list of API keys
- `accounts.json` - Detailed account info
- `harvester.log` - Execution logs
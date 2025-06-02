import time
import random
import logging
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional, Set
from pathlib import Path

from reddit_client import KarmaLordClient
from config import RedditConfig, load_config


class KarmaLord:
    def __init__(self, config: RedditConfig = None):
        self.config = config or load_config()
        self.accounts: List[KarmaLordClient] = []
        self.targets: Dict[str, Dict] = {}  # username -> action config
        self.current_account_index = 0

        # Tracking data
        self.processed_posts: Dict[
            str, Set[str]
        ] = {}  # account_username -> set of post IDs
        self.last_check_times: Dict[str, datetime] = {}  # Per-user last check
        self.session_stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "posts_processed": 0,
            "start_time": datetime.now(),
            "accounts_active": 0,
        }

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.config.log_file),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger("KarmaLord")

        # Load persistent data
        self._load_session_data()

    def send_discord_notification(
        self,
        message: str,
        color: int = 0x5865F2,
        title: str = None,
        fields: List[Dict] = None,
    ):
        """Send notification to Discord webhook"""
        if (
            not self.config.discord_webhook_enabled
            or not self.config.discord_webhook_url
        ):
            return

        try:
            embed = {
                "title": title or "KarmaLord",
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "KarmaLord"},
            }

            if fields:
                embed["fields"] = fields

            payload = {"username": "KarmaLord", "embeds": [embed]}

            response = requests.post(
                self.config.discord_webhook_url, json=payload, timeout=10
            )

            if response.status_code == 204:
                self.logger.debug("Discord notification sent successfully")
            else:
                self.logger.warning(
                    f"Discord notification failed: {response.status_code}"
                )

        except Exception as e:
            self.logger.error(f"Error sending Discord notification: {e}")

    def load_accounts(self, accounts_file: str = None) -> int:
        """Load accounts from JSON file"""
        file_path = accounts_file or self.config.accounts_file

        try:
            with open(file_path, "r") as f:
                accounts_data = json.load(f)

            loaded_count = 0
            for account_data in accounts_data:
                client = KarmaLordClient(
                    username=account_data["username"],
                    password=account_data["password"],
                    client_id=account_data["client_id"],
                    client_secret=account_data["client_secret"],
                    config=self.config,  # Pass config to client
                )

                if client.connect():
                    self.accounts.append(client)
                    loaded_count += 1
                    self.logger.info(
                        f"Account {account_data['username']} loaded successfully"
                    )

                    # Log proxy stats for the first account to show configuration
                    if loaded_count == 1:
                        proxy_stats = client.get_proxy_stats()
                        if proxy_stats["proxy_rotation_enabled"]:
                            self.logger.info(
                                f"🔄 Proxy rotation enabled: {proxy_stats['total_proxies']} proxies configured"
                            )
                            if proxy_stats["current_proxy"]:
                                self.logger.info(
                                    f"🌐 Using proxy: {proxy_stats['current_proxy']}"
                                )
                            else:
                                self.logger.info(
                                    "🌐 No proxy currently active (fallback to direct)"
                                )
                        else:
                            self.logger.info(
                                "🌐 Proxy rotation disabled - using direct connection"
                            )
                else:
                    self.logger.error(
                        f"Failed to load account {account_data['username']}"
                    )

            self.session_stats["accounts_active"] = loaded_count
            self.logger.info(f"Loaded {loaded_count} accounts from {file_path}")
            return loaded_count

        except Exception as e:
            self.logger.error(f"Error loading accounts: {e}")
            return 0

    def load_targets(self, targets_file: str = None) -> int:
        """Load target users and actions from JSON file"""
        file_path = targets_file or self.config.targets_file

        try:
            with open(file_path, "r") as f:
                self.targets = json.load(f)

            self.logger.info(f"Loaded {len(self.targets)} targets from {file_path}")

            # Log target configuration
            for username, config in self.targets.items():
                action = (
                    "upvote"
                    if config["action"] == 1
                    else "downvote"
                    if config["action"] == -1
                    else "clear"
                )
                self.logger.info(
                    f"Target: u/{username} -> {action} (enabled: {config.get('enabled', True)})"
                )

            return len(self.targets)

        except Exception as e:
            self.logger.error(f"Error loading targets: {e}")
            return 0

    def _load_session_data(self):
        """Load persistent session data"""
        try:
            if Path(self.config.session_data_file).exists():
                with open(self.config.session_data_file, "r") as f:
                    data = json.load(f)

                # Load processed posts to avoid duplicates
                self.processed_posts = {
                    username: set(posts)
                    for username, posts in data.get("processed_posts", {}).items()
                }

                # Load last check times
                last_checks = data.get("last_check_times", {})
                for username, timestamp_str in last_checks.items():
                    self.last_check_times[username] = datetime.fromisoformat(
                        timestamp_str
                    )

                self.logger.info(
                    f"Loaded session data: {sum(len(posts) for posts in self.processed_posts.values())} processed posts"
                )

        except Exception as e:
            self.logger.warning(f"Could not load session data: {e}")

    def _save_session_data(self):
        """Save persistent session data"""
        if not self.config.save_session_data:
            return

        try:
            data = {
                "processed_posts": {
                    username: list(posts)
                    for username, posts in self.processed_posts.items()
                },
                "last_check_times": {
                    username: timestamp.isoformat()
                    for username, timestamp in self.last_check_times.items()
                },
                "session_stats": self.get_session_stats(),
                "saved_at": datetime.now().isoformat(),
            }

            with open(self.config.session_data_file, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            self.logger.error(f"Error saving session data: {e}")

    def _get_next_account(self) -> Optional[KarmaLordClient]:
        """Get next available account with rotation"""
        if not self.accounts:
            return None

        attempts = 0
        while attempts < len(self.accounts):
            account = self.accounts[self.current_account_index]

            if account.can_perform_action(
                self.config.max_actions_per_hour, self.config.max_actions_per_day
            ):
                return account

            # Rotate to next account
            self.current_account_index = (self.current_account_index + 1) % len(
                self.accounts
            )
            attempts += 1

        self.logger.warning("No accounts available for actions")
        return None

    def _wait_stealth_delay(self, min_delay: float = None, max_delay: float = None):
        """Wait with random delay for stealth"""
        min_d = min_delay or self.config.min_delay_between_actions
        max_d = max_delay or self.config.max_delay_between_actions

        delay = random.uniform(min_d, max_d)
        self.logger.debug(f"Stealth delay: {delay:.2f}s")
        time.sleep(delay)

    def check_and_process_user(self, username: str, target_config: Dict) -> Dict:
        """Check a user for new posts and process them"""
        if not target_config.get("enabled", True):
            return {"skipped": True, "reason": "disabled"}

        self.logger.info(f"Checking user: u/{username}")

        # Get an account to fetch posts
        fetch_account = self._get_next_account()
        if not fetch_account:
            return {"error": "no_accounts_available"}

        # Get recent posts
        posts = fetch_account.get_user_posts(
            username=username,
            limit=target_config.get("max_posts", 25),
            max_age_hours=self.config.max_post_age_hours,
        )

        results = {
            "username": username,
            "posts_found": len(posts),
            "posts_processed": 0,
            "successful_votes": 0,
            "failed_votes": 0,
            "skipped_posts": 0,
        }

        action = target_config["action"]
        action_name = (
            "upvote" if action == 1 else "downvote" if action == -1 else "clear"
        )

        for i, post in enumerate(posts):
            # Check if all accounts have already processed this post
            all_accounts_processed = all(
                post.id in self.processed_posts.get(acc.username, set())
                for acc in self.accounts
            )

            if all_accounts_processed:
                results["skipped_posts"] += 1
                continue

            # For each post, try to vote with ALL accounts
            for account_index, voting_account in enumerate(self.accounts):
                # Skip if this account can't perform actions (rate limits)
                if not voting_account.can_perform_action(
                    self.config.max_actions_per_hour, self.config.max_actions_per_day
                ):
                    self.logger.debug(
                        f"Account {voting_account.username} rate limited, skipping"
                    )
                    continue

                # Skip if already processed by this voting account
                if post.id in self.processed_posts.get(voting_account.username, set()):
                    self.logger.debug(
                        f"Post {post.id} already processed by {voting_account.username}, skipping"
                    )
                    continue

                # Perform vote
                if voting_account.vote_post(post.id, action):
                    results["successful_votes"] += 1
                    self.session_stats["successful_actions"] += 1
                    self.logger.info(
                        f"Successfully {action_name}d post: {post.title[:50]}... (by {voting_account.username})"
                    )

                    # Send Discord notification for action
                    if self.config.discord_notify_on_action:
                        color = (
                            0x00FF00
                            if action == 1
                            else 0xFF6B6B
                            if action == -1
                            else 0x95A5A6
                        )
                        action_emoji = (
                            "⬆️" if action == 1 else "⬇️" if action == -1 else "🔄"
                        )

                        # Ensure we have a complete Reddit URL
                        post_url = post.permalink
                        if not post_url.startswith("http"):
                            post_url = f"https://reddit.com{post.permalink}"

                        fields = [
                            {"name": "User", "value": f"u/{username}", "inline": True},
                            {
                                "name": "Action",
                                "value": f"{action_emoji} {action_name.title()}",
                                "inline": True,
                            },
                            {
                                "name": "Account",
                                "value": f"u/{voting_account.username}",
                                "inline": True,
                            },
                            {
                                "name": "Post",
                                "value": f"[{post.title[:50]}...]({post_url})",
                                "inline": False,
                            },
                        ]

                        self.send_discord_notification(
                            f"Successfully {action_name}d a post by u/{username}",
                            color=color,
                            title=f"{action_emoji} Vote Action Completed",
                            fields=fields,
                        )
                else:
                    results["failed_votes"] += 1
                    self.session_stats["failed_actions"] += 1

                    # Send Discord notification for failed action
                    if self.config.discord_notify_on_errors:
                        self.send_discord_notification(
                            f"❌ Failed to {action_name} post by u/{username}: {post.title[:50]}... (account: {voting_account.username})",
                            color=0xFF0000,
                            title="🚨 Vote Action Failed",
                        )

                # Mark as processed by this voting account
                self.processed_posts.setdefault(voting_account.username, set()).add(
                    post.id
                )
                self.session_stats["total_actions"] += 1

                # Stealth delay between votes from the same account
                if (
                    account_index < len(self.accounts) - 1
                ):  # Not the last account for this post
                    self._wait_stealth_delay()

            # Count this post as processed (at least attempted by all accounts)
            results["posts_processed"] += 1
            self.session_stats["posts_processed"] += 1

            # Longer delay between posts
            if i < len(posts) - 1:  # Not the last post
                self._wait_stealth_delay(
                    self.config.min_delay_between_accounts,
                    self.config.max_delay_between_accounts,
                )

        # Update last check time
        self.last_check_times[username] = datetime.now()

        self.logger.info(f"Processed u/{username}: {results}")
        return results

    def run_single_check(self) -> Dict:
        """Run a single check cycle for all targets"""
        self.logger.info("Starting check cycle...")

        cycle_results = {
            "cycle_start": datetime.now().isoformat(),
            "users_checked": 0,
            "total_posts_processed": 0,
            "total_votes_cast": 0,
            "errors": 0,
        }

        targets_list = list(self.targets.items())
        total_targets = len(targets_list)

        for target_index, (username, target_config) in enumerate(targets_list):
            try:
                result = self.check_and_process_user(username, target_config)

                if "error" in result:
                    cycle_results["errors"] += 1
                    self.logger.error(
                        f"Error processing u/{username}: {result['error']}"
                    )

                    # Send Discord notification for processing error
                    if self.config.discord_notify_on_errors:
                        self.send_discord_notification(
                            f"❌ Error processing u/{username}: {result['error']}",
                            color=0xFF0000,
                            title="🚨 User Processing Error",
                        )
                elif not result.get("skipped", False):
                    cycle_results["users_checked"] += 1
                    cycle_results["total_posts_processed"] += result["posts_processed"]
                    cycle_results["total_votes_cast"] += result["successful_votes"]

                # Delay between users for stealth (but only if actions were performed and not the last target)
                if target_index < total_targets - 1:  # Not the last target
                    # Check if any actual actions were performed
                    actions_performed = result.get("successful_votes", 0) + result.get(
                        "failed_votes", 0
                    )

                    if actions_performed > 0:
                        self.logger.debug(
                            f"Stealth delay before next target ({target_index + 1}/{total_targets}) - {actions_performed} actions performed"
                        )
                        self._wait_stealth_delay(
                            self.config.min_delay_between_targets,
                            self.config.max_delay_between_targets,
                        )
                    else:
                        self.logger.debug(
                            f"No actions performed for u/{username}, skipping stealth delay"
                        )

            except Exception as e:
                self.logger.error(f"Exception processing u/{username}: {e}")
                cycle_results["errors"] += 1

                # Send Discord notification for exception
                if self.config.discord_notify_on_errors:
                    self.send_discord_notification(
                        f"💥 Exception while processing u/{username}: {str(e)}",
                        color=0xFF0000,
                        title="🚨 Processing Exception",
                    )

        # Save session data after each cycle
        self._save_session_data()

        cycle_results["cycle_end"] = datetime.now().isoformat()
        self.logger.info(f"Check cycle completed: {cycle_results}")

        # Send Discord notification for cycle completion
        if self.config.discord_notify_on_cycle_complete:
            duration = datetime.fromisoformat(
                cycle_results["cycle_end"]
            ) - datetime.fromisoformat(cycle_results["cycle_start"])
            duration_str = str(duration).split(".")[0]  # Remove microseconds

            fields = [
                {
                    "name": "👥 Users Checked",
                    "value": str(cycle_results["users_checked"]),
                    "inline": True,
                },
                {
                    "name": "📝 Posts Processed",
                    "value": str(cycle_results["total_posts_processed"]),
                    "inline": True,
                },
                {
                    "name": "🗳️ Votes Cast",
                    "value": str(cycle_results["total_votes_cast"]),
                    "inline": True,
                },
                {
                    "name": "⚠️ Errors",
                    "value": str(cycle_results["errors"]),
                    "inline": True,
                },
                {"name": "⏱️ Duration", "value": duration_str, "inline": True},
                {
                    "name": "📊 Success Rate",
                    "value": f"{self.get_session_stats()['success_rate']:.1f}%",
                    "inline": True,
                },
            ]

            color = 0x00FF00 if cycle_results["errors"] == 0 else 0xFFA500
            emoji = "✅" if cycle_results["errors"] == 0 else "⚠️"

            self.send_discord_notification(
                "Check cycle completed successfully!",
                color=color,
                title=f"{emoji} Cycle Complete",
                fields=fields,
            )

        return cycle_results

    def start_auto_tracking(self, check_interval: int = None):
        """Start automatic tracking loop"""
        interval = check_interval or self.config.check_interval

        self.logger.info(f"Starting auto-tracking with {interval}s interval")

        while True:
            try:
                self.run_single_check()

                # Wait for next cycle
                self.logger.info(f"Waiting {interval}s until next check...")
                time.sleep(interval)

            except KeyboardInterrupt:
                self.logger.info("Auto-tracking stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in tracking loop: {e}")
                # Wait before retrying
                time.sleep(60)

    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        duration = datetime.now() - self.session_stats["start_time"]

        return {
            **self.session_stats,
            "start_time": self.session_stats[
                "start_time"
            ].isoformat(),  # Convert datetime to ISO string
            "session_duration": str(duration),
            "success_rate": (
                self.session_stats["successful_actions"]
                / max(self.session_stats["total_actions"], 1)
                * 100
            ),
            "processed_posts_count": sum(
                len(posts) for posts in self.processed_posts.values()
            ),
            "targets_count": len(self.targets),
        }

    def cleanup(self):
        """Clean up connections and save data"""
        self.logger.info("Cleaning up...")

        # Save final session data
        self._save_session_data()

        # Disconnect all accounts
        for account in self.accounts:
            account.disconnect()

        self.logger.info("Cleanup completed")

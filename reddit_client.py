import time
import random
import logging
import base64
import json
from datetime import datetime, timedelta
from typing import List, Optional
from curl_cffi import requests
from dataclasses import dataclass


@dataclass
class RedditPost:
    """Represents a Reddit post"""

    id: str
    title: str
    author: str
    created_utc: float
    score: int
    subreddit: str
    permalink: str
    is_self: bool


@dataclass
class AccountStats:
    """Statistics for account usage"""

    actions_today: int = 0
    actions_this_hour: int = 0
    last_action_time: Optional[datetime] = None
    last_hour_reset: Optional[datetime] = None
    last_day_reset: Optional[datetime] = None
    total_votes_cast: int = 0


class KarmaLordClient:
    """
    Advanced Reddit client for karma manipulation and automation
    """

    # Browser versions for rotation
    BROWSERS = ["chrome", "firefox", "safari", "edge"]

    def __init__(
        self,
        username: str,
        password: str,
        client_id: str,
        client_secret: str,
        config=None,
    ):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.config = config
        self.stats = AccountStats()

        # Session and auth
        self.session = None
        self.access_token = None
        self.token_expires = None

        # Stealth features
        self.current_browser = random.choice(self.BROWSERS)
        self.last_browser_change = datetime.now()

        # Proxy management
        self.current_proxy_index = 0
        self.current_proxy = None
        self.failed_proxies = set()

        # Timestamps
        now = datetime.now()
        self.stats.last_hour_reset = now
        self.stats.last_day_reset = now

        self.logger = logging.getLogger(f"StealthClient.{username}")

    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy from the list, handling rotation and failures"""
        if (
            not self.config
            or not self.config.use_proxy_rotation
            or not self.config.proxy_list
        ):
            return None

        available_proxies = [
            proxy
            for proxy in self.config.proxy_list
            if proxy not in self.failed_proxies
        ]

        if not available_proxies:
            # If all proxies failed, reset failed set and try again
            self.logger.warning("All proxies failed, resetting failed proxy list")
            self.failed_proxies.clear()
            available_proxies = self.config.proxy_list.copy()

        if not available_proxies:
            return None

        # Rotate to next proxy
        self.current_proxy_index = (self.current_proxy_index + 1) % len(
            available_proxies
        )
        return available_proxies[self.current_proxy_index]

    def _mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed"""
        if proxy:
            self.failed_proxies.add(proxy)
            self.logger.warning(f"Marking proxy as failed: {proxy}")

    def _rotate_browser(self):
        """Rotate browser impersonation periodically"""
        rotation_hours = self.config.browser_rotation_hours if self.config else 2

        if datetime.now() - self.last_browser_change > timedelta(hours=rotation_hours):
            old_browser = self.current_browser
            self.current_browser = random.choice(self.BROWSERS)
            self.last_browser_change = datetime.now()
            self.logger.debug(
                f"Browser rotated: {old_browser} -> {self.current_browser}"
            )

            # Create new session with new browser
            if self.session:
                self.session.close()
            self._create_session()

    def _create_session(self):
        """Create a new session with stealth features"""
        timeout = self.config.request_timeout if self.config else 45

        # Determine proxy to use
        proxy = None
        if self.config and self.config.use_proxy_rotation and self.config.proxy_list:
            proxy = self._get_next_proxy()
            if proxy:
                self.current_proxy = proxy
                self.logger.info(f"Using proxy: {proxy}")
            else:
                self.logger.info("No proxy available, using direct connection")

        # Create session with or without proxy
        try:
            if proxy:
                self.session = requests.Session(
                    impersonate=self.current_browser,
                    timeout=timeout,
                    proxies={"http": proxy, "https": proxy},
                )
            else:
                self.session = requests.Session(
                    impersonate=self.current_browser, timeout=timeout
                )
                self.current_proxy = None
        except Exception as e:
            self.logger.error(f"Failed to create session with proxy {proxy}: {e}")
            if proxy:
                self._mark_proxy_failed(proxy)
                # Fallback to no proxy
                self.session = requests.Session(
                    impersonate=self.current_browser, timeout=timeout
                )
                self.current_proxy = None

    def _get_oauth_token(self) -> bool:
        """Get OAuth token for API access with proxy retry logic"""
        max_retries = self.config.max_retries if self.config else 3

        for attempt in range(max_retries):
            try:
                if not self.session:
                    self._create_session()

                # Prepare auth
                auth_str = base64.b64encode(
                    f"{self.client_id}:{self.client_secret}".encode()
                ).decode()

                headers = {
                    "Authorization": f"Basic {auth_str}",
                    "User-Agent": f"RedditApp/1.0 by {self.username}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                data = {
                    "grant_type": "password",
                    "username": self.username,
                    "password": self.password,
                }

                response = self.session.post(
                    "https://www.reddit.com/api/v1/access_token",
                    headers=headers,
                    data=data,
                )

                self.logger.debug(f"OAuth response status: {response.status_code}")
                self.logger.debug(f"OAuth response text: {response.text}")

                if response.status_code == 200:
                    try:
                        token_data = response.json()
                        self.logger.debug(f"Token data keys: {list(token_data.keys())}")

                        if "access_token" not in token_data:
                            self.logger.error(
                                f"Missing access_token in response: {token_data}"
                            )
                            return False

                        self.access_token = token_data["access_token"]
                        self.token_expires = datetime.now() + timedelta(
                            seconds=token_data["expires_in"] - 300
                        )
                        self.logger.info(f"OAuth token obtained for {self.username}")
                        return True
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.error(f"Error parsing OAuth response: {e}")
                        self.logger.error(f"Response content: {response.text}")
                        return False
                else:
                    self.logger.error(
                        f"OAuth failed: {response.status_code} - {response.text}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)  # Exponential backoff
                        continue
                    return False

            except Exception as e:
                error_msg = str(e).lower()
                is_proxy_error = any(
                    keyword in error_msg
                    for keyword in [
                        "proxy",
                        "connection",
                        "timeout",
                        "unreachable",
                        "refused",
                    ]
                )

                self.logger.error(f"OAuth error (attempt {attempt + 1}): {e}")
                self.logger.error(f"Exception type: {type(e).__name__}")

                # If it's a proxy error and we're using a proxy, try to switch
                if is_proxy_error and self.current_proxy:
                    self.logger.warning(
                        f"OAuth proxy error detected with {self.current_proxy}"
                    )
                    self._mark_proxy_failed(self.current_proxy)

                    # Try to create a new session with a different proxy or no proxy
                    try:
                        if self.session:
                            self.session.close()
                        self._create_session()
                        self.logger.info(
                            "Created new session for OAuth after proxy failure"
                        )

                        # Retry immediately with new session
                        continue
                    except Exception as session_error:
                        self.logger.error(
                            f"Failed to create new session for OAuth: {session_error}"
                        )

                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
                return False

        return False

    def _ensure_token_valid(self) -> bool:
        """Ensure we have a valid token"""
        if not self.access_token or (
            self.token_expires and datetime.now() >= self.token_expires
        ):
            return self._get_oauth_token()
        return True

    def _api_request(
        self, endpoint: str, method: str = "GET", data: dict = None
    ) -> Optional[dict]:
        """Make authenticated API request with proxy retry logic"""
        if not self._ensure_token_valid():
            return None

        # Only rotate browser if config allows it
        if self.config and self.config.rotate_tls_profiles:
            self._rotate_browser()

        # Determine content type based on endpoint
        is_form_data = endpoint in ["/api/vote", "/api/submit", "/api/comment"]

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": f"RedditApp/1.0 by {self.username}",
        }

        # Set appropriate content type
        if method.upper() == "POST" and data:
            if is_form_data:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                headers["Content-Type"] = "application/json"

        url = f"https://oauth.reddit.com/{endpoint.lstrip('/')}"

        max_retries = self.config.max_retries if self.config else 3
        backoff_factor = self.config.backoff_factor if self.config else 2.5

        for attempt in range(max_retries):
            try:
                if method.upper() == "POST":
                    if is_form_data:
                        # Send as form data for voting and similar actions
                        response = self.session.post(url, headers=headers, data=data)
                    else:
                        # Send as JSON for other requests
                        response = self.session.post(
                            url, headers=headers, json=data if data else {}
                        )
                else:
                    response = self.session.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    wait_time = (backoff_factor**attempt) * 5
                    self.logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.warning(
                        f"API request failed: {response.status_code} - {endpoint}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(backoff_factor**attempt)
                        continue
                    return None

            except Exception as e:
                error_msg = str(e).lower()
                is_proxy_error = any(
                    keyword in error_msg
                    for keyword in [
                        "proxy",
                        "connection",
                        "timeout",
                        "unreachable",
                        "refused",
                    ]
                )

                self.logger.error(f"API request error (attempt {attempt + 1}): {e}")

                # If it's a proxy error and we're using a proxy, try to switch
                if is_proxy_error and self.current_proxy:
                    self.logger.warning(
                        f"Proxy error detected with {self.current_proxy}"
                    )
                    self._mark_proxy_failed(self.current_proxy)

                    # Try to create a new session with a different proxy or no proxy
                    try:
                        if self.session:
                            self.session.close()
                        self._create_session()
                        self.logger.info("Created new session after proxy failure")

                        # Retry immediately with new session
                        continue
                    except Exception as session_error:
                        self.logger.error(
                            f"Failed to create new session: {session_error}"
                        )

                if attempt < max_retries - 1:
                    time.sleep(backoff_factor**attempt)
                    continue
                return None

        return None

    def connect(self) -> bool:
        """Establish connection and authenticate"""
        try:
            self._create_session()

            # Test connection with OAuth
            if not self._get_oauth_token():
                return False

            # Verify by getting user info
            user_data = self._api_request("/api/v1/me")
            if user_data and user_data.get("name"):
                self.logger.info(f"Successfully connected as {user_data['name']}")
                return True
            else:
                self.logger.error("Failed to verify user identity")
                return False

        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    def _reset_counters_if_needed(self):
        """Reset action counters if needed"""
        now = datetime.now()

        # Reset hourly counter
        if now - self.stats.last_hour_reset >= timedelta(hours=1):
            self.stats.actions_this_hour = 0
            self.stats.last_hour_reset = now

        # Reset daily counter
        if now - self.stats.last_day_reset >= timedelta(days=1):
            self.stats.actions_today = 0
            self.stats.last_day_reset = now

    def can_perform_action(self, max_hourly: int, max_daily: int) -> bool:
        """Check if account can perform an action"""
        self._reset_counters_if_needed()

        if self.stats.actions_this_hour >= max_hourly:
            self.logger.warning(f"Hourly limit reached ({max_hourly})")
            return False

        if self.stats.actions_today >= max_daily:
            self.logger.warning(f"Daily limit reached ({max_daily})")
            return False

        return True

    def record_action(self):
        """Record that an action was performed"""
        now = datetime.now()
        self.stats.actions_this_hour += 1
        self.stats.actions_today += 1
        self.stats.last_action_time = now
        self.stats.total_votes_cast += 1

        self.logger.info(
            f"Action recorded. Today: {self.stats.actions_today}, "
            f"This hour: {self.stats.actions_this_hour}"
        )

    def get_user_posts(
        self, username: str, limit: int = 25, max_age_hours: int = 48
    ) -> List[RedditPost]:
        """Get recent posts from a user"""
        try:
            # Get user's submissions
            data = self._api_request(
                f"/user/{username}/submitted.json?limit={limit}&sort=new"
            )

            if not data or "data" not in data:
                self.logger.warning(f"No data found for user {username}")
                return []

            posts = []
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

            for item in data["data"]["children"]:
                post_data = item["data"]

                # Skip if too old
                if post_data["created_utc"] < cutoff_time:
                    continue

                post = RedditPost(
                    id=post_data["id"],
                    title=post_data["title"],
                    author=post_data["author"],
                    created_utc=post_data["created_utc"],
                    score=post_data["score"],
                    subreddit=post_data["subreddit"],
                    permalink=post_data["permalink"],
                    is_self=post_data["is_self"],
                )
                posts.append(post)

            self.logger.info(f"Retrieved {len(posts)} recent posts from u/{username}")
            return posts

        except Exception as e:
            self.logger.error(f"Error getting posts for {username}: {e}")
            return []

    def vote_post(self, post_id: str, direction: int) -> bool:
        """
        Vote on a post
        direction: 1 for upvote, -1 for downvote, 0 to clear vote
        """
        try:
            # Prepare vote data - Reddit expects form data, not JSON
            vote_data = {"id": f"t3_{post_id}", "dir": str(direction), "rank": "1"}

            self.logger.debug(f"Voting on post {post_id} with direction {direction}")
            self.logger.debug(f"Vote data: {vote_data}")

            # Make vote request with form data
            if not self._ensure_token_valid():
                self.logger.error("No valid token for voting")
                return False

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": f"RedditApp/1.0 by {self.username}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            url = "https://oauth.reddit.com/api/vote"

            self.logger.debug(f"Making vote request to: {url}")

            response = self.session.post(
                url,
                headers=headers,
                data=vote_data,  # Use data instead of json
            )

            self.logger.debug(f"Vote response status: {response.status_code}")
            self.logger.debug(f"Vote response text: {response.text}")

            if response.status_code == 200:
                action = (
                    "upvoted"
                    if direction == 1
                    else "downvoted"
                    if direction == -1
                    else "cleared vote on"
                )
                self.logger.info(f"Successfully {action} post {post_id}")
                self.record_action()
                return True
            else:
                self.logger.error(
                    f"Vote failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error voting on post {post_id}: {e}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            return False

    def disconnect(self):
        """Close connection"""
        if self.session:
            self.session.close()
        self.access_token = None
        self.logger.info("Connection closed")

    def get_proxy_stats(self) -> dict:
        """Get proxy usage statistics"""
        if not self.config or not self.config.use_proxy_rotation:
            return {
                "proxy_rotation_enabled": False,
                "current_proxy": None,
                "total_proxies": 0,
                "failed_proxies": 0,
                "working_proxies": 0,
            }

        total_proxies = len(self.config.proxy_list)
        failed_proxies = len(self.failed_proxies)
        working_proxies = total_proxies - failed_proxies

        return {
            "proxy_rotation_enabled": True,
            "current_proxy": self.current_proxy,
            "total_proxies": total_proxies,
            "failed_proxies": failed_proxies,
            "working_proxies": working_proxies,
            "failed_proxy_list": list(self.failed_proxies),
        }

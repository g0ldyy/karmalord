import json
import argparse
from pathlib import Path
from manager import KarmaLord
from config import load_config, save_default_config


def create_sample_accounts_file():
    """Create sample accounts configuration file"""
    sample_accounts = [
        {
            "username": "your_username_1",
            "password": "your_password_1",
            "client_id": "YOUR_CLIENT_ID_1",
            "client_secret": "YOUR_CLIENT_SECRET_1",
        },
        {
            "username": "your_username_2",
            "password": "your_password_2",
            "client_id": "YOUR_CLIENT_ID_2",
            "client_secret": "YOUR_CLIENT_SECRET_2",
        },
    ]

    with open("accounts.json", "w") as f:
        json.dump(sample_accounts, f, indent=4)

    print("📁 Created accounts.json")
    print("   Edit with your real account credentials")


def create_sample_targets_file():
    """Create sample targets configuration file"""
    sample_targets = {
        "target_username_1": {
            "action": 1,  # 1 for upvote, -1 for downvote, 0 for clear
            "enabled": True,
            "max_posts": 10,
            "description": "Upvote this user's posts",
        },
        "target_username_2": {
            "action": -1,
            "enabled": True,
            "max_posts": 5,
            "description": "Downvote this user's posts",
        },
        "target_username_3": {
            "action": 1,
            "enabled": False,  # Disabled target
            "max_posts": 15,
            "description": "Disabled target (will be skipped)",
        },
    }

    with open("targets.json", "w") as f:
        json.dump(sample_targets, f, indent=4)

    print("📁 Created targets.json")
    print("   Configure target users and actions")


def interactive_mode():
    """Interactive mode for the stealth tracker"""
    print("\n👑 KarmaLord - Interactive Mode")
    print("=" * 55)

    # Load configuration
    config_file = input("⚙️  Config file (config.json): ") or "config.json"
    config = load_config(config_file)

    tracker = KarmaLord(config)

    # Load accounts
    accounts_file = (
        input(f"📁 Accounts file ({config.accounts_file}): ") or config.accounts_file
    )

    if not Path(accounts_file).exists():
        print(f"❌ File {accounts_file} not found.")
        create_sample = input("Create sample file? (y/n): ")
        if create_sample.lower() == "y":
            create_sample_accounts_file()
        return

    accounts_loaded = tracker.load_accounts(accounts_file)
    if accounts_loaded == 0:
        print("❌ No valid accounts loaded.")
        return

    print(f"✅ Loaded {accounts_loaded} accounts successfully.")

    # Load targets
    targets_file = (
        input(f"🎯 Targets file ({config.targets_file}): ") or config.targets_file
    )

    if not Path(targets_file).exists():
        print(f"❌ File {targets_file} not found.")
        create_sample = input("Create sample targets file? (y/n): ")
        if create_sample.lower() == "y":
            create_sample_targets_file()
        return

    targets_loaded = tracker.load_targets(targets_file)
    if targets_loaded == 0:
        print("❌ No targets loaded.")
        return

    print(f"✅ Loaded {targets_loaded} targets successfully.")

    # Show current configuration
    print("\n⚙️  Current Configuration:")
    print(
        f"   Delay between actions: {config.min_delay_between_actions}-{config.max_delay_between_actions}s"
    )
    print(f"   Max actions per hour: {config.max_actions_per_hour}")
    print(f"   Max actions per day: {config.max_actions_per_day}")
    print(f"   Check interval: {config.check_interval}s")
    print(f"   Browser rotation: {config.rotate_tls_profiles}")

    while True:
        print("\n📋 Available options:")
        print("1. Run single check cycle")
        print("2. Start auto-tracking loop")
        print("3. View session statistics")
        print("4. View current configuration")
        print("5. Save session data")
        print("6. Exit")

        choice = input("\nChoice (1-6): ")

        if choice == "1":
            print("\n🔄 Running single check cycle...")
            results = tracker.run_single_check()
            print("✅ Cycle completed:")
            print(f"   Users checked: {results['users_checked']}")
            print(f"   Posts processed: {results['total_posts_processed']}")
            print(f"   Votes cast: {results['total_votes_cast']}")
            print(f"   Errors: {results['errors']}")

        elif choice == "2":
            interval = input(
                f"⏱️  Check interval in seconds ({config.check_interval}): "
            )
            try:
                interval = int(interval) if interval else config.check_interval
            except ValueError:
                interval = config.check_interval

            print(f"\n🚀 Starting auto-tracking (interval: {interval}s)")
            print("   Press Ctrl+C to stop...")
            tracker.start_auto_tracking(interval)

        elif choice == "3":
            stats = tracker.get_session_stats()
            print("\n📊 Session Statistics:")
            print(f"   Total actions: {stats['total_actions']}")
            print(f"   Successful: {stats['successful_actions']}")
            print(f"   Failed: {stats['failed_actions']}")
            print(f"   Success rate: {stats['success_rate']:.1f}%")
            print(f"   Posts processed: {stats['posts_processed']}")
            print(f"   Session duration: {stats['session_duration']}")
            print(f"   Active accounts: {stats['accounts_active']}")
            print(f"   Targets: {stats['targets_count']}")

        elif choice == "4":
            print("\n⚙️  Current Configuration:")
            print(f"   Config file: {config_file}")
            print(f"   Min delay between actions: {config.min_delay_between_actions}s")
            print(f"   Max delay between actions: {config.max_delay_between_actions}s")
            print(
                f"   Min delay between accounts: {config.min_delay_between_accounts}s"
            )
            print(
                f"   Max delay between accounts: {config.max_delay_between_accounts}s"
            )
            print(f"   Max actions per hour: {config.max_actions_per_hour}")
            print(f"   Max actions per day: {config.max_actions_per_day}")
            print(f"   Check interval: {config.check_interval}s")
            print(f"   Max post age: {config.max_post_age_hours}h")
            print(f"   Browser rotation: {config.rotate_tls_profiles}")
            print(f"   Log level: {config.log_level}")

        elif choice == "5":
            tracker._save_session_data()
            print("💾 Session data saved.")

        elif choice == "6":
            break

        else:
            print("❌ Invalid choice.")

    tracker.cleanup()
    print("\n👋 Goodbye!")


def command_line_mode(args):
    """Command line mode"""
    config = load_config(args.config) if args.config else load_config()
    tracker = KarmaLord(config)

    # Load accounts
    accounts_loaded = tracker.load_accounts(args.accounts)
    if accounts_loaded == 0:
        print("❌ No valid accounts loaded.")
        return

    print(f"✅ Loaded {accounts_loaded} accounts.")

    # Load targets
    targets_loaded = tracker.load_targets(args.targets)
    if targets_loaded == 0:
        print("❌ No targets loaded.")
        return

    print(f"✅ Loaded {targets_loaded} targets.")

    # Execute action
    if args.mode == "single":
        print("\n🔄 Running single check cycle...")
        results = tracker.run_single_check()
        print(f"✅ Completed: {results['total_votes_cast']} votes cast")

    elif args.mode == "auto":
        print(f"\n🚀 Starting auto-tracking (interval: {args.interval}s)")
        print("   Press Ctrl+C to stop...")
        tracker.start_auto_tracking(args.interval)

    if args.save_data:
        tracker._save_session_data()
        print("💾 Session data saved.")

    tracker.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="KarmaLord",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  Interactive mode:
    python main.py

  Command line - single check:
    python main.py -a accounts.json -t targets.json -m single

  Command line - auto tracking:
    python main.py -a accounts.json -t targets.json -m auto -i 300

  Create sample files:
    python main.py --create-samples

  Create configuration files:
    python main.py --create-config
        """,
    )

    parser.add_argument("-c", "--config", help="Configuration file (JSON)")
    parser.add_argument("-a", "--accounts", help="JSON file containing Reddit accounts")
    parser.add_argument(
        "-t", "--targets", help="JSON file containing target users and actions"
    )
    parser.add_argument(
        "-m", "--mode", choices=["single", "auto"], help="Execution mode"
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=300,
        help="Check interval for auto mode in seconds (default: 300)",
    )
    parser.add_argument("--save-data", action="store_true", help="Save session data")
    parser.add_argument(
        "--create-samples",
        action="store_true",
        help="Create sample configuration files",
    )
    parser.add_argument(
        "--create-config", action="store_true", help="Create configuration files"
    )

    args = parser.parse_args()

    # Create sample files if requested
    if args.create_samples:
        create_sample_accounts_file()
        create_sample_targets_file()
        return

    # Create config files if requested
    if args.create_config:
        save_default_config()
        print("\n✅ Configuration file created: config.json")
        print("\n📝 Edit to customize settings")
        return

    # Command line mode if all required arguments provided
    if args.accounts and args.targets and args.mode:
        command_line_mode(args)
    else:
        # Interactive mode by default
        interactive_mode()


if __name__ == "__main__":
    main()

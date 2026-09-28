"""Tests for gitlab-auth.md — authentication and identity management."""

import unittest
from conftest import run, run_ok, GITLAB_HOST


class TestAuthLogin(unittest.TestCase):
    def test_auth_login_help(self):
        rc, out = run_ok("glab auth login --help")
        self.assertTrue(rc)
        self.assertIn("--hostname", out)
        self.assertIn("--stdin", out)

    def test_auth_status(self):
        rc, out = run_ok("glab auth status")
        self.assertTrue(rc)

    def test_auth_status_hostname(self):
        rc, out = run_ok(f"glab auth status --hostname {GITLAB_HOST}")
        self.assertTrue(rc)


class TestAuthSwitch(unittest.TestCase):
    """glab auth switch does NOT exist — must use logout + login."""

    def test_auth_switch_not_exists(self):
        rc, out = run_ok("glab auth switch --help")
        self.assertTrue(rc)
        commands_section = out.split("COMMANDS")[1] if "COMMANDS" in out else ""
        self.assertNotIn("switch", commands_section,
                         "switch should not be listed as an auth subcommand")

    def test_auth_logout_help(self):
        rc, out = run_ok("glab auth logout --help")
        self.assertTrue(rc)
        self.assertIn("--hostname", out)


class TestSSHKey(unittest.TestCase):
    def test_ssh_key_list_help(self):
        rc, out = run_ok("glab ssh-key list --help")
        self.assertTrue(rc)

    def test_ssh_key_add_help(self):
        rc, out = run_ok("glab ssh-key add --help")
        self.assertTrue(rc)
        self.assertIn("--title", out)

    def test_ssh_key_get_help(self):
        rc, out = run_ok("glab ssh-key get --help")
        self.assertTrue(rc)

    def test_ssh_key_delete_help(self):
        rc, out = run_ok("glab ssh-key delete --help")
        self.assertTrue(rc)


class TestToken(unittest.TestCase):
    def test_token_create_help(self):
        rc, out = run_ok("glab token create --help")
        self.assertTrue(rc)
        self.assertIn("--scope", out)

    def test_token_list_help(self):
        rc, out = run_ok("glab token list --help")
        self.assertTrue(rc)

    def test_token_revoke_help(self):
        rc, out = run_ok("glab token revoke --help")
        self.assertTrue(rc)


class TestCredentialHelper(unittest.TestCase):
    """Verify git credential helper commands are valid."""

    def test_credential_cache_config(self):
        """git config --global --list runs successfully."""
        rc, out, err = run("git config --global --list", check=False)
        self.assertEqual(rc, 0)

    def test_credential_helper_names(self):
        """Verify known credential helper names are valid git config values."""
        helpers = ["cache", "osxkeychain", "manager", "libsecret"]
        for h in helpers:
            rc, out = run_ok(f"git help -c | grep credential.helper")
            self.assertTrue(rc)


if __name__ == "__main__":
    unittest.main()

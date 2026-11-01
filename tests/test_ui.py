import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "src" / "ui.py"


class StreamlitAppTests(unittest.TestCase):
    def test_new_session_resets_messages_and_thread(self) -> None:
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        original_thread_id = app.session_state["thread_id"]
        app.session_state["messages"] = [{"role": "user", "content": "Earlier question"}]

        app.button[0].click().run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["messages"], [])
        self.assertNotEqual(app.session_state["thread_id"], original_thread_id)

    def test_agent_failure_is_safe_and_recorded_in_chat(self) -> None:
        with (
            patch("src.orchestrator.agent.stream", side_effect=RuntimeError("sensitive details")),
            patch("src.audit.write_audit_log") as write_audit_log,
        ):
            app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
            app.chat_input[0].set_value("Find high-risk shipments").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertNotIn("sensitive details", app.error[0].value)
        self.assertEqual(app.session_state["messages"][-1]["role"], "assistant")
        self.assertIn("could not complete", app.session_state["messages"][-1]["content"])
        self.assertTrue(
            any(
                call.kwargs["node_name"] == "agent_error" for call in write_audit_log.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
